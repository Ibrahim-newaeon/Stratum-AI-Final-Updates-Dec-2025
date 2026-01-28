# =============================================================================
# Stratum AI - CDP (Customer Data Platform) Tasks
# =============================================================================
"""
Background tasks for CDP segment computation, RFM analysis, and funnels.

Security: Beat-scheduled tasks use distributed locks to prevent
duplicate execution across multiple Celery workers.
"""

from datetime import UTC, datetime
from typing import Any, Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.db.session import SyncSessionLocal
from app.workers.celery_app import with_distributed_lock
from app.workers.tasks.helpers import publish_event

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def compute_cdp_segment(self, tenant_id: int, segment_id: str):
    """
    Compute membership for a CDP segment.

    Args:
        tenant_id: Tenant ID for isolation
        segment_id: Segment ID to compute
    """
    logger.info(f"Computing segment {segment_id} for tenant {tenant_id}")

    # Import CDP models here to avoid circular imports
    from app.models.cdp import CDPProfile, CDPSegment

    with SyncSessionLocal() as db:
        segment = db.execute(
            select(CDPSegment).where(
                CDPSegment.tenant_id == tenant_id,
                CDPSegment.id == segment_id,
            )
        ).scalar_one_or_none()

        if not segment:
            logger.warning(f"Segment {segment_id} not found")
            return {"status": "not_found"}

        # Get all profiles for tenant
        profiles = (
            db.execute(
                select(CDPProfile).where(
                    CDPProfile.tenant_id == tenant_id,
                    CDPProfile.is_deleted == False,
                )
            )
            .scalars()
            .all()
        )

        # Evaluate segment rules against each profile
        matched_profiles = []
        for profile in profiles:
            result = _evaluate_segment_rules(profile, segment.rules)
            if result["matched"]:
                matched_profiles.append(profile.id)

        # Update segment membership
        segment.profile_ids = matched_profiles
        segment.profile_count = len(matched_profiles)
        segment.last_computed_at = datetime.now(UTC)

        db.commit()

        publish_event(
            tenant_id,
            "segment_computed",
            {
                "segment_id": segment_id,
                "segment_name": segment.name,
                "profile_count": len(matched_profiles),
            },
        )

    logger.info(f"Segment {segment_id}: {len(matched_profiles)} profiles matched")
    return {"profile_count": len(matched_profiles)}


def _evaluate_segment_rules(profile, rules: dict[str, Any]) -> dict[str, Any]:
    """Evaluate segment rules against a profile."""
    if not rules:
        return {"matched": True, "reason": "no_rules"}

    conditions = rules.get("conditions", [])
    operator = rules.get("operator", "AND")

    results = []
    for condition in conditions:
        matched = _evaluate_condition_single(profile, condition)
        results.append(matched)

    if operator == "AND":
        return {"matched": all(results), "results": results}
    else:  # OR
        return {"matched": any(results), "results": results}


def _evaluate_condition_single(profile, condition: dict[str, Any]) -> bool:
    """Evaluate a single condition against a profile."""
    field = condition.get("field")
    op = condition.get("operator")
    value = condition.get("value")

    # Get field value from profile
    if "." in field:
        # Nested field (e.g., "traits.lifetime_value")
        parts = field.split(".")
        actual = profile
        for part in parts:
            if hasattr(actual, part):
                actual = getattr(actual, part)
            elif isinstance(actual, dict):
                actual = actual.get(part)
            else:
                return False
    else:
        actual = getattr(profile, field, None)

    if actual is None:
        return False

    # Evaluate condition
    if op == "equals":
        return actual == value
    elif op == "not_equals":
        return actual != value
    elif op == "greater_than":
        return float(actual) > float(value)
    elif op == "less_than":
        return float(actual) < float(value)
    elif op == "contains":
        return str(value).lower() in str(actual).lower()
    elif op == "in":
        return actual in value

    return False


