# =============================================================================
# Attribution Variance (Platform vs GA4)
# =============================================================================
"""
Attribution Variance Calculator.
From AI_Logic_Formulas_Pseudocode.md Section 5.

Goal: Quantify divergence between platform-reported and GA4 data.
Helps explain "platform says X but GA4 says Y".

Use:
- If abs(rev_var_pct) > 30% consistently: show an "Attribution Noise" banner.
"""

from app.analytics.logic.types import AttributionVarianceResult


def attribution_variance(
    entity_id: str,
    platform_revenue: float,
    platform_conversions: int,
    ga4_revenue: float,
    ga4_conversions: int,
    variance_threshold_pct: float = 30.0,
) -> AttributionVarianceResult:
    """
    Calculate attribution variance between platform and GA4.

    Args:
        entity_id: Entity identifier (campaign, adset, etc.)
        platform_revenue: Platform-reported revenue
        platform_conversions: Platform-reported conversions
        ga4_revenue: GA4-attributed revenue
        ga4_conversions: GA4-attributed conversions
        variance_threshold_pct: Threshold for significant variance (default 30%)

    Returns:
        AttributionVarianceResult with variance percentages and warnings
    """
    # Calculate revenue variance
    if ga4_revenue > 0:
        rev_var = (platform_revenue - ga4_revenue) / ga4_revenue
    else:
        rev_var = 0.0 if platform_revenue == 0 else 1.0  # 100% variance if GA4 is 0

    # Calculate conversion variance
    if ga4_conversions > 0:
        conv_var = (platform_conversions - ga4_conversions) / ga4_conversions
    else:
        conv_var = 0.0 if platform_conversions == 0 else 1.0

    # Convert to percentages
    rev_var_pct = rev_var * 100
    conv_var_pct = conv_var * 100

    # Check for significant variance
    has_significant_variance = (
        abs(rev_var_pct) > variance_threshold_pct or abs(conv_var_pct) > variance_threshold_pct
    )

    # Generate warning message
    warning_message = None
    if has_significant_variance:
        if rev_var_pct > variance_threshold_pct:
            warning_message = (
                f"Platform reports {rev_var_pct:.1f}% more revenue than GA4. "
                "This may indicate attribution window differences or cross-device tracking gaps."
            )
        elif rev_var_pct < -variance_threshold_pct:
            warning_message = (
                f"GA4 reports {abs(rev_var_pct):.1f}% more revenue than platform. "
                "Check for organic/direct conversions incorrectly attributed to paid."
            )
        else:
            warning_message = (
                f"Significant conversion variance detected ({conv_var_pct:.1f}%). "
                "Review attribution settings and tracking implementation."
            )

    return AttributionVarianceResult(
        entity_id=entity_id,
        revenue_variance_pct=round(rev_var_pct, 2),
        conversion_variance_pct=round(conv_var_pct, 2),
        platform_revenue=platform_revenue,
        ga4_revenue=ga4_revenue,
        platform_conversions=platform_conversions,
        ga4_conversions=ga4_conversions,
        has_significant_variance=has_significant_variance,
        warning_message=warning_message,
    )


def batch_attribution_variance(
    entities: list[dict],
    variance_threshold_pct: float = 30.0,
) -> list[AttributionVarianceResult]:
    """
    Calculate attribution variance for multiple entities.

    Args:
        entities: List of dicts with entity_id, platform/ga4 revenue/conversions
        variance_threshold_pct: Threshold for significant variance

    Returns:
        List of AttributionVarianceResult, sorted by absolute variance
    """
    results = []

    for entity in entities:
        result = attribution_variance(
            entity_id=entity["entity_id"],
            platform_revenue=entity.get("platform_revenue", 0),
            platform_conversions=entity.get("platform_conversions", 0),
            ga4_revenue=entity.get("ga4_revenue", 0),
            ga4_conversions=entity.get("ga4_conversions", 0),
            variance_threshold_pct=variance_threshold_pct,
        )
        results.append(result)

    # Sort by absolute revenue variance
    results.sort(key=lambda x: abs(x.revenue_variance_pct), reverse=True)

    return results


def get_attribution_health(results: list[AttributionVarianceResult]) -> dict:
    """
    Get overall attribution health summary.

    Args:
        results: List of attribution variance results

    Returns:
        Dict with summary statistics
    """
    if not results:
        return {"status": "no_data", "entities_checked": 0}

    significant_count = sum(1 for r in results if r.has_significant_variance)
    avg_rev_variance = sum(abs(r.revenue_variance_pct) for r in results) / len(results)
    avg_conv_variance = sum(abs(r.conversion_variance_pct) for r in results) / len(results)

    # Determine status
    if significant_count == 0:
        status = "healthy"
    elif significant_count / len(results) < 0.2:
        status = "minor_variance"
    elif significant_count / len(results) < 0.5:
        status = "moderate_variance"
    else:
        status = "high_variance"

    return {
        "status": status,
        "entities_checked": len(results),
        "entities_with_variance": significant_count,
        "variance_rate": round(significant_count / len(results) * 100, 1),
        "avg_revenue_variance_pct": round(avg_rev_variance, 1),
        "avg_conversion_variance_pct": round(avg_conv_variance, 1),
        "needs_attention": status in ["moderate_variance", "high_variance"],
    }
