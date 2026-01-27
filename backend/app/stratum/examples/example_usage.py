#!/usr/bin/env python3
"""
Stratum AI: Example Usage Script
================================

This script demonstrates the complete workflow for bi-directional
integration with all four advertising platforms using Stratum's
trust-gated automation system.

Run this script to see how the different components work together.
"""

import asyncio
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("stratum.example")


async def example_meta_integration():
    """
    Example: Full Meta (Facebook/Instagram) integration workflow.

    This demonstrates:
    1. Initializing the adapter
    2. Pulling campaign data
    3. Fetching performance metrics
    4. Getting EMQ scores
    5. Calculating signal health
    6. Evaluating an action through trust gate
    7. Executing the action (if approved)
    """
    from app.stratum import (
        AutomationAction,
        EMQScore,
        PerformanceMetrics,
        Platform,
    )
    from app.stratum.core import (
        SignalHealthCalculator,
        TrustGate,
    )

    logger.info("=" * 60)
    logger.info("META INTEGRATION EXAMPLE")
    logger.info("=" * 60)

    # In production, load these from config.yaml
    credentials = {
        "app_id": "YOUR_APP_ID",
        "app_secret": "YOUR_APP_SECRET",
        "access_token": "YOUR_ACCESS_TOKEN",
        "pixel_id": "YOUR_PIXEL_ID",
    }

    # For this example, we'll simulate the workflow
    logger.info("Step 1: Initialize adapter")
    logger.info("  adapter = await create_adapter(Platform.META, credentials)")
    logger.info("  -> Would connect to Meta Marketing API")

    logger.info("\nStep 2: Pull campaigns")
    logger.info("  campaigns = await adapter.get_campaigns('act_123456789')")
    logger.info("  -> Returns list of UnifiedCampaign objects")

    logger.info("\nStep 3: Fetch metrics")
    logger.info("  metrics = await adapter.get_metrics(")
    logger.info("      account_id='act_123456789',")
    logger.info("      entity_type='campaign',")
    logger.info("      entity_ids=['1234567890'],")
    logger.info("      date_start=datetime.now() - timedelta(days=7),")
    logger.info("      date_end=datetime.now()")
    logger.info("  )")

    # Simulate EMQ scores
    logger.info("\nStep 4: Get EMQ scores")
    emq_scores = [
        EMQScore(platform=Platform.META, event_name="Purchase", score=8.2),
        EMQScore(platform=Platform.META, event_name="AddToCart", score=6.5),
    ]
    logger.info("  Simulated EMQ scores: Purchase=8.2, AddToCart=6.5")

    # Simulate metrics
    logger.info("\nStep 5: Simulate historical metrics")
    recent_metrics = []
    for i in range(7):
        metrics = PerformanceMetrics(
            impressions=10000 + i * 500,
            clicks=200 + i * 10,
            spend=100.0 + i * 5,
            conversions=20 + i,
            cpa=5.0 + (i * 0.1),
            date_start=datetime.now() - timedelta(days=7 - i),
            date_end=datetime.now() - timedelta(days=6 - i),
        )
        recent_metrics.append(metrics)
    logger.info("  Generated 7 days of metrics data")

    # Calculate signal health
    logger.info("\nStep 6: Calculate signal health")
    calculator = SignalHealthCalculator()
    signal_health = calculator.calculate(
        platform=Platform.META,
        account_id="act_123456789",
        emq_scores=emq_scores,
        recent_metrics=recent_metrics,
    )
    logger.info(f"  Signal Health Score: {signal_health.score}/100")
    logger.info(f"    EMQ Component: {signal_health.emq_score}")
    logger.info(f"    Freshness Component: {signal_health.freshness_score}")
    logger.info(f"    Variance Component: {signal_health.variance_score}")
    logger.info(f"    Anomaly Component: {signal_health.anomaly_score}")
    logger.info(f"  Autopilot Allowed: {signal_health.autopilot_allowed}")

    # Create an automation action
    logger.info("\nStep 7: Create automation action")
    action = AutomationAction(
        platform=Platform.META,
        account_id="act_123456789",
        entity_type="campaign",
        entity_id="1234567890",
        action_type="update_budget",
        parameters={"daily_budget": 150.00},
        signal_health_at_creation=signal_health.score,
    )
    logger.info("  Action: Update campaign budget to $150/day")

    # Evaluate through trust gate
    logger.info("\nStep 8: Evaluate through trust gate")
    gate = TrustGate()
    result = gate.evaluate(action, signal_health)
    logger.info(f"  Gate Decision: {result.decision.value.upper()}")
    logger.info(f"  Reason: {result.reason}")

    if result.decision.value in ["approved", "overridden"]:
        logger.info("\n[OK] Action APPROVED - Would execute:")
        logger.info("   await adapter.execute_action(action)")
    else:
        logger.info("\n[WARN] Action NOT APPROVED")
        logger.info(f"   Status: {result.decision.value}")

    # Show recommendations
    if signal_health.recommendations:
        logger.info("\n[INFO] Recommendations:")
        for rec in signal_health.recommendations:
            logger.info(f"   - {rec}")


