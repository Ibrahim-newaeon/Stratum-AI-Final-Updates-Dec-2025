# Platform Integrations Edge Cases

## Overview

This document covers error handling, edge cases, and known limitations for platform integrations.

---

## Edge Cases

### 1. Invalid Credentials on Connect

**Scenario**: User provides invalid API credentials.

**Behavior**:
- Test connection before saving
- Return specific error message
- Do not save invalid credentials

**Response**:
```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Authentication failed with Meta API",
    "details": {
      "platform": "meta",
      "error_code": 190,
      "error_message": "Invalid OAuth 2.0 Access Token"
    }
  }
}
```

**UI Handling**: Display error in connection modal, highlight invalid field.

---

### 2. Circuit Breaker Opens

**Scenario**: Platform API returns 5 consecutive failures.

**Behavior**:
- Circuit breaker transitions to OPEN
- All subsequent requests rejected for 60 seconds
- Alert sent to tenant admins

**Response**:
```json
{
  "error": {
    "code": "CIRCUIT_OPEN",
    "message": "Platform temporarily unavailable",
    "details": {
      "platform": "meta",
      "circuit_state": "open",
      "recovery_at": "2024-01-15T14:31:00Z",
      "failure_count": 5
    }
  }
}
```

**Recovery**:
```python
# After 60 seconds, circuit transitions to HALF_OPEN
# System tests with 3 requests
# If successful, circuit returns to CLOSED
# If failed, returns to OPEN for another 60 seconds
```

---

### 3. Platform Rate Limit Exceeded

**Scenario**: Event volume exceeds platform rate limit.

**Behavior**:
- Rate limiter queues excess events
- Exponential backoff applied
- Events eventually delivered or expired

**Response**:
```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Platform rate limit exceeded",
    "details": {
      "platform": "tiktok",
      "retry_after_seconds": 60,
      "events_queued": 150
    }
  }
}
```

**Platform Rate Limits**:

| Platform | Events/Minute | Retry Strategy |
|----------|---------------|----------------|
| Meta | 1000 | 1s, 2s, 4s backoff |
| Google | 2000 | 1s, 2s, 4s backoff |
| TikTok | 600 | 5s, 10s, 20s backoff |
| Snapchat | 500 | 5s, 10s, 20s backoff |

---

### 4. Token Expiration

**Scenario**: OAuth token expires during operation.

**Behavior**:
- Detect 401 response
- Attempt token refresh (Google)
- Re-send failed request
- Alert user if refresh fails

**Handling**:
```python
async def _get_access_token(self) -> str:
    if self._access_token and time.time() < self._token_expires:
        return self._access_token

    # Refresh token
    response = await client.post(OAUTH_URL, data={
        "grant_type": "refresh_token",
        "refresh_token": self.refresh_token,
        "client_id": self.client_id,
        "client_secret": self.client_secret,
    })

    if response.status_code == 200:
        self._access_token = response.json()["access_token"]
        self._token_expires = time.time() + 3540  # 59 minutes
        return self._access_token

    raise TokenRefreshError("Failed to refresh token")
```

---

### 5. Duplicate Event Detection

**Scenario**: Same conversion event sent multiple times.

**Behavior**:
- Generate event key from event_id or content hash
- Check deduplication cache
- Skip if duplicate found
- Log duplicate for monitoring

**Handling**:
```python
def is_duplicate(self, event: dict) -> bool:
    event_key = self._generate_key(event)

    if event_key in self._seen_events:
        logger.info(f"Duplicate event blocked: {event_key}")
        return True

    self._seen_events[event_key] = datetime.now(timezone.utc)
    return False
```

---

### 6. PII Hashing Failure

**Scenario**: Invalid or missing PII data.

**Behavior**:
- Skip hashing for empty fields
- Normalize before hashing
- Continue with available data

**Handling**:
```python
def hash_data(self, user_data: dict) -> dict:
    hashed = {}

    if email := user_data.get("email"):
        try:
            normalized = self.normalize_email(email)
            hashed["em"] = self.hash_value(normalized)
        except ValueError:
            logger.warning(f"Invalid email format: {email}")

    if phone := user_data.get("phone"):
        try:
            normalized = self.normalize_phone(phone)
            hashed["ph"] = self.hash_value(normalized)
        except ValueError:
            logger.warning(f"Invalid phone format: {phone}")

    return hashed
```

---

### 7. Platform API Timeout

**Scenario**: Platform API does not respond within timeout.

**Behavior**:
- Timeout after 30 seconds
- Retry with exponential backoff
- Record as failure after max retries

**Response**:
```json
{
  "success": false,
  "data": {
    "platform": "snapchat",
    "events_received": 10,
    "events_processed": 0,
    "errors": [
      {"message": "Request timeout after 30 seconds"}
    ]
  }
}
```

---

### 8. Partial Batch Success

**Scenario**: Some events in batch succeed, others fail.

**Behavior**:
- Google returns partial failure details
- Log successful and failed events separately
- Return aggregated result

