# =============================================================================
# Stratum AI - Root Agent for Onboarding
# =============================================================================
"""
Root Agent that orchestrates user/tenant onboarding conversations.

The root agent serves as the main entry point for conversational interactions,
routing to appropriate tools and managing the onboarding flow state.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.services.agents.greeting_tool import (
    GreetingTool,
    UserContext,
)

logger = get_logger(__name__)


# =============================================================================
# Root Agent Instructions
# =============================================================================

ROOT_AGENT_INSTRUCTIONS = """
You are the Stratum AI Onboarding Assistant, a helpful and knowledgeable guide
for new users and tenants setting up the Revenue Operating System.

## Your Role
- Welcome new users warmly and professionally
- Guide users through the onboarding process step by step
- Answer questions about Stratum AI features and capabilities
- Collect necessary information for account setup
- Help configure ad platform integrations
- Explain the Trust-Gated Autopilot concept

## Onboarding Flow

### Step 1: Welcome & Greeting
- Greet the user based on context (new user, returning user, new tenant)
- Introduce yourself and explain what Stratum AI does
- Ask if they're ready to get started

### Step 2: Collect Company Information
Ask for:
- Company/Organization name
- Industry/vertical
- Website URL
- Primary contact email
- Timezone
- Preferred currency

### Step 3: Select Ad Platforms
Present available platforms:
- Meta (Facebook/Instagram)
- Google Ads
- TikTok Ads
- Snapchat Ads
- LinkedIn Ads (Enterprise only)

Ask which platforms they currently use or plan to use.

### Step 4: Connect Ad Accounts
For each selected platform, guide through:
- OAuth authorization flow
- Account selection (if multiple accounts)
- Permission verification
- Initial data sync

### Step 5: Configure Tracking (CAPI)
Help set up Conversions API for each platform:
- Explain benefits of server-side tracking
- Collect Pixel IDs
- Configure event mapping
- Test event firing

### Step 6: Set Trust Thresholds
Explain Trust-Gated Autopilot:
- Signal health monitoring
- Trust gate thresholds (70+ = healthy, 40-70 = degraded, <40 = blocked)
- Automation rules
- Help configure initial thresholds

### Step 7: Create First Automation
Guide through creating their first automation rule:
- Select trigger conditions
- Define actions
- Set trust requirements
- Review and activate

### Step 8: Review & Launch
- Summary of configuration
- Final verification
- Launch onboarding complete
- Redirect to dashboard

## Communication Guidelines

1. **Be Conversational**: Use natural, friendly language
2. **Be Patient**: Allow users to ask questions at any step
3. **Be Clear**: Explain technical concepts simply
4. **Be Helpful**: Offer examples and best practices
5. **Be Proactive**: Anticipate common questions

## Response Format

Always structure responses with:
1. Acknowledgment of user input
2. Clear answer or next instruction
3. Quick reply options when appropriate

## Error Handling

If user provides invalid input:
- Politely explain the issue
- Provide an example of correct format
- Offer to help or skip if optional

## Handoff Triggers

