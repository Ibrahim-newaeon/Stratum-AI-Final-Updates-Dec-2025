---
name: add-api-endpoint
description: Use when adding a new FastAPI endpoint to Stratum AI. Encodes the standard route → schema → service → repo → test → docs pattern so endpoints land complete with auth, tenant scoping, audit logging, and rate limiting. Trigger when the user says "add endpoint", "add API", "new route", or creates a file under `backend/app/api/v1/endpoints/`.
---

# Add API Endpoint

Stratum AI has 50+ FastAPI endpoints. They all follow the same shape so reviewers can scan them quickly and so cross-cutting concerns (auth, tenant scoping, audit, rate limiting) are guaranteed.

## The 6-Layer Pattern

```
Route (api/v1/endpoints/)
   ↓ depends on
Schema (schemas/)        Pydantic request/response
   ↓ used by
Service (services/)      business logic, no FastAPI imports
   ↓ uses
Repo / Model (models/)   data access, no business logic
   ↓
Test (tests/unit + integration)
   ↓
Docs (OpenAPI tags + docstring)
```

## Step-by-step

### 1. Schema — `backend/app/schemas/<domain>.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime

class SegmentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    rules: dict
    # NEVER include tenant_id here — it comes from auth.

class SegmentRead(BaseModel):
    id: int
    name: str
    rules: dict
    created_at: datetime
    model_config = {"from_attributes": True}
```

### 2. Service — `backend/app/services/<domain>_service.py`

```python
async def create_segment(
    db: AsyncSession,
    tenant_id: int,
    user_id: int,
    payload: SegmentCreate,
) -> Segment:
    segment = Segment(tenant_id=tenant_id, **payload.model_dump())
    db.add(segment)
    await db.flush()
    await audit_log.create(db, action="segment.create", tenant_id=tenant_id,
                            user_id=user_id, target_id=segment.id)
    await db.commit()
    return segment
```

- No FastAPI imports here.
- Always accept `tenant_id` and `user_id`.
- Always write the audit log inside the same transaction as the mutation.

### 3. Route — `backend/app/api/v1/endpoints/<domain>.py`

```python
from fastapi import APIRouter, Depends, status

router = APIRouter(prefix="/segments", tags=["segments"])

@router.post(
    "",
    response_model=SegmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a segment",
)
@rate_limit("20/minute")
async def create_segment(
    payload: SegmentCreate,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
) -> SegmentRead:
    """Create a new audience segment for the current tenant."""
    segment = await segment_service.create_segment(
        db, tenant_id=user.tenant_id, user_id=user.id, payload=payload,
    )
    return SegmentRead.model_validate(segment)
```

- `Depends(get_current_user)` is mandatory unless route is explicitly public (with `# PUBLIC: <reason>` comment).
- `response_model` always set.
- `@rate_limit` always set on POST/PUT/PATCH/DELETE.
- Tenant comes from `user.tenant_id`, never from the request body.

### 4. Tests

**Unit** — `backend/tests/unit/services/test_<domain>_service.py`:

- Happy path
- Validation failure
- Tenant isolation (tenant A cannot see tenant B's segment)
- Audit log written

**Integration** — `backend/tests/integration/test_<domain>_api.py`:

- Auth required (401 without token)
- Rate limit fires (after N requests)
- 422 on bad payload
- 404 on cross-tenant access

Coverage target: 90%+ for new files.

### 5. Register the router

Edit `backend/app/api/v1/__init__.py` or `backend/app/main.py`:

```python
from app.api.v1.endpoints import segments
api_router.include_router(segments.router)
```

### 6. Docs

- Docstring on every route (becomes OpenAPI description).
- If new domain, add a section to `docs/API_REFERENCE.md`.
- Update `docs/02-backend/` if architecture changed.

## Definition of Done

- [ ] Pydantic schemas in `schemas/`
- [ ] Service in `services/` with tenant_id and audit log
- [ ] Route in `api/v1/endpoints/` with auth, response_model, rate limit
- [ ] Router registered in `api/v1/__init__.py`
- [ ] Unit + integration tests
- [ ] `make lint` clean
- [ ] `make test` passes
- [ ] No `tenant_id` field in request schemas
- [ ] Audit log on every mutation
- [ ] `api-endpoint-reviewer` agent passes (delegate before merging)
- [ ] `tenancy-auditor` agent passes (delegate before merging)

## Anti-patterns

- ❌ `tenant_id` in the request body (must come from auth)
- ❌ Returning `dict` instead of a Pydantic model
- ❌ Business logic in the route (move to service)
- ❌ Direct DB access in the route (move to service/repo)
- ❌ `try/except: pass` in the route (use HTTPException)
- ❌ Logging the full request body (PII risk)
- ❌ Hardcoded thresholds in the service (use config)
