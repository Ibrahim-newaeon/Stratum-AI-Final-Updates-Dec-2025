# Stratum CDP - 4-Week Build Plan

> MVP-first implementation with a small team: 1 Backend, 1 Data Engineer, 1 Frontend, 1 PM (part-time)

---

## Overview

| Week | Focus | Key Deliverable |
|------|-------|-----------------|
| 1 | Foundation | Schema + Migrations + Models |
| 2 | Core API | Event Ingestion + Profile Resolution |
| 3 | Testing | Unit + Integration Tests + Edge Cases |
| 4 | Frontend + Docs | ROI Calculator + Pitch Deck + Launch |

---

## Week 1: Foundation

### Objectives
- Finalize database schema design
- Create and run all migrations
- Implement ORM models with relationships

### Task Breakdown

#### Backend Engineer
| Task | Description | Est. Hours |
|------|-------------|------------|
| Review SCHEMA.md | Validate table design against requirements | 2 |
| Create cdp_sources migration | Source configuration table | 2 |
| Create cdp_profiles migration | Unified customer profile table | 2 |
| Create cdp_profile_identifiers migration | Identity mapping table | 2 |
| Create cdp_events migration | Append-only event store | 3 |
| Create cdp_consents migration | Privacy consent tracking | 2 |
| Create cdp.py models file | SQLAlchemy models with relationships | 4 |
| Verify migrations | Run locally, test rollback | 2 |

#### Data Engineer
| Task | Description | Est. Hours |
|------|-------------|------------|
| Design partitioning strategy | Events table by month | 3 |
| Define retention policies | What data expires, what doesn't | 2 |
| Create index recommendations | Optimize common query patterns | 3 |
| Document dedupe approach | Idempotency keys + TTL | 2 |

#### Frontend Engineer
| Task | Description | Est. Hours |
|------|-------------|------------|
| Review existing calculator widgets | Understand patterns (SimulatorWidget) | 2 |
| Sketch ROI Calculator wireframe | Input/output layout | 3 |
| Set up component file structure | Create placeholder files | 1 |

#### PM (Part-time)
| Task | Description | Est. Hours |
|------|-------------|------------|
| Finalize MVP scope | Confirm features in/out | 2 |
| Review schema with team | Sign-off on data model | 1 |
| Draft pitch deck outline | Slide structure | 2 |

### Definition of Done - Week 1
- [ ] SCHEMA.md approved by team
- [ ] All 5 migrations created and tested locally
- [ ] Models file created with all relationships
- [ ] `alembic upgrade head` succeeds
- [ ] Tables visible in database with correct columns
- [ ] README.md stub created

### Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Schema changes mid-week | Rework migrations | Freeze schema by Day 2 |
| Alembic conflicts | Blocked migrations | Single branch, coordinate commits |
| Missing indexes | Slow queries later | Data engineer reviews early |

---

## Week 2: Core API

### Objectives
- Implement event ingestion endpoint (single + batch)
- Implement profile resolution logic
- Implement identifier hashing and linking

### Task Breakdown

#### Backend Engineer
| Task | Description | Est. Hours |
|------|-------------|------------|
| Create cdp.py schemas | Pydantic models for request/response | 3 |
| Create cdp.py router | FastAPI router with prefix | 2 |
| Implement POST /events | Event ingestion (validate, store) | 6 |
| Implement identifier hashing | SHA256 for email/phone | 2 |
| Implement profile resolution | Find-or-create by identifier | 6 |
| Implement identifier linking | Link new identifiers to profile | 4 |
| Implement GET /profiles/:id | Fetch profile with identifiers | 3 |
| Implement GET /profiles?identifier | Lookup by hashed identifier | 3 |
| Implement GET /sources | List tenant sources | 2 |
| Implement POST /sources | Create new source | 2 |
| Add structured logging | Log all operations with context | 2 |

#### Data Engineer
| Task | Description | Est. Hours |
|------|-------------|------------|
| Validate event storage | Verify append-only behavior | 2 |
| Test deduplication | Idempotency key handling | 3 |
| Monitor query performance | Check explain plans | 2 |
| Optimize batch inserts | Bulk insert strategy | 3 |

#### Frontend Engineer
| Task | Description | Est. Hours |
|------|-------------|------------|
| Create cdp.ts API file | Axios hooks for CDP endpoints | 4 |
| Start ROI Calculator UI | Input fields, basic layout | 6 |
| Implement calculation logic | Real-time formula evaluation | 4 |

