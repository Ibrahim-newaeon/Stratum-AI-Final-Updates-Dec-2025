# Audience Sync Specification

## Overview

Audience Sync enables pushing CDP segments directly to ad platforms for targeting. This feature bridges customer data with advertising by syncing segments to Meta, Google, TikTok, and Snapchat custom audiences.

---

## Supported Platforms

| Platform | API | Identifier Types | Match Method |
|----------|-----|------------------|--------------|
| **Meta** | Custom Audiences API | Email, Phone, MAID | SHA256 hashed |
| **Google** | Customer Match API | Email, Phone, MAID | SHA256 hashed |
| **TikTok** | DMP Custom Audience API | Email, Phone, MAID | SHA256 hashed |
| **Snapchat** | Audience Match SAM API | Email, Phone, MAID | SHA256 hashed |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   AUDIENCE SYNC ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    CDP SEGMENTS                           │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │  │
│  │  │ High Value   │ │  Newsletter  │ │   At Risk    │     │  │
│  │  │  Customers   │ │  Subscribers │ │   Churning   │     │  │
│  │  │   (1,234)    │ │   (5,678)    │ │    (890)     │     │  │
│  │  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘     │  │
│  └─────────┼────────────────┼────────────────┼─────────────┘  │
│            │                │                │                 │
│            └────────────────┴────────────────┘                 │
│                            │                                   │
│                            ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               AUDIENCE SYNC SERVICE                       │  │
│  │                                                          │  │
│  │  1. Get segment members                                  │  │
│  │  2. Extract identifiers (email, phone, MAID)            │  │
│  │  3. Hash identifiers (SHA256)                            │  │
│  │  4. Format for platform API                              │  │
│  │  5. Upload in batches                                    │  │
│  │  6. Record sync history                                  │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                            │                                   │
│         ┌──────────────────┼──────────────────┐               │
│         ▼                  ▼                  ▼               │
│  ┌───────────┐      ┌───────────┐      ┌───────────┐         │
│  │   Meta    │      │  Google   │      │  TikTok   │         │
│  │ Custom    │      │ Customer  │      │   DMP     │         │
│  │ Audiences │      │  Match    │      │ Audiences │         │
│  └───────────┘      └───────────┘      └───────────┘         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### PlatformAudience

Links a CDP segment to a platform custom audience.

```python
class PlatformAudience:
    id: UUID
    tenant_id: int
    segment_id: UUID                    # Source CDP segment

    # Platform details
    platform: SyncPlatform              # meta, google, tiktok, snapchat
    platform_audience_id: str | None    # Platform's audience ID
    platform_audience_name: str
    ad_account_id: str
    description: str | None

    # Sync configuration
    auto_sync: bool = True
    sync_interval_hours: int = 24       # 1, 6, 12, 24, 168 (1 week)
    next_sync_at: datetime | None

    # Status
    is_active: bool = True
    last_sync_at: datetime | None
    last_sync_status: SyncStatus | None
    last_sync_error: str | None

    # Metrics
    platform_size: int | None           # Size reported by platform
    matched_size: int | None            # Matched users count
    match_rate: float | None            # Match percentage
```

### SyncPlatform Enum

```python
class SyncPlatform(str, Enum):
    META = "meta"
    GOOGLE = "google"
    TIKTOK = "tiktok"
    SNAPCHAT = "snapchat"
```

### AudienceSyncJob

Tracks individual sync operations.

```python
class AudienceSyncJob:
    id: UUID
    tenant_id: int
    platform_audience_id: UUID

    # Operation
    operation: SyncOperation            # create, update, replace, delete
    status: SyncStatus                  # pending, running, completed, failed

    # Metrics
    profiles_sent: int = 0
    profiles_added: int = 0
    profiles_removed: int = 0
    profiles_failed: int = 0
    match_rate: float | None

    # Execution
    started_at: datetime | None
    completed_at: datetime | None
    duration_ms: int | None
    error_message: str | None

    # Audit
    triggered_by: str                   # manual, scheduled, api
    triggered_by_user_id: int | None
```

### SyncOperation Enum

```python
class SyncOperation(str, Enum):
    CREATE = "create"           # Create new audience with users
    UPDATE = "update"           # Add/remove delta users
    REPLACE = "replace"         # Replace all users
    DELETE = "delete"           # Delete audience
```

