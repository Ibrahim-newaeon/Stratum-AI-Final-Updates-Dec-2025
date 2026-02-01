# =============================================================================
# Stratum AI - Conversational Onboarding Agent API
# =============================================================================
"""
REST API endpoints for the conversational onboarding agent.

This provides a chat-like interface for onboarding new users/tenants
using the RootAgent and GreetingTool.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from redis import asyncio as aioredis

from app.auth.deps import CurrentUserDep, OptionalUserDep
from app.core.config import settings
from app.core.logging import get_logger
from app.services.agents import (
    ConversationContext,
    ConversationState,
    UserContext,
    root_agent,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/onboarding-agent", tags=["onboarding-agent"])


# =============================================================================
# Schemas
# =============================================================================


class StartConversationRequest(BaseModel):
    """Request to start a new onboarding conversation."""

    name: Optional[str] = Field(None, description="User's name if known")
    email: Optional[str] = Field(None, description="User's email if known")
    company: Optional[str] = Field(None, description="Company name if known")
    language: str = Field(default="en", description="Preferred language (en, ar)")
    is_new_tenant: bool = Field(default=False, description="Whether this is a new tenant setup")


class StartConversationResponse(BaseModel):
    """Response when starting a conversation."""

    session_id: str
    message: str
    quick_replies: list[str]
    state: str
    progress_percent: int


class SendMessageRequest(BaseModel):
    """Request to send a message to the agent."""

    session_id: str = Field(..., description="The conversation session ID")
    message: str = Field(..., min_length=1, max_length=2000, description="User's message")


class SendMessageResponse(BaseModel):
    """Response from the agent."""

    message: str
    state: str
    quick_replies: list[str]
    progress_percent: int
    next_step: Optional[str] = None
    requires_action: bool = False
    action_type: Optional[str] = None
    action_data: dict = {}
    data_collected: dict = {}


class ConversationStatusResponse(BaseModel):
    """Current conversation status."""

    session_id: str
    state: str
    progress_percent: int
    started_at: datetime
    last_activity: datetime
    onboarding_data: dict


# =============================================================================
# Session Storage (Redis)
# =============================================================================


async def get_redis_client() -> aioredis.Redis:
    """Get Redis client for session storage."""
    return await aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )


async def save_session(
    session_id: str,
    context: ConversationContext,
    redis: aioredis.Redis,
) -> None:
    """Save conversation session to Redis."""
    session_data = context.model_dump_json()
    await redis.set(
        f"onboarding_session:{session_id}",
        session_data,
        ex=86400,  # 24 hour expiry
    )


async def load_session(
    session_id: str,
    redis: aioredis.Redis,
) -> Optional[ConversationContext]:
    """Load conversation session from Redis."""
    session_data = await redis.get(f"onboarding_session:{session_id}")
    if session_data:
        return ConversationContext.model_validate_json(session_data)
    return None


async def delete_session(
    session_id: str,
    redis: aioredis.Redis,
) -> None:
    """Delete conversation session."""
    await redis.delete(f"onboarding_session:{session_id}")


# =============================================================================
# Endpoints
# =============================================================================


@router.post("/start", response_model=StartConversationResponse)
async def start_conversation(
    request: StartConversationRequest,
    current_user: OptionalUserDep = None,
):
    """
    Start a new onboarding conversation.

    Creates a new session and returns the initial greeting.
    Can be used with or without authentication.
    """
    # Generate session ID
    session_id = str(uuid4())

    # Build user context
    user_context = UserContext(
        user_id=str(current_user.id) if current_user else None,
        tenant_id=str(current_user.tenant_id) if current_user else None,
        name=request.name or (current_user.name if current_user else None),
        email=request.email or (current_user.email if current_user else None),
        company=request.company,
        language=request.language,
        is_new_user=not bool(current_user),
    )

    # If new tenant setup, mark accordingly
    if request.is_new_tenant and current_user:
        user_context.tenant_id = str(current_user.tenant_id)
        user_context.is_new_user = False

    try:
        # Start conversation with agent
        response, context = await root_agent.start_conversation(
            user_context=user_context,
            session_id=session_id,
        )

        # Save session to Redis
        redis = await get_redis_client()
        await save_session(session_id, context, redis)
        await redis.aclose()

        logger.info(
            "onboarding_conversation_started",
            session_id=session_id,
            user_id=user_context.user_id,
            language=request.language,
        )

        return StartConversationResponse(
            session_id=session_id,
            message=response.message,
            quick_replies=response.quick_replies,
            state=response.state.value,
            progress_percent=response.progress_percent,
        )

    except Exception as e:
        logger.error(
            "onboarding_start_failed",
            error=str(e),
            session_id=session_id,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start onboarding conversation",
        )


@router.post("/message", response_model=SendMessageResponse)
async def send_message(
    request: SendMessageRequest,
    current_user: OptionalUserDep = None,
):
    """
    Send a message to the onboarding agent.

    The agent processes the message and returns a response
    based on the current conversation state.
    """
    redis = await get_redis_client()

    try:
        # Load session
        context = await load_session(request.session_id, redis)

        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or expired. Please start a new conversation.",
            )

        # Process message with agent
        response = await root_agent.process_message(
            message=request.message,
            context=context,
        )

        # Save updated session
        await save_session(request.session_id, context, redis)

        logger.info(
            "onboarding_message_processed",
            session_id=request.session_id,
            state=response.state.value,
            progress=response.progress_percent,
        )

        return SendMessageResponse(
            message=response.message,
            state=response.state.value,
            quick_replies=response.quick_replies,
            progress_percent=response.progress_percent,
            next_step=response.next_step,
            requires_action=response.requires_action,
            action_type=response.action_type,
            action_data=response.action_data,
            data_collected=response.data_collected,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "onboarding_message_failed",
            session_id=request.session_id,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message",
        )
    finally:
        await redis.aclose()


@router.get("/status/{session_id}", response_model=ConversationStatusResponse)
async def get_conversation_status(
    session_id: str,
    current_user: OptionalUserDep = None,
):
    """
    Get the current status of an onboarding conversation.

    Returns the conversation state, progress, and collected data.
    """
    redis = await get_redis_client()

    try:
        context = await load_session(session_id, redis)

        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or expired",
            )

        return ConversationStatusResponse(
            session_id=session_id,
            state=context.state.value,
            progress_percent=_calculate_progress(context.state),
            started_at=context.started_at,
            last_activity=context.last_activity,
            onboarding_data=context.onboarding_data.model_dump(),
        )

    finally:
        await redis.aclose()


@router.post("/complete/{session_id}")
async def complete_onboarding(
    session_id: str,
    current_user: CurrentUserDep,
):
    """
    Complete the onboarding conversation and save data to database.

    This endpoint is called when the user completes the conversational
    onboarding to persist the collected data.
    """
    redis = await get_redis_client()

    try:
        context = await load_session(session_id, redis)

        if not context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or expired",
            )

        if context.state != ConversationState.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Onboarding not yet completed",
            )

        # TODO: Persist onboarding data to database
        # This would integrate with the existing TenantOnboarding model

        # Delete session after completion
        await delete_session(session_id, redis)

        logger.info(
            "onboarding_conversation_completed",
            session_id=session_id,
            user_id=current_user.id,
            tenant_id=current_user.tenant_id,
        )

        return {
            "success": True,
            "message": "Onboarding completed successfully",
            "redirect_to": "/dashboard",
        }

    finally:
        await redis.aclose()


@router.delete("/session/{session_id}")
async def cancel_conversation(
    session_id: str,
    current_user: OptionalUserDep = None,
):
    """
    Cancel and delete an onboarding conversation.

    Use this if the user wants to start over or abandons the flow.
    """
    redis = await get_redis_client()

    try:
        await delete_session(session_id, redis)

        logger.info(
            "onboarding_conversation_cancelled",
            session_id=session_id,
        )

        return {
            "success": True,
            "message": "Conversation cancelled",
        }

    finally:
        await redis.aclose()


@router.get("/quick-replies/{state}")
async def get_quick_replies(
    state: str,
):
    """
    Get available quick replies for a conversation state.

    Useful for refreshing UI options.
    """
    quick_replies_map = {
        "greeting": ["Get Started", "Learn More", "Watch Demo", "Talk to Sales"],
        "collecting_company_info": ["Skip"],
        "selecting_platforms": ["meta", "google", "tiktok", "snapchat", "Done"],
        "connecting_accounts": ["Connect Now", "Skip for Later"],
        "configuring_tracking": ["Yes", "Help me find them", "Skip"],
        "setting_thresholds": ["Keep Default (70%)", "Adjust"],
        "creating_automation": ["Yes, create one", "Skip for now"],
        "reviewing": ["Launch", "Make Changes"],
        "completed": ["Go to Dashboard", "Create Automation", "Get Help"],
    }

    return {
        "state": state,
        "quick_replies": quick_replies_map.get(state, []),
    }


# =============================================================================
# Helper Functions
# =============================================================================


def _calculate_progress(state: ConversationState) -> int:
    """Calculate progress percentage based on state."""
    progress_map = {
        ConversationState.INITIAL: 0,
        ConversationState.GREETING: 0,
        ConversationState.COLLECTING_COMPANY_INFO: 20,
        ConversationState.SELECTING_PLATFORMS: 40,
        ConversationState.CONNECTING_ACCOUNTS: 50,
        ConversationState.CONFIGURING_TRACKING: 60,
        ConversationState.SETTING_THRESHOLDS: 75,
        ConversationState.CREATING_AUTOMATION: 85,
        ConversationState.REVIEWING: 95,
        ConversationState.COMPLETED: 100,
        ConversationState.NEEDS_HELP: 0,
    }
    return progress_map.get(state, 0)