async def example_multi_platform_sync():
    """
    Example: Syncing data across multiple platforms.

    This demonstrates how you might pull data from all platforms
    to build a unified dashboard or reporting system.
    """
    from app.stratum import Platform
    from app.stratum.models import UnifiedCampaign

    logger.info("\n" + "=" * 60)
    logger.info("MULTI-PLATFORM SYNC EXAMPLE")
    logger.info("=" * 60)

    # Simulated unified view
    all_campaigns = []

    platforms = [Platform.META, Platform.GOOGLE, Platform.TIKTOK, Platform.SNAPCHAT]

    for platform in platforms:
        logger.info(f"\n[SYNC] Syncing {platform.value.upper()}...")

        # In production:
        # adapter = await create_adapter(platform, credentials[platform])
        # campaigns = await adapter.get_campaigns(account_id)

        # Simulated campaigns
        simulated_campaigns = [
            UnifiedCampaign(
                platform=platform,
                account_id=f"{platform.value}_account_123",
                campaign_id=f"{platform.value}_campaign_1",
                campaign_name=f"{platform.value.title()} - Furniture Sales Q1",
                daily_budget=100.0,
                last_synced=datetime.now(),
            ),
            UnifiedCampaign(
                platform=platform,
                account_id=f"{platform.value}_account_123",
                campaign_id=f"{platform.value}_campaign_2",
                campaign_name=f"{platform.value.title()} - Brand Awareness",
                daily_budget=50.0,
                last_synced=datetime.now(),
            ),
        ]

        all_campaigns.extend(simulated_campaigns)
        logger.info(f"   Found {len(simulated_campaigns)} campaigns")

    # Summary
    logger.info("\n" + "-" * 40)
    logger.info("UNIFIED CAMPAIGN VIEW")
    logger.info("-" * 40)

    total_budget = sum(c.daily_budget or 0 for c in all_campaigns)
    logger.info(f"Total Campaigns: {len(all_campaigns)}")
    logger.info(f"Total Daily Budget: ${total_budget:.2f}")

    for platform in platforms:
        platform_campaigns = [c for c in all_campaigns if c.platform == platform]
        platform_budget = sum(c.daily_budget or 0 for c in platform_campaigns)
        logger.info(
            f"  {platform.value.title()}: {len(platform_campaigns)} campaigns, ${platform_budget:.2f}/day"
        )


