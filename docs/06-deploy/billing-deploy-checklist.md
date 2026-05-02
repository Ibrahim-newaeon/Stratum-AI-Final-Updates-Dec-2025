# Deploy Checklist — Billing & Upgrade Flow Arc

The 5-commit billing arc on `claude/fix-overview-404-fallback` is ready
to merge. This checklist covers everything that needs to happen between
clicking "Merge" and a working production checkout flow.

## What's in the branch

```
6f1eed6  P14  outcome-nudge Phase A wiring (stub estimator)
4471e4f  P13.5  graceful expiry → autopilot advisory mode
4054dcf  P13  limit-triggered upgrade (HTTP 402 + drawer)
83d3d32  P12  14-day Starter trial + Plans page + TrialBanner
3baf44a  P11.5  Overview 404 fallback fix
```

## Pre-merge verification

```bash
# From the repo root, on the feature branch
git fetch origin
git log origin/main..HEAD --oneline    # expect 5 commits

cd frontend
npm ci --legacy-peer-deps
npx tsc --noEmit -p tsconfig.build.json   # exit 0
npx vite build                            # success
npx vitest run src/components/primitives src/views/dashboard
# expect 14 files / 121 tests passing
```

## Merge

Open a PR `claude/fix-overview-404-fallback` → `main`. Squash or
merge-commit are both fine — the 5 commits are individually
reviewable so squash is cleaner.

## Migration on Railway

After main builds, the migration `048_autopilot_outcome_columns`
auto-runs via `start.sh`'s `make migrate` step. Sanity-check on the
Railway logs:

```
alembic upgrade head
INFO  [alembic.runtime.migration] Running upgrade 047_add_missing_indexes -> 048_autopilot_outcome_columns
```

Adds 3 nullable columns + 1 index — all defensive, safe to retry.

## Stripe production wiring

The frontend `/dashboard/plans` calls `paymentsApi.createCheckout()`
which hits `POST /payments/checkout` — that endpoint requires real
Stripe keys + price IDs. Without them, the call returns **"Billing
not configured"** instead of a checkout URL.

### 1. Stripe dashboard setup

In your Stripe dashboard (live mode):

1. **Create the Starter recurring price**
   - Product: "Stratum AI — Starter"
   - Price: **$499/month**, recurring, USD
   - Copy the price ID (`price_1NX...`)

2. **Create the Professional recurring price**
   - Product: "Stratum AI — Professional"
   - Price: **$999/month**, recurring, USD
   - Copy the price ID

3. **Enterprise** — no Stripe price needed; the Plans page short-circuits
   to a `mailto:sales@stratumai.app` link for that tier.

4. **Webhook endpoint**
   - URL: `https://callback.stratumai.app/api/v1/whatsapp/webhooks/stripe`
     **NOTE:** the path is `/api/v1/whatsapp/webhooks/stripe` because of
     historical routing — verify against `backend/app/api/v1/endpoints/
stripe_webhook.py` line 63 if the deployed router prefix has
     drifted. The actual prefix is whatever mounts that endpoint in
     `backend/app/api/v1/__init__.py`.
   - Events to subscribe:
     - `checkout.session.completed`
     - `customer.subscription.created`
     - `customer.subscription.updated`
     - `customer.subscription.deleted`
     - `invoice.payment_succeeded`
     - `invoice.payment_failed`
   - Copy the signing secret (`whsec_...`)

### 2. Railway env vars (backend service)

```
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_STARTER_PRICE_ID=price_1NX...
STRIPE_PROFESSIONAL_PRICE_ID=price_1NY...
STRIPE_ENTERPRISE_PRICE_ID=          # leave blank
```

The pydantic settings expect lower-case-with-underscore Python field
names; Railway will translate `STRIPE_SECRET_KEY` → `stripe_secret_key`
automatically (case-insensitive, env-var convention).

### 3. Railway env vars (frontend service)

The frontend uses `STRIPE_PUBLISHABLE_KEY` only if it ever calls Stripe
Elements directly. Currently it doesn't — checkout is server-side
hosted-redirect, so the publishable key is optional for the frontend
build. Skip this step unless we add Elements later.

### 4. Verify after deploy

```bash
# 1. Backend reports stripe_configured: true
curl -H "Authorization: Bearer $TOKEN" \
     https://callback.stratumai.app/api/v1/payments/config | jq '.stripe_configured'
# expect: true

# 2. Backend lists tiers with the live price IDs
curl -H "Authorization: Bearer $TOKEN" \
     https://callback.stratumai.app/api/v1/payments/config | jq '.tiers'
# expect: [{tier:"starter", name:"Starter", price:499, ...}, ...]

# 3. Frontend renders the Plans page
open https://stratumai.app/dashboard/plans
# Each tier card shows the live price; "Upgrade to Professional"
# button is enabled (not disabled with "Billing not configured")

# 4. End-to-end checkout test (use Stripe test card 4242 4242 4242 4242
#    in test mode first, then a real card in live mode after smoke tests)
#    Expected:
#    - Click "Continue to checkout" → drawer shows "Connecting to Stripe…"
#    - Browser redirects to checkout.stripe.com
#    - Complete payment → redirect back to /dashboard/plans?status=success
#    - Webhook fires → tenant.plan + stripe_customer_id update in DB
#    - TrialBanner disappears (subscription is no longer trial)
```

## Smoke test path on production (manual, ~5 min)

1. **Sign up** a fresh test account → success screen says "14-day Starter
   trial is now active."
2. **Land on dashboard** → TrialBanner visible: "14 days left in your
   Starter trial." Sidebar Account group shows "Plans".
3. **Visit `/dashboard/plans`** → 3 tier cards render with live prices.
   "Recommended" pill on Professional. "Active" pill on Starter (you're
   on the trial).
4. **Click Upgrade to Professional** → ConfirmDrawer opens with price
   preview. Click "Continue to checkout" → redirects to Stripe.
5. **Use test card 4242…** → completes → redirects back to
   `/dashboard/plans?status=success`.
6. **Check the DB** (or admin view):
   - `tenant.plan = 'professional'`
   - `tenant.stripe_customer_id` populated
   - `tenant.trial_ends_at` left intact (historical record)
7. **Refresh dashboard** → TrialBanner gone (no longer trial).

## Rollback plan

If anything breaks post-merge:

```bash
# Revert the 5-commit window on main
git checkout main
git pull origin main
git revert --no-commit 3baf44a^..6f1eed6
git commit -m "revert: roll back billing arc P11.5–P14"
git push origin main

# Migration 048 is non-destructive — no need to roll it back
# (3 NULL columns and 1 index are inert if unused).
```

Stripe-side: deactivate the live price IDs in the Stripe dashboard
to prevent any further checkouts; existing successful charges remain
processed.

## Open / known caveats

- **Outcome estimator is a stub** — `OutcomeNudge` renders nothing in
  production until Phase B replaces the stub body in
  `services/autopilot/outcomes.py`. This is intentional Phase A wiring.
- **Per-row autopilot CTAs (`[Pause]`/`[Scale]`/`[Hold]`) are wired in
  P15** (separate commit on the same branch) — see commit log.
- **Bulk-acknowledge action** — the SignalStrip "Acknowledge all"
  button is still a no-op. Wired in a follow-up.
