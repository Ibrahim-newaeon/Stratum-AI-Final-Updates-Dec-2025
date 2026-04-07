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
    "ROOT_AGENT_INSTRUCTIONS",
    "AgentResponse",
    "ConversationContext",
    "ConversationState",
    "GreetingResponse",
    # Greeting Tool
    "GreetingTool",
    "GreetingType",
    "OnboardingData",
    # Root Agent
    "RootAgent",
    "UserContext",
    "greet_user",
    "greeting_tool",
    "root_agent",
]
