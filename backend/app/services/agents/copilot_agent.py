# =============================================================================
# Stratum AI - Copilot Agent (Feature #4)
# =============================================================================
"""
AI Copilot Agent — a data-aware conversational assistant for the dashboard.

Understands natural language queries about campaigns, metrics, signal health,
anomalies, and recommendations. Queries real dashboard data to generate
contextual, actionable responses.

Architecture:
- Intent classification via keyword matching (upgradeable to LLM)
- Data fetching from existing dashboard queries
- Template-based response generation with real data injection
- Session state tracked in Redis
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Intent Classification
# =============================================================================

class CopilotIntent(str, Enum):
    """Recognized user intents."""
    GREETING = "greeting"
    PERFORMANCE_OVERVIEW = "performance_overview"
    SIGNAL_HEALTH = "signal_health"
    ANOMALIES = "anomalies"
    SPEND_ANALYSIS = "spend_analysis"
    ROAS_ANALYSIS = "roas_analysis"
    RECOMMENDATIONS = "recommendations"
    CAMPAIGNS = "campaigns"
    HELP = "help"
    UNKNOWN = "unknown"


# Keyword patterns for intent classification
INTENT_PATTERNS: Dict[CopilotIntent, List[str]] = {
    CopilotIntent.GREETING: [
        "hello", "hi", "hey", "good morning", "good afternoon",
        "good evening", "what's up", "howdy", "greetings",
    ],
    CopilotIntent.PERFORMANCE_OVERVIEW: [
        "how are things", "how is everything", "overview", "summary",
        "how are my campaigns doing", "overall performance", "dashboard",
        "what's happening", "status", "how's it going", "performance",
        "give me a summary", "brief me", "update me", "what's new",
    ],
    CopilotIntent.SIGNAL_HEALTH: [
        "signal", "health", "emq", "event match", "tracking",
        "data quality", "trust", "autopilot", "signal health",
        "is my data healthy", "trust gate", "event loss",
    ],
    CopilotIntent.ANOMALIES: [
        "anomal", "unusual", "weird", "strange", "abnormal",
        "something wrong", "issue", "problem", "alert", "warning",
        "spike", "drop", "surge", "crash",
    ],
    CopilotIntent.SPEND_ANALYSIS: [
        "spend", "budget", "cost", "how much", "spending",
        "money", "expense", "investment", "burn", "cpa",
        "cost per", "acquisition cost",
    ],
    CopilotIntent.ROAS_ANALYSIS: [
        "roas", "return", "roi", "efficiency", "profitable",
        "return on ad spend", "revenue vs spend", "margin",
    ],
    CopilotIntent.RECOMMENDATIONS: [
        "recommend", "suggest", "what should", "advice",
        "action", "next step", "what can i do", "improve",
        "optimize", "tip", "fix", "help me",
    ],
    CopilotIntent.CAMPAIGNS: [
        "campaign", "ad set", "ad group", "creative",
        "which campaign", "best campaign", "worst campaign",
        "top campaign", "bottom campaign", "active campaign",
    ],
    CopilotIntent.HELP: [
        "help", "what can you do", "capabilities", "features",
        "how do i", "teach me", "explain", "tutorial",
        "what do you know", "guide",
    ],
}


def classify_intent(message: str) -> CopilotIntent:
    """
    Classify user message into an intent.

    Uses keyword matching with scoring. Each intent gets a score
    based on how many of its keywords appear in the message.
    """
    msg_lower = message.lower().strip()

    scores: Dict[CopilotIntent, int] = {}
    for intent, keywords in INTENT_PATTERNS.items():
        score = sum(1 for kw in keywords if kw in msg_lower)
        if score > 0:
            scores[intent] = score

    if not scores:
        return CopilotIntent.UNKNOWN

    return max(scores, key=scores.get)


# =============================================================================
# Response Models
# =============================================================================

class CopilotMessage(BaseModel):
    """A single message in the copilot conversation."""
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    intent: Optional[str] = None
    suggestions: List[str] = []
    data_cards: List[Dict[str, Any]] = []


class CopilotSession(BaseModel):
    """Session state for a copilot conversation."""
    session_id: str
    user_id: int
    tenant_id: int
    messages: List[CopilotMessage] = []
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    context: Dict[str, Any] = {}


class CopilotResponse(BaseModel):
    """Response from the copilot agent."""
    message: str
    suggestions: List[str] = []
    data_cards: List[Dict[str, Any]] = []
    intent: str = "unknown"


# =============================================================================
# Response Generation
# =============================================================================

def generate_greeting_response(user_name: Optional[str] = None) -> CopilotResponse:
    """Generate a greeting response."""
    name = user_name or "there"
    hour = datetime.now(UTC).hour

    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    return CopilotResponse(
        message=(
            f"{greeting}, {name}! I'm your Stratum AI Copilot. "
            f"I can help you understand your campaign performance, signal health, "
            f"anomalies, and recommendations. What would you like to know?"
        ),
        suggestions=[
            "How are my campaigns doing?",
            "Any anomalies today?",
            "What's my signal health?",
            "Show me ROAS analysis",
        ],
        intent="greeting",
    )


def generate_performance_response(
    metrics: Optional[Dict] = None,
) -> CopilotResponse:
    """Generate a performance overview response."""
    if not metrics:
        return CopilotResponse(
            message=(
                "I don't have enough data to give you a full performance overview yet. "
                "Make sure your ad platforms are connected and campaigns are synced."
            ),
            suggestions=[
                "Check signal health",
                "How do I connect platforms?",
            ],
            intent="performance_overview",
        )

    spend = metrics.get("spend", 0)
    revenue = metrics.get("revenue", 0)
    roas = metrics.get("roas", 0)
    conversions = metrics.get("conversions", 0)
    active_campaigns = metrics.get("active_campaigns", 0)
    spend_change = metrics.get("spend_change_pct")
    revenue_change = metrics.get("revenue_change_pct")

    # Build narrative
    parts = [f"Here's your performance snapshot:"]

    if revenue > 0:
        roas_quality = "strong" if roas >= 3 else ("healthy" if roas >= 2 else ("below target" if roas >= 1 else "needs attention"))
        parts.append(
            f"You're generating **${revenue:,.0f}** in revenue from **${spend:,.0f}** in spend, "
            f"for a ROAS of **{roas:.2f}x** — that's {roas_quality}."
        )
    elif spend > 0:
        parts.append(f"You're spending **${spend:,.0f}** across your campaigns but I don't see revenue data yet.")

    if conversions > 0:
        cpa = spend / conversions if conversions > 0 else 0
        parts.append(f"You've driven **{conversions:,}** conversions at **${cpa:,.2f}** CPA.")

    if spend_change is not None:
        direction = "up" if spend_change > 0 else "down"
        parts.append(f"Spend is {direction} **{abs(spend_change):.1f}%** vs. the prior period.")

    if revenue_change is not None:
        direction = "up" if revenue_change > 0 else "down"
        parts.append(f"Revenue is {direction} **{abs(revenue_change):.1f}%**.")

    if active_campaigns > 0:
        parts.append(f"You have **{active_campaigns}** active campaigns running.")

    data_cards = []
    if spend > 0:
        data_cards = [
            {"label": "Spend", "value": f"${spend:,.0f}", "change": spend_change},
            {"label": "Revenue", "value": f"${revenue:,.0f}", "change": revenue_change},
            {"label": "ROAS", "value": f"{roas:.2f}x"},
            {"label": "Conversions", "value": f"{conversions:,}"},
        ]

    return CopilotResponse(
        message=" ".join(parts),
        suggestions=[
            "Show me anomalies",
            "What's my signal health?",
            "Which campaigns should I scale?",
            "Show me ROAS breakdown",
        ],
        data_cards=data_cards,
        intent="performance_overview",
    )


def generate_signal_health_response(
    health_data: Optional[Dict] = None,
) -> CopilotResponse:
    """Generate a signal health response."""
    if not health_data:
        return CopilotResponse(
            message="I couldn't fetch signal health data. Please check that your platforms are connected.",
            suggestions=["How are my campaigns doing?", "Help me connect platforms"],
            intent="signal_health",
        )

    score = health_data.get("overall_score", 0)
    status = health_data.get("status", "unknown")
    issues = health_data.get("issues", [])
    autopilot = health_data.get("autopilot_enabled", False)
    emq = health_data.get("emq_score")

    if status == "healthy":
        message = (
            f"Your signals are **healthy** with an overall score of **{score}/100**. "
        )
        if autopilot:
            message += "Autopilot is **enabled** — the trust gate is passing. "
        if emq:
            message += f"EMQ score: **{emq * 100:.0f}%**. "
        message += "Everything looks good!"
    elif status == "degraded":
        message = (
            f"Your signal health is **degraded** (score: **{score}/100**). "
            f"Autopilot is {'still running' if autopilot else '**suspended**'}. "
        )
        if issues:
            message += f"Issues: {'; '.join(issues[:3])}. "
        message += "I recommend checking Signal Recovery on your dashboard."
    elif status == "critical":
        message = (
            f"**Critical signal issue detected!** Health score: **{score}/100**. "
            f"Autopilot is **suspended**. "
        )
        if issues:
            message += f"Critical issues: {'; '.join(issues[:3])}. "
        message += "Immediate action required."
    else:
        message = (
            f"Signal health status is **unknown** (score: {score}). "
            "This usually means no platforms are connected yet."
        )

    data_cards = [
        {"label": "Health Score", "value": f"{score}/100", "status": status},
        {"label": "Autopilot", "value": "Enabled" if autopilot else "Disabled"},
    ]
    if emq:
        data_cards.append({"label": "EMQ", "value": f"{emq * 100:.0f}%"})

    return CopilotResponse(
        message=message,
        suggestions=[
            "Any anomalies?",
            "How are my campaigns doing?",
            "What should I do next?",
        ],
        data_cards=data_cards,
        intent="signal_health",
    )


def generate_anomaly_response(
    anomaly_data: Optional[Dict] = None,
) -> CopilotResponse:
    """Generate an anomaly analysis response."""
    if not anomaly_data:
        return CopilotResponse(
            message="No anomaly data available. This may mean all metrics are within normal ranges.",
            suggestions=["Show me performance overview", "Check signal health"],
            intent="anomalies",
        )

    total = anomaly_data.get("total_anomalies", 0)
    critical = anomaly_data.get("critical_count", 0)
    high = anomaly_data.get("high_count", 0)
    risk = anomaly_data.get("portfolio_risk", "low")
    summary = anomaly_data.get("executive_summary", "")
    narratives = anomaly_data.get("narratives", [])
    correlations = anomaly_data.get("correlations", [])

    if total == 0:
        return CopilotResponse(
            message=(
                "No anomalies detected! All your metrics are within normal operating ranges. "
                "Your portfolio risk is **low**. Keep up the good work."
            ),
            suggestions=[
                "Show me performance overview",
                "What's my ROAS?",
                "Any recommendations?",
            ],
            intent="anomalies",
        )

    parts = [f"I detected **{total}** anomal{'y' if total == 1 else 'ies'} in your data."]

    if critical > 0:
        parts.append(f"**{critical} critical** — needs immediate attention.")
    if high > 0:
        parts.append(f"**{high} high severity** — worth investigating today.")

    parts.append(f"Portfolio risk level: **{risk}**.")

    if correlations:
        top_corr = correlations[0]
        parts.append(f"Key pattern: **{top_corr.get('title', '')}** — {top_corr.get('description', '')[:120]}.")

    if narratives:
        top = narratives[0]
        parts.append(
            f"Top anomaly: **{top.get('title', '')}** "
            f"({top.get('change_percent', 0):.1f}% {'increase' if top.get('direction') == 'up' else 'decrease'})."
        )

    data_cards = [
        {"label": "Anomalies", "value": str(total)},
        {"label": "Portfolio Risk", "value": risk.title(), "status": risk},
    ]
    if critical > 0:
        data_cards.append({"label": "Critical", "value": str(critical), "status": "critical"})

    return CopilotResponse(
        message=" ".join(parts),
        suggestions=[
            "What should I do about this?",
            "Show me signal health",
            "How are my campaigns doing?",
        ],
        data_cards=data_cards,
        intent="anomalies",
    )


def generate_spend_response(
    metrics: Optional[Dict] = None,
) -> CopilotResponse:
    """Generate a spend analysis response."""
    if not metrics or metrics.get("spend", 0) == 0:
        return CopilotResponse(
            message="I don't see any spend data yet. Make sure campaigns are active and synced.",
            suggestions=["Check signal health", "Show me campaigns"],
            intent="spend_analysis",
        )

    spend = metrics.get("spend", 0)
    revenue = metrics.get("revenue", 0)
    conversions = metrics.get("conversions", 0)
    cpa = spend / conversions if conversions > 0 else 0
    spend_change = metrics.get("spend_change_pct")

    parts = [f"Here's your spend analysis:"]
    parts.append(f"Total spend: **${spend:,.0f}**.")

    if spend_change is not None:
        direction = "increased" if spend_change > 0 else "decreased"
        parts.append(f"Spend has {direction} **{abs(spend_change):.1f}%** vs. prior period.")

    if conversions > 0:
        parts.append(f"Cost per acquisition: **${cpa:,.2f}** across **{conversions:,}** conversions.")

    if revenue > 0:
        efficiency = revenue / spend if spend > 0 else 0
        parts.append(f"Every $1 spent is generating **${efficiency:.2f}** in revenue.")

    data_cards = [
        {"label": "Total Spend", "value": f"${spend:,.0f}", "change": spend_change},
        {"label": "CPA", "value": f"${cpa:,.2f}"},
        {"label": "Conversions", "value": f"{conversions:,}"},
    ]

    return CopilotResponse(
        message=" ".join(parts),
        suggestions=[
            "What's my ROAS?",
            "Which campaigns are most efficient?",
            "Any anomalies in spend?",
        ],
        data_cards=data_cards,
        intent="spend_analysis",
    )


def generate_roas_response(
    metrics: Optional[Dict] = None,
) -> CopilotResponse:
    """Generate ROAS analysis response."""
    if not metrics or metrics.get("spend", 0) == 0:
        return CopilotResponse(
            message="No ROAS data available yet. I need campaign spend and revenue data to analyze.",
            suggestions=["Show me performance", "Check signal health"],
            intent="roas_analysis",
        )

    roas = metrics.get("roas", 0)
    spend = metrics.get("spend", 0)
    revenue = metrics.get("revenue", 0)

    if roas >= 4:
        quality = "exceptional"
        advice = "Consider scaling budget on your top performers."
    elif roas >= 3:
        quality = "strong"
        advice = "Good efficiency — look for opportunities to scale."
    elif roas >= 2:
        quality = "healthy"
        advice = "Solid baseline — focus on optimizing underperformers."
    elif roas >= 1:
        quality = "break-even"
        advice = "You're covering costs but margins are thin. Audit low-ROAS campaigns."
    else:
        quality = "below target"
        advice = "You're spending more than earning. Review campaigns urgently."

    message = (
        f"Your overall ROAS is **{roas:.2f}x** — that's **{quality}**. "
        f"Revenue: **${revenue:,.0f}** / Spend: **${spend:,.0f}**. "
        f"{advice}"
    )

    data_cards = [
        {"label": "ROAS", "value": f"{roas:.2f}x", "status": "healthy" if roas >= 2 else "degraded"},
        {"label": "Revenue", "value": f"${revenue:,.0f}"},
        {"label": "Spend", "value": f"${spend:,.0f}"},
    ]

    return CopilotResponse(
        message=message,
        suggestions=[
            "Which campaigns have the best ROAS?",
            "Show me spend breakdown",
            "Any recommendations?",
        ],
        data_cards=data_cards,
        intent="roas_analysis",
    )


def generate_recommendations_response(
    metrics: Optional[Dict] = None,
    health_data: Optional[Dict] = None,
    anomaly_data: Optional[Dict] = None,
) -> CopilotResponse:
    """Generate recommendations based on all available data."""
    recommendations = []

    # Signal health recommendations
    if health_data:
        status = health_data.get("status", "unknown")
        if status == "critical":
            recommendations.append(
                "**Fix signal health immediately** — your data quality is critical. "
                "Check the Signal Recovery panel on your dashboard."
            )
        elif status == "degraded":
            recommendations.append(
                "**Investigate signal degradation** — EMQ or event loss may be affecting "
                "your campaign optimization. Check CAPI and pixel setup."
            )

    # Anomaly-based recommendations
    if anomaly_data:
        critical = anomaly_data.get("critical_count", 0)
        correlations = anomaly_data.get("correlations", [])
        if critical > 0:
            recommendations.append(
                f"**Address {critical} critical anomal{'y' if critical == 1 else 'ies'}** — "
                "check the Anomaly Intelligence panel for details and recommended actions."
            )
        for corr in correlations[:2]:
            if corr.get("severity") in ("critical", "high"):
                recommendations.append(f"**{corr.get('title', '')}** — {corr.get('description', '')[:100]}.")

    # Performance-based recommendations
    if metrics:
        roas = metrics.get("roas", 0)
        spend = metrics.get("spend", 0)
        if 0 < roas < 1.5 and spend > 0:
            recommendations.append(
                "**Review low-ROAS campaigns** — consider pausing campaigns below 1x ROAS "
                "and reallocating budget to top performers."
            )
        elif roas >= 3 and spend > 0:
            recommendations.append(
                "**Consider scaling** — your ROAS is strong. Try increasing budget "
                "by 15-20% on your best-performing campaigns."
            )

    if not recommendations:
        recommendations.append(
            "Everything looks stable. Keep monitoring your dashboard and I'll alert you "
            "when I spot opportunities or issues."
        )

    numbered = [f"{i+1}. {r}" for i, r in enumerate(recommendations[:5])]

    return CopilotResponse(
        message="Here are my recommendations:\n\n" + "\n".join(numbered),
        suggestions=[
            "Show me performance",
            "Check signal health",
            "Any anomalies?",
        ],
        intent="recommendations",
    )


def generate_campaigns_response(
    metrics: Optional[Dict] = None,
) -> CopilotResponse:
    """Generate campaign-focused response."""
    active = metrics.get("active_campaigns", 0) if metrics else 0
    total = metrics.get("total_campaigns", 0) if metrics else 0

    if total == 0:
        return CopilotResponse(
            message="No campaigns found. Connect your ad platforms and sync campaign data to get started.",
            suggestions=["How do I connect platforms?", "Help"],
            intent="campaigns",
        )

    message = (
        f"You have **{active}** active campaigns out of **{total}** total. "
    )

    if metrics and metrics.get("spend", 0) > 0:
        message += (
            f"Total spend: **${metrics['spend']:,.0f}** with "
            f"**{metrics.get('conversions', 0):,}** conversions. "
        )

    message += (
        "For detailed performance by campaign, check the Campaigns table on your dashboard."
    )

    return CopilotResponse(
        message=message,
        suggestions=[
            "Which campaign performs best?",
            "Show me ROAS analysis",
            "Any anomalies?",
        ],
        data_cards=[
            {"label": "Active Campaigns", "value": str(active)},
            {"label": "Total Campaigns", "value": str(total)},
        ],
        intent="campaigns",
    )


def generate_help_response() -> CopilotResponse:
    """Generate help/capabilities response."""
    return CopilotResponse(
        message=(
            "I'm your Stratum AI Copilot! Here's what I can help with:\n\n"
            "**Performance** — \"How are my campaigns doing?\" or \"Show me an overview\"\n\n"
            "**Signal Health** — \"Is my signal healthy?\" or \"Check EMQ\"\n\n"
            "**Anomalies** — \"Any anomalies?\" or \"Is anything unusual?\"\n\n"
            "**Spend & ROAS** — \"How much am I spending?\" or \"What's my ROAS?\"\n\n"
            "**Recommendations** — \"What should I do?\" or \"Give me advice\"\n\n"
            "**Campaigns** — \"How many campaigns are active?\" or \"Show me campaigns\"\n\n"
            "Just ask in plain English and I'll fetch the latest data for you!"
        ),
        suggestions=[
            "How are my campaigns doing?",
            "Any anomalies today?",
            "What's my signal health?",
            "What should I do next?",
        ],
        intent="help",
    )


def generate_unknown_response(message: str) -> CopilotResponse:
    """Generate a response for unrecognized intents."""
    return CopilotResponse(
        message=(
            "I'm not sure I understood that. I can help with campaign performance, "
            "signal health, anomalies, spend analysis, ROAS, and recommendations. "
            "Try one of the suggestions below!"
        ),
        suggestions=[
            "How are my campaigns doing?",
            "Any anomalies?",
            "What's my signal health?",
            "Help",
        ],
        intent="unknown",
    )


# =============================================================================
# Main Agent Entry Point
# =============================================================================

def process_message(
    message: str,
    user_name: Optional[str] = None,
    metrics: Optional[Dict] = None,
    health_data: Optional[Dict] = None,
    anomaly_data: Optional[Dict] = None,
) -> CopilotResponse:
    """
    Process a user message and return a copilot response.

    Args:
        message: User's natural language query
        user_name: User's display name for personalization
        metrics: Dashboard metrics data (spend, revenue, ROAS, etc.)
        health_data: Signal health data
        anomaly_data: Anomaly narratives data

    Returns:
        CopilotResponse with message, suggestions, and data cards
    """
    intent = classify_intent(message)

    logger.info("copilot_intent_classified", intent=intent.value, message_preview=message[:50])

    if intent == CopilotIntent.GREETING:
        return generate_greeting_response(user_name)
    elif intent == CopilotIntent.PERFORMANCE_OVERVIEW:
        return generate_performance_response(metrics)
    elif intent == CopilotIntent.SIGNAL_HEALTH:
        return generate_signal_health_response(health_data)
    elif intent == CopilotIntent.ANOMALIES:
        return generate_anomaly_response(anomaly_data)
    elif intent == CopilotIntent.SPEND_ANALYSIS:
        return generate_spend_response(metrics)
    elif intent == CopilotIntent.ROAS_ANALYSIS:
        return generate_roas_response(metrics)
    elif intent == CopilotIntent.RECOMMENDATIONS:
        return generate_recommendations_response(metrics, health_data, anomaly_data)
    elif intent == CopilotIntent.CAMPAIGNS:
        return generate_campaigns_response(metrics)
    elif intent == CopilotIntent.HELP:
        return generate_help_response()
    else:
        return generate_unknown_response(message)
