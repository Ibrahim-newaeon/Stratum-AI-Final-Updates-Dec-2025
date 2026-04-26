# =============================================================================
# Stratum AI - Launch Readiness Phase Catalog
# =============================================================================
"""
Fixed catalog of go-live phases and their checklist items for the Launch
Readiness wizard (superadmin-only).

Phases run sequentially: phase N+1 is locked until phase N is 100 percent
complete. The catalog is static in v1; only per-item state (checked / by
whom / when) is persisted to the database.

Each item has:
- key: stable snake_case identifier, unique within its phase
- title: short label shown in the UI
- description: longer guidance; optional

Adding or renaming an item is a code change that ships via deploy.
"""

from typing import List, TypedDict


class LaunchReadinessItemDef(TypedDict, total=False):
    key: str
    title: str
    description: str


class LaunchReadinessPhaseDef(TypedDict):
    number: int
    slug: str
    title: str
    description: str
    items: List[LaunchReadinessItemDef]


LAUNCH_READINESS_PHASES: List[LaunchReadinessPhaseDef] = [
    {
        "number": 1,
        "slug": "foundation",
        "title": "Foundation",
        "description": "GCP organization, projects, DNS, IAM, VPC, and infrastructure-as-code baseline.",
        "items": [
            {"key": "gcp_org_created", "title": "Dedicated GCP Organization created"},
            {"key": "projects_provisioned", "title": "Prod / staging / shared projects provisioned"},
            {"key": "domain_registered", "title": "Production domain registered"},
            {"key": "cloud_dns_zone", "title": "Cloud DNS managed zone configured"},
            {"key": "org_policies_enabled", "title": "Org policies enabled (uniform bucket access, restrict SA keys, no public IPs)"},
            {"key": "security_command_center", "title": "Security Command Center enabled (Standard tier)"},
            {"key": "audit_logs_enabled", "title": "Cloud Audit Logs + VPC Flow Logs enabled"},
            {"key": "iam_groups_configured", "title": "IAM groups configured via Cloud Identity"},
            {"key": "workload_identity_federation", "title": "Workload Identity Federation set up for GitHub Actions"},
            {"key": "service_accounts_created", "title": "Per-workload service accounts created (api, worker, scheduler, migrate)"},
            {"key": "vpc_created", "title": "VPC with private subnets + Private Google Access"},
            {"key": "cloud_nat_configured", "title": "Cloud NAT configured for egress"},
            {"key": "static_ip_reserved", "title": "Static external IP reserved for HTTPS Load Balancer"},
            {"key": "terraform_repo", "title": "Terraform repository initialised for infra-as-code"},
        ],
    },
    {
        "number": 2,
        "slug": "data-layer",
        "title": "Data Layer",
        "description": "Cloud SQL for PostgreSQL, Memorystore for Redis, backups, and migrations.",
        "items": [
            {"key": "cloud_sql_provisioned", "title": "Cloud SQL PostgreSQL 16 regional (HA) provisioned"},
            {"key": "cloud_sql_private_ip", "title": "Cloud SQL configured with private IP only"},
            {"key": "cloud_sql_auth_proxy", "title": "Cloud SQL Auth Proxy configured as workload sidecar"},
            {"key": "automated_backups", "title": "Automated daily backups, 30-day retention"},
            {"key": "pitr_enabled", "title": "Point-in-Time Recovery enabled"},
            {"key": "cross_region_backup", "title": "Cross-region backup copy to DR region"},
            {"key": "db_flags_tuned", "title": "DB flags tuned (shared_buffers, effective_cache_size, work_mem)"},
            {"key": "pgbouncer_deployed", "title": "PgBouncer connection pool deployed"},
            {"key": "memorystore_provisioned", "title": "Memorystore Redis 7 Standard tier (HA) provisioned"},
            {"key": "redis_tls_auth", "title": "Redis AUTH + in-transit TLS enabled"},
            {"key": "redis_logical_dbs_verified", "title": "Redis 3-database topology verified (cache / broker / results)"},
            {"key": "alembic_rehearsal", "title": "`alembic upgrade head` rehearsed against Cloud SQL clone"},
            {"key": "migration_rollbacks_documented", "title": "Rollback path documented for every risky migration"},
            {"key": "pg_dump_to_gcs", "title": "Scheduled pg_dump to GCS with lifecycle to Archive class"},
        ],
    },
    {
        "number": 3,
        "slug": "container-platform",
        "title": "Container Platform",
        "description": "Artifact Registry, GKE Autopilot, Load Balancer, CDN, and Cloud Armor.",
        "items": [
            {"key": "artifact_registry_created", "title": "Artifact Registry repository created (multi-region)"},
            {"key": "image_build_pipeline", "title": "Image build pipeline pushes to Artifact Registry on git SHA"},
            {"key": "gke_autopilot_cluster", "title": "GKE Autopilot cluster provisioned"},
            {"key": "private_control_plane", "title": "Private control plane + authorized networks configured"},
            {"key": "workload_identity_enabled", "title": "Workload Identity enabled on the cluster"},
            {"key": "binary_authorization", "title": "Binary Authorization requires signed images"},
            {"key": "manifests_deployed", "title": "Deployment manifests applied (api, worker, scheduler)"},
            {"key": "hpa_configured", "title": "HorizontalPodAutoscaler on api + worker (custom metrics)"},
            {"key": "network_policies", "title": "Default-deny NetworkPolicies applied"},
            {"key": "migrations_as_job", "title": "Alembic migrations run as a Kubernetes Job (not on api startup)"},
            {"key": "health_probes", "title": "Liveness + readiness probes on `/health`"},
            {"key": "sql_auth_proxy_sidecar", "title": "Cloud SQL Auth Proxy sidecar on DB-bound pods"},
            {"key": "frontend_bucket_deployed", "title": "Frontend built + deployed to GCS bucket"},
            {"key": "https_load_balancer", "title": "HTTPS Load Balancer with URL map (GCS backend + GKE NEG)"},
            {"key": "managed_ssl_cert", "title": "Google-managed SSL certificate attached"},
            {"key": "cloud_armor_policy", "title": "Cloud Armor policy applied (rate limit + OWASP rules)"},
            {"key": "https_redirect_hsts", "title": "HTTP to HTTPS redirect + HSTS preload configured"},
        ],
    },
    {
        "number": 4,
        "slug": "secrets-config",
        "title": "Secrets & Config",
        "description": "Production secrets generated, stored in Secret Manager, and wired into workloads.",
        "items": [
            {"key": "secret_key_generated", "title": "SECRET_KEY generated (32+ chars, random)"},
            {"key": "jwt_secret_generated", "title": "JWT_SECRET_KEY generated (32+ chars, random)"},
            {"key": "pii_encryption_key", "title": "PII_ENCRYPTION_KEY generated (Fernet key, base64)"},
            {"key": "cloud_sql_password", "title": "Cloud SQL password stored in Secret Manager"},
            {"key": "redis_auth_token", "title": "Redis AUTH token stored in Secret Manager"},
            {"key": "meta_credentials_stored", "title": "Meta OAuth app credentials + CAPI token stored"},
            {"key": "google_ads_credentials", "title": "Google Ads developer token + client credentials stored"},
            {"key": "tiktok_credentials", "title": "TikTok app credentials + CAPI token stored"},
            {"key": "snapchat_credentials", "title": "Snapchat app credentials + CAPI token stored"},
            {"key": "whatsapp_credentials", "title": "WhatsApp Business API tokens stored"},
            {"key": "stripe_live_keys", "title": "Stripe live keys (publishable + secret) stored"},
            {"key": "stripe_webhook_signing", "title": "Stripe webhook signing secret stored"},
            {"key": "smtp_credentials", "title": "SMTP / SendGrid credentials stored"},
            {"key": "sentry_dsn", "title": "Sentry DSN stored"},
            {"key": "csi_driver_mounted", "title": "Secret Manager CSI driver mounts secrets into pods"},
            {"key": "cors_origins_set", "title": "CORS_ORIGINS set to exact production frontend URL"},
            {"key": "mock_ad_data_disabled", "title": "USE_MOCK_AD_DATA set to false"},
            {"key": "git_history_scanned", "title": "Git history scanned for leaked secrets (gitleaks)"},
        ],
    },
    {
        "number": 5,
        "slug": "multi-tenancy",
        "title": "Multi-Tenancy Hardening",
        "description": "Tenant isolation verified across every query, every task, every endpoint.",
        "items": [
            {"key": "tenant_filter_audit", "title": "Every query audited for tenant_id filter"},
            {"key": "rls_policies_enabled", "title": "PostgreSQL Row-Level Security policies enabled where defined"},
            {"key": "cross_tenant_tests", "title": "Integration tests assert 403/404 on cross-tenant access"},
            {"key": "jwt_tenant_validation", "title": "JWT tenant_id validated on every request"},
            {"key": "per_tenant_rate_limits", "title": "Rate limits scoped per-tenant, not global"},
            {"key": "celery_tenant_context", "title": "Celery tasks carry + re-validate tenant context"},
            {"key": "tenant_audit_log", "title": "Audit log entries scoped per-tenant for autopilot + trust gate"},
            {"key": "gdpr_erasure_cascade", "title": "GDPR erasure cascade documented + tested"},
        ],
    },
    {
        "number": 6,
        "slug": "trust-engine-safety",
        "title": "Trust Engine / Autopilot Safety",
        "description": "Guardrails for automation that moves ad spend.",
        "items": [
            {"key": "per_tenant_thresholds", "title": "Trust gate thresholds configurable per tenant (never hardcoded)"},
            {"key": "advisory_default", "title": "New tenants default to Advisory enforcement mode"},
            {"key": "autopilot_kill_switch", "title": "Global autopilot kill switch feature flag live"},
            {"key": "circuit_breakers", "title": "Circuit breakers on outbound ad-platform API calls"},
            {"key": "dry_run_verified", "title": "Dry-run mode verified for every autopilot action type"},
            {"key": "audit_retention_one_year", "title": "Trust gate + autopilot audit retention set to 1 year minimum"},
            {"key": "spend_anomaly_alerts", "title": "Spend anomaly alerts configured (N% shift in M minutes)"},
        ],
    },
    {
        "number": 7,
        "slug": "observability",
        "title": "Observability",
        "description": "Logs, metrics, traces, alerts, and error tracking.",
        "items": [
            {"key": "cloud_logging_configured", "title": "Cloud Logging ingesting structured JSON from GKE"},
            {"key": "log_sinks_long_term", "title": "Log sinks export to GCS for long-term retention"},
            {"key": "cloud_monitoring_dashboards", "title": "Cloud Monitoring dashboards configured (latency, errors, queue, DB, trust gate)"},
            {"key": "managed_prometheus", "title": "Managed Service for Prometheus scraping FastAPI instrumentator"},
            {"key": "managed_grafana", "title": "Managed Grafana configured for dashboards"},
            {"key": "alerting_integrated", "title": "Alert routing to PagerDuty / Opsgenie / Slack"},
            {"key": "sentry_configured", "title": "Sentry project configured; source maps uploaded; release tagging"},
            {"key": "uptime_checks_external", "title": "External synthetic uptime check (not from GCP)"},
            {"key": "cloud_trace_profiler", "title": "Cloud Trace + Cloud Profiler enabled on api"},
        ],
    },
    {
        "number": 8,
        "slug": "security-compliance",
        "title": "Security & Compliance",
        "description": "Dependency scanning, pen testing, headers, encryption, legal documents.",
        "items": [
            {"key": "dependency_scanning", "title": "CI dependency scanning clears all high / critical"},
            {"key": "binary_authorization_required", "title": "Binary Authorization attestations required for prod"},
            {"key": "security_review_completed", "title": "Internal security review of branch completed"},
            {"key": "third_party_pentest", "title": "Third-party penetration test completed"},
            {"key": "mfa_required_admins", "title": "MFA required for admin users"},
            {"key": "csp_headers_verified", "title": "CSP headers verified (Stripe / Meta / GTM allow-lists)"},
            {"key": "auth_rate_limits", "title": "Rate limits applied to auth endpoints (login, reset, MFA)"},
            {"key": "pii_fernet_verified", "title": "PII fields verified Fernet-encrypted at rest"},
            {"key": "gdpr_endpoints_tested", "title": "GDPR export + erasure endpoints tested end-to-end"},
            {"key": "legal_documents_ready", "title": "ToS, Privacy Policy, DPA templates ready"},
            {"key": "vpc_service_controls", "title": "VPC Service Controls perimeter around sensitive services"},
            {"key": "incident_runbook", "title": "Incident response runbook documented"},
        ],
    },
    {
        "number": 9,
        "slug": "oauth-compliance",
        "title": "OAuth & Platform Compliance",
        "description": "External approvals from ad platforms and payment processors.",
        "items": [
            {"key": "meta_app_review_approved", "title": "Meta App Review approved for required scopes"},
            {"key": "google_ads_token_approved", "title": "Google Ads API production token approved"},
            {"key": "tiktok_app_approved", "title": "TikTok app approval complete"},
            {"key": "snapchat_app_approved", "title": "Snapchat app approval complete"},
            {"key": "stripe_live_mode", "title": "Stripe account activated + live webhook endpoint registered"},
            {"key": "whatsapp_number_verified", "title": "WhatsApp Business number verified"},
        ],
    },
    {
        "number": 10,
        "slug": "deploy-pipeline",
        "title": "Deploy Pipeline & Rollback",
        "description": "CI/CD, staging parity, and rollback procedures.",
        "items": [
            {"key": "github_actions_wif", "title": "GitHub Actions authenticates via Workload Identity Federation"},
            {"key": "pipeline_tests_build_push", "title": "Pipeline runs tests, builds, pushes to Artifact Registry"},
            {"key": "staging_mirrors_prod", "title": "Staging project mirrors prod (smaller sizes)"},
            {"key": "rolling_deploy_configured", "title": "Rolling deploy configured on GKE Deployments"},
            {"key": "migration_job_sequencing", "title": "Migration Job runs before api rollout"},
            {"key": "staging_first_policy", "title": "Staging-first policy enforced for every change"},
            {"key": "release_notes_automation", "title": "Release notes / change log automation live"},
        ],
    },
    {
        "number": 11,
        "slug": "dress-rehearsal",
        "title": "Pre-Launch Dress Rehearsal",
        "description": "Load test, failover, restore, secret rotation, DR drills.",
        "items": [
            {"key": "load_test_completed", "title": "Load test against staging sustained 30+ minutes"},
            {"key": "cloud_sql_failover_drill", "title": "Cloud SQL failover drill completed; RTO measured"},
            {"key": "backup_restore_drill", "title": "PITR restore drill into scratch instance verified"},
            {"key": "secret_rotation_drill", "title": "Secret rotation drill for JWT_SECRET_KEY completed"},
            {"key": "dr_drill_completed", "title": "Full DR drill in alternate region completed"},
            {"key": "security_headers_review", "title": "CORS, CSP, cookie flags reviewed in prod"},
        ],
    },
    {
        "number": 12,
        "slug": "launch",
        "title": "Launch",
        "description": "Soft launch, monitoring, and progressive enforcement rollout.",
        "items": [
            {"key": "pilot_tenants_onboarded", "title": "1 to 3 pilot tenants onboarded"},
            {"key": "advisory_mode_default", "title": "All tenants start in Advisory enforcement"},
            {"key": "two_week_monitor_complete", "title": "Two-week monitoring window completed with no P0 / P1"},
            {"key": "weekly_review_cadence", "title": "Weekly review cadence scheduled (errors, trust gate, autopilot)"},
            {"key": "enforcement_upgrade_plan", "title": "Per-tenant enforcement upgrade plan documented"},
            {"key": "postmortem_process", "title": "Post-mortem process documented (48-hour SLA)"},
        ],
    },
]


def get_phase_by_number(number: int) -> LaunchReadinessPhaseDef | None:
    """Return the phase definition for a given phase number, or None."""
    for phase in LAUNCH_READINESS_PHASES:
        if phase["number"] == number:
            return phase
    return None


def find_item(item_key: str) -> tuple[LaunchReadinessPhaseDef, LaunchReadinessItemDef] | None:
    """Locate the phase and item definition for a given item key."""
    for phase in LAUNCH_READINESS_PHASES:
        for item in phase["items"]:
            if item["key"] == item_key:
                return phase, item
    return None


def all_item_keys() -> list[tuple[int, str]]:
    """Return (phase_number, item_key) pairs for every item in the catalog."""
    return [(phase["number"], item["key"]) for phase in LAUNCH_READINESS_PHASES for item in phase["items"]]


def total_item_count() -> int:
    """Total number of items across all phases."""
    return sum(len(phase["items"]) for phase in LAUNCH_READINESS_PHASES)
