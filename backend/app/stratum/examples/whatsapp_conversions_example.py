#!/usr/bin/env python3
"""
Stratum AI: WhatsApp + Conversions API Integration Example
==========================================================

This example demonstrates:
1. Sending WhatsApp messages (templates and interactive)
2. Tracking conversions from WhatsApp conversations
3. Sending conversion events to all platforms (Meta CAPI, Google, TikTok, Snapchat)
4. Improving EMQ through server-side event passing

Use Case: Furniture E-commerce in Gulf Markets
----------------------------------------------

A typical flow for furniture e-commerce:
1. User clicks Click-to-WhatsApp ad on Meta/Instagram
2. Automated welcome message + product catalog
3. User asks questions about products
4. User places order via WhatsApp
5. Order confirmation template sent
6. Conversion tracked to Meta CAPI for attribution

This script shows how to implement each step.
"""

import asyncio
import logging
from datetime import UTC, datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stratum.example.whatsapp")


async def example_whatsapp_messaging():
    """
    Example: WhatsApp messaging for e-commerce.
    """

    logger.info("=" * 60)
    logger.info("WHATSAPP MESSAGING EXAMPLE")
    logger.info("=" * 60)

    # Credentials (in production, load from config)
    credentials = {
        "phone_number_id": "YOUR_PHONE_NUMBER_ID",
        "access_token": "YOUR_ACCESS_TOKEN",
        "business_account_id": "YOUR_WABA_ID",
        "pixel_id": "YOUR_META_PIXEL_ID",  # For conversion tracking
    }

    logger.info("\n[INIT] Step 1: Initialize WhatsApp Adapter")
    logger.info("   adapter = WhatsAppAdapter(credentials)")
    logger.info("   await adapter.initialize()")

    # Simulated customer journey
    customer_phone = "+966501234567"  # Saudi Arabia

    logger.info(f"\n[USER] Customer: {customer_phone}")
    logger.info("   Entry: Click-to-WhatsApp ad (Living Room Furniture)")

    # Step 1: Send welcome template
    logger.info("\n[SEND] Step 2: Send Welcome Template")
    logger.info(f"""
    await adapter.send_template_message(
        to="{customer_phone}",
        template_name="welcome_furniture",
        language="ar",
        components=[
            {{
                "type": "body",
                "parameters": [
                    {{"type": "text", "text": "Ahmed"}},
                    {{"type": "text", "text": "20%"}}
                ]
            }}
        ]
    )
    """)

    logger.info("   [OK] Template sent: Welcome + 20% discount offer")

    # Step 2: Send interactive product menu
    logger.info("\n[SEND] Step 3: Send Interactive Product Menu")
    logger.info(f"""
    await adapter.send_interactive_message(
        to="{customer_phone}",
        interactive_type="list",
        body_text="Choose the type of furniture you're looking for:",
        action={{
            "button": "View Categories",
            "sections": [
                {{
                    "title": "Living Room",
                    "rows": [
                        {{"id": "sofa", "title": "Sofas", "description": "Wide selection of sofas"}},
                        {{"id": "table", "title": "Tables", "description": "Coffee and dining tables"}}
                    ]
                }},
                {{
                    "title": "Bedroom",
                    "rows": [
                        {{"id": "bed", "title": "Beds", "description": "Comfortable beds"}},
                        {{"id": "wardrobe", "title": "Wardrobes", "description": "Clothing wardrobes"}}
                    ]
                }}
            ]
        }}
    )
    """)

    logger.info("   [OK] Interactive menu sent")

    # Step 3: Handle customer inquiry
    logger.info("\n[RECV] Step 4: Customer Selects 'Sofa'")
    logger.info("   webhook_payload = {...}")
    logger.info("   await adapter.process_webhook(webhook_payload)")
    logger.info("   -> Parsed: Customer selected 'sofa'")

    # Step 4: Send product details
    logger.info("\n[SEND] Step 5: Send Product Details with Buttons")
    logger.info(f"""
    await adapter.send_interactive_message(
        to="{customer_phone}",
        interactive_type="button",
        body_text="Luxury Corner Sofa - 7 Seats\\n\\nPrice: 4,500 SAR\\nDelivery: Free to Riyadh\\nWarranty: 5 years",
        header={{"type": "image", "image": {{"link": "https://..."}}}},
        action={{
            "buttons": [
                {{"type": "reply", "reply": {{"id": "buy_now", "title": "Buy Now"}}}},
                {{"type": "reply", "reply": {{"id": "more_info", "title": "More Info"}}}},
                {{"type": "reply", "reply": {{"id": "schedule_visit", "title": "Visit Showroom"}}}}
            ]
        }}
    )
    """)

    logger.info("   [OK] Product card sent with action buttons")

    # Step 5: Customer purchases
    logger.info("\n[ORDER] Step 6: Customer Clicks 'Buy Now' - Process Order")
    logger.info("   Order ID: ORD-2024-12345")
    logger.info("   Amount: 4,500 SAR")

    # Step 6: Send order confirmation template
    logger.info("\n[SEND] Step 7: Send Order Confirmation Template")
    logger.info(f"""
    await adapter.send_template_message(
        to="{customer_phone}",
        template_name="order_confirmation",
        language="ar",
        components=[
            {{
                "type": "body",
                "parameters": [
                    {{"type": "text", "text": "ORD-2024-12345"}},
                    {{"type": "text", "text": "Luxury Corner Sofa"}},
                    {{"type": "text", "text": "4,500 SAR"}},
                    {{"type": "text", "text": "3-5 business days"}}
                ]
            }}
        ]
    )
    """)

    logger.info("   [OK] Order confirmation sent")

    # Step 7: Track conversion
    logger.info("\n[TRACK] Step 8: Track Conversion to Meta CAPI")
    logger.info(f"""
    result = await adapter.mark_conversion(
        wa_id="{customer_phone}",
        value=4500.0,
        currency="SAR",
        event_name="Purchase"
    )
    """)

    logger.info("   [OK] Conversion tracked to Meta CAPI for attribution")
    logger.info("   -> Click-to-WhatsApp ad will get purchase attribution")


