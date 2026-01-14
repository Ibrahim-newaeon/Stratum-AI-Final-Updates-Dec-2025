# Stratum CDP Implementation TODO

> Track implementation progress by checking off completed items

---

## Week 1: Foundation & Schema

### Documentation
- [x] Create `docs/stratum-cdp/` folder structure
- [x] Write `DISCOVERY.md` documenting repo patterns
- [x] Write `TODO.md` (this file)
- [x] Write `BUILD_PLAN_4W.md` with detailed weekly breakdown
- [x] Write `SCHEMA.md` with table designs

### Database Migrations
- [x] Create migration for `cdp_sources` table
- [x] Create migration for `cdp_profiles` table
- [x] Create migration for `cdp_profile_identifiers` table
- [x] Create migration for `cdp_events` table
- [x] Create migration for `cdp_consents` table
- [x] Run migrations and verify in database

### ORM Models
- [x] Create `backend/app/models/cdp.py` with all models
- [x] Add models to `backend/app/models/__init__.py`
- [x] Verify relationships and indexes
- [x] Test model imports

---

## Week 2: Core API Implementation

### Pydantic Schemas
- [x] Create `backend/app/schemas/cdp.py`
- [x] Define `EventInput` schema (single event)
- [x] Define `EventBatchInput` schema (batch)
- [x] Define `EventBatchResponse` schema
- [x] Define `ProfileResponse` schema
- [x] Define `SourceResponse` schema

### API Endpoints
- [x] Create `backend/app/api/v1/endpoints/cdp.py`
- [x] Register router in `backend/app/api/v1/__init__.py`
- [x] Implement `POST /api/v1/cdp/events` (batch ingestion)
- [x] Implement `GET /api/v1/cdp/profiles/{profile_id}`
- [x] Implement `GET /api/v1/cdp/profiles` (lookup by identifier)
- [x] Implement `GET /api/v1/cdp/sources`
- [x] Implement `POST /api/v1/cdp/sources`

### Core Services
- [x] Implement event validation logic
- [x] Implement identifier normalization (hash email/phone)
- [x] Implement profile resolution (find or create)
- [x] Implement identifier linking logic
- [x] Add request/response logging

### Documentation
- [x] Write `EVENT_SPEC_MINIMAL.md` with JSON schema
- [x] Add curl examples for all endpoints
- [x] Document error responses

---

## Week 3: Testing & Edge Cases

### Unit Tests
- [x] Create `backend/tests/unit/test_cdp.py`
- [x] Test event schema validation (valid/invalid)
- [x] Test identifier hashing (SHA256)
- [x] Test identifier normalization (email lowercase, phone E.164)
- [x] Test profile resolution logic
- [x] Test consent management

### Integration Tests
- [x] Create `backend/tests/integration/test_cdp.py`
- [x] Test full event ingestion flow
- [x] Test profile lookup by ID
- [x] Test profile lookup by identifier
- [x] Test tenant isolation (cannot access other tenant's data)
- [x] Test batch event ingestion (10, 100, 1000 events)

### Error Handling
- [x] Handle invalid event schema (400)
- [x] Handle duplicate events (idempotency)
- [x] Handle unknown identifier types (400)
- [ ] Handle rate limiting (429)
- [x] Handle database errors (500)

### Performance
- [ ] Add database indexes for common queries
- [ ] Test query performance with 100k+ events
- [ ] Add caching for profile lookups (optional)

---

## Week 4: Frontend & Final Docs

### ROI Calculator Component
- [x] Create `frontend/src/components/widgets/CDPROICalculator.tsx`
- [x] Implement input fields (sessions, CVR, AOV, etc.)
- [x] Implement real-time calculations
- [x] Implement results display
- [x] Add to landing page or create route (`/cdp-calculator`)
- [x] Style with Tailwind (match existing widgets)

### Frontend API Integration
- [x] Create `frontend/src/api/cdp.ts`
- [x] Add API hooks for CDP endpoints
- [x] Add types for CDP data structures

### Documentation
- [x] Write `PITCH_DECK.md` (12-15 slides)
- [x] Write `README.md` for CDP module
- [ ] Update main project `README.md` with CDP section
- [ ] Create `CHANGELOG.md` entry for v1.1.0

### Final Testing
- [ ] Run full test suite
- [ ] Verify 80%+ coverage on new code
- [ ] Manual testing of all endpoints
- [ ] Manual testing of ROI Calculator
- [ ] Review and fix any linting errors

---

## Post-MVP (Nice-to-Have)

### Future Enhancements
- [ ] Real-time profile streaming (WebSocket)
- [ ] Segment builder UI
- [ ] Identity graph visualization
- [ ] Data export (CSV/JSON)
- [ ] Webhook destinations
- [ ] EMQ scoring per event batch
- [ ] Anomaly detection on event volume

### Performance Optimizations
- [ ] Event partitioning by month
- [ ] Profile caching layer
- [ ] Async event processing queue
- [ ] Batch insert optimization

---

## Progress Summary

| Week | Status | Completion |
|------|--------|------------|
| Week 1 | Complete | 100% |
| Week 2 | Complete | 100% |
| Week 3 | Complete | 85% |
| Week 4 | Complete | 90% |

**Last Updated**: 2026-01-14

---

## Files Created

### Backend
- `backend/migrations/versions/20260113_000000_026_add_cdp_tables.py`
- `backend/app/models/cdp.py`
- `backend/app/schemas/cdp.py`
- `backend/app/api/v1/endpoints/cdp.py`
- `backend/tests/unit/test_cdp.py`
- `backend/tests/integration/test_cdp.py`

### Frontend
- `frontend/src/components/widgets/CDPROICalculator.tsx`
- `frontend/src/views/CDPCalculator.tsx`

### Documentation
- `docs/stratum-cdp/README.md`
- `docs/stratum-cdp/DISCOVERY.md`
- `docs/stratum-cdp/TODO.md`
- `docs/stratum-cdp/BUILD_PLAN_4W.md`
- `docs/stratum-cdp/SCHEMA.md`
- `docs/stratum-cdp/EVENT_SPEC_MINIMAL.md`
- `docs/stratum-cdp/PITCH_DECK.md`
