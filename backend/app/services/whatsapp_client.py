# =============================================================================
# Stratum AI - WhatsApp Business API Client
# =============================================================================
"""
WhatsApp Business API client for sending messages, managing templates,
and handling webhook interactions with the Meta Graph API.
"""

from typing import List, Dict, Any, Optional
import httpx
import logging
from datetime import datetime

from app.core.config import settings

logger = logging.getLogger(__name__)


class WhatsAppAPIError(Exception):
    """Custom exception for WhatsApp API errors."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        error_subcode: Optional[str] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.error_subcode = error_subcode
        super().__init__(self.message)


class WhatsAppClient:
    """
    WhatsApp Business API client for Meta Graph API.

    Handles:
    - Sending template messages
    - Sending text messages (within 24-hour window)
    - Sending media messages
    - Managing message templates
    - Webhook verification
    """

    def __init__(
        self,
        phone_number_id: Optional[str] = None,
        access_token: Optional[str] = None,
        business_account_id: Optional[str] = None,
        api_version: Optional[str] = None,
    ):
        """
        Initialize WhatsApp client.

        Args:
            phone_number_id: WhatsApp Business Phone Number ID
            access_token: Meta Graph API access token
            business_account_id: WhatsApp Business Account ID
            api_version: Meta Graph API version (default: v18.0)
        """
        self.phone_number_id = phone_number_id or settings.whatsapp_phone_number_id
        self.access_token = access_token or settings.whatsapp_access_token
        self.business_account_id = (
            business_account_id or settings.whatsapp_business_account_id
        )
        self.api_version = api_version or settings.whatsapp_api_version
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """Make an authenticated request to the WhatsApp API."""
        url = f"{self.base_url}/{endpoint}"

        async with httpx.AsyncClient() as client:
            try:
                if method == "GET":
                    response = await client.get(
                        url, headers=self._get_headers(), params=payload
                    )
                elif method == "POST":
                    response = await client.post(
                        url, headers=self._get_headers(), json=payload
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as e:
                error_data = e.response.json().get("error", {})
                logger.error(
                    f"WhatsApp API error: {error_data.get('message')}",
                    extra={
                        "error_code": error_data.get("code"),
                        "error_subcode": error_data.get("error_subcode"),
                    },
                )
                raise WhatsAppAPIError(
                    message=error_data.get("message", str(e)),
                    error_code=str(error_data.get("code")),
                    error_subcode=str(error_data.get("error_subcode")),
                )

    # -------------------------------------------------------------------------
    # Message Sending Methods
    # -------------------------------------------------------------------------

    async def send_template_message(
        self,
        recipient_phone: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Send a template message via WhatsApp.

        Template messages can be sent outside the 24-hour window.
        They must be pre-approved by Meta.

        Args:
            recipient_phone: Recipient's phone number (with country code)
            template_name: Name of the approved template
            language_code: Template language code (default: en)
            components: Optional template components (header, body variables, buttons)

        Returns:
            API response with message ID (wamid)
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
            },
        }

        if components:
            payload["template"]["components"] = components

        return await self._make_request(
            "POST", f"{self.phone_number_id}/messages", payload
        )

    async def send_text_message(
        self, recipient_phone: str, text: str, preview_url: bool = False
    ) -> Dict[str, Any]:
        """
        Send a text message via WhatsApp.

        Note: Text messages can only be sent within the 24-hour conversation window
        after the user has messaged you first.

        Args:
            recipient_phone: Recipient's phone number (with country code)
            text: Message text content
            preview_url: Whether to show URL previews

        Returns:
            API response with message ID (wamid)
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "text",
            "text": {
                "body": text,
                "preview_url": preview_url,
            },
        }

        return await self._make_request(
            "POST", f"{self.phone_number_id}/messages", payload
        )

    async def send_media_message(
        self,
        recipient_phone: str,
        media_type: str,
        media_url: str,
        caption: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a media message (image, video, document, audio).

        Args:
            recipient_phone: Recipient's phone number (with country code)
            media_type: Type of media (image, video, document, audio)
            media_url: URL of the media file
            caption: Optional caption (for image/video)
            filename: Optional filename (for document)

        Returns:
            API response with message ID (wamid)
        """
        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": media_type,
            media_type: {"link": media_url},
        }

        if caption and media_type in ["image", "video"]:
            payload[media_type]["caption"] = caption

        if filename and media_type == "document":
            payload[media_type]["filename"] = filename

        return await self._make_request(
            "POST", f"{self.phone_number_id}/messages", payload
        )

    async def send_interactive_message(
        self,
        recipient_phone: str,
        interactive_type: str,
        body_text: str,
        action: Dict[str, Any],
        header: Optional[Dict] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send an interactive message (buttons, lists).

        Args:
            recipient_phone: Recipient's phone number
            interactive_type: Type (button, list, product, product_list)
            body_text: Message body text
            action: Interactive action (buttons array or sections array)
            header: Optional header (text, image, video, document)
            footer: Optional footer text

        Returns:
            API response with message ID (wamid)
        """
        interactive = {
            "type": interactive_type,
            "body": {"text": body_text},
            "action": action,
        }

        if header:
            interactive["header"] = header

        if footer:
            interactive["footer"] = {"text": footer}

        payload = {
            "messaging_product": "whatsapp",
            "to": recipient_phone,
            "type": "interactive",
            "interactive": interactive,
        }

        return await self._make_request(
            "POST", f"{self.phone_number_id}/messages", payload
        )

    # -------------------------------------------------------------------------
    # Message Status Methods
    # -------------------------------------------------------------------------

    async def mark_message_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark an incoming message as read.

        Args:
            message_id: WhatsApp message ID to mark as read

        Returns:
            API response
        """
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }

        return await self._make_request(
            "POST", f"{self.phone_number_id}/messages", payload
        )

    # -------------------------------------------------------------------------
    # Template Management Methods
    # -------------------------------------------------------------------------

    async def create_template(
        self,
        name: str,
        category: str,
        language: str,
        components: List[Dict],
    ) -> Dict[str, Any]:
        """
        Create a new message template.

        Note: Templates require Meta approval before use.

        Args:
            name: Template name (lowercase, underscores only)
            category: Template category (MARKETING, UTILITY, AUTHENTICATION)
            language: Template language code
            components: Template components (HEADER, BODY, FOOTER, BUTTONS)

        Returns:
            API response with template ID
        """
        payload = {
            "name": name,
            "category": category,
            "language": language,
            "components": components,
        }

        return await self._make_request(
            "POST", f"{self.business_account_id}/message_templates", payload
        )

    async def get_templates(
        self, limit: int = 100, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all message templates for the business account.

        Args:
            limit: Maximum number of templates to retrieve
            status: Optional status filter (APPROVED, PENDING, REJECTED)

        Returns:
            List of templates
        """
        params = {"limit": limit}
        if status:
            params["status"] = status

        response = await self._make_request(
            "GET", f"{self.business_account_id}/message_templates", params
        )
        return response.get("data", [])

    async def delete_template(self, template_name: str) -> Dict[str, Any]:
        """
        Delete a message template.

        Args:
            template_name: Name of the template to delete

        Returns:
            API response
        """
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.base_url}/{self.business_account_id}/message_templates",
                headers=self._get_headers(),
                params={"name": template_name},
            )
            response.raise_for_status()
            return response.json()

    # -------------------------------------------------------------------------
    # Webhook Methods
    # -------------------------------------------------------------------------

    def verify_webhook(
        self, mode: str, token: str, challenge: str
    ) -> Optional[str]:
        """
        Verify webhook subscription from Meta.

        Args:
            mode: Verification mode (should be 'subscribe')
            token: Verification token from Meta
            challenge: Challenge string to return

        Returns:
            Challenge string if verification successful, None otherwise
        """
        if mode == "subscribe" and token == settings.whatsapp_verify_token:
            logger.info("WhatsApp webhook verified successfully")
            return challenge

        logger.warning(
            f"WhatsApp webhook verification failed: mode={mode}, token mismatch"
        )
        return None

    @staticmethod
    def parse_webhook_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse incoming webhook payload from Meta.

        Args:
            payload: Raw webhook payload

        Returns:
            List of parsed events (messages, status updates)
        """
        events = []

        try:
            for entry in payload.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})

                    # Parse incoming messages
                    for message in value.get("messages", []):
                        contact = value.get("contacts", [{}])[0]
                        events.append({
                            "type": "message",
                            "from": message.get("from"),
                            "wamid": message.get("id"),
                            "timestamp": datetime.fromtimestamp(
                                int(message.get("timestamp", 0))
                            ),
                            "message_type": message.get("type"),
                            "content": message.get(message.get("type"), {}),
                            "contact_name": contact.get("profile", {}).get("name"),
                        })

                    # Parse status updates
                    for status in value.get("statuses", []):
                        events.append({
                            "type": "status",
                            "wamid": status.get("id"),
                            "status": status.get("status"),
                            "timestamp": datetime.fromtimestamp(
                                int(status.get("timestamp", 0))
                            ),
                            "recipient_id": status.get("recipient_id"),
                            "conversation": status.get("conversation"),
                            "pricing": status.get("pricing"),
                            "errors": status.get("errors"),
                        })

        except Exception as e:
            logger.error(f"Error parsing webhook payload: {e}")

        return events


# Singleton instance for convenience
def get_whatsapp_client() -> WhatsAppClient:
    """Get a configured WhatsApp client instance."""
    return WhatsAppClient()