async def example_server_side_conversions():
    """
    Example: Sending conversion events to all platforms for improved EMQ.
    """
    from app.stratum.conversions import ConversionEvent, EventType, UserData

    logger.info("\n" + "=" * 60)
    logger.info("SERVER-SIDE CONVERSIONS API EXAMPLE")
    logger.info("=" * 60)

    logger.info("\n[TARGET] Goal: Improve EMQ by sending server-side conversion events")
    logger.info("   -> Target EMQ: Purchase >=8.5, AddToCart >=6.0")

    # Create user data (simulating e-commerce checkout)
    logger.info("\n[USER] Step 1: Collect User Data")
    user_data = UserData(
        email="customer@example.com",
        phone="+966501234567",
        first_name="Ahmed",
        last_name="Al-Saud",
        city="Riyadh",
        country="SA",
        external_id="cust_abc123",
        client_ip_address="185.76.10.1",
        client_user_agent="Mozilla/5.0...",
        fbc="fb.1.1234567890.123456789",  # From URL ?fbclid=...
    )

    logger.info(f"   Email: {user_data.email}")
    logger.info(f"   Phone: {user_data.phone}")
    logger.info(f"   External ID: {user_data.external_id}")
    logger.info("   Click ID (fbc): Present")

    logger.info("\n[HASH] Step 2: Data is Automatically Hashed (SHA256)")
    logger.info(f"   Hashed email: {user_data.get_hashed('email')[:20]}...")
    logger.info(f"   Hashed phone: {user_data.get_hashed('phone')[:20]}...")

    # Create conversion event
    logger.info("\n[EVENT] Step 3: Create Conversion Event")
    event = ConversionEvent(
        event_name=EventType.PURCHASE,
        event_time=datetime.now(UTC),
        user_data=user_data,
        custom_data={
            "currency": "SAR",
            "value": 4500.0,
            "content_ids": ["SKU-SOFA-7SEAT"],
            "content_type": "product",
            "num_items": 1,
        },
        event_source_url="https://midasfurniture.sa/checkout/success",
        action_source="website",
    )

    logger.info(f"   Event: {event.event_name.value}")
    logger.info(f"   Value: {event.custom_data['currency']} {event.custom_data['value']}")
    logger.info(f"   Event ID: {event.event_id} (for deduplication)")

    # Send to multiple platforms
    logger.info("\n[SEND] Step 4: Send to All Platforms")

    logger.info("\n   [META] META (Facebook/Instagram):")
    logger.info("   capi = MetaConversionsAPI(pixel_id='123...', access_token='EAA...')")
    logger.info("   result = await capi.send_event(event)")
    logger.info("   -> Events received: 1")
    logger.info("   -> EMQ Impact: Email match, Phone match, FBC match")

    logger.info("\n   [GOOGLE] GOOGLE ADS:")
    logger.info("   enhanced = GoogleEnhancedConversions(customer_id='...', ...)")
    logger.info("   result = await enhanced.upload_conversion(event)")
    logger.info("   -> Conversion uploaded with Enhanced Conversions data")

    logger.info("\n   [TIKTOK] TIKTOK:")
    logger.info("   tiktok = TikTokEventsAPI(pixel_code='...', access_token='...')")
    logger.info("   result = await tiktok.send_event(event)")
    logger.info("   -> Event sent: CompletePayment")

    logger.info("\n   [SNAP] SNAPCHAT:")
    logger.info("   snap = SnapchatConversionsAPI(pixel_id='...', access_token='...')")
    logger.info("   result = await snap.send_event(event)")
    logger.info("   -> Event sent: PURCHASE")

    # Unified API example
    logger.info("\n\n[UNIFIED] Alternative: Unified Conversions API (All at Once)")
    logger.info("""
    unified = UnifiedConversionsAPI()
    unified.add_platform("meta", MetaConversionsAPI(...))
    unified.add_platform("tiktok", TikTokEventsAPI(...))
    unified.add_platform("snapchat", SnapchatConversionsAPI(...))

    results = await unified.send_event(event, platforms=["meta", "tiktok", "snapchat"])
    # Returns: {"meta": {...}, "tiktok": {...}, "snapchat": {...}}
    """)


