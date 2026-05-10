# CDP Edge Cases

## Overview

This document covers error handling, edge cases, and known limitations for the Customer Data Platform.

---

## Edge Cases

### 1. Multiple Matching Profiles

**Scenario**: Event contains identifiers that match multiple existing profiles.

**Example**:
- Profile A has email `john@example.com`
- Profile B has phone `+1-555-1234`
- Event arrives with both identifiers

**Behavior**:
- System detects both profiles match
- Initiates automatic merge
- Older profile survives (unless newer has stronger canonical identity)
- All identifiers, events, and consents transferred
- Merge recorded in audit trail

**Handling**:
```python
if len(matching_profiles) > 1:
    surviving = select_surviving_profile(matching_profiles)
    for profile in matching_profiles:
        if profile.id != surviving.id:
            merge_profiles(surviving, profile, reason="identity_match")
```

---

### 2. Duplicate Event (Idempotency)

**Scenario**: Same event sent twice with same `idempotency_key`.

**Behavior**:
- Second event marked as `duplicate`
- No changes to profile
- Original event_id returned

**Response**:
```json
{
  "accepted": 0,
  "rejected": 0,
  "duplicates": 1,
  "results": [{
    "event_id": "original-uuid",
    "status": "duplicate",
    "profile_id": "uuid-..."
  }]
}
```

**Best Practice**: Always include `idempotency_key` for critical events like purchases.

---

### 3. Anonymous to Known Transition

**Scenario**: Anonymous user provides email for the first time.

**Behavior**:
1. Search for existing profile with that email
2. If found: Link anonymous_id to existing profile
3. If not found: Update current profile
4. Lifecycle stage: `anonymous` → `known`

**Handling**:
```python
if new_identifier.type in ["email", "phone", "external_id"]:
    existing = find_profile_by_identifier(new_identifier)
    if existing and existing.id != current_profile.id:
        merge_profiles(existing, current_profile)
    else:
        current_profile.lifecycle_stage = "known"
```

---

### 4. Cross-Device Identification

**Scenario**: User logs in on new device, linking device_id to email.

**Flow**:
1. New device sends anonymous events
2. User logs in (email identifier attached)
3. System links anonymous device to known profile
4. Historical events from device reassigned

**Identity Link Created**:
```json
{
  "source_id": "device-uuid",
  "target_id": "email-uuid",
  "link_type": "login",
  "confidence_score": 1.0
}
```

---

### 5. Profile with No Identifiers

**Scenario**: Profile exists but all identifiers have been deleted (GDPR request).

**Behavior**:
- Profile still exists with events
- Cannot be matched to new events
- Appears as "orphaned" in analytics
- New events create new profiles

**Handling**: Profile deletion should be full deletion, not just identifier removal.

---

### 6. Conflicting Consent

**Scenario**: User grants consent on web, revokes on mobile app.

**Behavior**:
- Latest consent wins
- Each consent update is timestamped
- Full audit trail maintained
- Consent type granularity preserved

**Resolution**:
```python
# Order by updated_at, take most recent
current_consent = (
    profile.consents
    .filter(consent_type=type)
    .order_by(updated_at.desc())
    .first()
)
```

---

### 7. Event Arrives Before Profile

**Scenario**: Event references external_id that doesn't exist yet.

**Behavior**:
- New profile created automatically
- Profile linked to event
- Lifecycle: `anonymous` (no email/phone yet)

**Profile Creation**:
```python
if not existing_profile:
    profile = CDPProfile(
        external_id=event.identifiers.get("external_id"),
        lifecycle_stage="anonymous",
        first_seen_at=event.event_time
    )
```

---

### 8. Invalid Event Data

**Scenario**: Event missing required fields or with invalid data types.

**Validation Rules**:
| Field | Requirement |
|-------|-------------|
| `event_name` | Required, string, max 255 chars |
| `event_time` | Required, valid ISO 8601 datetime |
| `identifiers` | At least one identifier required |
| `properties` | Optional, valid JSON object |

**Response**:
```json
{
  "accepted": 0,
  "rejected": 1,
  "results": [{
    "status": "rejected",
    "error": "event_name is required"
  }]
}
```

---

### 9. Rate Limit Exceeded

**Scenario**: Tenant sends more than 100 event requests per minute.

**Behavior**:
- Returns 429 Too Many Requests
- Retry-After header set to 60 seconds
- Events should be queued client-side

**Response**:
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 60