#### PM (Part-time)
| Task | Description | Est. Hours |
|------|-------------|------------|
| Review API contracts | Sign-off on request/response | 1 |
| Test endpoints manually | Verify happy path | 2 |
| Continue pitch deck content | Write slide copy | 3 |

### Definition of Done - Week 2
- [ ] POST /api/v1/cdp/events accepts and stores events
- [ ] Events correctly linked to profiles
- [ ] Identifiers hashed before storage
- [ ] GET /profiles/:id returns profile with identifiers
- [ ] GET /profiles?identifier works with hashed lookup
- [ ] All endpoints return proper error codes
- [ ] EVENT_SPEC_MINIMAL.md complete with examples

### Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Profile resolution race conditions | Duplicate profiles | Use upsert with unique constraint |
| Slow batch inserts | Poor UX | Use COPY or bulk_insert_mappings |
| Identifier collisions | Wrong profile match | Use tenant_id + identifier_hash unique |

---

## Week 3: Testing & Hardening

### Objectives
- Achieve 80%+ test coverage on new code
- Handle all edge cases gracefully
- Performance test with realistic data volumes

### Task Breakdown

#### Backend Engineer
| Task | Description | Est. Hours |
|------|-------------|------------|
| Write unit tests - validation | Test schema validation | 3 |
| Write unit tests - hashing | Test identifier hashing | 2 |
| Write unit tests - resolution | Test profile resolution | 3 |
| Write integration tests - ingestion | Full flow with DB | 4 |
| Write integration tests - lookup | Profile queries | 3 |
| Write integration tests - tenant isolation | Cross-tenant blocked | 3 |
| Handle edge cases | Empty arrays, nulls, unicode | 4 |
| Add rate limiting | Protect ingestion endpoint | 2 |
| Fix bugs from testing | Address test failures | 4 |

#### Data Engineer
| Task | Description | Est. Hours |
|------|-------------|------------|
| Load test with 100k events | Verify performance | 4 |
| Test partition queries | Ensure partition pruning works | 3 |
| Validate data integrity | No orphan records | 2 |
| Document query patterns | Recommended queries for analytics | 3 |

#### Frontend Engineer
| Task | Description | Est. Hours |
|------|-------------|------------|
| Complete ROI Calculator | All inputs/outputs working | 4 |
| Add input validation | Sensible ranges, error states | 3 |
| Write component tests | Vitest tests for calculator | 4 |
| Style refinements | Match Stratum design system | 3 |

#### PM (Part-time)
| Task | Description | Est. Hours |
|------|-------------|------------|
| UAT testing | Test all features end-to-end | 3 |
| Finalize pitch deck | Complete all slides | 3 |
| Prepare demo script | Walk-through for stakeholders | 2 |

### Definition of Done - Week 3
- [ ] 80%+ test coverage on backend/app/models/cdp.py
- [ ] 80%+ test coverage on backend/app/api/v1/endpoints/cdp.py
- [ ] All edge cases handled with appropriate errors
- [ ] Rate limiting in place (100 req/min default)
- [ ] Load test passes: 1000 events/sec sustained
- [ ] ROI Calculator component complete and tested
- [ ] No critical bugs open

### Test Plan Checklist
```
Unit Tests:
[ ] Event validation - valid event accepted
[ ] Event validation - missing required fields rejected
[ ] Event validation - invalid identifier type rejected
[ ] Identifier hashing - email normalized and hashed
[ ] Identifier hashing - phone normalized to E.164 and hashed
[ ] Profile resolution - new profile created if none exists
[ ] Profile resolution - existing profile returned if match
[ ] Identifier linking - new identifier linked to profile
[ ] Consent management - consent recorded correctly

Integration Tests:
[ ] POST /events - single event ingested
[ ] POST /events - batch events ingested
[ ] POST /events - duplicate event deduplicated
[ ] GET /profiles/:id - profile returned with identifiers
[ ] GET /profiles/:id - 404 for unknown profile
[ ] GET /profiles?identifier - profile found by email hash
[ ] GET /profiles?identifier - 404 for unknown identifier
[ ] Tenant isolation - cannot access other tenant's profiles
[ ] Tenant isolation - cannot access other tenant's events

Data Quality Tests:
[ ] Events append-only (no updates)
[ ] Timestamps in UTC
[ ] No orphan identifiers (all linked to profile)
[ ] No duplicate profiles for same identifier
```