async def example_emq_improvement_strategy():
    """
    Example: Strategy for improving EMQ scores.
    """
    logger.info("\n" + "=" * 60)
    logger.info("EMQ IMPROVEMENT STRATEGY")
    logger.info("=" * 60)

    logger.info("""

    CURRENT vs TARGET EMQ SCORES
    +-------------------+---------+---------+-------------+
    | Event             | Current | Target  | Gap         |
    +-------------------+---------+---------+-------------+
    | Purchase          | 6.2     | 8.5     | -2.3 [X]    |
    | AddToCart         | 4.8     | 6.0     | -1.2 [!]    |
    | ViewContent       | 3.5     | 4.0     | -0.5 [!]    |
    | Lead              | 5.1     | 7.0     | -1.9 [X]    |
    +-------------------+---------+---------+-------------+

    ACTION PLAN TO IMPROVE EMQ

    1. IMPLEMENT SERVER-SIDE TRACKING (CAPI)
       Impact: +1.5 to +2.0 EMQ points

       - Send events via Meta Conversions API
       - Include hashed email + phone
       - Pass fbclid/fbc when available
       - Deduplicate with browser pixel

    2. IMPROVE USER DATA COLLECTION
       Impact: +1.0 to +1.5 EMQ points

       - Collect email at checkout
       - Collect phone (especially for Gulf markets)
       - Use external_id for cross-device matching
       - Capture click IDs from URL parameters

    3. WHATSAPP INTEGRATION
       Impact: +0.5 to +1.0 EMQ points (for WhatsApp orders)

       - Track WhatsApp conversions via CAPI
       - Link Click-to-WhatsApp ads to purchases
       - Pass phone number (always available in WhatsApp)

    4. ADVANCED MATCHING
       Impact: +0.3 to +0.5 EMQ points

       - Pass IP address and user agent
       - Include location data (city, country)
       - Add date of birth when available

    EXPECTED RESULTS AFTER IMPLEMENTATION
    +-------------------+----------+---------------------------+
    | Event             | Expected | Signal Health Impact      |
    +-------------------+----------+---------------------------+
    | Purchase          | 8.7      | EMQ component: 100/100    |
    | AddToCart         | 6.8      | EMQ component: 100/100    |
    | ViewContent       | 5.2      | EMQ component: 100/100    |
    | Lead              | 7.5      | EMQ component: 100/100    |
    +-------------------+----------+---------------------------+

    [TARGET] TRUST GATE STATUS: HEALTHY (Score: 85+)
       -> Autopilot can run budget/bid optimizations
       -> Stratum will auto-scale winning campaigns
    """)


