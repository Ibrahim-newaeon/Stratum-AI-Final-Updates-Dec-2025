# =============================================================================
# Stratum AI - Webhooks Module
# =============================================================================
"""
FastAPI-based webhook server that receives real-time updates from all platforms.

Webhook Overview by Platform
----------------------------

| Platform  | Webhook Support | Update Type           | Frequency        |
|-----------|-----------------|----------------------|------------------|
| Meta      | Full            | Leads, Messages, Ads | Real-time        |
| Google    | Limited         | Change History API   | Polling (15 min) |
| TikTok    | Limited         | Reporting webhooks   | Near real-time   |
| Snapchat  | None            | N/A                  | Polling only     |
| WhatsApp  | Full            | Messages, Status     | Real-time        |

Webhook Types Handled
---------------------

1. **Meta Webhooks**:
   - Lead Gen Form submissions (instant leads)
   - Ad account changes
   - Page messages (Messenger)
   - Instagram messages

2. **WhatsApp Webhooks**:
   - Incoming messages (text, media, interactive)
   - Message status updates (sent, delivered, read)
   - Template status changes

3. **TikTok Webhooks**:
   - Reporting notifications
   - Account status changes

4. **Custom Webhooks**:
   - Your e-commerce platform (orders, cart events)
   - CRM integrations
   - Payment processors

Running the Server
------------------

    # Development
    uvicorn app.stratum.webhooks:app --reload --port 8000

    # Production
    gunicorn app.stratum.webhooks:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any, List, Callable

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Query, Header
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
import asyncio

logger = logging.getLogger("app.stratum.webhooks")

# =============================================================================
# CONFIGURATION
# =============================================================================

class WebhookConfig:
    """
    Webhook configuration loaded from environment variables.

    Set these in your environment or .env file:

    # Meta
    META_APP_SECRET=your_app_secret
    META_VERIFY_TOKEN=your_verify_token
    META_PIXEL_ID=your_pixel_id
    META_ACCESS_TOKEN=your_access_token

    # WhatsApp
    WHATSAPP_PHONE_NUMBER_ID=your_phone_id
    WHATSAPP_VERIFY_TOKEN=your_verify_token
    WHATSAPP_APP_SECRET=your_app_secret

    # TikTok
    TIKTOK_APP_SECRET=your_app_secret

    # General
    WEBHOOK_SECRET=your_internal_secret
    """

    # Meta
    META_APP_SECRET: str = os.getenv("META_APP_SECRET", "")
    META_VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN", "stratum_verify_token")
    META_PIXEL_ID: str = os.getenv("META_PIXEL_ID", "")
    META_ACCESS_TOKEN: str = os.getenv("META_ACCESS_TOKEN", "")

    # WhatsApp (uses Meta infrastructure)
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "stratum_wa_verify")
    WHATSAPP_APP_SECRET: str = os.getenv("WHATSAPP_APP_SECRET", "")

    # TikTok
    TIKTOK_APP_SECRET: str = os.getenv("TIKTOK_APP_SECRET", "")

    # Internal webhook secret (for your own integrations)
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "change_me_in_production")


config = WebhookConfig()

# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="Stratum AI Webhook Server",
    description="Receives real-time updates from advertising platforms",
    version="1.0.0"
)

# Event handlers registry
_event_handlers: Dict[str, List[Callable]] = {
    "meta_lead": [],
    "meta_ad_change": [],
    "whatsapp_message": [],
    "whatsapp_status": [],
    "tiktok_report": [],
    "ecommerce_event": [],
}


def register_handler(event_type: str):
    """Decorator to register webhook event handlers."""
    def decorator(func: Callable):
        _event_handlers.setdefault(event_type, []).append(func)
        return func
    return decorator


async def dispatch_event(event_type: str, data: Dict[str, Any]):
    """Dispatch event to all registered handlers."""
    handlers = _event_handlers.get(event_type, [])
    for handler in handlers:
        try:
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)
        except Exception as e:
            logger.error(f"Handler error for {event_type}: {e}")


# =============================================================================
# SIGNATURE VERIFICATION
# =============================================================================

def verify_meta_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify Meta/WhatsApp webhook signature.

    Meta signs payloads with: sha256=HMAC(app_secret, payload)
    """
    if not secret:
        logger.warning("No app secret configured, skipping signature verification")
        return True

    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    expected_signature = f"sha256={expected}"
    return hmac.compare_digest(expected_signature, signature)


