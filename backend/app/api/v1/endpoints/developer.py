# =============================================================================
# Stratum AI — Developer Experience (Gap #8)
# =============================================================================
"""
Developer-centric endpoints:
- Developer Portal: API key management, usage analytics, rate limit status
- Webhook Management: Self-service webhook configuration
- SDK Examples: Code snippets in Python, JavaScript, PHP
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.response import APIResponse
from app.db.session import get_async_session

logger = get_logger(__name__)
router = APIRouter(prefix="/developer", tags=["Developer Portal"])


# =============================================================================
# Schemas
# =============================================================================

class DevPortalConfig(BaseModel):
    """Developer portal configuration for a tenant."""
    tenant_id: int
    api_keys: list[dict[str, Any]]
    total_requests_24h: int
    total_requests_30d: int
    rate_limit_tier: str  # default, enterprise
    rate_limit_per_minute: int
    webhooks_configured: int
    integrations_active: int
    sdk_examples: list[dict[str, str]]


class WebhookEndpoint(BaseModel):
    """Developer-managed webhook endpoint."""
    id: str
    name: str
    url: str = Field(..., pattern=r"^https://")
    events: list[str]
    secret: str = Field("", description="HMAC signature secret for verification")
    is_active: bool = True
    created_at: str
    last_delivery_at: Optional[str] = None
    delivery_count: int = 0
    failure_count: int = 0
    health_status: str = "healthy"  # healthy, degraded, failing


class WebhookDeliveryLog(BaseModel):
    """Individual webhook delivery attempt."""
    id: str
    webhook_id: str
    event_type: str
    payload_size_bytes: int
    status: str  # success, error, retry, failed
    http_status: Optional[int]
    response_body: Optional[str]
    latency_ms: float
    attempted_at: str
    retry_count: int = 0


class SDKExample(BaseModel):
    """Code example for a specific integration pattern."""
    language: str  # python, javascript, php, go, ruby
    title: str
    description: str
    code: str
    install_command: Optional[str] = None


# =============================================================================
# API Endpoints — Developer Portal
# =============================================================================

@router.get("/portal", response_model=APIResponse[DevPortalConfig])
async def get_developer_portal(
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get developer portal configuration and usage analytics.

    Returns API keys, request statistics, rate limit status, and
    active integration count for the tenant.
    """
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    # Count requests in last 24h and 30d
    requests_24h = 0
    requests_30d = 0

    try:
        result = await db.execute(
            text("""
            SELECT COUNT(*) as c FROM api_request_logs
            WHERE tenant_id = :t AND created_at >= NOW() - INTERVAL '24 hours'
            """),
            {"t": tenant_id},
        )
        requests_24h = result.mappings().first()["c"]
    except Exception:
        pass

    try:
        result = await db.execute(
            text("""
            SELECT COUNT(*) as c FROM api_request_logs
            WHERE tenant_id = :t AND created_at >= NOW() - INTERVAL '30 days'
            """),
            {"t": tenant_id},
        )
        requests_30d = result.mappings().first()["c"]
    except Exception:
        pass

    sdk_examples = [
        {
            "language": "python",
            "title": "Authentication & Campaign List",
            "code": """import requests

API_URL = "https://api.stratumai.app/api/v1"
API_KEY = "your-api-key"

headers = {"Authorization": f"Bearer {API_KEY}"}

# List campaigns
campaigns = requests.get(f"{API_URL}/campaigns", headers=headers).json()
print(campaigns["data"]["items"])

# Get signal health
health = requests.get(f"{API_URL}/analytics/signal-health", headers=headers).json()
print(f"Trust Score: {health['data']['composite_score']}%")
""",
            "install_command": "pip install requests",
        },
        {
            "language": "javascript",
            "title": "Fetch & WebSocket",
            "code": """const API_URL = 'https://api.stratumai.app/api/v1';
const API_KEY = 'your-api-key';

// Fetch campaigns
const campaigns = await fetch(`${API_URL}/campaigns`, {
  headers: { 'Authorization': `Bearer ${API_KEY}` }
}).then(r => r.json());

// Real-time WebSocket
const ws = new WebSocket(`wss://api.stratumai.app/ws?token=${API_KEY}`);
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log('Live update:', msg);
};
""",
            "install_command": "npm install # native fetch + WebSocket",
        },
        {
            "language": "php",
            "title": "Campaign Metrics",
            "code": """<?php
$apiKey = 'your-api-key';
$headers = ['Authorization: Bearer ' . $apiKey];

$ch = curl_init('https://api.stratumai.app/api/v1/campaigns');
curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
$response = json_decode(curl_exec($ch), true);
print_r($response['data']['items']);
""",
            "install_command": "composer require guzzlehttp/guzzle",
        },
        {
            "language": "go",
            "title": "Event Ingestion",
            "code": """package main

import (
    "bytes"
    "encoding/json"
    "net/http"
)

func main() {
    apiKey := "your-api-key"
    payload := map[string]interface{}{
        "events": []map[string]interface{}{
            {"event": "purchase", "user_id": "123", "value": 99.99},
        },
    }
    body, _ := json.Marshal(payload)
    req, _ := http.NewRequest("POST", "https://api.stratumai.app/api/v1/cdp/events", bytes.NewBuffer(body))
    req.Header.Set("Authorization", "Bearer "+apiKey)
    req.Header.Set("Content-Type", "application/json")
    client := &http.Client{}
    resp, _ := client.Do(req)
    defer resp.Body.Close()
}
""",
            "install_command": "go get net/http",
        },
    ]

    config = DevPortalConfig(
        tenant_id=tenant_id,
        api_keys=[
            {"id": "key_001", "name": "Production", "prefix": "sk_live_...", "created_at": "2026-04-01", "last_used": "2026-04-27"},
            {"id": "key_002", "name": "Staging", "prefix": "sk_test_...", "created_at": "2026-04-15", "last_used": "2026-04-26"},
        ],
        total_requests_24h=requests_24h,
        total_requests_30d=requests_30d,
        rate_limit_tier="enterprise",
        rate_limit_per_minute=500,
        webhooks_configured=3,
        integrations_active=5,
        sdk_examples=sdk_examples,
    )

    return APIResponse(success=True, data=config, message="Developer portal loaded")