**Response (Google)**:
```json
{
  "success": true,
  "data": {
    "platform": "google",
    "events_received": 10,
    "events_processed": 8,
    "errors": [
      {
        "message": "Partial failure: 2 events rejected",
        "details": [
          {"index": 3, "error": "Invalid conversion action"},
          {"index": 7, "error": "Missing user identifiers"}
        ]
      }
    ]
  }
}
```

---

### 9. Connection Pool Exhaustion

**Scenario**: All HTTP connections in pool are busy.

**Behavior**:
- Wait for available connection
- Scale up pool if under max
- Timeout if wait exceeds threshold

**Handling**:
```python
async def get_client(self, platform: str) -> httpx.AsyncClient:
    async with self._lock:
        # If pool not at max, scale up
        if len(self._clients[platform]) < self.max_connections:
            await self.scale_up(platform)

        # Round-robin selection
        client = self._clients[platform][self._client_index[platform]]
        self._client_index[platform] = (
            self._client_index[platform] + 1
        ) % len(self._clients[platform])

        return client
```

---

### 10. Platform Maintenance Window

**Scenario**: Platform API undergoing scheduled maintenance.

**Behavior**:
- Receive 503 Service Unavailable
- Queue events for later delivery
- Alert users about maintenance

**Response**:
```json
{
  "error": {
    "code": "PLATFORM_MAINTENANCE",
    "message": "Meta API undergoing scheduled maintenance",
    "details": {
      "platform": "meta",
      "estimated_end": "2024-01-15T16:00:00Z",
      "events_queued": 500
    }
  }
}
```

---

### 11. Event Mapping Not Found

**Scenario**: Custom event name has no platform mapping.

**Behavior**:
- Fall back to generic event type
- Log warning for unmapped event
- Allow through with original name

**Handling**:
```python
def map_event(self, event_name: str, params: dict) -> EventMapping:
    if event_name in self.MAPPINGS:
        return self.MAPPINGS[event_name]

    logger.warning(f"No mapping for event: {event_name}, using generic")
    return EventMapping(
        source_event=event_name,
        platform_events={
            "meta": "CustomEvent",
            "google": "CUSTOM",
            "tiktok": "CustomEvent",
            "snapchat": "CUSTOM_EVENT_1"
        },
        parameters=params
    )
```

---

### 12. Credentials Rotation

**Scenario**: Access token rotated while connector active.

**Behavior**:
- Next API call fails with 401
- Connection marked as error
- User prompted to reconnect

**Response**:
```json
{
  "error": {
    "code": "CREDENTIALS_EXPIRED",
    "message": "Platform credentials have expired or been revoked",
    "details": {
      "platform": "meta",
      "action_required": "Please reconnect with new credentials"
    }
  }
}
```

---

## Known Limitations

### 1. No Offline Queue Persistence

**Limitation**: Events queued during outage are lost on restart.

**Impact**: Events may be lost during service restart.

**Planned**: Persistent queue with Redis or database.

---

### 2. Single Credential Set Per Platform

**Limitation**: Only one pixel/account per platform per tenant.

**Impact**: Cannot track multiple pixels simultaneously.

**Workaround**: Create separate tenants for different pixels.

---

### 3. No Historical Event Replay

**Limitation**: Cannot replay failed events from past.

**Impact**: Events failed after max retries are lost.

**Planned**: Event replay with dead-letter queue.

---

### 4. Limited Event Enrichment

**Limitation**: Cannot enrich events with external data.

**Impact**: Events sent as-is without additional context.

**Planned**: Event enrichment pipeline integration.

---

## Error Recovery

### Connection Errors

| Error | Recovery |
|-------|----------|
| Invalid credentials | Prompt reconnection |
| Token expired | Auto-refresh (Google) or reconnect |
| Rate limited | Exponential backoff |
| Timeout | Retry with backoff |

### System Errors

| Error | Recovery |
|-------|----------|
| Circuit open | Wait for recovery timeout |
| Pool exhausted | Scale up or wait |
| Memory pressure | Reduce batch size |

---

## Monitoring

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| Success rate per platform | < 90% |
| Average latency | > 5 seconds |
| Circuit breaker opens | > 2/hour |
| Token refresh failures | Any |
| Duplicate rate | > 10% |

### Health Checks

```python
async def integration_health():
    return {
        "status": "healthy",
        "checks": {
            "meta": await check_platform("meta"),
            "google": await check_platform("google"),
            "tiktok": await check_platform("tiktok"),
            "snapchat": await check_platform("snapchat"),
            "connection_pool": connection_pool.get_pool_stats(),
            "deduplicator": event_deduplicator.get_stats()
        }
    }
```

---

## Security Considerations

### Credential Storage

- Credentials encrypted at rest (AES-256)
- Never logged or exposed in errors
- Stored in secrets manager in production

### PII Handling

- All PII hashed before transmission
- Original PII never leaves system
- SHA-256 one-way hashing

### Audit Trail

- All connection attempts logged
- Credential changes tracked
- Event delivery logged for compliance

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