@shared_task
@with_distributed_lock(timeout=3600)  # 1 hour lock timeout
def compute_all_cdp_segments(tenant_id: Optional[int] = None):
    """
    Compute all CDP segments for a tenant or all tenants.
    Scheduled hourly by Celery beat.

    Uses distributed lock to prevent duplicate execution across workers.
    """
    logger.info("Computing all CDP segments")

    from app.models import Tenant
    from app.models.cdp import CDPSegment

    with SyncSessionLocal() as db:
        if tenant_id:
            tenants = [
                db.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()
            ]
        else:
            tenants = db.execute(select(Tenant).where(Tenant.is_deleted == False)).scalars().all()

        task_count = 0
        for tenant in tenants:
            if not tenant:
                continue

            segments = (
                db.execute(
                    select(CDPSegment).where(
                        CDPSegment.tenant_id == tenant.id,
                        CDPSegment.is_active == True,
                    )
                )
                .scalars()
                .all()
            )

            for segment in segments:
                compute_cdp_segment.delay(tenant.id, str(segment.id))
                task_count += 1

    logger.info(f"Queued {task_count} segment computation tasks")
    return {"tasks_queued": task_count}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def compute_cdp_rfm(self, tenant_id: int, config: Optional[dict] = None):
    """
    Compute RFM (Recency, Frequency, Monetary) scores for all profiles.

    Args:
        tenant_id: Tenant ID for isolation
        config: Optional RFM configuration overrides
    """
    logger.info(f"Computing RFM scores for tenant {tenant_id}")

    from app.ml.rfm_segmenter import RFMSegmenter
    from app.models.cdp import CDPProfile

    with SyncSessionLocal() as db:
        profiles = (
            db.execute(
                select(CDPProfile).where(
                    CDPProfile.tenant_id == tenant_id,
                    CDPProfile.is_deleted == False,
                )
            )
            .scalars()
            .all()
        )

        if not profiles:
            return {"status": "no_profiles"}

        segmenter = RFMSegmenter(tenant_id)
        results = segmenter.compute_rfm_scores(profiles, config)

        # Update profiles with RFM scores
        for profile in profiles:
            rfm = results.get(str(profile.id))
            if rfm:
                profile.rfm_recency = rfm["recency"]
                profile.rfm_frequency = rfm["frequency"]
                profile.rfm_monetary = rfm["monetary"]
                profile.rfm_segment = rfm["segment"]
                profile.rfm_score = rfm["score"]

        db.commit()

        publish_event(
            tenant_id,
            "rfm_computed",
            {
                "profiles_scored": len(results),
                "segment_distribution": results.get("distribution", {}),
            },
        )

    logger.info(f"Computed RFM for {len(results)} profiles")
    return {"profiles_scored": len(results)}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def compute_cdp_traits(self, tenant_id: int, trait_id: Optional[str] = None):
    """
    Compute computed traits for CDP profiles.

    Args:
        tenant_id: Tenant ID for isolation
        trait_id: Optional specific trait to compute (all if None)
    """
    logger.info(f"Computing CDP traits for tenant {tenant_id}")

    from app.models.cdp import CDPComputedTrait, CDPProfile

    with SyncSessionLocal() as db:
        # Get trait definitions
        traits_query = select(CDPComputedTrait).where(
            CDPComputedTrait.tenant_id == tenant_id,
            CDPComputedTrait.is_active == True,
        )
        if trait_id:
            traits_query = traits_query.where(CDPComputedTrait.id == trait_id)

        traits = db.execute(traits_query).scalars().all()

        if not traits:
            return {"status": "no_traits"}

        profiles = (
            db.execute(
                select(CDPProfile).where(
                    CDPProfile.tenant_id == tenant_id,
                    CDPProfile.is_deleted == False,
                )
            )
            .scalars()
            .all()
        )

        computed_count = 0
        for profile in profiles:
            for trait in traits:
                try:
                    value = _compute_trait_value(db, profile, trait)
                    profile.computed_traits = profile.computed_traits or {}
                    profile.computed_traits[trait.name] = value
                    computed_count += 1
                except Exception as e:
                    logger.error(f"Trait {trait.name} failed for profile {profile.id}: {e}")

        db.commit()

    logger.info(f"Computed {computed_count} trait values")
    return {"computed": computed_count}