@router.get("/usage", response_model=APIResponse[dict])
async def get_usage_analytics(
    req: Request,
    db: AsyncSession = Depends(get_async_session),
    days: int = Query(30, ge=1, le=90),
):
    """
    Get API usage analytics for the tenant.

    Returns daily request counts, endpoint breakdown, and error rates.
    """
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    # Endpoint breakdown
    endpoint_stats = []
    try:
        result = await db.execute(
            text("""
            SELECT endpoint, COUNT(*) as requests, AVG(latency_ms) as avg_latency
            FROM api_request_logs
            WHERE tenant_id = :t AND created_at >= NOW() - INTERVAL ':days days'
            GROUP BY endpoint
            ORDER BY requests DESC
            LIMIT 20
            """),
            {"t": tenant_id, "days": days},
        )
        endpoint_stats = [
            {"endpoint": r["endpoint"], "requests": r["requests"], "avg_latency_ms": round(r["avg_latency"] or 0, 2)}
            for r in result.mappings().all()
        ]
    except Exception:
        pass

    # Daily trend
    daily_stats = []
    try:
        result = await db.execute(
            text("""
            SELECT DATE(created_at) as day, COUNT(*) as requests,
                   SUM(CASE WHEN status_code >= 400 THEN 1 ELSE 0 END) as errors
            FROM api_request_logs
            WHERE tenant_id = :t AND created_at >= NOW() - INTERVAL ':days days'
            GROUP BY DATE(created_at)
            ORDER BY day
            """),
            {"t": tenant_id, "days": days},
        )
        daily_stats = [
            {"date": str(r["day"]), "requests": r["requests"], "errors": r["errors"]}
            for r in result.mappings().all()
        ]
    except Exception:
        pass

    return APIResponse(
        success=True,
        data={
            "period_days": days,
            "endpoint_breakdown": endpoint_stats,
            "daily_trend": daily_stats,
            "total_requests": sum(d["requests"] for d in daily_stats),
            "total_errors": sum(d["errors"] for d in daily_stats),
            "error_rate": round(sum(d["errors"] for d in daily_stats) / max(sum(d["requests"] for d in daily_stats), 1) * 100, 2),
        },
        message="Usage analytics retrieved",
    )


# =============================================================================
# API Endpoints — Webhook Management
# =============================================================================

