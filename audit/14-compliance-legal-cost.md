# Phase 14 — Compliance, Legal & Cost

## 1. GDPR / Privacy Tooling

Backend endpoints module: `backend/app/api/v1/endpoints/gdpr.py` (registered in router).

Feature flag: `feature_gdpr_compliance: bool = Field(default=True)` (`config.py:435`).

PII handling:
- Fernet encryption at rest (`security.py:204-226`)
- Per-tenant DEK (`pii_keys`, migration 061)
- Anonymization helper for erasure (`security.py:320-334`)
- Decrypt failure never leaks ciphertext (`security.py:280-285`)

Frontend legal pages:
- `frontend/src/views/pages/legal/Privacy.tsx`
- `frontend/src/views/pages/legal/DPA.tsx`
- `frontend/src/views/pages/legal/Terms.tsx`
- `frontend/src/views/pages/legal/Security.tsx`

Integration tests: `backend/tests/integration/test_gdpr_api.py`, `test_compliance_api.py`.

## 2. Payments / PCI

Stripe.js on frontend (`@stripe/react-stripe-js` `package.json:36-37`).

Card data handled by Stripe — **ASSUMPTION:** SAQ A scope if Stripe Checkout/Elements only — confidence MEDIUM, needs_human_review.

Webhook signature verification enforced (`stripe_webhook.py:150-161`).

## 3. Multi-Tenancy & Data Isolation

RLS migrations + tenant middleware + encrypted PII per tenant.

Superadmin bypass audited (`tenancy/deps.py` referenced in package docstring).

## 4. WhatsApp / Messaging Compliance

WhatsApp integration gated `ENABLE_WHATSAPP` default false (`docker-compose.yml:151`).

Verify token required in compose (`docker-compose.yml:148`).

## 5. Data Processing Agreements

DPA page renders CMS content with sanitization (`DPA.tsx` grep pattern matches other legal pages).

**UNKNOWN — not present in available evidence:** signed DPA template version, subprocessor list maintenance process.

## 6. Cost Drivers (Static Analysis)

| Resource | Cost risk | Evidence |
|----------|-----------|----------|
| LLM (Copilot) | API spend if enabled | `copilot_llm_enabled=False` default (`config.py:317-319`) |
| OpenAI embeddings (RAG) | API spend | `copilot_rag_enabled=False` default (`config.py:341-343`) |
| Vertex AI ML | GCP billing | `ml_provider=local` default (`config.py:103-106`) |
| SendGrid/SMTP | Email volume | optional config |
| Stripe | transaction fees | payments module |
| Sentry | event volume | sample rates 0.1 (`config.py:252-256`) |

**Cannot estimate monthly cost** — missing data: tenant count, event volume, email volume, LLM usage.

## 7. Compliance Findings

| ID | Sev | Title |
|----|-----|-------|
| F-009 | P2 | Stripe idempotency fail-open — billing state consistency under Redis outage |
| — | P2 | Cookie/consent for marketing site not evidenced in repo |

No P0 compliance blockers found in code review; operational compliance depends on deploy config and legal docs accuracy.

## 8. Positive Controls

- GDPR feature on by default
- PII encryption + tenant DEK
- Email masking in logs
- Sentry PII redaction
- Stripe webhook signature required
- Legal pages in app with sanitized CMS HTML

## 9. Searches Run

```
glob backend/app/api/v1/endpoints/gdpr.py        → exists
glob backend/tests/**/test_gdpr*.py              → test_gdpr_api.py
grep "feature_gdpr" backend/app/core/config.py  → line 435
glob frontend/src/views/pages/legal/*.tsx        → Privacy, Terms, DPA, Security
grep "PCI|SAQ" backend/ frontend/               → 0 matches (no explicit PCI doc in repo)
```

## 10. Pre-Release Compliance Checklist

- [ ] Legal review of Privacy/Terms/DPA content vs actual data flows
- [ ] Subprocessor list includes Stripe, SendGrid, Sentry, cloud host
- [ ] DPIA for CDP profile storage and cross-platform audience sync
- [ ] Verify GDPR export/erase endpoints on staging with test tenant
- [ ] Confirm `PII_ENCRYPTION_KEY` rotation runbook exists ops-side