{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded for event ingestion. Max 100 requests/minute."
  }
}
```

---

### 10. Large Batch Processing

**Scenario**: Batch with 1000+ events submitted.

**Behavior**:
- Events processed in chunks
- Partial success possible
- Results include status for each event

**Best Practices**:
- Batch size: max 100 events per request
- Use separate requests for very large imports
- Monitor for rate limits

---

### 11. Segment Computation Timeout

**Scenario**: Complex segment takes too long to compute.

**Behavior**:
- Default timeout: 5 minutes
- Status: `computing` → `stale`
- Manual retry available
- Simplify rules if recurring

**Mitigation**:
- Index commonly used fields
- Limit condition complexity
- Use computed traits for expensive calculations

---

### 12. Profile Merge Conflict

**Scenario**: Merge attempted while both profiles are being updated.

**Behavior**:
- Pessimistic locking on profiles
- Transaction rollback on conflict
- Retry with exponential backoff
- Merge recorded atomically

**Handling**:
```python
async with db.begin():
    # Lock both profiles
    surviving = await db.get(CDPProfile, surviving_id, with_for_update=True)
    merged = await db.get(CDPProfile, merged_id, with_for_update=True)

    # Perform merge
    transfer_identifiers(merged, surviving)
    transfer_events(merged, surviving)
    await db.delete(merged)
```

---

### 13. Circular Identity Links

**Scenario**: Identity graph creates circular references.

**Prevention**:
- Unique constraint on (source_id, target_id)
- Direction normalized (lower UUID first)
- Validation on link creation

**Detection**:
```sql
-- Detect cycles
WITH RECURSIVE identity_path AS (
    SELECT source_identifier_id, target_identifier_id, 1 as depth
    FROM cdp_identity_links
    WHERE tenant_id = ?
    UNION ALL
    SELECT p.source_identifier_id, l.target_identifier_id, p.depth + 1
    FROM identity_path p
    JOIN cdp_identity_links l ON p.target_identifier_id = l.source_identifier_id
    WHERE p.depth < 10
)
SELECT * FROM identity_path WHERE source_identifier_id = target_identifier_id;
```

---

### 14. Timezone Handling

**Scenario**: Events arrive with various timezone formats.

**Behavior**:
- All times stored as UTC
- `event_time` parsed with timezone if provided
- `received_at` always UTC server time
- Display in user's timezone (frontend)

**Parsing**:
```python
# Accept: ISO 8601 with timezone, Unix timestamp
if isinstance(event_time, int):
    event_time = datetime.fromtimestamp(event_time, tz=timezone.utc)
elif isinstance(event_time, str):
    event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
```

---

### 15. PII Handling

**Scenario**: Ensuring GDPR/CCPA compliance for personal data.

**Safeguards**:
1. Identifiers hashed (SHA256) for storage
2. Original values can be encrypted or redacted
3. Profile deletion removes all PII
4. Consent checked before data use
5. Audit logs for all operations

**Hash Function**:
```python
def hash_identifier(value: str) -> str:
    normalized = value.lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()
```

---

## Known Limitations

### 1. Event Immutability

**Limitation**: Events cannot be updated after creation.

**Reason**: Append-only event store for audit integrity.

**Workaround**: Create correction events with adjustments.

---

### 2. Real-time Segment Membership

**Limitation**: Dynamic segments are computed periodically, not real-time.

**Default Interval**: 24 hours (configurable to 1 hour minimum).

**Workaround**: Trigger manual recomputation for critical segments.

---

### 3. Identifier Matching Precision

**Limitation**: Fuzzy matching not supported (exact match only).

**Reason**: Privacy-first design with hashed identifiers.

**Workaround**: Normalize identifiers before sending:
- Emails: lowercase, trim whitespace
- Phones: E.164 format (+1234567890)

---

### 4. Profile History

**Limitation**: Profile data history not maintained (only current state).

**Workaround**: Events provide full behavioral history.

---

### 5. Cross-Tenant Identity

**Limitation**: Identity resolution is tenant-isolated.

**Reason**: Multi-tenant data isolation requirements.

---

## Error Recovery

### Event Ingestion Failures

| Failure | Recovery |
|---------|----------|
| Network timeout | Retry with exponential backoff |
| 429 Rate limit | Queue and retry after Retry-After |
| 400 Validation | Fix data, retry |
| 500 Server error | Retry with backoff, alert if persistent |

### Profile Merge Failures

| Failure | Recovery |
|---------|----------|
| Lock timeout | Automatic retry |
| Constraint violation | Manual investigation |
| Data corruption | Restore from merge snapshot |

---

## Monitoring

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| Event ingestion rate | Baseline ± 3 std dev |
| Profile creation rate | Baseline ± 3 std dev |
| Merge rate | > 100/hour |
| Segment computation time | > 5 minutes |
| API error rate | > 1% |

### Health Checks

```bash
# CDP health endpoint
GET /api/v1/cdp/health

# Expected response
{"status": "healthy", "module": "CDP", "version": "1.0.0"}
```

---

## Related Documentation

- [Specification](./spec.md)
- [User Flows](./user-flows.md)
- [API Contracts](./api-contracts.md)
