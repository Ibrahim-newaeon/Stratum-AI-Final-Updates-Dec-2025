# Mobile Structure - Memory Node

> **Created:** 2026-01-24
> **Purpose:** Reference document for native mobile app development (iOS/Android)

---

## Current Architecture Assessment

| Aspect | Status | Mobile Readiness |
|--------|--------|------------------|
| **Backend API** | FastAPI REST | Ready - all endpoints consumable |
| **Authentication** | JWT + Refresh tokens | Ready - standard mobile pattern |
| **Data Format** | JSON with Pydantic schemas | Ready - easy to map to native models |
| **Real-time** | WebSocket support | Ready - native WS libraries available |
| **Multi-tenancy** | Header-based (`X-Tenant-ID`) | Ready - simple header injection |

---

## API Endpoints for Mobile Consumption

### Authentication
```
POST   /auth/login              # User login (email, password)
POST   /auth/refresh            # Refresh access token
POST   /auth/logout             # Logout (token revocation)
GET    /auth/me                 # Get current user profile
POST   /auth/mfa/setup          # Enable 2FA
POST   /auth/mfa/verify         # Verify 2FA code
POST   /auth/whatsapp/send-otp  # WhatsApp OTP auth
POST   /auth/whatsapp/verify-otp # Verify WhatsApp OTP
```

### Dashboard
```
GET    /dashboard/overview      # KPI dashboard
GET    /dashboard/kpis          # Key metrics
GET    /dashboard/alerts        # Active alerts
```

### Campaigns
```
GET    /campaigns               # List campaigns (paginated)
GET    /campaigns/{id}          # Campaign details
POST   /campaigns               # Create campaign
PATCH  /campaigns/{id}          # Update campaign
DELETE /campaigns/{id}          # Delete/archive
```

### CDP (Customer Data Platform)
```
GET    /cdp/profiles            # List profiles (search, filter)
GET    /cdp/profiles/{id}       # Profile details
POST   /cdp/events              # Ingest events (batch)
GET    /cdp/segments            # List segments
POST   /cdp/segments            # Create segment
GET    /cdp/audience-sync/audiences      # List synced audiences
POST   /cdp/audience-sync/audiences      # Push to ad platforms
POST   /cdp/audience-sync/audiences/{id}/sync # Trigger sync
```

### Real-time (WebSocket)
```
ws://api.stratum.ai/ws/tenant/{tenant_id}

Message Types:
- EMQ_UPDATE
- EMQ_DRIVER_UPDATE
- INCIDENT_OPENED
- INCIDENT_CLOSED
- AUTOPILOT_MODE_CHANGE
- ACTION_RECOMMENDATION
- ACTION_STATUS_UPDATE
- PLATFORM_STATUS
- HEARTBEAT
```

---

## Screen Mapping (Web to Mobile)

| Web Route | Mobile Screen | Priority |
|-----------|---------------|----------|
| `/dashboard/overview` | Home/Dashboard | P0 |
| `/dashboard/campaigns` | Campaign List | P0 |
| `/dashboard/campaigns/{id}` | Campaign Detail | P0 |
| `/dashboard/cdp` | CDP Dashboard | P1 |
| `/dashboard/cdp/profiles` | Profile Search | P1 |
| `/dashboard/cdp/segments` | Segment List | P1 |
| `/dashboard/cdp/audience-sync` | Sync Status | P2 |
| `/dashboard/cdp/events` | Event Timeline | P2 |
| `/dashboard/settings` | Settings | P1 |
| `/dashboard/rules` | Automation Rules | P2 |
| `/dashboard/autopilot` | Autopilot Config | P2 |

---

## Authentication Flow

### Token Management
- **Access Token:** 30 minutes expiry
- **Refresh Token:** 7 days expiry
- **Algorithm:** HS256 (HMAC SHA-256)

### Request Headers
```
Authorization: Bearer <access_token>
X-Tenant-ID: <number>
Content-Type: application/json
```

### Token Refresh Logic
```
1. Store tokens in secure storage (Keychain iOS / Keystore Android)
2. On 401 response -> attempt token refresh
3. If refresh fails -> redirect to login
4. Implement token expiry check before requests
```

### 2FA/MFA Support
- TOTP (Time-based One-Time Password)
- Compatible with Google Authenticator, Authy
- 10 backup codes for recovery
- 5-minute MFA session window

---

## Data Models (Native Mapping)

### User
```swift
// iOS Swift
struct User: Codable {
    let id: Int
    let email: String
    let fullName: String
    let role: UserRole
    let isActive: Bool
    let isVerified: Bool
    let tenantId: Int
    let createdAt: Date
    let updatedAt: Date
}

enum UserRole: String, Codable {
    case superadmin, admin, manager, analyst, viewer
}
```