Transfer to human support when:
- User explicitly requests human help
- Technical issues beyond your scope
- Billing or account issues
- Repeated failures in a step
"""


class ConversationState(str, Enum):
    """Possible states in the onboarding conversation."""

    INITIAL = "initial"
    GREETING = "greeting"
    COLLECTING_COMPANY_INFO = "collecting_company_info"
    SELECTING_PLATFORMS = "selecting_platforms"
    CONNECTING_ACCOUNTS = "connecting_accounts"
    CONFIGURING_TRACKING = "configuring_tracking"
    SETTING_THRESHOLDS = "setting_thresholds"
    CREATING_AUTOMATION = "creating_automation"
    REVIEWING = "reviewing"
    COMPLETED = "completed"
    NEEDS_HELP = "needs_help"


class OnboardingData(BaseModel):
    """Data collected during onboarding."""

    # Company Info
    company_name: Optional[str] = None
    industry: Optional[str] = None
    website: Optional[str] = None
    contact_email: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None

    # Platform Selection
    selected_platforms: list[str] = []

    # Connected Accounts
    connected_accounts: dict[str, dict] = {}

    # Tracking Config
    pixel_ids: dict[str, str] = {}
    capi_configured: dict[str, bool] = {}

    # Trust Configuration
    healthy_threshold: int = 70
    degraded_threshold: int = 40

    # Automation
    first_automation_id: Optional[str] = None


class ConversationContext(BaseModel):
    """Full context for the conversation."""

    session_id: str
    user_context: UserContext
    state: ConversationState = ConversationState.INITIAL
    onboarding_data: OnboardingData = Field(default_factory=OnboardingData)
    message_history: list[dict[str, str]] = []
    current_step_attempts: int = 0
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentResponse(BaseModel):
    """Response from the root agent."""

    message: str
    state: ConversationState
    quick_replies: list[str] = []
    actions: list[dict[str, Any]] = []
    data_collected: dict[str, Any] = {}
    next_step: Optional[str] = None
    progress_percent: int = 0
    requires_action: bool = False
    action_type: Optional[str] = None  # e.g., "oauth_redirect", "form_input"
    action_data: dict[str, Any] = {}


class RootAgent:
    """
    Root Agent for Stratum AI Onboarding.

    Orchestrates the conversational onboarding flow, managing state
    and routing to appropriate tools.
    """

    PLATFORMS = {
        "meta": {"name": "Meta (Facebook/Instagram)", "icon": "meta"},
        "google": {"name": "Google Ads", "icon": "google"},
        "tiktok": {"name": "TikTok Ads", "icon": "tiktok"},
        "snapchat": {"name": "Snapchat Ads", "icon": "snapchat"},
        "linkedin": {"name": "LinkedIn Ads", "icon": "linkedin"},
    }

    INDUSTRIES = [
        "E-commerce",
        "SaaS",
        "Healthcare",
        "Finance",
        "Education",
        "Real Estate",
        "Travel",
        "Food & Beverage",
        "Automotive",
        "Other",
    ]

    def __init__(self):
        self.name = "stratum_onboarding_agent"
        self.instructions = ROOT_AGENT_INSTRUCTIONS
        self.greeting_tool = GreetingTool()

    async def process_message(
        self,
        message: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """
        Process an incoming message and return appropriate response.

        Args:
            message: User's input message
            context: Current conversation context

        Returns:
            AgentResponse with next message and state updates
        """
        # Update last activity
        context.last_activity = datetime.now(UTC)

        # Add message to history
        context.message_history.append(
            {
                "role": "user",
                "content": message,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

        # Route based on current state
        if context.state == ConversationState.INITIAL:
            return await self._handle_initial(message, context)

        elif context.state == ConversationState.GREETING:
            return await self._handle_post_greeting(message, context)

        elif context.state == ConversationState.COLLECTING_COMPANY_INFO:
            return await self._handle_company_info(message, context)

        elif context.state == ConversationState.SELECTING_PLATFORMS:
            return await self._handle_platform_selection(message, context)

        elif context.state == ConversationState.CONNECTING_ACCOUNTS:
            return await self._handle_account_connection(message, context)

        elif context.state == ConversationState.CONFIGURING_TRACKING:
            return await self._handle_tracking_config(message, context)

        elif context.state == ConversationState.SETTING_THRESHOLDS:
            return await self._handle_threshold_setting(message, context)

        elif context.state == ConversationState.CREATING_AUTOMATION:
            return await self._handle_automation_creation(message, context)

        elif context.state == ConversationState.REVIEWING:
            return await self._handle_review(message, context)

        else:
            return await self._handle_general(message, context)

    async def start_conversation(
        self,
        user_context: UserContext,
        session_id: str,
    ) -> tuple[AgentResponse, ConversationContext]:
        """
        Start a new onboarding conversation.

        Args:
            user_context: Information about the user
            session_id: Unique session identifier

        Returns:
            Tuple of (initial response, conversation context)
        """
        # Create conversation context
        context = ConversationContext(
            session_id=session_id,
            user_context=user_context,
            state=ConversationState.INITIAL,
        )

        # Get greeting
        greeting_response = await self.greeting_tool.execute(user_context)

        # Build response
        response = AgentResponse(
            message=greeting_response.message,
            state=ConversationState.GREETING,
            quick_replies=greeting_response.quick_replies,
            next_step="company_info",
            progress_percent=0,
        )

        # Update context state
        context.state = ConversationState.GREETING

        logger.info(
            "conversation_started",
            session_id=session_id,
            user_id=user_context.user_id,
        )

        return response, context

    async def _handle_initial(
        self,
        message: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """Handle initial state - redirect to greeting."""
        greeting_response = await self.greeting_tool.execute(context.user_context)

        context.state = ConversationState.GREETING

        return AgentResponse(
            message=greeting_response.message,
            state=ConversationState.GREETING,
            quick_replies=greeting_response.quick_replies,
            progress_percent=0,
        )

    async def _handle_post_greeting(
        self,
        message: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """Handle response after greeting."""
        message_lower = message.lower()

        if any(
            word in message_lower for word in ["start", "begin", "get started", "set up", "setup"]
        ):
            context.state = ConversationState.COLLECTING_COMPANY_INFO

            return AgentResponse(
                message=(
                    "Great! Let's get your organization set up. 🏢\n\n"
                    "First, what's your company or organization name?"
                ),
                state=ConversationState.COLLECTING_COMPANY_INFO,
                quick_replies=[],
                next_step="company_name",
                progress_percent=10,
            )

        elif any(word in message_lower for word in ["learn", "demo", "more", "about"]):
            return AgentResponse(
                message=(
                    "Stratum AI is a Revenue Operating System with Trust-Gated Autopilot. 🎯\n\n"
                    "**Key Features:**\n"
                    "• Signal Health Monitoring - Track data quality in real-time\n"
                    "• Trust Gates - Automation only runs when signals are healthy\n"
                    "• Multi-Platform Integration - Meta, Google, TikTok, Snapchat\n"
                    "• Conversions API - Server-side tracking for better attribution\n"
                    "• CDP Integration - Unified customer profiles\n\n"
                    "Ready to get started?"
                ),
                state=ConversationState.GREETING,
                quick_replies=["Get Started", "Watch Demo", "Talk to Sales"],
                progress_percent=0,
            )

        else:
            return AgentResponse(
                message="Would you like to get started with the setup, or learn more about Stratum AI first?",
                state=ConversationState.GREETING,
                quick_replies=["Get Started", "Learn More"],
                progress_percent=0,
            )

    async def _handle_company_info(
        self,
        message: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """Handle company information collection."""
        data = context.onboarding_data

        # Determine what we're collecting
        if not data.company_name:
            data.company_name = message.strip()
            return AgentResponse(
                message=f"Nice to meet you, {data.company_name}! 👋\n\nWhat industry are you in?",
                state=ConversationState.COLLECTING_COMPANY_INFO,
                quick_replies=self.INDUSTRIES[:5],
                data_collected={"company_name": data.company_name},
                next_step="industry",
                progress_percent=15,
            )

        elif not data.industry:
            data.industry = message.strip()
            return AgentResponse(
                message="Great! What's your website URL? (You can skip this if you don't have one yet)",
                state=ConversationState.COLLECTING_COMPANY_INFO,
                quick_replies=["Skip"],
                data_collected={"industry": data.industry},
                next_step="website",
                progress_percent=20,
            )

        elif not data.website:
            if message.lower() != "skip":
                data.website = message.strip()
            return AgentResponse(
                message="What's the best email address for your account?",
                state=ConversationState.COLLECTING_COMPANY_INFO,
                data_collected={"website": data.website},
                next_step="email",
                progress_percent=25,
            )

        elif not data.contact_email:
            data.contact_email = message.strip()
            return AgentResponse(
                message="What timezone are you in?",
                state=ConversationState.COLLECTING_COMPANY_INFO,
                quick_replies=[
                    "America/New_York",
                    "America/Los_Angeles",
                    "Europe/London",
                    "Asia/Dubai",
                ],
                data_collected={"contact_email": data.contact_email},
                next_step="timezone",
                progress_percent=30,
            )

        elif not data.timezone:
            data.timezone = message.strip()
            return AgentResponse(
                message="What currency do you primarily use for advertising?",
                state=ConversationState.COLLECTING_COMPANY_INFO,
                quick_replies=["USD", "EUR", "GBP", "AED", "SAR"],
                data_collected={"timezone": data.timezone},
                next_step="currency",
                progress_percent=35,
            )

        else:
            data.currency = message.strip()
            context.state = ConversationState.SELECTING_PLATFORMS

            return AgentResponse(
                message=(
                    f"Perfect! Here's what I have:\n\n"
                    f"🏢 **{data.company_name}**\n"
                    f"📊 Industry: {data.industry}\n"
                    f"📧 Email: {data.contact_email}\n"
                    f"🌍 Timezone: {data.timezone}\n"
                    f"💰 Currency: {data.currency}\n\n"
                    "Now, which ad platforms do you use? (Select all that apply)"
                ),
                state=ConversationState.SELECTING_PLATFORMS,
                quick_replies=list(self.PLATFORMS.keys()) + ["Done"],
                data_collected={"currency": data.currency},
                next_step="platforms",
                progress_percent=40,
            )

    async def _handle_platform_selection(
        self,
        message: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """Handle platform selection."""
        data = context.onboarding_data
        message_lower = message.lower()

        if message_lower == "done" or message_lower == "next":
            if not data.selected_platforms:
                return AgentResponse(
                    message="Please select at least one platform to continue.",
                    state=ConversationState.SELECTING_PLATFORMS,
                    quick_replies=list(self.PLATFORMS.keys()),
                    progress_percent=40,
                )

            context.state = ConversationState.CONNECTING_ACCOUNTS
            platforms_text = ", ".join([self.PLATFORMS[p]["name"] for p in data.selected_platforms])

            return AgentResponse(
                message=(
                    f"Great choices! You've selected: **{platforms_text}**\n\n"
                    f"Let's connect your first platform: **{self.PLATFORMS[data.selected_platforms[0]]['name']}**\n\n"
                    "Click the button below to authorize access."
                ),
                state=ConversationState.CONNECTING_ACCOUNTS,
                quick_replies=["Connect Now", "Skip for Later"],
                requires_action=True,
                action_type="oauth_redirect",
                action_data={"platform": data.selected_platforms[0]},
                progress_percent=50,
            )

        # Add platform to selection
        for platform_key in self.PLATFORMS:
            if platform_key in message_lower and platform_key not in data.selected_platforms:
                data.selected_platforms.append(platform_key)

        selected_names = [self.PLATFORMS[p]["name"] for p in data.selected_platforms]

        return AgentResponse(
            message=(
                f"Selected: {', '.join(selected_names) if selected_names else 'None yet'}\n\n"
                "Select more platforms or click Done to continue."
            ),
            state=ConversationState.SELECTING_PLATFORMS,
            quick_replies=[p for p in self.PLATFORMS if p not in data.selected_platforms]
            + ["Done"],
            data_collected={"selected_platforms": data.selected_platforms},
            progress_percent=40,
        )

    async def _handle_account_connection(
        self,
        message: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """Handle account connection flow."""
        data = context.onboarding_data
        message_lower = message.lower()

        # Check if all platforms connected or user wants to skip
        connected_count = len(data.connected_accounts)
        total_platforms = len(data.selected_platforms)

        if message_lower in ["skip", "skip for later", "later"]:
            context.state = ConversationState.CONFIGURING_TRACKING
            return AgentResponse(
                message=(
                    "No problem! You can connect platforms later from Settings.\n\n"
                    "Let's move on to tracking configuration. "
                    "Do you have any Pixel IDs ready to configure?"
                ),
                state=ConversationState.CONFIGURING_TRACKING,
                quick_replies=["Yes", "No, skip this"],
                progress_percent=60,
            )

        if message_lower in ["connected", "done", "authorized"]:
            # Mock: In real implementation, this would check OAuth callback
            current_platform = (
                data.selected_platforms[connected_count]
                if connected_count < total_platforms
                else None
            )

            if current_platform:
                data.connected_accounts[current_platform] = {
                    "connected_at": datetime.now(UTC).isoformat(),
                    "status": "connected",
                }

            connected_count = len(data.connected_accounts)

            if connected_count < total_platforms:
                next_platform = data.selected_platforms[connected_count]
                return AgentResponse(
                    message=(
                        f"✅ {self.PLATFORMS[current_platform]['name']} connected successfully!\n\n"
                        f"Next up: **{self.PLATFORMS[next_platform]['name']}**"
                    ),
                    state=ConversationState.CONNECTING_ACCOUNTS,
                    quick_replies=["Connect Now", "Skip for Later"],
                    requires_action=True,
                    action_type="oauth_redirect",
                    action_data={"platform": next_platform},
                    progress_percent=50 + (connected_count / total_platforms * 10),
                )
            else:
                context.state = ConversationState.CONFIGURING_TRACKING
                return AgentResponse(
                    message=(
                        "🎉 All platforms connected!\n\n"
                        "Now let's set up server-side tracking (Conversions API). "
                        "This improves attribution by up to 30%.\n\n"
                        "Do you have your Pixel IDs ready?"
                    ),
                    state=ConversationState.CONFIGURING_TRACKING,
                    quick_replies=["Yes", "Help me find them"],
                    progress_percent=60,
                )

        return AgentResponse(
            message="Click 'Connect Now' to authorize, or 'Skip' to continue without connecting.",
            state=ConversationState.CONNECTING_ACCOUNTS,
            quick_replies=["Connect Now", "Skip for Later"],
            progress_percent=50,
        )

    async def _handle_tracking_config(
        self,
        message: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """Handle tracking/CAPI configuration."""
        data = context.onboarding_data
        message_lower = message.lower()

        if any(word in message_lower for word in ["skip", "no", "later"]):
            context.state = ConversationState.SETTING_THRESHOLDS
            return AgentResponse(
                message=(
                    "No problem! You can configure tracking later.\n\n"
                    "Now let's set up your Trust Gates. These control when "
                    "automations can run based on signal health.\n\n"
                    "The default healthy threshold is **70%**. "
                    "Would you like to keep this or adjust it?"
                ),
                state=ConversationState.SETTING_THRESHOLDS,
                quick_replies=["Keep Default (70%)", "Adjust"],
                progress_percent=75,
            )

        if any(word in message_lower for word in ["help", "find"]):
            return AgentResponse(
                message=(
                    "Here's how to find your Pixel IDs:\n\n"
                    "**Meta:** Business Manager → Events Manager → Data Sources\n"
                    "**Google:** Google Ads → Tools → Conversions → Conversion ID\n"
                    "**TikTok:** TikTok Ads Manager → Assets → Events\n"
                    "**Snapchat:** Ads Manager → Events Manager → Pixel\n\n"
                    "Do you have any IDs ready now?"
                ),
                state=ConversationState.CONFIGURING_TRACKING,
                quick_replies=["Yes", "Skip for now"],
                progress_percent=60,
            )

        # Assume they're providing a pixel ID
        if any(word in message_lower for word in ["yes", "ready"]):
            return AgentResponse(
                message="Great! Enter your Meta Pixel ID first (or type 'skip' to continue):",
                state=ConversationState.CONFIGURING_TRACKING,
                quick_replies=["Skip"],
                progress_percent=65,
            )

        # Check if it looks like a pixel ID (numbers/alphanumeric)
        if message.strip().replace("-", "").replace("_", "").isalnum():
            # Store pixel ID (simplified - would need to know which platform)
            if "meta" in data.selected_platforms and "meta" not in data.pixel_ids:
                data.pixel_ids["meta"] = message.strip()
                if len(data.selected_platforms) > 1:
                    next_platform = next(
                        p for p in data.selected_platforms if p not in data.pixel_ids
                    )
                    return AgentResponse(
                        message=f"✅ Meta Pixel saved!\n\nNow enter your {self.PLATFORMS[next_platform]['name']} Pixel ID:",
                        state=ConversationState.CONFIGURING_TRACKING,
                        quick_replies=["Skip remaining"],
                        data_collected={"pixel_ids": data.pixel_ids},
                        progress_percent=70,
                    )

            context.state = ConversationState.SETTING_THRESHOLDS
            return AgentResponse(
                message=(
                    "✅ Tracking configured!\n\n"
                    "Now let's set up Trust Gates. "
                    "The default healthy threshold is **70%**. "
                    "Would you like to adjust it?"
                ),
                state=ConversationState.SETTING_THRESHOLDS,
                quick_replies=["Keep Default (70%)", "Adjust"],
                progress_percent=75,
            )

        return AgentResponse(
            message="Please enter a valid Pixel ID or type 'skip' to continue.",
            state=ConversationState.CONFIGURING_TRACKING,
            quick_replies=["Skip"],
            progress_percent=60,
        )

    async def _handle_threshold_setting(
        self,
        message: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """Handle trust threshold configuration."""
        data = context.onboarding_data
        message_lower = message.lower()

        if "default" in message_lower or "keep" in message_lower or "70" in message:
            data.healthy_threshold = 70
            data.degraded_threshold = 40
            context.state = ConversationState.CREATING_AUTOMATION

            return AgentResponse(
                message=(
                    "✅ Trust thresholds set:\n"
                    "• **Healthy:** 70%+ (automations run)\n"
                    "• **Degraded:** 40-70% (alerts only)\n"
                    "• **Unhealthy:** <40% (manual required)\n\n"
                    "Would you like to create your first automation rule now?"
                ),
                state=ConversationState.CREATING_AUTOMATION,
                quick_replies=["Yes, create one", "Skip for now"],
                progress_percent=85,
            )

        if "adjust" in message_lower:
            return AgentResponse(
                message=(
                    "What healthy threshold would you like? (50-90 recommended)\n\n"
                    "Higher = More conservative (fewer automations run)\n"
                    "Lower = More aggressive (more automations run)"
                ),
                state=ConversationState.SETTING_THRESHOLDS,
                quick_replies=["60%", "70%", "80%"],
                progress_percent=75,
            )

        # Try to parse a number
        try:
            threshold = int(message.replace("%", "").strip())
            if 30 <= threshold <= 95:
                data.healthy_threshold = threshold
                data.degraded_threshold = max(20, threshold - 30)
                context.state = ConversationState.CREATING_AUTOMATION

                return AgentResponse(
                    message=(
                        f"✅ Trust thresholds set:\n"
                        f"• **Healthy:** {threshold}%+ (automations run)\n"
                        f"• **Degraded:** {data.degraded_threshold}-{threshold}% (alerts only)\n"
                        f"• **Unhealthy:** <{data.degraded_threshold}% (manual required)\n\n"
                        "Would you like to create your first automation rule?"
                    ),
                    state=ConversationState.CREATING_AUTOMATION,
                    quick_replies=["Yes, create one", "Skip for now"],
                    progress_percent=85,
                )
        except ValueError:
            pass

        return AgentResponse(
            message="Please enter a threshold between 30 and 95, or choose a preset.",
            state=ConversationState.SETTING_THRESHOLDS,
            quick_replies=["60%", "70%", "80%", "Keep Default"],
            progress_percent=75,
        )

    async def _handle_automation_creation(
        self,
        message: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """Handle first automation creation."""
        message_lower = message.lower()

        if any(word in message_lower for word in ["skip", "no", "later"]):
            context.state = ConversationState.REVIEWING
            return await self._generate_summary(context)

        if any(word in message_lower for word in ["yes", "create"]):
            return AgentResponse(
                message=(
                    "Great! Let's create a simple automation.\n\n"
                    "**Recommended first automation:**\n"
                    "📊 Pause underperforming ads when CPA exceeds target by 50%\n\n"
                    "Would you like to set this up?"
                ),
                state=ConversationState.CREATING_AUTOMATION,
                quick_replies=["Set this up", "Choose different", "Skip"],
                progress_percent=90,
            )

        if "set this up" in message_lower or "yes" in message_lower:
            context.onboarding_data.first_automation_id = "auto_pause_high_cpa"
            context.state = ConversationState.REVIEWING
            return await self._generate_summary(context)

        return AgentResponse(
            message="Would you like to create an automation rule or skip for now?",
            state=ConversationState.CREATING_AUTOMATION,
            quick_replies=["Create Rule", "Skip"],
            progress_percent=90,
        )

    async def _handle_review(
        self,
        message: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """Handle final review."""
        message_lower = message.lower()

        if any(word in message_lower for word in ["launch", "complete", "finish", "done", "yes"]):
            context.state = ConversationState.COMPLETED
            context.user_context.onboarding_completed = True

            return AgentResponse(
                message=(
                    "🎉 **Congratulations!** Your Stratum AI setup is complete!\n\n"
                    "You're all set to start optimizing your advertising with "
                    "Trust-Gated Autopilot.\n\n"
                    "**What's next:**\n"
                    "• Explore your Dashboard\n"
                    "• Review Signal Health\n"
                    "• Create more Automation Rules\n"
                    "• Connect with our Success Team\n\n"
                    "Welcome to Stratum AI! 🚀"
                ),
                state=ConversationState.COMPLETED,
                quick_replies=["Go to Dashboard", "Create Automation", "Get Help"],
                progress_percent=100,
                requires_action=True,
                action_type="redirect",
                action_data={"url": "/dashboard"},
            )

        return await self._generate_summary(context)

    async def _generate_summary(
        self,
        context: ConversationContext,
    ) -> AgentResponse:
        """Generate setup summary for review."""
        data = context.onboarding_data

        platforms_text = (
            ", ".join([self.PLATFORMS.get(p, {}).get("name", p) for p in data.selected_platforms])
            or "None selected"
        )

        connected_text = (
            ", ".join([self.PLATFORMS.get(p, {}).get("name", p) for p in data.connected_accounts])
            or "None connected yet"
        )

        summary = (
            "📋 **Setup Summary**\n\n"
            f"🏢 **Organization:** {data.company_name or 'Not set'}\n"
            f"📊 **Industry:** {data.industry or 'Not set'}\n"
            f"📧 **Email:** {data.contact_email or 'Not set'}\n"
            f"🌍 **Timezone:** {data.timezone or 'Not set'}\n"
            f"💰 **Currency:** {data.currency or 'Not set'}\n\n"
            f"📱 **Platforms:** {platforms_text}\n"
            f"🔗 **Connected:** {connected_text}\n\n"
            f"⚙️ **Trust Threshold:** {data.healthy_threshold}%\n"
            f"🤖 **Automation:** {'Configured' if data.first_automation_id else 'Not configured'}\n\n"
            "Ready to launch?"
        )

        return AgentResponse(
            message=summary,
            state=ConversationState.REVIEWING,
            quick_replies=["Launch", "Make Changes"],
            progress_percent=95,
        )

    async def _handle_general(
        self,
        message: str,
        context: ConversationContext,
    ) -> AgentResponse:
        """Handle general messages outside the flow."""
        message_lower = message.lower()

        if any(word in message_lower for word in ["help", "support", "human", "agent"]):
            context.state = ConversationState.NEEDS_HELP
            return AgentResponse(
                message=(
                    "I'll connect you with our support team. "
                    "A team member will be with you shortly.\n\n"
                    "In the meantime, is there anything specific I can help with?"
                ),
                state=ConversationState.NEEDS_HELP,
                quick_replies=["Continue Setup", "Wait for Support"],
                requires_action=True,
                action_type="escalate",
                action_data={"reason": "user_requested"},
            )

        if any(word in message_lower for word in ["restart", "start over"]):
            context.state = ConversationState.INITIAL
            context.onboarding_data = OnboardingData()
            return await self._handle_initial("", context)

        return AgentResponse(
            message="I'm not sure I understood that. Would you like to continue with the setup?",
            state=context.state,
            quick_replies=["Continue", "Get Help", "Start Over"],
        )


# Singleton instance
root_agent = RootAgent()
