# =============================================================================
# Stratum AI - AI Event Mapper
# =============================================================================
"""
AI-powered event mapping for Conversion APIs.
Automatically maps custom events to standard platform events.
"""

import re
from typing import Any, Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum

from app.core.logging import get_logger

logger = get_logger(__name__)


class StandardEvent(str, Enum):
    """Standard conversion events across platforms."""
    # Purchase/Revenue
    PURCHASE = "Purchase"
    ADD_TO_CART = "AddToCart"
    INITIATE_CHECKOUT = "InitiateCheckout"
    ADD_PAYMENT_INFO = "AddPaymentInfo"

    # Lead Generation
    LEAD = "Lead"
    COMPLETE_REGISTRATION = "CompleteRegistration"
    SUBMIT_APPLICATION = "SubmitApplication"
    SUBSCRIBE = "Subscribe"

    # Engagement
    VIEW_CONTENT = "ViewContent"
    SEARCH = "Search"
    ADD_TO_WISHLIST = "AddToWishlist"
    CONTACT = "Contact"

    # App Events
    APP_INSTALL = "AppInstall"
    START_TRIAL = "StartTrial"
    ACHIEVEMENT_UNLOCKED = "AchievementUnlocked"

    # Custom
    CUSTOM = "Custom"


@dataclass
class EventMapping:
    """Result of event mapping."""
    original_event: str
    standard_event: StandardEvent
    confidence: float
    platform_events: Dict[str, str]  # platform -> event name
    parameters: Dict[str, Any]
    suggestions: List[str]


