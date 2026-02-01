# =============================================================================
# Stratum AI - Agents Package
# =============================================================================
"""
Conversational AI Agents for Stratum AI.

This package contains the agent implementations for:
- User/Tenant onboarding conversations
- Support interactions
- Guided configuration flows
"""

from app.services.agents.greeting_tool import (
    GreetingResponse,
    GreetingTool,
    GreetingType,
    UserContext,
    greet_user,
    greeting_tool,
)
from app.services.agents.root_agent import (
    ROOT_AGENT_INSTRUCTIONS,
    AgentResponse,
    ConversationContext,
    ConversationState,
    OnboardingData,
    RootAgent,
    root_agent,
)

__all__ = [
    # Greeting Tool
    "GreetingTool",
    "GreetingResponse",
    "GreetingType",
    "UserContext",
    "greet_user",
    "greeting_tool",
    # Root Agent
    "RootAgent",
    "AgentResponse",
    "ConversationContext",
    "ConversationState",
    "OnboardingData",
    "root_agent",
    "ROOT_AGENT_INSTRUCTIONS",
]