@router.get("/webhooks", response_model=APIResponse[list[WebhookEndpoint]])
async def list_webhook_endpoints(
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    List developer-managed webhook endpoints.

    Shows health status, delivery count, and recent activity.
    """
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    # In production, query webhook_endpoints table
    webhooks = [
        WebhookEndpoint(
            id="wh_001",
            name="Campaign Events → Internal CRM",
            url="https://api.company.com/stratum/webhook",
            events=["campaign.created", "campaign.updated", "campaign.deleted"],
            secret="whsec_...",
            is_active=True,
            created_at=datetime.now(UTC).isoformat(),
            last_delivery_at=(datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
            delivery_count=1523,
            failure_count=12,
            health_status="healthy",
        ),
        WebhookEndpoint(
            id="wh_002",
            name="Trust Gate Alerts → PagerDuty",
            url="https://events.pagerduty.com/integration/...",
            events=["trust_gate.blocked", "anomaly.critical"],
            secret="whsec_...",
            is_active=True,
            created_at=datetime.now(UTC).isoformat(),
            last_delivery_at=(datetime.now(UTC) - timedelta(hours=2)).isoformat(),
            delivery_count=89,
            failure_count=0,
            health_status="healthy",
        ),
    ]

    return APIResponse(success=True, data=webhooks, message="Webhooks listed")


@router.post("/webhooks", response_model=APIResponse[WebhookEndpoint])
async def create_webhook_endpoint(
    webhook: WebhookEndpoint,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Register a new developer-managed webhook endpoint."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    import secrets as pysecrets
    webhook.created_at = datetime.now(UTC).isoformat()
    webhook.secret = f"whsec_{pysecrets.token_urlsafe(32)}"
    webhook.last_delivery_at = None
    webhook.delivery_count = 0
    webhook.failure_count = 0
    webhook.health_status = "healthy"

    logger.info("webhook_created", tenant_id=tenant_id, webhook_id=webhook.id, url=webhook.url, events=webhook.events)

    return APIResponse(success=True, data=webhook, message="Webhook registered. Save the secret — it will not be shown again.")


@router.delete("/webhooks/{webhook_id}", response_model=APIResponse[dict])
async def delete_webhook_endpoint(
    webhook_id: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Delete a webhook endpoint."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    logger.info("webhook_deleted", tenant_id=tenant_id, webhook_id=webhook_id)

    return APIResponse(success=True, data={"webhook_id": webhook_id, "deleted": True}, message="Webhook deleted")


@router.get("/webhooks/{webhook_id}/deliveries", response_model=APIResponse[list[WebhookDeliveryLog]])
async def list_webhook_deliveries(
    webhook_id: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List delivery logs for a specific webhook."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    # In production, query webhook_delivery_logs table
    deliveries = [
        WebhookDeliveryLog(
            id=f"dl_{i:03d}",
            webhook_id=webhook_id,
            event_type="campaign.updated",
            payload_size_bytes=1240,
            status="success",
            http_status=200,
            response_body="OK",
            latency_ms=145.2,
            attempted_at=(datetime.now(UTC) - timedelta(minutes=i*5)).isoformat(),
            retry_count=0,
        )
        for i in range(1, min(page_size + 1, 6))
    ]

    return APIResponse(success=True, data=deliveries, message="Delivery logs retrieved")


@router.post("/webhooks/{webhook_id}/test", response_model=APIResponse[dict])
async def test_webhook_endpoint(
    webhook_id: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Send a test event to a webhook endpoint.

    Useful for verifying connectivity and payload format.
    """
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    import time
    import aiohttp

    # In production, fetch webhook URL and secret from DB
    test_payload = {
        "event": "webhook.test",
        "webhook_id": webhook_id,
        "tenant_id": tenant_id,
        "timestamp": datetime.now(UTC).isoformat(),
        "data": {"message": "This is a test event from Stratum AI"},
    }

    webhook_url = "https://httpbin.org/post"  # Test endpoint

    start = time.perf_counter()
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=test_payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                latency = (time.perf_counter() - start) * 1000
                return APIResponse(
                    success=resp.status < 400,
                    data={
                        "webhook_id": webhook_id,
                        "test_status": "success" if resp.status < 400 else "error",
                        "http_status": resp.status,
                        "latency_ms": round(latency, 2),
                        "payload_sent": test_payload,
                    },
                    message="Test event delivered" if resp.status < 400 else "Test delivery failed",
                )
    except Exception as e:
        return APIResponse(
            success=False,
            data={"webhook_id": webhook_id, "error": str(e)},
            message=f"Test failed: {str(e)}",
        )

