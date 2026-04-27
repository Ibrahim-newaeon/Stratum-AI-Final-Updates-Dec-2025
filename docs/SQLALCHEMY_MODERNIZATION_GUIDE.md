# SQLAlchemy 2.0 Modernization Guide

Total `Column(...)` declarations to migrate: **1613**

## Migration Pattern

### Before (SQLAlchemy 1.x)
```python
tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
```

### After (SQLAlchemy 2.0)
```python
tenant_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)
```

## Key Changes
1. Add `Mapped[T]` type annotation
2. Replace `Column(...)` with `mapped_column(...)`
3. Import `Mapped` and `mapped_column` from `sqlalchemy.orm`
4. Keep all existing arguments (nullable, default, index, etc.)

## Files Affected

### /mnt/agents/output/stratum-fixes/backend/app/models/attribution.py
Count: 112

- Line 44: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
- Line 45: `tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullab`
- Line 46: `date = Column(Date, nullable=False)`
- Line 49: `attribution_model = Column(StrEnumType(AttributionModel), nullable=False)`
- Line 52: `dimension_type = Column(String(50), nullable=False)  # platform, campaign, adset`
- ... and 107 more

### /mnt/agents/output/stratum-fixes/backend/app/models/audience_sync.py
Count: 52

- Line 90: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
- Line 91: `tenant_id = Column(`
- Line 99: `segment_id = Column(`
- Line 107: `platform = Column(String(50), nullable=False)  # meta, google, tiktok, snapchat`
- Line 108: `platform_audience_id = Column(String(255), nullable=True)  # ID on the platform`
- ... and 47 more

### /mnt/agents/output/stratum-fixes/backend/app/models/audit_services.py
Count: 294

- Line 90: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
- Line 91: `tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullab`
- Line 94: `platform = Column(String(50), nullable=False)  # meta, google, tiktok, etc.`
- Line 95: `pixel_id = Column(String(255), nullable=False)`
- Line 96: `measurement_date = Column(Date, nullable=False)`
- ... and 289 more

### /mnt/agents/output/stratum-fixes/backend/app/models/autopilot.py
Count: 40

- Line 80: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
- Line 81: `tenant_id = Column(`
- Line 90: `enforcement_enabled = Column(Boolean, nullable=False, default=True)`
- Line 93: `default_mode = Column(`
- Line 100: `max_daily_budget = Column(Float, nullable=True)`
- ... and 35 more

### /mnt/agents/output/stratum-fixes/backend/app/models/campaign_builder.py
Count: 69

- Line 75: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
- Line 76: `tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullab`
- Line 77: `platform = Column(String(50), nullable=False)`
- Line 78: `status = Column(String(50), nullable=False, default=ConnectionStatus.DISCONNECTE`
- Line 81: `token_ref = Column(Text, nullable=True)  # Reference to encrypted token in secre`
- ... and 64 more

### /mnt/agents/output/stratum-fixes/backend/app/models/capi_delivery.py
Count: 65

- Line 42: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
- Line 43: `tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullab`
- Line 46: `platform = Column(String(50), nullable=False)  # meta, google, tiktok, etc.`
- Line 47: `event_id = Column(String(255), nullable=True)  # External event ID for deduplica`
- Line 48: `event_name = Column(String(100), nullable=False)  # Purchase, Lead, etc.`
- ... and 60 more

### /mnt/agents/output/stratum-fixes/backend/app/models/cdp.py
Count: 179

- Line 98: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
- Line 99: `tenant_id = Column(`
- Line 107: `name = Column(String(255), nullable=False)`
- Line 108: `source_type = Column(String(50), nullable=False)  # Using string for flexibility`
- Line 109: `source_key = Column(String(64), nullable=False)  # API key for this source`
- ... and 174 more

### /mnt/agents/output/stratum-fixes/backend/app/models/cms.py
Count: 132

- Line 108: `Column(`
- Line 114: `Column(`
- Line 136: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
- Line 139: `name = Column(String(100), nullable=False, unique=True)`
- Line 140: `slug = Column(String(100), nullable=False, unique=True)`
- ... and 127 more

### /mnt/agents/output/stratum-fixes/backend/app/models/crm.py
Count: 212

- Line 84: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
- Line 85: `tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullab`
- Line 88: `provider = Column(StrEnumType(CRMProvider), nullable=False)`
- Line 89: `provider_account_id = Column(String(255), nullable=True)  # HubSpot portal ID, e`
- Line 90: `provider_account_name = Column(String(255), nullable=True)`
- ... and 207 more

### /mnt/agents/output/stratum-fixes/backend/app/models/embed_widgets.py
Count: 53

- Line 98: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
- Line 99: `tenant_id = Column(`
- Line 107: `name = Column(String(255), nullable=False)`
- Line 108: `description = Column(Text, nullable=True)`
- Line 111: `widget_type = Column(String(50), nullable=False)`
- ... and 48 more

### /mnt/agents/output/stratum-fixes/backend/app/models/pacing.py
Count: 134

- Line 92: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
- Line 93: `tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullab`
- Line 96: `name = Column(String(255), nullable=False)`
- Line 97: `description = Column(Text, nullable=True)`
- Line 100: `period_type = Column(StrEnumType(TargetPeriod), nullable=False, default=TargetPe`
- ... and 129 more

### /mnt/agents/output/stratum-fixes/backend/app/models/profit.py
Count: 128

- Line 69: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
- Line 70: `tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullab`
- Line 73: `sku = Column(String(100), nullable=False)`
- Line 74: `name = Column(String(500), nullable=False)`
- Line 75: `description = Column(Text, nullable=True)`
- ... and 123 more

### /mnt/agents/output/stratum-fixes/backend/app/models/reporting.py
Count: 91

- Line 102: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
- Line 103: `tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullab`
- Line 106: `name = Column(String(255), nullable=False)`
- Line 107: `description = Column(Text, nullable=True)`
- Line 108: `report_type = Column(StrEnumType(ReportType), nullable=False)`
- ... and 86 more

### /mnt/agents/output/stratum-fixes/backend/app/models/trust_layer.py
Count: 52

- Line 56: `id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)`
- Line 57: `tenant_id = Column(Integer, ForeignKey("tenants.id", ondelete="CASCADE"), nullab`
- Line 58: `date = Column(Date, nullable=False)`
- Line 59: `platform = Column(String(50), nullable=False)  # meta, google, tiktok, snapchat`
- Line 60: `account_id = Column(String(255), nullable=True)  # Optional, for account-level t`
- ... and 47 more