### SyncStatus Enum

```python
class SyncStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

---

## Platform Connectors

### Base Connector Interface

```python
class BaseAudienceConnector(ABC):
    PLATFORM_NAME: str
    BATCH_SIZE: int = 10000

    @abstractmethod
    async def create_audience(
        config: AudienceConfig,
        users: List[AudienceUser],
    ) -> AudienceSyncResult

    @abstractmethod
    async def add_users(
        audience_id: str,
        users: List[AudienceUser],
    ) -> AudienceSyncResult

    @abstractmethod
    async def remove_users(
        audience_id: str,
        users: List[AudienceUser],
    ) -> AudienceSyncResult

    @abstractmethod
    async def replace_audience(
        audience_id: str,
        users: List[AudienceUser],
    ) -> AudienceSyncResult

    @abstractmethod
    async def delete_audience(
        audience_id: str,
    ) -> AudienceSyncResult

    @abstractmethod
    async def get_audience_info(
        audience_id: str,
    ) -> Dict[str, Any]
```

### Platform-Specific Details

#### Meta (Facebook/Instagram)

```python
class MetaAudienceConnector(BaseAudienceConnector):
    PLATFORM_NAME = "meta"
    BATCH_SIZE = 10000

    # API endpoints
    BASE_URL = "https://graph.facebook.com/v18.0"

    # Supported identifier schema
    SCHEMA = ["EMAIL", "PHONE", "MADID", "FN", "LN", "CT", "ST", "ZIP", "COUNTRY"]
```

**Hashing Requirements**:
- Email: lowercase, SHA256
- Phone: E.164 format without +, SHA256
- First/Last Name: lowercase, UTF-8, SHA256

#### Google Customer Match

```python
class GoogleAudienceConnector(BaseAudienceConnector):
    PLATFORM_NAME = "google"
    BATCH_SIZE = 100000  # Google allows larger batches

    # Uses Google Ads API v15
    # Customer Match requires enhanced_matching scope
```

**Hashing Requirements**:
- Email: lowercase, remove spaces, SHA256
- Phone: E.164 format, SHA256
- MAID: uppercase, no hashing required

#### TikTok

```python
class TikTokAudienceConnector(BaseAudienceConnector):
    PLATFORM_NAME = "tiktok"
    BATCH_SIZE = 10000

    # Uses TikTok DMP API
    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"
```

#### Snapchat

```python
class SnapchatAudienceConnector(BaseAudienceConnector):
    PLATFORM_NAME = "snapchat"
    BATCH_SIZE = 50000

    # Uses Snapchat Marketing API SAM
    BASE_URL = "https://adsapi.snapchat.com/v1"
```

---

## Identifier Handling

### Identifier Types

| Type | Format | Example |
|------|--------|---------|
| `email` | Lowercase, normalized | john@example.com |
| `phone` | E.164 format | +14155551234 |
| `mobile_id` | IDFA/GAID | AEBE52E7-03EE-... |
| `external_id` | Custom ID | CUST-12345 |

### Hashing Process

```python
def hash_identifier(value: str, identifier_type: IdentifierType) -> str:
    # 1. Normalize
    if identifier_type == IdentifierType.EMAIL:
        normalized = value.strip().lower()
    elif identifier_type == IdentifierType.PHONE:
        # Remove non-digits except +
        normalized = ''.join(c for c in value if c.isdigit() or c == '+')
        # Remove + for most platforms
        if platform != "tiktok":
            normalized = normalized.lstrip('+')
    else:
        normalized = value.strip()

    # 2. Hash with SHA256
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()
```

### User Data Structure

```python
@dataclass
class AudienceUser:
    profile_id: str
    identifiers: List[UserIdentifier]

    # Optional enhanced matching
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    date_of_birth: Optional[str] = None  # YYYYMMDD
    gender: Optional[str] = None  # m/f