```kotlin
// Android Kotlin
data class User(
    val id: Int,
    val email: String,
    val fullName: String,
    val role: UserRole,
    val isActive: Boolean,
    val isVerified: Boolean,
    val tenantId: Int,
    val createdAt: Instant,
    val updatedAt: Instant
)

enum class UserRole { SUPERADMIN, ADMIN, MANAGER, ANALYST, VIEWER }
```

### API Response Wrapper
```swift
// iOS Swift
struct APIResponse<T: Codable>: Codable {
    let success: Bool
    let data: T?
    let message: String?
    let errors: [APIError]?
}

struct PaginatedResponse<T: Codable>: Codable {
    let items: [T]
    let total: Int
    let page: Int
    let pageSize: Int
    let totalPages: Int
}
```

```kotlin
// Android Kotlin
data class APIResponse<T>(
    val success: Boolean,
    val data: T?,
    val message: String?,
    val errors: List<APIError>?
)

data class PaginatedResponse<T>(
    val items: List<T>,
    val total: Int,
    val page: Int,
    val pageSize: Int,
    val totalPages: Int
)
```

---

## Network Layer Requirements

### iOS (Swift)
- **HTTP Client:** Alamofire or URLSession
- **Token Interceptor:** RequestInterceptor protocol
- **WebSocket:** URLSessionWebSocketTask or Starscream
- **JSON Parsing:** Codable with custom date strategies

### Android (Kotlin)
- **HTTP Client:** Retrofit + OkHttp
- **Token Interceptor:** OkHttp Interceptor
- **WebSocket:** OkHttp WebSocket or Scarlet
- **JSON Parsing:** Moshi or Kotlinx.serialization

### Common Patterns
```
1. Request interceptor adds Authorization header
2. Request interceptor adds X-Tenant-ID header
3. Response interceptor handles 401 -> refresh token
4. Response interceptor handles errors -> map to domain errors
5. Retry logic with exponential backoff
6. Request/response logging for debugging
```

---

## Gaps to Address for Mobile

| Gap | Effort | Implementation Notes |
|-----|--------|---------------------|
| Push notification endpoints | Medium | Add `/devices/register` for APNS/FCM tokens |
| Mobile-optimized responses | Low | Add `?fields=` query param for sparse responses |
| Offline sync strategy | High | Implement queue for mutations when offline |
| Deep linking scheme | Low | Configure `stratum://` URL scheme |
| Biometric auth | Low | Client-side only, unlock stored tokens |
| App-specific rate limits | Low | Higher limits for mobile clients |

---

## Recommended Tech Stack

### iOS
```
- Language: Swift 5.9+
- UI: SwiftUI
- Architecture: MVVM + Coordinator
- Networking: Alamofire
- State: Combine / async-await
- Storage: Keychain (tokens), CoreData/SwiftData (cache)
- Push: APNS
```

### Android
```
- Language: Kotlin 1.9+
- UI: Jetpack Compose
- Architecture: MVVM + Navigation Component
- Networking: Retrofit + OkHttp
- State: Kotlin Flow / Coroutines
- Storage: EncryptedSharedPreferences (tokens), Room (cache)
- Push: FCM
```

### Cross-Platform Alternative
```
- Framework: React Native or Flutter
- Advantage: Share logic with existing React codebase
- Consideration: Reuse API hooks from frontend/src/api/
```

---

## Security Considerations

1. **Token Storage:** Use platform secure storage (Keychain/Keystore)
2. **Certificate Pinning:** Pin API server certificates
3. **Biometric Gate:** Require biometric for sensitive actions
4. **Jailbreak/Root Detection:** Warn or block on compromised devices
5. **Code Obfuscation:** Enable for release builds
6. **Network Security Config:** Block cleartext traffic (Android)
7. **App Transport Security:** Enforce HTTPS (iOS)

---

## Project Structure Reference

```
Backend API Base: /api/v1
Frontend API Modules: frontend/src/api/ (28 modules, 13,631 lines)
Backend Endpoints: backend/app/api/v1/endpoints/ (48+ modules)
Pydantic Schemas: backend/app/models/
SQLAlchemy Models: backend/app/base_models.py
WebSocket: backend/app/api/v1/endpoints/ws.py (assumed)
```

---

## Next Steps for Mobile Development

1. **Phase 1 - Foundation**
   - Set up native project (iOS/Android or cross-platform)
   - Implement network layer with token management
   - Build authentication flow (login, refresh, logout)
   - Create secure storage for tokens

2. **Phase 2 - Core Features**
   - Dashboard screen with KPIs
   - Campaign list with pagination
   - Campaign detail view
   - Basic settings

3. **Phase 3 - CDP Features**
   - Profile search and detail
   - Segment list
   - Audience sync status

4. **Phase 4 - Advanced**
   - Push notifications integration
   - Offline support
   - Deep linking
   - Biometric authentication

---

*This memory node serves as the reference architecture for building native mobile applications that consume the Stratum AI platform API.*