class AIEventMapper:
    """
    AI-powered event mapper that automatically maps custom events
    to standard platform events.

    Features:
    - Pattern matching for common event names
    - Semantic similarity detection
    - Platform-specific event translation
    - Parameter mapping suggestions
    """

    # Event name patterns and their standard mappings
    EVENT_PATTERNS = {
        StandardEvent.PURCHASE: [
            r"purchase", r"order", r"buy", r"bought", r"transaction",
            r"sale", r"checkout[-_]?complete", r"order[-_]?complete",
            r"payment[-_]?complete", r"conversion"
        ],
        StandardEvent.ADD_TO_CART: [
            r"add[-_]?to[-_]?cart", r"cart[-_]?add", r"basket[-_]?add",
            r"add[-_]?item", r"add[-_]?product"
        ],
        StandardEvent.INITIATE_CHECKOUT: [
            r"initiate[-_]?checkout", r"begin[-_]?checkout", r"start[-_]?checkout",
            r"checkout[-_]?start", r"checkout[-_]?begin"
        ],
        StandardEvent.ADD_PAYMENT_INFO: [
            r"add[-_]?payment", r"payment[-_]?info", r"billing[-_]?info",
            r"card[-_]?added", r"payment[-_]?method"
        ],
        StandardEvent.LEAD: [
            r"lead", r"inquiry", r"enquiry", r"contact[-_]?form",
            r"form[-_]?submit", r"request[-_]?quote", r"get[-_]?quote"
        ],
        StandardEvent.COMPLETE_REGISTRATION: [
            r"register", r"sign[-_]?up", r"signup", r"create[-_]?account",
            r"registration", r"new[-_]?user", r"join"
        ],
        StandardEvent.SUBSCRIBE: [
            r"subscribe", r"newsletter", r"opt[-_]?in", r"email[-_]?signup",
            r"subscription"
        ],
        StandardEvent.VIEW_CONTENT: [
            r"view", r"page[-_]?view", r"content[-_]?view", r"product[-_]?view",
            r"detail[-_]?view", r"item[-_]?view"
        ],
        StandardEvent.SEARCH: [
            r"search", r"query", r"find", r"lookup"
        ],
        StandardEvent.ADD_TO_WISHLIST: [
            r"wishlist", r"save[-_]?for[-_]?later", r"favorite", r"bookmark"
        ],
        StandardEvent.CONTACT: [
            r"contact", r"call", r"phone", r"chat", r"message"
        ],
        StandardEvent.APP_INSTALL: [
            r"install", r"app[-_]?install", r"download", r"app[-_]?download"
        ],
        StandardEvent.START_TRIAL: [
            r"trial", r"free[-_]?trial", r"start[-_]?trial", r"demo"
        ],
    }

    # Platform-specific event name translations
    PLATFORM_EVENTS = {
        "meta": {
            StandardEvent.PURCHASE: "Purchase",
            StandardEvent.ADD_TO_CART: "AddToCart",
            StandardEvent.INITIATE_CHECKOUT: "InitiateCheckout",
            StandardEvent.ADD_PAYMENT_INFO: "AddPaymentInfo",
            StandardEvent.LEAD: "Lead",
            StandardEvent.COMPLETE_REGISTRATION: "CompleteRegistration",
            StandardEvent.SUBSCRIBE: "Subscribe",
            StandardEvent.VIEW_CONTENT: "ViewContent",
            StandardEvent.SEARCH: "Search",
            StandardEvent.ADD_TO_WISHLIST: "AddToWishlist",
            StandardEvent.CONTACT: "Contact",
            StandardEvent.APP_INSTALL: "AppInstall",
            StandardEvent.START_TRIAL: "StartTrial",
            StandardEvent.CUSTOM: "CustomEvent",
        },
        "google": {
            StandardEvent.PURCHASE: "purchase",
            StandardEvent.ADD_TO_CART: "add_to_cart",
            StandardEvent.INITIATE_CHECKOUT: "begin_checkout",
            StandardEvent.ADD_PAYMENT_INFO: "add_payment_info",
            StandardEvent.LEAD: "generate_lead",
            StandardEvent.COMPLETE_REGISTRATION: "sign_up",
            StandardEvent.SUBSCRIBE: "subscribe",
            StandardEvent.VIEW_CONTENT: "view_item",
            StandardEvent.SEARCH: "search",
            StandardEvent.ADD_TO_WISHLIST: "add_to_wishlist",
            StandardEvent.CONTACT: "contact",
            StandardEvent.APP_INSTALL: "app_install",
            StandardEvent.START_TRIAL: "start_trial",
            StandardEvent.CUSTOM: "custom_event",
        },
        "tiktok": {
            StandardEvent.PURCHASE: "CompletePayment",
            StandardEvent.ADD_TO_CART: "AddToCart",
            StandardEvent.INITIATE_CHECKOUT: "InitiateCheckout",
            StandardEvent.ADD_PAYMENT_INFO: "AddPaymentInfo",
            StandardEvent.LEAD: "SubmitForm",
            StandardEvent.COMPLETE_REGISTRATION: "CompleteRegistration",
            StandardEvent.SUBSCRIBE: "Subscribe",
            StandardEvent.VIEW_CONTENT: "ViewContent",
            StandardEvent.SEARCH: "Search",
            StandardEvent.ADD_TO_WISHLIST: "AddToWishlist",
            StandardEvent.CONTACT: "Contact",
            StandardEvent.APP_INSTALL: "AppInstall",
            StandardEvent.START_TRIAL: "StartTrial",
            StandardEvent.CUSTOM: "CustomEvent",
        },
        "snapchat": {
            StandardEvent.PURCHASE: "PURCHASE",
            StandardEvent.ADD_TO_CART: "ADD_CART",
            StandardEvent.INITIATE_CHECKOUT: "START_CHECKOUT",
            StandardEvent.ADD_PAYMENT_INFO: "ADD_BILLING",
            StandardEvent.LEAD: "SIGN_UP",
            StandardEvent.COMPLETE_REGISTRATION: "SIGN_UP",
            StandardEvent.SUBSCRIBE: "SUBSCRIBE",
            StandardEvent.VIEW_CONTENT: "VIEW_CONTENT",
            StandardEvent.SEARCH: "SEARCH",
            StandardEvent.ADD_TO_WISHLIST: "ADD_TO_WISHLIST",
            StandardEvent.CONTACT: "CUSTOM_EVENT_1",
            StandardEvent.APP_INSTALL: "APP_INSTALL",
            StandardEvent.START_TRIAL: "START_TRIAL",
            StandardEvent.CUSTOM: "CUSTOM_EVENT_1",
        },
    }

    # Standard parameters for each event type
    EVENT_PARAMETERS = {
        StandardEvent.PURCHASE: {
            "required": ["value", "currency"],
            "optional": ["content_ids", "content_type", "num_items", "order_id"],
        },
        StandardEvent.ADD_TO_CART: {
            "required": ["value", "currency"],
            "optional": ["content_ids", "content_type", "content_name"],
        },
        StandardEvent.INITIATE_CHECKOUT: {
            "required": ["value", "currency"],
            "optional": ["content_ids", "num_items"],
        },
        StandardEvent.LEAD: {
            "required": [],
            "optional": ["value", "currency", "lead_type"],
        },
        StandardEvent.COMPLETE_REGISTRATION: {
            "required": [],
            "optional": ["value", "currency", "method"],
        },
        StandardEvent.VIEW_CONTENT: {
            "required": [],
            "optional": ["content_ids", "content_type", "content_name", "value", "currency"],
        },
        StandardEvent.SEARCH: {
            "required": [],
            "optional": ["search_string", "content_ids"],
        },
    }

    # Parameter name mappings
    PARAMETER_MAPPINGS = {
        "amount": "value",
        "price": "value",
        "total": "value",
        "revenue": "value",
        "product_id": "content_ids",
        "item_id": "content_ids",
        "sku": "content_ids",
        "product_name": "content_name",
        "item_name": "content_name",
        "quantity": "num_items",
        "count": "num_items",
        "query": "search_string",
        "search_term": "search_string",
        "keyword": "search_string",
    }

    def __init__(self):
        """Initialize the event mapper."""
        self._compiled_patterns: Dict[StandardEvent, List[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for performance."""
        for event, patterns in self.EVENT_PATTERNS.items():
            self._compiled_patterns[event] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def map_event(
        self, event_name: str, parameters: Dict[str, Any] = None
    ) -> EventMapping:
        """
        Map a custom event to standard platform events.

        Args:
            event_name: The custom event name
            parameters: Event parameters

        Returns:
            EventMapping with standard event and platform translations
        """
        parameters = parameters or {}

        # Find best matching standard event
        standard_event, confidence = self._find_standard_event(event_name)

        # Get platform-specific event names
        platform_events = {
            platform: events.get(standard_event, events[StandardEvent.CUSTOM])
            for platform, events in self.PLATFORM_EVENTS.items()
        }

        # Map parameters to standard names
        mapped_params = self._map_parameters(parameters, standard_event)

        # Generate suggestions
        suggestions = self._generate_suggestions(standard_event, mapped_params)

        return EventMapping(
            original_event=event_name,
            standard_event=standard_event,
            confidence=confidence,
            platform_events=platform_events,
            parameters=mapped_params,
            suggestions=suggestions,
        )

    def _find_standard_event(self, event_name: str) -> Tuple[StandardEvent, float]:
        """Find the best matching standard event for an event name."""
        normalized = event_name.lower().replace(" ", "_").replace("-", "_")

        best_match = StandardEvent.CUSTOM
        best_confidence = 0.0

        for event, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.fullmatch(normalized):
                    return event, 1.0
                elif pattern.search(normalized):
                    confidence = 0.8
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = event

        return best_match, best_confidence if best_confidence > 0 else 0.3

    def _map_parameters(
        self, params: Dict[str, Any], event: StandardEvent
    ) -> Dict[str, Any]:
        """Map custom parameter names to standard names."""
        mapped = {}

        for key, value in params.items():
            normalized_key = key.lower().replace(" ", "_").replace("-", "_")

            # Check if it's already a standard parameter
            standard_key = self.PARAMETER_MAPPINGS.get(normalized_key, normalized_key)

            # Handle special cases
            if standard_key == "content_ids" and not isinstance(value, list):
                value = [value]
            elif standard_key == "value":
                value = float(value) if value else 0

            mapped[standard_key] = value

        return mapped

    def _generate_suggestions(
        self, event: StandardEvent, params: Dict[str, Any]
    ) -> List[str]:
        """Generate suggestions for improving event data."""
        suggestions = []
        event_params = self.EVENT_PARAMETERS.get(event, {"required": [], "optional": []})

        # Check for missing required parameters
        for param in event_params["required"]:
            if param not in params or params[param] is None:
                suggestions.append(f"Add '{param}' parameter for better tracking")

        # Suggest high-value optional parameters
        for param in event_params["optional"][:3]:
            if param not in params:
                suggestions.append(f"Consider adding '{param}' for richer insights")

        # Event-specific suggestions
        if event == StandardEvent.PURCHASE:
            if "value" in params and params["value"] == 0:
                suggestions.append("Purchase value is 0 - ensure you're sending actual revenue")
            if "currency" not in params:
                suggestions.append("Add currency code (e.g., 'USD') for accurate revenue reporting")

        return suggestions[:3]  # Limit to top 3 suggestions

    def get_platform_event(self, standard_event: StandardEvent, platform: str) -> str:
        """Get the platform-specific event name for a standard event."""
        platform_events = self.PLATFORM_EVENTS.get(platform, self.PLATFORM_EVENTS["meta"])
        return platform_events.get(standard_event, platform_events[StandardEvent.CUSTOM])

    def validate_event_data(
        self, event_name: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate event data and return validation results.

        Returns:
            Dictionary with validation status, issues, and recommendations
        """
        mapping = self.map_event(event_name, parameters)

        issues = []
        warnings = []

        # Check confidence
        if mapping.confidence < 0.5:
            warnings.append({
                "type": "low_confidence",
                "message": f"Event '{event_name}' may not be recognized by all platforms",
                "suggestion": "Consider using a standard event name",
            })

        # Check required parameters
        event_params = self.EVENT_PARAMETERS.get(mapping.standard_event, {})
        for param in event_params.get("required", []):
            if param not in mapping.parameters:
                issues.append({
                    "type": "missing_required",
                    "parameter": param,
                    "message": f"Required parameter '{param}' is missing",
                })

        # Check value/currency for revenue events
        if mapping.standard_event in [StandardEvent.PURCHASE, StandardEvent.ADD_TO_CART]:
            if "value" not in mapping.parameters:
                issues.append({
                    "type": "missing_value",
                    "message": "Revenue events should include 'value' parameter",
                })
            elif mapping.parameters.get("value", 0) <= 0:
                warnings.append({
                    "type": "zero_value",
                    "message": "Event value is 0 or negative",
                    "suggestion": "Ensure you're passing the actual transaction value",
                })

        return {
            "valid": len(issues) == 0,
            "event_mapping": {
                "original": mapping.original_event,
                "standard": mapping.standard_event.value,
                "confidence": mapping.confidence,
            },
            "platform_events": mapping.platform_events,
            "issues": issues,
            "warnings": warnings,
            "suggestions": mapping.suggestions,
        }

    def bulk_map_events(
        self, events: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Map multiple events at once.

        Args:
            events: List of event dictionaries with 'name' and 'parameters'

        Returns:
            List of mapping results
        """
        results = []

        for event in events:
            event_name = event.get("name", event.get("event_name", "unknown"))
            parameters = event.get("parameters", event.get("data", {}))

            validation = self.validate_event_data(event_name, parameters)
            results.append({
                **validation,
                "original_event": event,
            })

        return results
