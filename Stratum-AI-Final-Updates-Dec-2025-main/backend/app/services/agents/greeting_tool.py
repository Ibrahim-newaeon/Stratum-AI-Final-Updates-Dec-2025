# =============================================================================
# Stratum AI - Greeting Tool
# =============================================================================
"""
Greeting Tool for Conversational Onboarding Agent.

This tool handles initial user greetings and collects basic information
to personalize the onboarding experience.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel

from app.core.logging import get_logger

logger = get_logger(__name__)


class GreetingType(str, Enum):
    """Types of greetings based on context."""

    NEW_USER = "new_user"
    RETURNING_USER = "returning_user"
    NEW_TENANT = "new_tenant"
    SUPPORT = "support"
    GENERAL = "general"


class UserContext(BaseModel):
    """Context information about the user."""

    user_id: Optional[str] = None
    tenant_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    timezone: Optional[str] = None
    language: str = "en"
    is_new_user: bool = True
    last_visit: Optional[datetime] = None
    onboarding_completed: bool = False
    current_step: Optional[str] = None


class GreetingResponse(BaseModel):
    """Response from the greeting tool."""

    message: str
    greeting_type: GreetingType
    suggested_actions: list[str] = []
    next_step: Optional[str] = None
    context: dict[str, Any] = {}
    quick_replies: list[str] = []


class GreetingTool:
    """
    Greeting Tool for Stratum AI Onboarding Agent.

    Handles:
    - Initial user greetings
    - Context-aware welcome messages
    - Personalized onboarding flow initiation
    - Language detection and localization
    """

    GREETINGS = {
        "en": {
            "new_user": "Welcome to Stratum AI! 👋 I'm your onboarding assistant. I'll help you get set up with our Revenue Operating System.",
            "returning_user": "Welcome back, {name}! 👋 Great to see you again.",
            "new_tenant": "Welcome to Stratum AI! 🚀 Let's set up your organization and get you started with Trust-Gated Autopilot.",
            "support": "Hi {name}! 👋 I'm here to help. What can I assist you with today?",
            "general": "Hello! 👋 Welcome to Stratum AI. How can I help you today?",
        },
        "ar": {
            "new_user": "مرحباً بك في Stratum AI! 👋 أنا مساعد الإعداد الخاص بك. سأساعدك في إعداد نظام تشغيل الإيرادات.",
            "returning_user": "مرحباً بعودتك، {name}! 👋 سعيد برؤيتك مرة أخرى.",
            "new_tenant": "مرحباً بك في Stratum AI! 🚀 دعنا نقوم بإعداد مؤسستك.",
            "support": "مرحباً {name}! 👋 أنا هنا للمساعدة. كيف يمكنني مساعدتك اليوم؟",
            "general": "مرحباً! 👋 أهلاً بك في Stratum AI. كيف يمكنني مساعدتك؟",
        },
    }

    ONBOARDING_STEPS = [
        "welcome",
        "collect_company_info",
        "select_platforms",
        "connect_ad_accounts",
        "configure_tracking",
        "set_trust_thresholds",
        "create_first_automation",
        "review_and_launch",
    ]

    QUICK_REPLIES = {
        "new_user": [
            "Get Started",
            "Learn More",
            "Watch Demo",
            "Talk to Sales",
        ],
        "new_tenant": [
            "Set Up Organization",
            "Connect Ad Platforms",
            "Import Data",
            "Schedule Demo",
        ],
        "returning_user": [
            "View Dashboard",
            "Check Automations",
            "View Reports",
            "Get Help",
        ],
    }

    def __init__(self):
        self.name = "greeting_tool"
        self.description = "Handles user greetings and initiates onboarding flow"

    async def execute(
        self,
        user_context: Optional[UserContext] = None,
        input_message: Optional[str] = None,
    ) -> GreetingResponse:
        """
        Execute the greeting tool.

        Args:
            user_context: Context about the user (if known)
            input_message: Optional input message from user

        Returns:
            GreetingResponse with personalized greeting
        """
        context = user_context or UserContext()

        # Determine greeting type
        greeting_type = self._determine_greeting_type(context)

        # Get localized greeting
        greeting = self._get_greeting(greeting_type, context)

        # Get suggested actions
        actions = self._get_suggested_actions(greeting_type, context)

        # Get quick replies
        quick_replies = self._get_quick_replies(greeting_type)

        # Determine next step
        next_step = self._get_next_step(context)

        logger.info(
            "greeting_generated",
            greeting_type=greeting_type.value,
            user_id=context.user_id,
            next_step=next_step,
        )

        return GreetingResponse(
            message=greeting,
            greeting_type=greeting_type,
            suggested_actions=actions,
            next_step=next_step,
            context={
                "language": context.language,
                "is_new_user": context.is_new_user,
                "onboarding_completed": context.onboarding_completed,
            },
            quick_replies=quick_replies,
        )

    def _determine_greeting_type(self, context: UserContext) -> GreetingType:
        """Determine the appropriate greeting type based on context."""
        if context.tenant_id and not context.user_id:
            return GreetingType.NEW_TENANT

        if context.is_new_user:
            return GreetingType.NEW_USER

        if context.user_id and context.last_visit:
            return GreetingType.RETURNING_USER

        return GreetingType.GENERAL

    def _get_greeting(self, greeting_type: GreetingType, context: UserContext) -> str:
        """Get localized greeting message."""
        lang = context.language if context.language in self.GREETINGS else "en"
        greetings = self.GREETINGS[lang]

        greeting_template = greetings.get(greeting_type.value, greetings["general"])

        # Personalize with name if available
        name = context.name or "there"
        return greeting_template.format(name=name)

    def _get_suggested_actions(
        self,
        greeting_type: GreetingType,
        context: UserContext,
    ) -> list[str]:
        """Get suggested actions based on greeting type and context."""
        actions = []

        if greeting_type == GreetingType.NEW_USER:
            actions = [
                "Complete your profile",
                "Connect your first ad platform",
                "Take a product tour",
            ]
        elif greeting_type == GreetingType.NEW_TENANT:
            actions = [
                "Set up your organization",
                "Invite team members",
                "Configure integrations",
            ]
        elif greeting_type == GreetingType.RETURNING_USER:
            if not context.onboarding_completed:
                actions = [
                    f"Continue onboarding: {context.current_step or 'next step'}",
                    "View your dashboard",
                ]
            else:
                actions = [
                    "View dashboard",
                    "Check automation status",
                    "View latest reports",
                ]

        return actions

    def _get_quick_replies(self, greeting_type: GreetingType) -> list[str]:
        """Get quick reply options."""
        key = greeting_type.value
        if key in self.QUICK_REPLIES:
            return self.QUICK_REPLIES[key]
        return self.QUICK_REPLIES.get("new_user", [])

    def _get_next_step(self, context: UserContext) -> Optional[str]:
        """Determine the next onboarding step."""
        if context.onboarding_completed:
            return None

        if context.current_step:
            try:
                current_idx = self.ONBOARDING_STEPS.index(context.current_step)
                if current_idx < len(self.ONBOARDING_STEPS) - 1:
                    return self.ONBOARDING_STEPS[current_idx + 1]
            except ValueError:
                pass

        return self.ONBOARDING_STEPS[0]  # Start from beginning


# Singleton instance
greeting_tool = GreetingTool()


async def greet_user(
    user_context: Optional[UserContext] = None,
    input_message: Optional[str] = None,
) -> GreetingResponse:
    """
    Convenience function to greet a user.

    Args:
        user_context: Optional context about the user
        input_message: Optional input message

    Returns:
        GreetingResponse with personalized greeting
    """
    return await greeting_tool.execute(user_context, input_message)
