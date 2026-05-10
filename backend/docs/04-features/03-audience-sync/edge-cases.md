# Audience Sync Edge Cases

## Overview

This document covers error handling, edge cases, and known limitations for the Audience Sync feature.

---

## Edge Cases

### 1. Empty Segment

**Scenario**: Attempting to create/sync an audience from an empty segment.

**Behavior**:
- Sync proceeds but sends 0 profiles
- Platform audience created (if new)
- Warning logged, user notified

**Response**:
```json
{
  "warning": "Segment has no profiles matching identifier criteria",
  "profiles_sent": 0
}
```

---

### 2. No Valid Identifiers

**Scenario**: Segment has profiles but none with email/phone/MAID.

**Behavior**:
- Sync proceeds with 0 sendable profiles
- Warning returned
- Match rate: 0%

**Handling**:
```python
sendable_profiles = [p for p in profiles if has_valid_identifier(p)]
if not sendable_profiles:
    job.warning = "No profiles with valid identifiers (email, phone, MAID)"
```

---

### 3. Platform Credentials Expired

**Scenario**: OAuth token has expired.

**Behavior**:
- Sync fails with `CREDENTIALS_EXPIRED` error
- Auto-sync disabled for audience
- User notification sent

**Recovery**:
1. User must re-authenticate with platform
2. Re-enable auto-sync after reconnection

**Error Response**:
```json
{
  "error": {
    "code": "CREDENTIALS_EXPIRED",
    "message": "Meta access token has expired. Please reconnect your account.",
    "action_required": "reconnect_platform"
  }
}
```

---

### 4. Platform Rate Limit

**Scenario**: Too many API calls to platform.

**Behavior**:
- Retry with exponential backoff
- Max 4 retries (1m, 5m, 15m, 1h)
- If all retries fail, mark sync as failed

**Platform Rate Limits**:

| Platform | Limit | Window |
|----------|-------|--------|
| Meta | 200 calls/hour | Per app |
| Google | 10,000 operations/day | Per account |
| TikTok | 100 calls/min | Per access token |
| Snapchat | 100 calls/min | Per account |

---

### 5. Large Segment (>100K Profiles)

**Scenario**: Syncing a segment with over 100,000 profiles.

**Behavior**:
- Profiles uploaded in batches (10,000 per batch)
- Progress tracked per batch
- Longer duration (minutes instead of seconds)

**Optimization**:
```python
BATCH_SIZE = 10000

for batch in chunk_list(profiles, BATCH_SIZE):
    await upload_batch(batch)
    await asyncio.sleep(1)  # Rate limit protection
```

---

### 6. Segment Changes During Sync

**Scenario**: Segment membership changes while sync is running.

**Behavior**:
- Sync uses snapshot taken at start
- Changes picked up in next sync
- No partial state corruption

**Isolation**:
```python
async def sync_audience():
    # Snapshot segment at start
    members = await get_segment_members_snapshot(segment_id)

    # Process snapshot
    for batch in chunk_list(members, BATCH_SIZE):
        await upload_batch(batch)
```

---

### 7. Platform Audience Deleted Externally

**Scenario**: User deletes audience directly in ad platform UI.

**Behavior**:
- Next sync fails with "audience not found"
- Audience marked as "stale"
- Option to recreate or unlink

**Detection**:
```python
try:
    await connector.add_users(audience_id, users)
except AudienceNotFoundError:
    audience.status = "stale"
    audience.error = "Audience deleted on platform"
```

---

### 8. Duplicate Audience Names

**Scenario**: Creating audience with name that already exists on platform.

**Behavior**:
- Platform may accept (Meta) or reject (Google)
- If rejected, append timestamp to name
- Notify user of name change

**Handling**:
```python
try:
    result = await connector.create_audience(name)
except DuplicateNameError:
    new_name = f"{name} - {datetime.now().strftime('%Y%m%d')}"
    result = await connector.create_audience(new_name)
```

---

### 9. Concurrent Sync Requests

**Scenario**: Two sync requests for same audience at same time.

**Behavior**:
- First request proceeds
- Second request rejected with `SYNC_IN_PROGRESS`
- No duplicate data sent

**Locking**:
```python
async def sync_audience(audience_id):
    lock_key = f"audience_sync:{audience_id}"

    if await redis.exists(lock_key):
        raise SyncInProgressError()

    await redis.setex(lock_key, 300, "1")  # 5 min lock
    try:
        await execute_sync()
    finally:
        await redis.delete(lock_key)
```

