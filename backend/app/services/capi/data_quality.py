# =============================================================================
# Stratum AI - Data Quality Analyzer
# =============================================================================
"""
AI-powered data quality analysis for Conversion APIs.
Identifies data gaps and provides recommendations to improve Event Match Quality.
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from app.core.logging import get_logger

from .pii_hasher import PIIField, PIIHasher

logger = get_logger(__name__)


class DataGapSeverity(str, Enum):
    """Severity level of data gaps."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class DataGap:
    """Identified data gap."""

    field: str
    severity: DataGapSeverity
    impact_percent: float
    affected_events: int
    recommendation: str
    how_to_fix: str


@dataclass
class PlatformQualityScore:
    """Quality score for a specific platform."""

    platform: str
    score: float  # 0-100
    event_match_quality: str  # Poor, Fair, Good, Excellent
    data_gaps: list[DataGap]
    potential_roas_lift: float  # Percentage
    events_analyzed: int
    fields_present: list[str]
    fields_missing: list[str]


@dataclass
class QualityReport:
    """Overall data quality report."""

    overall_score: float
    platform_scores: dict[str, PlatformQualityScore]
    top_recommendations: list[dict[str, Any]]
    estimated_roas_improvement: float
    data_gaps_summary: dict[str, int]
    trend: str  # improving, stable, declining
    generated_at: str


