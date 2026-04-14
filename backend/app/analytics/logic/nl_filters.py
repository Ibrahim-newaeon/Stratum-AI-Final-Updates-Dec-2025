# =============================================================================
# Feature #20 — Natural Language Filters
# =============================================================================
"""
Parse natural language queries into structured dashboard filters.

Features:
- Intent classification (filter, compare, analyze, summarize)
- Entity extraction (platforms, metrics, time ranges, thresholds)
- Filter generation from natural text
- Query suggestions and autocomplete
- Recent query history
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from pydantic import BaseModel, Field


# ── Response models ──────────────────────────────────────────────────────────


class ParsedFilter(BaseModel):
    """A structured filter extracted from natural language."""

    filter_type: str = ""  # platform / metric / date_range / threshold / campaign_type / region
    field: str = ""
    operator: str = "eq"  # eq / gt / lt / gte / lte / contains / in / between
    value: str = ""
    display_label: str = ""


class FilterInterpretation(BaseModel):
    """How the system interpreted the query."""

    original_query: str = ""
    intent: str = ""  # filter / compare / analyze / summarize / question
    confidence: float = 0.0
    parsed_filters: list[ParsedFilter] = Field(default_factory=list)
    explanation: str = ""
    applied: bool = False


class QuerySuggestion(BaseModel):
    """Suggested follow-up or related query."""

    query: str = ""
    description: str = ""
    category: str = ""  # filter / insight / comparison


class RecentQuery(BaseModel):
    """A recently executed query."""

    query: str = ""
    timestamp: str = ""
    filters_count: int = 0
    results_count: int = 0


class NLFilterResponse(BaseModel):
    """Full natural language filter response."""

    interpretation: FilterInterpretation = Field(default_factory=FilterInterpretation)
    suggestions: list[QuerySuggestion] = Field(default_factory=list)
    recent_queries: list[RecentQuery] = Field(default_factory=list)
    available_fields: list[str] = Field(default_factory=list)
    example_queries: list[str] = Field(default_factory=list)


# ── Constants ────────────────────────────────────────────────────────────────

PLATFORM_ALIASES: dict[str, str] = {
    "meta": "meta", "facebook": "meta", "fb": "meta", "instagram": "meta", "ig": "meta",
    "google": "google", "adwords": "google", "gads": "google",
    "tiktok": "tiktok", "tt": "tiktok",
    "snapchat": "snapchat", "snap": "snapchat",
    "linkedin": "linkedin", "li": "linkedin",
    "twitter": "twitter", "x": "twitter",
    "pinterest": "pinterest",
}

METRIC_ALIASES: dict[str, str] = {
    "roas": "roas", "return on ad spend": "roas", "roi": "roas",
    "spend": "spend", "cost": "spend", "budget": "spend",
    "revenue": "revenue", "income": "revenue", "sales": "revenue",
    "conversions": "conversions", "conv": "conversions", "converts": "conversions",
    "ctr": "ctr", "click through rate": "ctr", "click-through": "ctr",
    "cpa": "cpa", "cost per acquisition": "cpa", "cost per conversion": "cpa",
    "cpm": "cpm", "cost per mille": "cpm", "cost per thousand": "cpm",
    "impressions": "impressions", "imps": "impressions",
    "clicks": "clicks",
}

INTENT_KEYWORDS: dict[str, list[str]] = {
    "filter": ["show", "filter", "only", "where", "with", "having", "include", "exclude"],
    "compare": ["compare", "versus", "vs", "against", "difference", "between"],
    "analyze": ["analyze", "analyse", "breakdown", "deep dive", "detail", "why"],
    "summarize": ["summary", "summarize", "overview", "total", "overall", "aggregate"],
    "question": ["what", "how", "which", "when", "why", "is", "are", "does", "do", "can"],
}

TIME_PATTERNS: dict[str, int] = {
    "today": 0, "yesterday": 1, "last week": 7, "this week": 7,
    "last month": 30, "this month": 30, "last 7 days": 7, "last 14 days": 14,
    "last 30 days": 30, "last 90 days": 90, "last quarter": 90,
    "this quarter": 90, "this year": 365, "last year": 365,
}

THRESHOLD_PATTERN = re.compile(
    r'(roas|spend|revenue|cpa|ctr|cpm|conversions|clicks|impressions)\s*'
    r'(above|below|over|under|greater than|less than|more than|>=|<=|>|<|=)\s*'
    r'(\$?\d+\.?\d*%?x?)',
    re.IGNORECASE,
)


# ── Parser ───────────────────────────────────────────────────────────────────


def _classify_intent(query: str) -> tuple[str, float]:
    """Classify the intent of a natural language query."""
    q = query.lower().strip()
    scores: dict[str, int] = {intent: 0 for intent in INTENT_KEYWORDS}

    words = q.split()
    for intent, keywords in INTENT_KEYWORDS.items():
        for kw in keywords:
            if kw in words or kw in q:
                scores[intent] += 1

    best = max(scores, key=lambda k: scores[k])
    total = sum(scores.values())
    confidence = (scores[best] / total * 100) if total > 0 else 50

    if total == 0:
        return "filter", 50.0  # default to filter

    return best, min(confidence, 95)


def _extract_platforms(query: str) -> list[ParsedFilter]:
    """Extract platform filters from query."""
    filters: list[ParsedFilter] = []
    q = query.lower()

    for alias, canonical in PLATFORM_ALIASES.items():
        if alias in q.split() or alias in q:
            filters.append(ParsedFilter(
                filter_type="platform",
                field="platform",
                operator="eq",
                value=canonical,
                display_label=f"Platform: {canonical.title()}",
            ))
            break  # take first match

    return filters


def _extract_metrics(query: str) -> list[ParsedFilter]:
    """Extract metric threshold filters from query."""
    filters: list[ParsedFilter] = []

    for match in THRESHOLD_PATTERN.finditer(query):
        metric = METRIC_ALIASES.get(match.group(1).lower(), match.group(1).lower())
        op_text = match.group(2).lower()
        val = match.group(3).replace("$", "").replace("%", "").replace("x", "")

        op_map = {
            "above": "gt", "over": "gt", "greater than": "gt", "more than": "gt", ">": "gt", ">=": "gte",
            "below": "lt", "under": "lt", "less than": "lt", "<": "lt", "<=": "lte",
            "=": "eq",
        }
        op = op_map.get(op_text, "gt")

        filters.append(ParsedFilter(
            filter_type="threshold",
            field=metric,
            operator=op,
            value=val,
            display_label=f"{metric.upper()} {op_text} {match.group(3)}",
        ))

    return filters


def _extract_time_range(query: str) -> list[ParsedFilter]:
    """Extract date range filters from query."""
    filters: list[ParsedFilter] = []
    q = query.lower()

    for pattern, days in sorted(TIME_PATTERNS.items(), key=lambda x: -len(x[0])):
        if pattern in q:
            now = datetime.now(timezone.utc)
            start = (now - timedelta(days=days)).strftime("%Y-%m-%d")
            end = now.strftime("%Y-%m-%d")

            filters.append(ParsedFilter(
                filter_type="date_range",
                field="date",
                operator="between",
                value=f"{start},{end}",
                display_label=pattern.title(),
            ))
            break

    return filters


def _generate_suggestions(query: str, platforms: list[str]) -> list[QuerySuggestion]:
    """Generate relevant query suggestions."""
    suggestions: list[QuerySuggestion] = []

    base_suggestions = [
        QuerySuggestion(query="Show Meta campaigns with ROAS above 3x", description="Filter high-performing Meta campaigns", category="filter"),
        QuerySuggestion(query="Compare Google vs Meta last 30 days", description="Side-by-side platform performance", category="comparison"),
        QuerySuggestion(query="Which campaigns have CPA below $20?", description="Find cost-efficient campaigns", category="filter"),
        QuerySuggestion(query="Show me underperforming campaigns this week", description="Campaigns needing attention", category="insight"),
        QuerySuggestion(query="Top 5 campaigns by revenue last month", description="Best revenue generators", category="insight"),
    ]

    # Add platform-specific suggestions
    for plat in platforms[:2]:
        suggestions.append(QuerySuggestion(
            query=f"Show {plat.title()} campaigns with ROAS above 2x",
            description=f"High-performing {plat.title()} campaigns",
            category="filter",
        ))

    suggestions.extend(base_suggestions[:3])
    return suggestions[:6]


# ── Main entry point ─────────────────────────────────────────────────────────


def build_nl_filter(
    query: str,
    campaigns: list[dict],
) -> NLFilterResponse:
    """Parse a natural language query into structured filters."""
    if not query.strip():
        platforms = list({str(c.get("platform", "")).lower() for c in campaigns if c.get("platform")})
        return NLFilterResponse(
            interpretation=FilterInterpretation(
                original_query="",
                intent="filter",
                confidence=0,
                explanation="Enter a natural language query to filter your dashboard.",
            ),
            suggestions=_generate_suggestions("", platforms),
            available_fields=["platform", "spend", "revenue", "roas", "cpa", "ctr", "conversions", "impressions", "date"],
            example_queries=[
                "Show Meta campaigns with ROAS above 3x",
                "Compare Google vs TikTok last 30 days",
                "Which campaigns spend over $1000?",
                "Top performers this month",
                "Campaigns with CPA below $15",
            ],
        )

    # Parse query
    intent, confidence = _classify_intent(query)
    platform_filters = _extract_platforms(query)
    metric_filters = _extract_metrics(query)
    time_filters = _extract_time_range(query)

    all_filters = platform_filters + metric_filters + time_filters

    # Build explanation
    parts: list[str] = []
    if intent == "filter":
        parts.append("Filtering dashboard")
    elif intent == "compare":
        parts.append("Comparing")
    elif intent == "analyze":
        parts.append("Analyzing")
    elif intent == "summarize":
        parts.append("Summarizing")
    else:
        parts.append("Searching for")

    if platform_filters:
        parts.append(f"on {platform_filters[0].value.title()}")
    if metric_filters:
        labels = [f.display_label for f in metric_filters]
        parts.append(f"where {', '.join(labels)}")
    if time_filters:
        parts.append(f"for {time_filters[0].display_label.lower()}")
    if not all_filters:
        parts.append(f'matching "{query}"')

    explanation = " ".join(parts) + "."

    # Apply filters to count results
    results_count = len(campaigns)
    for f in all_filters:
        if f.filter_type == "platform":
            results_count = sum(1 for c in campaigns if f.value in str(c.get("platform", "")).lower())
        elif f.filter_type == "threshold" and f.field in ("roas", "spend", "revenue", "cpa"):
            try:
                threshold = float(f.value)
                results_count = sum(
                    1 for c in campaigns
                    if (f.operator == "gt" and float(c.get(f.field, 0)) > threshold)
                    or (f.operator == "lt" and float(c.get(f.field, 0)) < threshold)
                    or (f.operator == "gte" and float(c.get(f.field, 0)) >= threshold)
                    or (f.operator == "lte" and float(c.get(f.field, 0)) <= threshold)
                )
            except (ValueError, TypeError):
                pass

    platforms = list({str(c.get("platform", "")).lower() for c in campaigns if c.get("platform")})

    interpretation = FilterInterpretation(
        original_query=query,
        intent=intent,
        confidence=round(confidence, 1),
        parsed_filters=all_filters,
        explanation=explanation,
        applied=len(all_filters) > 0,
    )

    # Recent queries (simulated)
    now = datetime.now(timezone.utc)
    recent = [
        RecentQuery(query="Show Meta ROAS above 3x", timestamp=now.isoformat(), filters_count=2, results_count=5),
        RecentQuery(query="Google campaigns last 7 days", timestamp=(now - timedelta(hours=2)).isoformat(), filters_count=2, results_count=8),
        RecentQuery(query="Top performers this month", timestamp=(now - timedelta(hours=5)).isoformat(), filters_count=1, results_count=10),
    ]

    return NLFilterResponse(
        interpretation=interpretation,
        suggestions=_generate_suggestions(query, platforms),
        recent_queries=recent,
        available_fields=["platform", "spend", "revenue", "roas", "cpa", "ctr", "conversions", "impressions", "date"],
        example_queries=[
            "Show Meta campaigns with ROAS above 3x",
            "Compare Google vs TikTok last 30 days",
            "Which campaigns spend over $1000?",
            "Top performers this month",
            "Campaigns with CPA below $15",
        ],
    )