---

### 10. Partial Batch Failure

**Scenario**: Some batches succeed, others fail during large upload.

**Behavior**:
- Successful batches remain on platform
- Failed batches logged for retry
- Sync marked as "partial"

**Tracking**:
```python
results = {
    "total_batches": 10,
    "successful_batches": 7,
    "failed_batches": 3,
    "profiles_sent": 70000,
    "profiles_failed": 30000
}
```

---

### 11. Invalid Phone Format

**Scenario**: Profile has phone number in non-E.164 format.

**Behavior**:
- Attempt normalization
- If can't normalize, skip identifier
- Log warning, continue with other identifiers

**Normalization**:
```python
def normalize_phone(phone: str) -> Optional[str]:
    # Remove spaces, dashes, parentheses
    digits = ''.join(c for c in phone if c.isdigit() or c == '+')

    # Validate E.164 format
    if len(digits) >= 10 and len(digits) <= 15:
        return digits if digits.startswith('+') else f"+{digits}"

    return None  # Invalid, skip this identifier
```

---

### 12. Platform Maintenance

**Scenario**: Platform API is down for maintenance.

**Behavior**:
- Sync fails with `PLATFORM_UNAVAILABLE`
- Automatic retry after delay
- Scheduled syncs postponed

**Detection**:
```python
if response.status in [502, 503, 504]:
    raise PlatformUnavailableError(retry_after=300)
```

---

## Known Limitations

### 1. Match Rate Delay

**Limitation**: Platform match rate may not be immediately accurate.

**Reason**: Platforms take time to process uploaded data.

**Workaround**: Check audience info after 24 hours for accurate match rate.

---

### 2. Minimum Audience Size

**Limitation**: Some platforms require minimum audience size.

| Platform | Minimum Size |
|----------|--------------|
| Meta | 100 users |
| Google | 100 users |
| TikTok | 1,000 users |
| Snapchat | 100 users |

**Impact**: Audiences below minimum may not be usable for targeting.

---

### 3. Identifier Matching Accuracy

**Limitation**: Match rates depend on user-provided data quality.

**Factors**:
- Email domain (personal vs business)
- Phone number format consistency
- User account creation date

---

### 4. Cross-Platform Consistency

**Limitation**: Same segment may have different match rates across platforms.

**Reason**: Each platform has different user base and matching algorithms.

---

### 5. Real-time Sync

**Limitation**: Audience sync is not real-time (minimum 1 hour interval).

**Reason**: Platform API rate limits and processing time.

---

## Error Recovery

### Retry Strategy

| Error Type | Retry | Delay | Max Attempts |
|------------|-------|-------|--------------|
| Rate limit | Yes | Exponential | 4 |
| Timeout | Yes | Fixed 60s | 3 |
| Auth expired | No | - | 0 |
| Validation | No | - | 0 |
| Platform 5xx | Yes | Exponential | 4 |

### Exponential Backoff

```python
RETRY_DELAYS = [60, 300, 900, 3600]  # 1m, 5m, 15m, 1h

for attempt, delay in enumerate(RETRY_DELAYS):
    try:
        return await sync()
    except RetryableError:
        if attempt < len(RETRY_DELAYS) - 1:
            await asyncio.sleep(delay)
        else:
            raise
```

---

## Monitoring

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| Sync failure rate | > 10% |
| Avg match rate | < 50% |
| Sync duration | > 5 minutes |
| Credential expiry | < 7 days |

### Health Checks

```python
async def audience_sync_health():
    checks = {
        "meta": await check_meta_connection(),
        "google": await check_google_connection(),
        "scheduler": await check_scheduler_running(),
        "queue_depth": await get_pending_syncs_count(),
    }
    return {
        "status": "healthy" if all(checks.values()) else "degraded",
        "checks": checks
    }
```

---

## Troubleshooting

### Sync Stuck in "Running"

1. Check if platform API is responding
2. Check for lock key in Redis
3. Force unlock if stuck > 30 minutes
4. Retry sync

### Low Match Rate

1. Check identifier quality
2. Verify email/phone format
3. Compare with platform minimum requirements
4. Test with known valid identifiers

### Credentials Keep Expiring

1. Check OAuth token refresh logic
2. Verify app permissions on platform
3. Check for rate limit impact on refresh

---

## Related Documentation

- [Specification](./spec.md)
- [User Flows](./user-flows.md)
- [API Contracts](./api-contracts.md)