async def example_whatsapp_webhook_handler():
    """
    Example: Setting up WhatsApp webhook handler.
    """
    logger.info("\n" + "=" * 60)
    logger.info("WHATSAPP WEBHOOK HANDLER EXAMPLE")
    logger.info("=" * 60)

    logger.info("""

    WEBHOOK SETUP (Flask Example)

    ```python
    from flask import Flask, request
    from app.stratum.adapters.whatsapp_adapter import WhatsAppAdapter

    app = Flask(__name__)
    adapter = WhatsAppAdapter(credentials)

    # Webhook verification
    @app.route('/webhook', methods=['GET'])
    def verify():
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        result = adapter.verify_webhook(mode, token, challenge)
        return result if result else ('Forbidden', 403)

    # Webhook handler
    @app.route('/webhook', methods=['POST'])
    async def webhook():
        # Verify signature
        signature = request.headers.get('X-Hub-Signature-256', '')
        if not adapter.verify_signature(request.data, signature):
            return ('Forbidden', 403)

        # Process webhook
        payload = request.json
        await adapter.process_webhook(payload)
        return 'OK'

    # Register message handler
    @adapter.on_message
    async def handle_message(message):
        print(f"Received from {message.wa_id}: {message.text}")

        # Auto-reply logic
        if "price" in message.text.lower():
            await adapter.send_text_message(
                to=message.wa_id,
                text="Our prices start from 1,500 SAR. What product are you interested in?",
                reply_to=message.message_id
            )

    # Register status handler
    @adapter.on_status_update
    async def handle_status(message_id, status):
        print(f"Message {message_id} status: {status}")
    ```

    WEBHOOK EVENTS HANDLED:

    [OK] Incoming Messages
       - Text messages
       - Media (images, videos, documents)
       - Interactive replies (button clicks, list selections)
       - Location shares
       - Contact shares

    [OK] Status Updates
       - sent: Message accepted by WhatsApp
       - delivered: Message delivered to device
       - read: Message read by recipient
       - failed: Message delivery failed

    [OK] Conversation Tracking
       - Auto-tracks all messages per contact
       - 24-hour window management
       - Conversion attribution
    """)


async def main():
    """Run all examples."""
    logger.info("[START] STRATUM AI: WhatsApp + Conversions API Examples")
    logger.info("=" * 60)

    await example_whatsapp_messaging()
    await example_server_side_conversions()
    await example_emq_improvement_strategy()
    await example_whatsapp_webhook_handler()

    logger.info("\n" + "=" * 60)
    logger.info("[OK] All examples completed!")
    logger.info("=" * 60)

    logger.info("""

    SUMMARY: What You Now Have

    1. ADVERTISING PLATFORMS (4 adapters)
       - Meta (Facebook/Instagram)
       - Google Ads
       - TikTok
       - Snapchat

    2. MESSAGING PLATFORM (1 adapter)
       - WhatsApp Business API

    3. SERVER-SIDE TRACKING (5 CAPI clients)
       - Meta Conversions API
       - Google Enhanced Conversions
       - TikTok Events API
       - Snapchat Conversions API
       - Unified API (all-in-one)

    4. SIGNAL HEALTH & TRUST GATE
       - Real EMQ from platforms (not estimated)
       - Trust-gated automation

    [NEXT] Next Steps:
       1. Configure credentials in config.yaml
       2. Implement CAPI for all conversion points
       3. Set up WhatsApp webhook endpoint
       4. Monitor EMQ scores and trust gate status
    """)


if __name__ == "__main__":
    asyncio.run(main())