class DataQualityAnalyzer:
    """
    Analyzes data quality for Conversion APIs and identifies gaps
    that lower Event Match Quality scores.

    Features:
    - Per-platform quality scoring
    - Data gap identification
    - ROAS impact estimation
    - Actionable recommendations
    """

    # Field importance weights by platform (out of 100)
    FIELD_WEIGHTS = {
        "meta": {
            PIIField.EMAIL: 25,
            PIIField.PHONE: 20,
            PIIField.EXTERNAL_ID: 15,
            PIIField.FBC: 10,
            PIIField.FBP: 10,
            PIIField.FIRST_NAME: 5,
            PIIField.LAST_NAME: 5,
            PIIField.CLIENT_IP: 5,
            PIIField.CLIENT_USER_AGENT: 5,
        },
        "google": {
            PIIField.EMAIL: 30,
            PIIField.PHONE: 25,
            PIIField.GCLID: 20,
            PIIField.FIRST_NAME: 8,
            PIIField.LAST_NAME: 8,
            PIIField.ZIP_CODE: 5,
            PIIField.COUNTRY: 4,
        },
        "tiktok": {
            PIIField.EMAIL: 30,
            PIIField.PHONE: 25,
            PIIField.TTCLID: 20,
            PIIField.EXTERNAL_ID: 15,
            PIIField.CLIENT_IP: 10,
        },
        "snapchat": {
            PIIField.EMAIL: 35,
            PIIField.PHONE: 30,
            PIIField.EXTERNAL_ID: 20,
            PIIField.CLIENT_IP: 15,
        },
    }

    # ROAS impact per match quality level
    QUALITY_ROAS_IMPACT = {
        "Poor": {"range": (0, 40), "roas_multiplier": 1.0},
        "Fair": {"range": (40, 60), "roas_multiplier": 1.15},
        "Good": {"range": (60, 80), "roas_multiplier": 1.30},
        "Excellent": {"range": (80, 100), "roas_multiplier": 1.50},
    }

    def __init__(self):
        """Initialize the data quality analyzer."""
        self.hasher = PIIHasher()
        self._event_history: list[dict[str, Any]] = []

    def analyze_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze a single event for data quality.

        Args:
            event: Event data including user_data and parameters

        Returns:
            Analysis results with scores and recommendations
        """
        user_data = event.get("user_data", {})

        # Analyze for all platforms
        platform_results = {}
        for platform in self.FIELD_WEIGHTS:
            completeness = self.hasher.calculate_data_completeness(user_data, platform)
            platform_results[platform] = completeness

        # Overall score is weighted average
        overall_score = sum(r["score"] for r in platform_results.values()) / len(platform_results)

        return {
            "overall_score": round(overall_score, 1),
            "platform_scores": platform_results,
            "user_data_fields": list(user_data.keys()),
            "quality_level": self._get_quality_level(overall_score),
        }

    def analyze_batch(
        self, events: list[dict[str, Any]], platforms: list[str] = None
    ) -> QualityReport:
        """
        Analyze a batch of events for data quality patterns.

        Args:
            events: List of events to analyze
            platforms: Specific platforms to analyze (default: all)

        Returns:
            Comprehensive quality report
        """
        platforms = platforms or list(self.FIELD_WEIGHTS.keys())

        # Track field presence across all events
        field_presence: dict[str, dict[PIIField, int]] = {p: defaultdict(int) for p in platforms}
        total_events = len(events)

        # Analyze each event
        for event in events:
            user_data = event.get("user_data", {})
            detections = self.hasher.detect_pii_fields(user_data)
            detected_types = {d.detected_type for d in detections}

            for platform in platforms:
                for field in self.FIELD_WEIGHTS.get(platform, {}):
                    if field in detected_types:
                        field_presence[platform][field] += 1

        # Calculate platform scores
        platform_scores = {}
        all_gaps = []

        for platform in platforms:
            score, gaps = self._calculate_platform_score(
                platform, field_presence[platform], total_events
            )
            all_gaps.extend(gaps)

            quality_level = self._get_quality_level(score)
            potential_lift = self._estimate_roas_lift(score)

            # Get field lists
            weights = self.FIELD_WEIGHTS.get(platform, {})
            present = [
                f.value for f in weights if field_presence[platform].get(f, 0) > total_events * 0.5
            ]
            missing = [
                f.value for f in weights if field_presence[platform].get(f, 0) < total_events * 0.3
            ]

            platform_scores[platform] = PlatformQualityScore(
                platform=platform,
                score=score,
                event_match_quality=quality_level,
                data_gaps=gaps,
                potential_roas_lift=potential_lift,
                events_analyzed=total_events,
                fields_present=present,
                fields_missing=missing,
            )

        # Overall score
        overall_score = sum(ps.score for ps in platform_scores.values()) / len(platform_scores)

        # Top recommendations
        top_recs = self._generate_top_recommendations(all_gaps, platform_scores)

        # Data gaps summary
        gaps_summary = {
            DataGapSeverity.CRITICAL.value: sum(
                1 for g in all_gaps if g.severity == DataGapSeverity.CRITICAL
            ),
            DataGapSeverity.HIGH.value: sum(
                1 for g in all_gaps if g.severity == DataGapSeverity.HIGH
            ),
            DataGapSeverity.MEDIUM.value: sum(
                1 for g in all_gaps if g.severity == DataGapSeverity.MEDIUM
            ),
            DataGapSeverity.LOW.value: sum(
                1 for g in all_gaps if g.severity == DataGapSeverity.LOW
            ),
        }

        # Estimate overall ROAS improvement potential
        avg_current_lift = sum(ps.potential_roas_lift for ps in platform_scores.values()) / len(
            platform_scores
        )

        return QualityReport(
            overall_score=round(overall_score, 1),
            platform_scores=dict(platform_scores.items()),
            top_recommendations=top_recs,
            estimated_roas_improvement=round(avg_current_lift, 1),
            data_gaps_summary=gaps_summary,
            trend="stable",  # Would calculate from historical data
            generated_at=datetime.now(UTC).isoformat(),
        )

    def _calculate_platform_score(
        self, platform: str, field_counts: dict[PIIField, int], total_events: int
    ) -> tuple[float, list[DataGap]]:
        """Calculate quality score and identify gaps for a platform."""
        weights = self.FIELD_WEIGHTS.get(platform, {})
        total_weight = sum(weights.values())

        achieved_weight = 0
        gaps = []

        for field, weight in weights.items():
            count = field_counts.get(field, 0)
            presence_rate = count / total_events if total_events > 0 else 0

            # Score contribution based on presence rate
            achieved_weight += weight * presence_rate

            # Identify gaps (less than 50% presence)
            if presence_rate < 0.5:
                severity = self._get_gap_severity(weight, presence_rate)
                impact = weight * (1 - presence_rate)

                gaps.append(
                    DataGap(
                        field=field.value,
                        severity=severity,
                        impact_percent=round(impact, 1),
                        affected_events=total_events - count,
                        recommendation=self._get_field_recommendation(field, platform),
                        how_to_fix=self._get_fix_instructions(field),
                    )
                )

        score = (achieved_weight / total_weight * 100) if total_weight > 0 else 0
        return round(score, 1), gaps

    def _get_gap_severity(self, weight: float, presence_rate: float) -> DataGapSeverity:
        """Determine severity of a data gap."""
        if weight >= 20 and presence_rate < 0.2:
            return DataGapSeverity.CRITICAL
        elif weight >= 15 or presence_rate < 0.3:
            return DataGapSeverity.HIGH
        elif weight >= 10:
            return DataGapSeverity.MEDIUM
        else:
            return DataGapSeverity.LOW

    def _get_quality_level(self, score: float) -> str:
        """Get quality level from score."""
        for level, config in self.QUALITY_ROAS_IMPACT.items():
            min_score, max_score = config["range"]
            if min_score <= score < max_score:
                return level
        return "Excellent" if score >= 80 else "Poor"

    def _estimate_roas_lift(self, current_score: float) -> float:
        """Estimate potential ROAS lift if score improved to Excellent."""
        current_level = self._get_quality_level(current_score)
        current_multiplier = self.QUALITY_ROAS_IMPACT[current_level]["roas_multiplier"]
        max_multiplier = self.QUALITY_ROAS_IMPACT["Excellent"]["roas_multiplier"]

        potential_lift = ((max_multiplier - current_multiplier) / current_multiplier) * 100
        return round(potential_lift, 1)

    def _get_field_recommendation(self, field: PIIField, platform: str) -> str:
        """Get recommendation for missing field."""
        recommendations = {
            PIIField.EMAIL: "Add hashed email for 25-45% better match rates",
            PIIField.PHONE: "Include phone numbers to improve match by 20-30%",
            PIIField.EXTERNAL_ID: "Pass your internal user ID for consistent tracking",
            PIIField.FBC: "Capture fbclid parameter from URLs for Meta attribution",
            PIIField.FBP: "Set _fbp cookie value for browser identification",
            PIIField.GCLID: "Capture gclid parameter for Google Ads attribution",
            PIIField.TTCLID: "Capture ttclid parameter for TikTok attribution",
            PIIField.FIRST_NAME: "Include first name for enhanced matching",
            PIIField.LAST_NAME: "Include last name for enhanced matching",
            PIIField.CLIENT_IP: "Pass client IP address (non-hashed)",
            PIIField.CLIENT_USER_AGENT: "Include browser user agent string",
            PIIField.ZIP_CODE: "Add postal/zip code for location matching",
            PIIField.COUNTRY: "Include country code (e.g., US, UK)",
        }
        return recommendations.get(field, f"Add {field.value} field to improve matching")

    def _get_fix_instructions(self, field: PIIField) -> str:
        """Get technical instructions to fix a data gap."""
        instructions = {
            PIIField.EMAIL: "Collect email during checkout/registration. Hash with SHA256 after lowercasing.",
            PIIField.PHONE: "Collect phone at checkout. Remove special characters, keep country code, hash with SHA256.",
            PIIField.FBC: "Parse URL query string for 'fbclid' parameter on landing pages.",
            PIIField.FBP: "Read '_fbp' cookie value from document.cookie.",
            PIIField.GCLID: "Parse URL query string for 'gclid' parameter, store in session.",
            PIIField.TTCLID: "Parse URL query string for 'ttclid' parameter.",
            PIIField.EXTERNAL_ID: "Use your CRM/database user ID. Hash with SHA256.",
            PIIField.CLIENT_IP: "Get from request headers (X-Forwarded-For or CF-Connecting-IP).",
            PIIField.CLIENT_USER_AGENT: "Get from request headers (User-Agent).",
        }
        return instructions.get(
            field, f"Collect {field.value} from your data source and include in event data."
        )

    def _generate_top_recommendations(
        self, gaps: list[DataGap], platform_scores: dict[str, PlatformQualityScore]
    ) -> list[dict[str, Any]]:
        """Generate top actionable recommendations."""
        # Sort gaps by impact
        sorted_gaps = sorted(gaps, key=lambda g: g.impact_percent, reverse=True)

        # Deduplicate by field
        seen_fields = set()
        unique_gaps = []
        for gap in sorted_gaps:
            if gap.field not in seen_fields:
                seen_fields.add(gap.field)
                unique_gaps.append(gap)

        recommendations = []
        for i, gap in enumerate(unique_gaps[:5]):
            affected_platforms = [
                p for p, ps in platform_scores.items() if gap.field in ps.fields_missing
            ]

            recommendations.append(
                {
                    "priority": i + 1,
                    "field": gap.field,
                    "action": gap.recommendation,
                    "how_to_fix": gap.how_to_fix,
                    "impact": f"+{gap.impact_percent}% match quality",
                    "affected_platforms": affected_platforms,
                    "severity": gap.severity.value,
                }
            )

        return recommendations

    def get_live_insights(
        self, recent_events: list[dict[str, Any]], platform: str = "meta"
    ) -> dict[str, Any]:
        """
        Get live insights for recent events.

        Args:
            recent_events: Recent conversion events
            platform: Target platform

        Returns:
            Live insights with real-time recommendations
        """
        if not recent_events:
            return {
                "status": "no_data",
                "message": "No recent events to analyze",
            }

        # Analyze recent events
        report = self.analyze_batch(recent_events, [platform])
        platform_score = report.platform_scores.get(platform)

        if not platform_score:
            return {"status": "error", "message": "Platform not analyzed"}

        # Calculate trend from event quality over time
        quality_trend = self._calculate_trend(recent_events, platform)

        return {
            "status": "active",
            "current_score": platform_score.score,
            "quality_level": platform_score.event_match_quality,
            "events_analyzed": len(recent_events),
            "trend": quality_trend,
            "top_gaps": [
                {
                    "field": g.field,
                    "impact": g.impact_percent,
                    "fix": g.how_to_fix,
                }
                for g in platform_score.data_gaps[:3]
            ],
            "estimated_roas_lift": platform_score.potential_roas_lift,
            "action_required": platform_score.score < 70,
        }

    def _calculate_trend(self, events: list[dict[str, Any]], platform: str) -> str:
        """Calculate quality trend from events."""
        if len(events) < 10:
            return "insufficient_data"

        # Split into halves and compare
        mid = len(events) // 2
        first_half = events[:mid]
        second_half = events[mid:]

        first_report = self.analyze_batch(first_half, [platform])
        second_report = self.analyze_batch(second_half, [platform])

        first_score = first_report.overall_score
        second_score = second_report.overall_score

        if second_score > first_score + 5:
            return "improving"
        elif second_score < first_score - 5:
            return "declining"
        else:
            return "stable"