async def example_budget_optimization():
    """
    Example: Automated budget optimization workflow.

    This demonstrates how Stratum's autopilot might automatically
    reallocate budget based on performance.
    """
    from app.stratum import AutomationAction, Platform
    from app.stratum.core import TrustGatedAutopilot
    from app.stratum.models import EMQScore, PerformanceMetrics

    logger.info("\n" + "=" * 60)
    logger.info("BUDGET OPTIMIZATION EXAMPLE")
    logger.info("=" * 60)

    # Initialize the trust-gated autopilot
    autopilot = TrustGatedAutopilot()

    # Simulated campaign performance data
    campaigns_performance = [
        {"id": "campaign_1", "name": "Living Room", "spend": 100, "conversions": 25, "roas": 4.5},
        {"id": "campaign_2", "name": "Bedroom", "spend": 100, "conversions": 10, "roas": 2.1},
        {"id": "campaign_3", "name": "Office", "spend": 100, "conversions": 30, "roas": 5.2},
    ]

    logger.info("\n[PERF] Current Campaign Performance:")
    for cp in campaigns_performance:
        logger.info(
            f"  {cp['name']}: ${cp['spend']} spend, {cp['conversions']} conv, {cp['roas']}x ROAS"
        )

    # Optimization logic: shift budget from worst to best
    sorted_campaigns = sorted(campaigns_performance, key=lambda x: x["roas"], reverse=True)
    best = sorted_campaigns[0]
    worst = sorted_campaigns[-1]

    logger.info("\n[TARGET] Optimization Decision:")
    logger.info(f"  Best performer: {best['name']} ({best['roas']}x ROAS)")
    logger.info(f"  Worst performer: {worst['name']} ({worst['roas']}x ROAS)")
    logger.info(f"  -> Shift $20 from {worst['name']} to {best['name']}")

    # Create the actions
    actions = [
        AutomationAction(
            platform=Platform.META,
            account_id="act_123",
            entity_type="campaign",
            entity_id=worst["id"],
            action_type="update_budget",
            parameters={"daily_budget": 80.0},  # Reduce by $20
            signal_health_at_creation=75.0,
        ),
        AutomationAction(
            platform=Platform.META,
            account_id="act_123",
            entity_type="campaign",
            entity_id=best["id"],
            action_type="update_budget",
            parameters={"daily_budget": 120.0},  # Increase by $20
            signal_health_at_creation=75.0,
        ),
    ]

    # Simulated signal health data
    emq_scores = [EMQScore(platform=Platform.META, event_name="Purchase", score=8.0)]
    recent_metrics = [
        PerformanceMetrics(
            impressions=30000,
            clicks=600,
            spend=300,
            conversions=65,
            date_start=datetime.now() - timedelta(days=1),
            date_end=datetime.now(),
        )
    ]

    logger.info("\n[GATE] Trust Gate Evaluation:")
    for action in actions:
        can_proceed, result = await autopilot.can_execute(
            action=action, emq_scores=emq_scores, recent_metrics=recent_metrics
        )

        campaign_name = next(
            (c["name"] for c in campaigns_performance if c["id"] == action.entity_id), "Unknown"
        )
        new_budget = action.parameters.get("daily_budget")

        if can_proceed:
            logger.info(f"  [OK] {campaign_name} -> ${new_budget}: APPROVED")
        else:
            logger.info(f"  [X] {campaign_name} -> ${new_budget}: {result.decision.value}")


async def main():
    """Run all examples."""
    logger.info("[START] STRATUM AI: Multi-Platform Integration Examples")
    logger.info("=" * 60)

    await example_meta_integration()
    await example_multi_platform_sync()
    await example_budget_optimization()

    logger.info("\n" + "=" * 60)
    logger.info("[OK] All examples completed!")
    logger.info("=" * 60)

    logger.info("\n[NEXT] Next Steps:")
    logger.info("  1. Copy config.example.yaml to config.yaml")
    logger.info("  2. Add your platform credentials")
    logger.info("  3. Run with real API connections")
    logger.info("  4. Build your automation rules on top of this framework")


if __name__ == "__main__":
    asyncio.run(main())