def verify_tiktok_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify TikTok webhook signature."""
    if not secret:
        return True

    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


def verify_internal_signature(payload: bytes, signature: str) -> bool:
    """Verify signature for internal/custom webhooks."""
    if not config.WEBHOOK_SECRET:
        return True

    expected = hmac.new(
        config.WEBHOOK_SECRET.encode('utf-8'),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


# =============================================================================
# META WEBHOOKS (Facebook/Instagram Ads)
# =============================================================================

@app.get("/webhooks/meta")
async def meta_webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    """
    Meta webhook verification endpoint.

    When you subscribe to webhooks in Meta's App Dashboard, Meta sends a GET
    request to verify your endpoint. You must return the challenge parameter.

    Setup in Meta App Dashboard:
    1. Go to your app -> Webhooks
    2. Subscribe to: leads, feed, ads, etc.
    3. Set callback URL to: https://your-domain.com/webhooks/meta
    4. Set verify token to match META_VERIFY_TOKEN env var
    """
    if hub_mode == "subscribe" and hub_verify_token == config.META_VERIFY_TOKEN:
        logger.info("Meta webhook verified successfully")
        return PlainTextResponse(content=hub_challenge)

    logger.warning(f"Meta webhook verification failed: mode={hub_mode}")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhooks/meta")
async def meta_webhook_receive(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256")
):
    """
    Receive Meta webhook events.

    Handles:
    - Lead Gen Form submissions
    - Ad account changes
    - Page feed updates
    - Messenger messages

    Event Structure:
    {
        "object": "page" | "ad_account" | "instagram",
        "entry": [
            {
                "id": "page_or_account_id",
                "time": 1234567890,
                "changes": [
                    {
                        "field": "leadgen" | "feed" | "ads",
                        "value": {...}
                    }
                ]
            }
        ]
    }
    """
    body = await request.body()

    # Verify signature
    if x_hub_signature_256 and not verify_meta_signature(
        body, x_hub_signature_256, config.META_APP_SECRET
    ):
        logger.warning("Invalid Meta webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.info(f"Meta webhook received: {payload.get('object')}")

    # Process in background
    background_tasks.add_task(process_meta_webhook, payload)

    return {"status": "received"}


async def process_meta_webhook(payload: Dict[str, Any]):
    """Process Meta webhook payload."""
    object_type = payload.get("object")

    for entry in payload.get("entry", []):
        entry_id = entry.get("id")
        entry_time = entry.get("time")

        # Handle changes
        for change in entry.get("changes", []):
            field = change.get("field")
            value = change.get("value")

            if field == "leadgen":
                # Lead Gen Form submission
                await process_meta_lead(entry_id, value)

            elif field == "ads":
                # Ad account change
                await dispatch_event("meta_ad_change", {
                    "account_id": entry_id,
                    "change": value,
                    "timestamp": entry_time
                })

            elif field == "feed":
                # Page feed update
                logger.debug(f"Page feed update: {value}")

        # Handle messaging (Messenger)
        for messaging in entry.get("messaging", []):
            sender_id = messaging.get("sender", {}).get("id")
            message = messaging.get("message", {})

            logger.info(f"Messenger message from {sender_id}")
            # Could integrate with WhatsApp adapter logic


async def process_meta_lead(page_id: str, lead_data: Dict[str, Any]):
    """
    Process Meta Lead Gen form submission.

    This is triggered instantly when someone submits a Lead Ad form.

    Lead Data Structure:
    {
        "leadgen_id": "123456789",
        "page_id": "987654321",
        "form_id": "111222333",
        "ad_id": "444555666",
        "ad_group_id": "777888999",
        "created_time": 1234567890
    }
    """
    lead_id = lead_data.get("leadgen_id")
    form_id = lead_data.get("form_id")
    ad_id = lead_data.get("ad_id")

    logger.info(f"New Meta lead: {lead_id} from form {form_id}")

    # Fetch full lead details from API
    # In production, you'd call the Leads API:
    # GET /{lead_id}?access_token=...

    # Dispatch to handlers
    await dispatch_event("meta_lead", {
        "lead_id": lead_id,
        "page_id": page_id,
        "form_id": form_id,
        "ad_id": ad_id,
        "raw_data": lead_data,
        "received_at": datetime.utcnow().isoformat()
    })


# =============================================================================
# WHATSAPP WEBHOOKS
# =============================================================================

@app.get("/webhooks/whatsapp")
async def whatsapp_webhook_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    """
    WhatsApp webhook verification.

    Same as Meta verification (WhatsApp uses Meta's infrastructure).

    Setup in Meta App Dashboard:
    1. Go to your app -> WhatsApp -> Configuration
    2. Set webhook URL to: https://your-domain.com/webhooks/whatsapp
    3. Set verify token to match WHATSAPP_VERIFY_TOKEN env var
    4. Subscribe to: messages, message_status
    """
    if hub_mode == "subscribe" and hub_verify_token == config.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return PlainTextResponse(content=hub_challenge)

    logger.warning("WhatsApp webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhooks/whatsapp")
async def whatsapp_webhook_receive(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256")
):
    """
    Receive WhatsApp webhook events.

    Handles:
    - Incoming messages (text, image, video, audio, document, location, contacts)
    - Message status updates (sent, delivered, read, failed)
    - Interactive message responses (button clicks, list selections)

    Event Structure:
    {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {...},
                            "contacts": [...],
                            "messages": [...],
                            "statuses": [...]
                        },
                        "field": "messages"
                    }
                ]
            }
        ]
    }
    """
    body = await request.body()

    # Verify signature
    if x_hub_signature_256 and not verify_meta_signature(
        body, x_hub_signature_256, config.WHATSAPP_APP_SECRET
    ):
        logger.warning("Invalid WhatsApp webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.info("WhatsApp webhook received")

    # Process in background
    background_tasks.add_task(process_whatsapp_webhook, payload)

    return {"status": "received"}


async def process_whatsapp_webhook(payload: Dict[str, Any]):
    """Process WhatsApp webhook payload."""
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})

            # Get phone number info
            metadata = value.get("metadata", {})
            phone_number_id = metadata.get("phone_number_id")

            # Process messages
            for message in value.get("messages", []):
                await process_whatsapp_message(phone_number_id, message, value)

            # Process status updates
            for status in value.get("statuses", []):
                await process_whatsapp_status(status)


async def process_whatsapp_message(
    phone_number_id: str,
    message: Dict[str, Any],
    value: Dict[str, Any]
):
    """
    Process incoming WhatsApp message.

    Message Types:
    - text: {"body": "Hello"}
    - image/video/audio/document: {"id": "media_id", "mime_type": "..."}
    - location: {"latitude": ..., "longitude": ...}
    - contacts: [{"name": {...}, "phones": [...]}]
    - interactive: {"type": "button_reply"|"list_reply", ...}
    - button: Quick reply button click
    """
    message_id = message.get("id")
    from_number = message.get("from")
    message_type = message.get("type")
    timestamp = message.get("timestamp")

    # Get contact info
    contacts = value.get("contacts", [])
    contact_name = contacts[0].get("profile", {}).get("name") if contacts else None

    logger.info(f"WhatsApp message from {from_number} ({contact_name}): {message_type}")

    # Extract content based on type
    content = None
    if message_type == "text":
        content = message.get("text", {}).get("body")
    elif message_type == "interactive":
        interactive = message.get("interactive", {})
        int_type = interactive.get("type")
        if int_type == "button_reply":
            content = interactive.get("button_reply", {})
        elif int_type == "list_reply":
            content = interactive.get("list_reply", {})
    elif message_type == "button":
        content = message.get("button", {}).get("text")

    # Dispatch event
    await dispatch_event("whatsapp_message", {
        "phone_number_id": phone_number_id,
        "message_id": message_id,
        "from": from_number,
        "contact_name": contact_name,
        "type": message_type,
        "content": content,
        "raw_message": message,
        "timestamp": timestamp,
        "received_at": datetime.utcnow().isoformat()
    })


async def process_whatsapp_status(status: Dict[str, Any]):
    """
    Process WhatsApp message status update.

    Status Types:
    - sent: Message sent to WhatsApp servers
    - delivered: Message delivered to recipient's device
    - read: Message read by recipient
    - failed: Message failed to send (includes error info)
    """
    message_id = status.get("id")
    status_type = status.get("status")
    recipient = status.get("recipient_id")
    timestamp = status.get("timestamp")

    logger.debug(f"WhatsApp status: {message_id} -> {status_type}")

    # Handle errors
    errors = status.get("errors", [])
    error_info = None
    if errors:
        error_info = {
            "code": errors[0].get("code"),
            "title": errors[0].get("title"),
            "message": errors[0].get("message")
        }
        logger.warning(f"WhatsApp message failed: {error_info}")

    await dispatch_event("whatsapp_status", {
        "message_id": message_id,
        "status": status_type,
        "recipient": recipient,
        "timestamp": timestamp,
        "error": error_info
    })


# =============================================================================
# TIKTOK WEBHOOKS
# =============================================================================

@app.post("/webhooks/tiktok")
async def tiktok_webhook_receive(
    request: Request,
    background_tasks: BackgroundTasks,
    x_tiktok_signature: str = Header(None, alias="X-TikTok-Signature")
):
    """
    Receive TikTok webhook events.

    TikTok webhooks are limited compared to Meta. They primarily support:
    - Reporting notifications (report ready)
    - Account status changes

    Note: Most TikTok data sync is done via polling the API.
    """
    body = await request.body()

    # Verify signature
    if x_tiktok_signature and not verify_tiktok_signature(
        body, x_tiktok_signature, config.TIKTOK_APP_SECRET
    ):
        logger.warning("Invalid TikTok webhook signature")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    logger.info(f"TikTok webhook received: {payload.get('event_type')}")

    # Process in background
    background_tasks.add_task(process_tiktok_webhook, payload)

    return {"status": "received"}


async def process_tiktok_webhook(payload: Dict[str, Any]):
    """Process TikTok webhook payload."""
    event_type = payload.get("event_type")

    if event_type == "REPORT_READY":
        # Async report is ready for download
        report_id = payload.get("report_id")
        advertiser_id = payload.get("advertiser_id")

        logger.info(f"TikTok report ready: {report_id}")

        await dispatch_event("tiktok_report", {
            "event_type": event_type,
            "report_id": report_id,
            "advertiser_id": advertiser_id,
            "payload": payload
        })

    else:
        logger.info(f"TikTok event: {event_type}")
        await dispatch_event("tiktok_report", {
            "event_type": event_type,
            "payload": payload
        })


# =============================================================================
# E-COMMERCE / CUSTOM WEBHOOKS
# =============================================================================

class EcommerceEvent(BaseModel):
    """Schema for e-commerce webhook events."""
    event_type: str  # page_view, view_content, add_to_cart, purchase, etc.
    event_id: Optional[str] = None
    timestamp: Optional[str] = None

    # User data
    user_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    # Event data
    page_url: Optional[str] = None
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    product_price: Optional[float] = None
    quantity: Optional[int] = 1
    order_id: Optional[str] = None
    order_total: Optional[float] = None
    currency: str = "USD"

    # Click IDs
    fbclid: Optional[str] = None
    gclid: Optional[str] = None
    ttclid: Optional[str] = None

    # Additional data
    extra: Optional[Dict[str, Any]] = None


@app.post("/webhooks/ecommerce")
async def ecommerce_webhook_receive(
    event: EcommerceEvent,
    request: Request,
    background_tasks: BackgroundTasks,
    x_webhook_signature: str = Header(None, alias="X-Webhook-Signature")
):
    """
    Receive e-commerce events from your website/app.

    This endpoint receives events from your e-commerce platform and
    forwards them to all advertising platforms via server-side tracking.

    Supported Events:
    - page_view
    - view_content
    - search
    - add_to_cart
    - add_to_wishlist
    - initiate_checkout
    - add_payment_info
    - purchase
    - lead

    Example Payload:
    {
        "event_type": "purchase",
        "user_id": "cust_123",
        "email": "customer@example.com",
        "phone": "+966501234567",
        "order_id": "ORD-12345",
        "order_total": 4500.0,
        "currency": "SAR",
        "fbclid": "fb.1.xxx",
        "extra": {
            "products": [
                {"id": "SKU123", "name": "Sofa", "price": 2500, "quantity": 1}
            ]
        }
    }

    Integration Options:

    1. Direct HTTP POST from your backend
    2. GTM Server-Side container
    3. Segment/RudderStack webhook destination
    4. Shopify webhook (custom app)
    5. WooCommerce webhook
    """
    # Optional signature verification
    if x_webhook_signature:
        body = await request.body()
        if not verify_internal_signature(body, x_webhook_signature):
            raise HTTPException(status_code=403, detail="Invalid signature")

    logger.info(f"E-commerce event received: {event.event_type}")

    # Process in background
    background_tasks.add_task(process_ecommerce_event, event.dict())

    return {"status": "received", "event_id": event.event_id}


async def process_ecommerce_event(event_data: Dict[str, Any]):
    """
    Process e-commerce event and forward to all platforms.

    This converts the incoming event to our unified format and sends
    to Meta, Google, TikTok, Snapchat via server-side tracking.
    """
    from app.stratum.events import (
        ServerEvent, StandardEvent, UserData, ContentItem,
        UnifiedEventsAPI, MetaEventsSender
    )

    # Map event type
    event_mapping = {
        "page_view": StandardEvent.PAGE_VIEW,
        "view_content": StandardEvent.VIEW_CONTENT,
        "search": StandardEvent.SEARCH,
        "add_to_cart": StandardEvent.ADD_TO_CART,
        "add_to_wishlist": StandardEvent.ADD_TO_WISHLIST,
        "initiate_checkout": StandardEvent.INITIATE_CHECKOUT,
        "add_payment_info": StandardEvent.ADD_PAYMENT_INFO,
        "purchase": StandardEvent.PURCHASE,
        "lead": StandardEvent.LEAD,
        "complete_registration": StandardEvent.COMPLETE_REGISTRATION,
    }

    event_type = event_mapping.get(event_data["event_type"])
    if not event_type:
        logger.warning(f"Unknown event type: {event_data['event_type']}")
        return

    # Build user data
    user_data = UserData(
        email=event_data.get("email"),
        phone=event_data.get("phone"),
        external_id=event_data.get("user_id"),
        fbc=event_data.get("fbclid"),
        gclid=event_data.get("gclid"),
        ttclid=event_data.get("ttclid"),
    )

    # Build content items
    contents = []
    extra = event_data.get("extra") or {}
    products = extra.get("products", [])

    if products:
        for p in products:
            contents.append(ContentItem(
                id=p.get("id", ""),
                name=p.get("name"),
                price=p.get("price"),
                quantity=p.get("quantity", 1)
            ))
    elif event_data.get("product_id"):
        contents.append(ContentItem(
            id=event_data["product_id"],
            name=event_data.get("product_name"),
            price=event_data.get("product_price"),
            quantity=event_data.get("quantity", 1)
        ))

    # Build server event
    server_event = ServerEvent(
        event_name=event_type,
        user_data=user_data,
        contents=contents,
        value=event_data.get("order_total") or event_data.get("product_price"),
        currency=event_data.get("currency", "USD"),
        order_id=event_data.get("order_id"),
        event_source_url=event_data.get("page_url"),
        event_id=event_data.get("event_id")
    )

    # Initialize API and send to all platforms
    # Note: In production, these would be initialized once at startup
    api = UnifiedEventsAPI()

    if config.META_PIXEL_ID and config.META_ACCESS_TOKEN:
        api.add_sender("meta", MetaEventsSender(
            config.META_PIXEL_ID,
            config.META_ACCESS_TOKEN
        ))

    # Add other platforms as configured...

    # Send to all platforms
    try:
        results = await api.send(server_event)
        logger.info(f"Event forwarded to platforms: {results}")

        # Dispatch for additional processing
        await dispatch_event("ecommerce_event", {
            "event": event_data,
            "results": results
        })
    except Exception as e:
        logger.error(f"Error forwarding event: {e}")


# =============================================================================
# HEALTH & STATUS ENDPOINTS
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.get("/webhooks/status")
async def webhook_status():
    """Check webhook configuration status."""
    return {
        "meta": {
            "configured": bool(config.META_APP_SECRET),
            "verify_token_set": bool(config.META_VERIFY_TOKEN),
            "pixel_configured": bool(config.META_PIXEL_ID)
        },
        "whatsapp": {
            "configured": bool(config.WHATSAPP_APP_SECRET),
            "phone_number_id_set": bool(config.WHATSAPP_PHONE_NUMBER_ID)
        },
        "tiktok": {
            "configured": bool(config.TIKTOK_APP_SECRET)
        },
        "ecommerce": {
            "signature_verification": bool(config.WEBHOOK_SECRET)
        },
        "handlers_registered": {
            event_type: len(handlers)
            for event_type, handlers in _event_handlers.items()
        }
    }


# =============================================================================
# EXAMPLE HANDLERS (Register your own)
# =============================================================================

@register_handler("meta_lead")
async def example_lead_handler(data: Dict[str, Any]):
    """
    Example handler for Meta lead submissions.

    Replace this with your actual lead processing logic:
    - Send to CRM
    - Send notification
    - Trigger automation
    """
    logger.info(f"Processing lead: {data['lead_id']}")
    # Your logic here:
    # await crm.create_lead(data)
    # await notify_sales_team(data)


@register_handler("whatsapp_message")
async def example_whatsapp_handler(data: Dict[str, Any]):
    """
    Example handler for WhatsApp messages.

    Replace with your chatbot/CRM logic.
    """
    logger.info(f"Processing WhatsApp message from {data['from']}")
    # Your logic here:
    # response = await chatbot.process(data['content'])
    # await whatsapp.send_reply(data['from'], response)


@register_handler("ecommerce_event")
async def example_ecommerce_handler(data: Dict[str, Any]):
    """
    Example handler for e-commerce events.

    Use for additional processing after platform forwarding.
    """
    event = data.get("event", {})
    results = data.get("results", {})

    logger.info(f"E-commerce event {event.get('event_type')} forwarded: {results}")
    # Your logic here:
    # await analytics.track(event)
    # await update_signal_health(results)


# =============================================================================
# STARTUP / SHUTDOWN
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize on server startup."""
    logger.info("Stratum Webhook Server starting...")
    logger.info(f"Meta webhooks: {'enabled' if config.META_APP_SECRET else 'disabled'}")
    logger.info(f"WhatsApp webhooks: {'enabled' if config.WHATSAPP_APP_SECRET else 'disabled'}")
    logger.info(f"TikTok webhooks: {'enabled' if config.TIKTOK_APP_SECRET else 'disabled'}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown."""
    logger.info("Stratum Webhook Server shutting down...")


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # FastAPI app
    "app",
    # Configuration
    "WebhookConfig",
    "config",
    # Event handling
    "register_handler",
    "dispatch_event",
    # Signature verification
    "verify_meta_signature",
    "verify_tiktok_signature",
    "verify_internal_signature",
    # Models
    "EcommerceEvent",
]