```

---

## Sync Process

### Create Audience

```
1. Validate segment exists and is active
2. Validate platform credentials
3. Get segment members with identifiers
4. Hash identifiers per platform requirements
5. Create audience on platform
6. Upload users in batches
7. Record sync job with results
8. Schedule next sync (if auto_sync enabled)
```

### Update Audience (Incremental)

```
1. Get current segment members
2. Compare with last sync snapshot
3. Calculate delta (added/removed)
4. Hash new identifiers
5. Add new users to platform
6. Remove departed users from platform
7. Record sync job with metrics
```

### Replace Audience (Full)

```
1. Get current segment members
2. Hash all identifiers
3. Replace entire audience on platform
4. Record sync job with metrics
```

---

## Sync Scheduling

### Interval Options

| Interval | Use Case |
|----------|----------|
| 1 hour | High-velocity segments |
| 6 hours | Daily campaigns |
| 12 hours | Standard campaigns |
| 24 hours | Stable segments (default) |
| 168 hours (1 week) | Low-churn segments |

### Scheduler Flow

```python
# Celery beat task runs every 15 minutes
@celery.task
async def process_audience_sync_queue():
    # Find audiences due for sync
    due_audiences = await db.execute(
        select(PlatformAudience)
        .where(
            PlatformAudience.auto_sync == True,
            PlatformAudience.is_active == True,
            PlatformAudience.next_sync_at <= datetime.utcnow(),
        )
    )

    for audience in due_audiences:
        await sync_platform_audience(audience.id)
        audience.next_sync_at = datetime.utcnow() + timedelta(
            hours=audience.sync_interval_hours
        )
```

---

## Manual Export

In addition to platform sync, audiences can be exported directly.

### Export Formats

| Format | Description |
|--------|-------------|
| CSV | Comma-separated values |
| JSON | JSON array of profiles |

### Export Options

```python
class ExportOptions:
    format: str = "csv"           # csv, json
    include_traits: bool = True   # Include computed traits
    include_events: bool = False  # Include recent events
    identifier_types: List[str] = ["email", "phone"]
    hash_identifiers: bool = True
```

### Export Response

```json
{
  "download_url": "https://cdn.stratum.ai/exports/segment-123.csv",
  "expires_at": "2024-01-16T14:30:00Z",
  "profile_count": 1234,
  "file_size_bytes": 245000
}
```

---

## Metrics & Tracking

### Per-Sync Metrics

| Metric | Description |
|--------|-------------|
| `profiles_sent` | Profiles included in upload |
| `profiles_added` | Successfully added to audience |
| `profiles_removed` | Successfully removed from audience |
| `profiles_failed` | Failed to process |
| `match_rate` | % matched by platform |
| `duration_ms` | Sync duration |

### Audience Health Metrics

| Metric | Description |
|--------|-------------|
| `platform_size` | Current audience size on platform |
| `matched_size` | Users matched by platform |
| `match_rate` | Overall match percentage |
| `sync_success_rate` | % of successful syncs (30d) |

---

## Error Handling

### Retry Strategy

```python
RETRY_DELAYS = [60, 300, 900, 3600]  # 1m, 5m, 15m, 1h

async def sync_with_retry(job: AudienceSyncJob):
    for attempt, delay in enumerate(RETRY_DELAYS):
        try:
            return await execute_sync(job)
        except RetryableError as e:
            if attempt < len(RETRY_DELAYS) - 1:
                await asyncio.sleep(delay)
            else:
                raise
        except NonRetryableError:
            raise
```

### Error Categories

| Category | Retry | Examples |
|----------|-------|----------|
| Rate limit | Yes | 429 responses |
| Timeout | Yes | Network timeout |
| Auth expired | No | Invalid/expired token |
| Validation | No | Invalid audience name |
| Platform error | Maybe | 500 responses |

---

## Configuration

### Environment Variables

```bash
# Platform credentials (per tenant in DB)
# OAuth tokens stored securely

# Rate limiting
AUDIENCE_SYNC_MAX_BATCH_SIZE=10000
AUDIENCE_SYNC_MAX_CONCURRENT_SYNCS=5

# Scheduling
AUDIENCE_SYNC_MIN_INTERVAL_HOURS=1
AUDIENCE_SYNC_DEFAULT_INTERVAL_HOURS=24
```

### Feature Flags

| Flag | Description |
|------|-------------|
| `audience_sync` | Enable audience sync feature |
| `audience_sync_meta` | Enable Meta connector |
| `audience_sync_google` | Enable Google connector |
| `audience_sync_tiktok` | Enable TikTok connector |
| `audience_sync_snapchat` | Enable Snapchat connector |
| `audience_export` | Enable manual export |

---

## Related Documentation

- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
- [CDP Feature](../02-cdp/spec.md) - CDP segment management
