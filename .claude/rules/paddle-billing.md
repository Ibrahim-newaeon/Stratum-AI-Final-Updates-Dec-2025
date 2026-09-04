---
paths:
  - "backend/app/services/payment_gateway.py"
  - "backend/**/billing*"
  - "backend/**/*paddle*"
  - "frontend/**/*billing*"
  - "frontend/**/*checkout*"
  - "docs/**/*paddle*"
---

# Paddle billing rules

- Paddle is the only supported payment provider. Stripe references are migration residue, not an implementation pattern.
- Keep billing access behind the existing payment-gateway abstraction.
- Preserve Paddle signature verification, event idempotency, transaction boundaries, tenant synchronization, retries, and provider identifiers.
- Never log secrets or raw signed webhook payloads.
- Do not run production billing changes, migrations, or cutovers without explicit user approval and the documented recovery plan.