def _compute_trait_value(db, profile, trait) -> Any:
    """Compute a single trait value for a profile."""
    formula = trait.formula or {}
    trait_type = formula.get("type")

    if trait_type == "count":
        # Count events of a certain type
        event_type = formula.get("event_type")
        # Implementation would query events table
        return 0

    elif trait_type == "sum":
        # Sum a field from events
        field = formula.get("field")
        return 0

    elif trait_type == "last":
        # Get last value of a field
        field = formula.get("field")
        return getattr(profile, field, None)

    elif trait_type == "first":
        # Get first value of a field
        field = formula.get("field")
        return getattr(profile, field, None)

    return None


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=2,
)
def compute_cdp_funnel(self, tenant_id: int, funnel_id: str):
    """
    Compute conversion funnel metrics.

    Args:
        tenant_id: Tenant ID for isolation
        funnel_id: Funnel definition ID
    """
    logger.info(f"Computing funnel {funnel_id} for tenant {tenant_id}")

    from app.models.cdp import CDPFunnel

    with SyncSessionLocal() as db:
        funnel = db.execute(
            select(CDPFunnel).where(
                CDPFunnel.tenant_id == tenant_id,
                CDPFunnel.id == funnel_id,
            )
        ).scalar_one_or_none()

        if not funnel:
            return {"status": "not_found"}

        # Compute funnel metrics
        steps = funnel.steps or []
        results = {
            "funnel_id": funnel_id,
            "steps": [],
            "overall_conversion": 0,
        }

        previous_count = 0
        for i, step in enumerate(steps):
            # Count profiles that completed this step
            # Implementation would query events
            count = 0  # Placeholder
            conversion = (count / previous_count * 100) if previous_count > 0 else 100

            results["steps"].append(
                {
                    "step": i + 1,
                    "name": step.get("name"),
                    "count": count,
                    "conversion": round(conversion, 2),
                }
            )
            previous_count = count

        # Update funnel with results
        funnel.last_computed_at = datetime.now(UTC)
        funnel.metrics = results

        db.commit()

        publish_event(
            tenant_id,
            "funnel_computed",
            {
                "funnel_id": funnel_id,
                "funnel_name": funnel.name,
            },
        )

    return results


@shared_task
@with_distributed_lock(timeout=7200)  # 2 hour lock timeout
def compute_all_cdp_funnels(tenant_id: Optional[int] = None):
    """
    Compute all CDP funnels for a tenant or all tenants.
    Scheduled daily by Celery beat.

    Uses distributed lock to prevent duplicate execution across workers.
    """
    logger.info("Computing all CDP funnels")

    from app.models import Tenant
    from app.models.cdp import CDPFunnel

    with SyncSessionLocal() as db:
        if tenant_id:
            tenants = [
                db.execute(select(Tenant).where(Tenant.id == tenant_id)).scalar_one_or_none()
            ]
        else:
            tenants = db.execute(select(Tenant).where(Tenant.is_deleted == False)).scalars().all()

        task_count = 0
        for tenant in tenants:
            if not tenant:
                continue

            funnels = (
                db.execute(
                    select(CDPFunnel).where(
                        CDPFunnel.tenant_id == tenant.id,
                        CDPFunnel.is_active == True,
                    )
                )
                .scalars()
                .all()
            )

            for funnel in funnels:
                compute_cdp_funnel.delay(tenant.id, str(funnel.id))
                task_count += 1

    logger.info(f"Queued {task_count} funnel computation tasks")
    return {"tasks_queued": task_count}
