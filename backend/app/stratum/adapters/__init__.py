# =============================================================================
# Stratum AI - Platform Adapters
# =============================================================================
"""
Platform adapters for bi-directional sync with advertising platforms.

Each adapter provides:
- Read operations: Pull campaigns, ad sets, ads, metrics, EMQ
- Write operations: Update budgets, bids, status, create entities
- Rate limiting: Respect platform API limits
- Error handling: Platform-specific error translation

Supported Platforms:
- Meta (Facebook/Instagram) Ads
- Google Ads
- TikTok Ads
- Snapchat Ads
- WhatsApp Business API
"""

from app.stratum.adapters.base import (
    BaseAdapter,
    RateLimiter,
    AdapterError,
    AuthenticationError,
    RateLimitError,
    PlatformError,
    ValidationError,
)
from app.stratum.adapters.registry import AdapterRegistry, get_adapter
from app.stratum.adapters.whatsapp_adapter import (
    WhatsAppAdapter,
    MessageType,
    MessageStatus,
    ConversationType,
    Contact,
    Message,
    Conversation,
    Template,
)

__all__ = [
    # Base adapter
    "BaseAdapter",
    "RateLimiter",
    # Errors
    "AdapterError",
    "AuthenticationError",
    "RateLimitError",
    "PlatformError",
    "ValidationError",
    # Registry
    "AdapterRegistry",
    "get_adapter",
    # WhatsApp
    "WhatsAppAdapter",
    "MessageType",
    "MessageStatus",
    "ConversationType",
    "Contact",
    "Message",
    "Conversation",
    "Template",
]