### Risks & Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| Test coverage below 80% | Quality concerns | Prioritize critical paths |
| Performance issues at scale | Poor UX | Profile early, optimize hot paths |
| Flaky tests | CI/CD delays | Use proper fixtures, avoid timing deps |

---

## Week 4: Frontend & Documentation

### Objectives
- Complete ROI Calculator and integrate into landing
- Finalize all documentation
- Prepare for launch

### Task Breakdown

#### Backend Engineer
| Task | Description | Est. Hours |
|------|-------------|------------|
| API documentation | OpenAPI/Swagger annotations | 3 |
| Curl examples | Examples for all endpoints | 2 |
| Final bug fixes | Address any remaining issues | 4 |
| Code review | Review all PRs, clean up | 3 |

#### Data Engineer
| Task | Description | Est. Hours |
|------|-------------|------------|
| Data retention script | Automated cleanup job | 3 |
| Monitoring dashboards | Grafana panels for CDP metrics | 4 |
| Runbook documentation | Operational procedures | 3 |

#### Frontend Engineer
| Task | Description | Est. Hours |
|------|-------------|------------|
| Add ROI Calculator to landing | Integrate component | 3 |
| Final styling pass | Polish UI | 3 |
| Create /cdp-roi route (optional) | Standalone page | 2 |
| Final component tests | Ensure coverage | 2 |
| Build verification | Ensure prod build works | 1 |

#### PM (Part-time)
| Task | Description | Est. Hours |
|------|-------------|------------|
| Finalize PITCH_DECK.md | Complete slide content | 2 |
| Write CDP README | Entry point documentation | 2 |
| Update main README | Add CDP section | 1 |
| Create CHANGELOG entry | v1.1.0 release notes | 1 |
| Stakeholder demo | Present completed MVP | 2 |

### Definition of Done - Week 4
- [ ] ROI Calculator live on landing page
- [ ] PITCH_DECK.md complete (12-15 slides)
- [ ] CDP README.md complete
- [ ] Main README updated
- [ ] All documentation reviewed
- [ ] All tests passing
- [ ] Production build successful
- [ ] Demo completed for stakeholders

### Launch Checklist
```
Code:
[ ] All PRs merged to main
[ ] All tests passing in CI
[ ] No critical/high severity bugs open
[ ] Linting passes with no warnings

Documentation:
[ ] DISCOVERY.md - Repository patterns
[ ] TODO.md - Implementation checklist
[ ] BUILD_PLAN_4W.md - This document
[ ] SCHEMA.md - Database design
[ ] EVENT_SPEC_MINIMAL.md - Event JSON schema
[ ] PITCH_DECK.md - Sales deck
[ ] README.md - Module entry point

Infrastructure:
[ ] Migrations applied to staging
[ ] Migrations applied to production
[ ] Monitoring configured
[ ] Alerts configured
[ ] Retention jobs scheduled

Verification:
[ ] Manual smoke test in staging
[ ] Manual smoke test in production
[ ] ROI Calculator accessible
[ ] API endpoints responding
```

---

## Summary Timeline

```
Week 1 (Days 1-5):   Schema → Migrations → Models
Week 2 (Days 6-10):  API → Ingestion → Resolution
Week 3 (Days 11-15): Tests → Edge Cases → Performance
Week 4 (Days 16-20): Frontend → Docs → Launch
```

## Resource Allocation

| Role | Week 1 | Week 2 | Week 3 | Week 4 | Total |
|------|--------|--------|--------|--------|-------|
| Backend | 19h | 35h | 28h | 12h | 94h |
| Data | 10h | 10h | 12h | 10h | 42h |
| Frontend | 6h | 14h | 14h | 11h | 45h |
| PM | 5h | 6h | 8h | 8h | 27h |
| **Total** | **40h** | **65h** | **62h** | **41h** | **208h** |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test Coverage | 80%+ | pytest-cov report |
| API Response Time | <100ms p95 | Prometheus metrics |
| Event Throughput | 1000/sec | Load test results |
| Documentation | 100% | All files complete |
| Bugs at Launch | 0 critical | Bug tracker |
