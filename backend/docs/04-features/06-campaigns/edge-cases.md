# Campaign Builder Edge Cases

## Overview

This document covers error handling, edge cases, and known limitations for the Campaign Builder feature.

---

## Edge Cases

### 1. OAuth Token Expiry

**Scenario**: Access token expires before publish attempt.

**Behavior**:
- Connection status: `expired`
- Publish blocked until refreshed
- Auto-refresh attempted if refresh token valid

**Handling**:
```python
async def publish_campaign(draft_id):
    connection = await get_connection(platform)

    if connection.status == ConnectionStatus.EXPIRED:
        success = await try_refresh_token(connection)
        if not success:
            raise TokenExpiredError("Please reconnect platform")
```

**Response**:
```json
{
  "error": {
    "code": "TOKEN_EXPIRED",
    "message": "Meta access token has expired. Please reconnect your account.",
    "details": {
      "platform": "meta",
      "action_required": "reconnect"
    }
  }
}
```

---

### 2. Budget Exceeds Account Cap

**Scenario**: Campaign budget exceeds ad account daily cap.

**Behavior**:
- Validation fails at submit/publish
- Error message shows cap limit

**Validation**:
```python
def validate_budget(draft, ad_account):
    campaign_budget = draft.draft_json["campaign"]["budget"]["amount"]

    if ad_account.daily_budget_cap:
        if campaign_budget > ad_account.daily_budget_cap:
            raise ValidationError(
                f"Campaign budget ${campaign_budget} exceeds "
                f"daily cap ${ad_account.daily_budget_cap}"
            )
```

**Response**:
```json
{
  "error": {
    "code": "BUDGET_EXCEEDS_CAP",
    "message": "Campaign budget $1500 exceeds daily cap $1000",
    "details": {
      "campaign_budget": 1500.00,
      "daily_cap": 1000.00
    }
  }
}
```

---

### 3. Platform API Failure During Publish

**Scenario**: Platform API returns error during campaign creation.

**Behavior**:
- Status changes to `failed`
- Error logged in publish_log
- Retry available

**Response**:
```json
{
  "error": {
    "code": "PUBLISH_FAILED",
    "message": "Failed to publish campaign to Meta",
    "details": {
      "platform_error_code": 2654,
      "platform_error_message": "Targeting audience is too narrow",
      "retry_available": true
    }
  }
}
```

**Retry Logic**:
```python
MAX_RETRIES = 3
RETRY_DELAYS = [60, 300, 900]  # 1m, 5m, 15m

async def publish_with_retry(draft_id):
    for attempt in range(MAX_RETRIES):
        try:
            return await publish_campaign(draft_id)
        except RetryableError:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAYS[attempt])
    raise PublishFailedError()
```

---

### 4. Concurrent Edit Conflict

**Scenario**: Two users edit same draft simultaneously.

**Behavior**:
- Last save wins
- No locking mechanism currently
- Future: Optimistic locking with version

**Mitigation**:
```python
# Future implementation
class CampaignDraft:
    version: int = 1

async def update_draft(draft_id, data, expected_version):
    draft = await get_draft(draft_id)
    if draft.version != expected_version:
        raise ConflictError("Draft was modified by another user")

    draft.version += 1
    await save_draft(draft)
```

---

### 5. Invalid Workflow Transition

**Scenario**: Attempting to publish a draft that isn't approved.

**Valid Transitions**:
| From | To |
|------|-----|
| draft | submitted |
| submitted | approved, rejected |
| rejected | draft (via resubmit → submitted) |
| approved | publishing, draft (cancel) |
| publishing | published, failed |
| failed | publishing (retry) |

**Response**:
```json
{
  "error": {
    "code": "INVALID_STATUS_TRANSITION",
    "message": "Cannot publish from 'draft' status. Submit for approval first.",
    "details": {
      "current_status": "draft",
      "required_status": "approved",
      "valid_actions": ["submit"]
    }
  }
}
```

---

### 6. Ad Account Disabled After Draft Creation

**Scenario**: Ad account disabled after campaign draft was created.

**Behavior**:
- Validation fails at publish time
- Draft remains intact
- User must enable account or switch

**Response**:
```json
{
  "error": {
    "code": "AD_ACCOUNT_NOT_ENABLED",
    "message": "Ad account 'Acme Corp Main' is not enabled",
    "details": {
      "ad_account_id": "uuid-...",
      "platform_account_id": "act_123456789",
      "action_required": "enable_account"
    }
  }
}
```

---

### 7. Platform Rate Limiting

**Scenario**: Too many API calls to ad platform.

**Platform Limits**:
| Platform | Limit |
|----------|-------|
| Meta | 200 calls/hour |
| Google | 10,000 operations/day |
| TikTok | 100 calls/min |
| Snapchat | 100 calls/min |

