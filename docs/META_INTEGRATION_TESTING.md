# Meta Marketing API Integration Testing Guide

This guide covers testing the Meta (Facebook) integration for pulling campaign data into the Stratum AI platform for ML training.

## Prerequisites

### 1. Meta Business Account Setup

1. **Create/Access Meta Business Manager**
   - Go to [business.facebook.com](https://business.facebook.com)
   - Create a business account if you don't have one

2. **Ad Account Access**
   - Ensure you have at least one Ad Account linked to your business
   - Note your Ad Account ID (format: `act_XXXXXXXXXXXXXXX`)

3. **Create a System User** (Recommended for API access)
   - Go to Business Settings > Users > System Users
   - Click "Add" to create a new system user
   - Assign the system user to your ad accounts with at least "Standard" access

### 2. Generate Access Token

**Option A: System User Token (Recommended for Production)**

1. Go to Business Settings > Users > System Users
2. Select your system user
3. Click "Generate New Token"
4. Select these permissions:
   - `ads_read` - Required for reading campaign data
   - `ads_management` - For future write operations
   - `business_management` - For business-level access
5. Copy the generated token (starts with `EAABsbCS...`)

**Option B: User Access Token (For Development/Testing)**

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Create or select an app
3. Go to Tools > Graph API Explorer
4. Select your app and generate a User Token
5. Add permissions: `ads_read`, `ads_management`
6. Click "Generate Access Token"

### 3. Required Credentials

| Field | Description | Example |
|-------|-------------|---------|
| `access_token` | System User or User Access Token | `EAABsbCS1234...` |
| `pixel_id` | (Optional) Meta Pixel ID for CAPI events | `123456789012345` |

## Testing Steps

### Step 1: Run Database Migration

```bash
cd backend
alembic upgrade head
```

This creates the `platform_connections` table for storing encrypted credentials.

### Step 2: Start Backend Server

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step 3: Start Frontend Dev Server

```bash
cd frontend
npm run dev
```

### Step 4: Connect Meta Platform

1. Navigate to **CAPI Setup** page in the frontend
2. Click on **Meta (Facebook)** platform card
3. Enter your credentials:
   - **Pixel ID**: Your Meta Pixel ID (optional for sync, required for CAPI events)
   - **Access Token**: Your System User or User token
4. Click **Connect Platform**

**Expected Result:**
- Green "Connected" badge appears
- Account name displays (if available)
- Success message: "Successfully connected to Meta (Facebook)!"

### Step 5: Sync Campaign Data

1. After connecting, a new "Campaign Data Sync" section appears
2. Click **Sync All Platforms** or **Sync Now** next to Meta
3. Wait for sync to complete (may take 1-2 minutes depending on data volume)

**Expected Result:**
- Sync complete message with metrics:
  - Number of campaigns synced
  - Number of daily metrics (impressions, clicks, spend, etc.)
  - Platform sync status

### Step 6: Verify Data in Database

Connect to PostgreSQL and run:

```sql
-- Check campaigns synced
SELECT id, name, status, objective, daily_budget_cents, external_id
FROM campaigns
WHERE platform = 'meta'
ORDER BY created_at DESC
LIMIT 10;

-- Check campaign metrics
SELECT c.name, m.date, m.impressions, m.clicks, m.spend_cents, m.conversions
FROM campaign_metrics m
JOIN campaigns c ON m.campaign_id = c.id
WHERE c.platform = 'meta'
ORDER BY m.date DESC
LIMIT 20;

-- Check platform connection status
SELECT platform, status, account_name, connected_at, last_sync_at, error_message
FROM platform_connections;
```

## API Endpoints Reference

### Connect Platform
```http
POST /api/v1/capi/platforms/connect
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "platform": "meta",
  "credentials": {
    "access_token": "EAABsbCS...",
    "pixel_id": "123456789012345"
  }
}
```

### Check Connection Status
```http
GET /api/v1/capi/platforms/status
Authorization: Bearer <jwt_token>
```

### Sync Campaign Data
```http
POST /api/v1/capi/platforms/sync?platform=meta&days_back=90
Authorization: Bearer <jwt_token>
```

### Get Synced Campaigns
```http
GET /api/v1/capi/platforms/meta/campaigns
Authorization: Bearer <jwt_token>
```

### Disconnect Platform
```http
DELETE /api/v1/capi/platforms/meta/disconnect
Authorization: Bearer <jwt_token>
```

## Troubleshooting

### Error: "Invalid OAuth access token"
- Token may have expired (User tokens expire after ~60 days)
- Solution: Generate a new token from Business Manager

### Error: "User does not have sufficient permissions"
- System user lacks required permissions on ad account
- Solution: Assign the system user to the ad account with "Standard" or higher access

### Error: "No ad accounts found"
- Token doesn't have access to any ad accounts
- Solution: Verify the system user is assigned to at least one ad account

### Error: "Rate limit exceeded"
- Too many API calls in a short period
- Solution: Wait and retry; the system has built-in rate limiting

### Sync returns 0 campaigns
- Ad account may not have any active/recent campaigns
- Check the date range (defaults to 90 days)
- Verify the ad account has campaigns in the specified period

## Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│   Backend API   │────▶│   Meta Graph    │
│   CAPISetup.tsx │     │   capi.py       │     │   API v18.0     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   PostgreSQL    │
                        │   - campaigns   │
                        │   - metrics     │
                        │   - connections │
                        └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   ML Pipeline   │
                        │   Training      │
                        └─────────────────┘
```

## Next Steps After Testing

1. **Train ML Models**: Once you have synced campaign data, use the ML training pipeline
   ```bash
   cd backend
   python -m app.ml.training.trainer --tenant-id 1 --model-type budget_optimizer
   ```

2. **Set Up Automated Sync**: Configure sync intervals in platform connection settings

3. **Add More Platforms**: Connect Google Ads, TikTok, etc. for cross-platform optimization

## Security Notes

- Access tokens are encrypted at rest using Fernet symmetric encryption
- Each tenant has a unique encryption key derived from the app secret + tenant ID
- Tokens are never logged or exposed in API responses
- Use System User tokens in production (they don't expire like User tokens)