**Handling**:
```python
async def call_platform_api(platform, request):
    try:
        return await api_client.request(request)
    except RateLimitError as e:
        retry_after = e.retry_after or 60
        raise RateLimitExceededError(
            f"Rate limit exceeded. Retry after {retry_after}s"
        )
```

---

### 8. Draft JSON Schema Change

**Scenario**: Draft created with old JSON schema version.

**Behavior**:
- Migration applied at load time
- New fields get defaults
- Deprecated fields ignored

**Migration**:
```python
def migrate_draft_json(draft_json, from_version, to_version):
    if from_version < 2:
        # v2: Added schedule to campaign
        if "schedule" not in draft_json["campaign"]:
            draft_json["campaign"]["schedule"] = None

    return draft_json
```

---

### 9. Large Campaign (Many Ad Sets/Ads)

**Scenario**: Campaign with 50+ ad sets or 100+ ads.

**Limits**:
| Item | Limit |
|------|-------|
| Ad sets per campaign | 50 |
| Ads per ad set | 50 |
| Total ads per campaign | 500 |

**Response**:
```json
{
  "error": {
    "code": "CAMPAIGN_TOO_LARGE",
    "message": "Campaign exceeds maximum 50 ad sets",
    "details": {
      "ad_sets_count": 65,
      "max_ad_sets": 50
    }
  }
}
```

---

### 10. Image/Video Asset Not Found

**Scenario**: Creative references URL that returns 404.

**Behavior**:
- Validation at submit time
- Async check for asset accessibility
- Warning if asset unavailable

**Response**:
```json
{
  "error": {
    "code": "ASSET_NOT_FOUND",
    "message": "Creative image URL is not accessible",
    "details": {
      "ad_index": 0,
      "image_url": "https://...",
      "http_status": 404
    }
  }
}
```

---

### 11. Platform Connection Lost During Publish

**Scenario**: OAuth revoked externally during publish.

**Behavior**:
- Publish fails with auth error
- Connection marked as `disconnected`
- Requires reconnection

**Detection**:
```python
try:
    await platform_api.create_campaign(...)
except AuthenticationError:
    connection.status = ConnectionStatus.DISCONNECTED
    await db.commit()
    raise ReconnectionRequiredError()
```

---

### 12. Partial Publish Success

**Scenario**: Campaign created but some ad sets failed.

**Behavior**:
- Campaign created on platform
- Failed items logged
- Status: `published` with warnings

**Response**:
```json
{
  "success": true,
  "data": {
    "status": "published",
    "platform_campaign_id": "23842927...",
    "warnings": [
      {
        "ad_set_index": 2,
        "error": "Targeting audience too small"
      }
    ],
    "created": {
      "campaign": true,
      "ad_sets": 3,
      "ad_sets_failed": 1,
      "ads": 8,
      "ads_failed": 2
    }
  }
}
```

---

## Known Limitations

### 1. No Bulk Operations

**Limitation**: Cannot bulk approve/reject/publish multiple drafts.

**Workaround**: Process one at a time via API.

---

### 2. Platform-Specific Features

**Limitation**: Some platform features not supported in canonical JSON.

**Examples**:
- Meta: Lead forms, dynamic creatives
- Google: Responsive display ads
- TikTok: Spark ads

**Workaround**: Use platform directly for advanced features.

---

### 3. Real-time Status Sync

**Limitation**: Campaign status not synced in real-time from platform.

**Impact**: Platform changes (pause, budget change) not reflected immediately.

**Planned**: Webhook integration for status updates.

---

### 4. No Editing Published Campaigns

**Limitation**: Cannot edit campaigns after publishing.

**Current**: Must modify in platform directly.

**Planned**: Edit → republish flow.

---

## Error Recovery

### Publish Failures

| Error | Recovery |
|-------|----------|
| Token expired | Reconnect platform |
| Budget exceeded | Lower budget or raise cap |
| Targeting invalid | Edit targeting in draft |
| Rate limited | Wait and retry |

### Connection Issues

| Error | Recovery |
|-------|----------|
| Disconnected | Initiate new OAuth flow |
| Expired | Refresh token (auto-attempted) |
| Error | Check platform status, reconnect |

---

## Monitoring

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| Publish success rate | < 90% |
| Token refresh failures | > 5/hour |
| API error rate | > 5% |
| Avg publish time | > 30 seconds |

### Health Checks

```python
async def campaign_builder_health():
    return {
        "status": "healthy",
        "checks": {
            "database": await check_db(),
            "redis": await check_redis(),
            "meta_api": await check_meta_api(),
            "google_api": await check_google_api(),
            "celery": await check_celery_workers()
        }
    }
```

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
