# Session Checkpoint — 2026-04-28

## Outcome

Stratum AI shipped to production on Railway with a working signup flow, email delivery via Resend SMTP, WhatsApp webhook integration with Meta, and a hardened deploy pipeline. Both backend and frontend are healthy and serving traffic.

---

## What was done today

### Infrastructure & Deploy

- **Backend deploy** stabilized on Railway. Custom domain `callback.stratumai.app` provisioned with SSL.
- **Frontend deploy** stabilized on Railway. Custom domain `stratumai.app` (and `www`) live.
- **Healthcheck timeout** bumped from 300s → 600s (`d75a911`) as safety net.
- **ML models pre-baked into Docker image** (`b8f34b8`) — eliminates the ~9.5 GB / 5-min auto-train at every container start. Runtime startup now ~3-5s instead of ~5min.
- **Frontend `dist not found` log** downgraded from warning to info (it's expected on backend-only deploys).
- **DB DNS race in `start.sh`** fixed: added a `getent hosts` retry loop so `fix_alembic_version.py` doesn't silently skip on cold starts.

### Backend code fixes

- **NameError on startup** (`6b88709`) — imported missing `drip_campaigns` and `push_notifications` routers that were referenced in `include_router()` but never imported in `backend/app/api/v1/__init__.py`.
- **Tenant middleware** (`39db578`) — allowlisted `/api/v1/whatsapp/webhooks/` and `/api/v1/stripe/webhooks/` so platform webhooks bypass tenant auth (each handler still verifies via signature/verify-token).
- **OTP TTL bump** (`c550abe`) — 5 min → 10 min. The previous tight window was failing real users (email delivery + reading time + typing time).
- **OTP verify-miss diagnostic logs** (`e212fae`) — added `email_otp_verify_miss` (Redis key absent) vs `email_otp_verify_mismatch` (wrong code) so future failures are diagnosable in seconds.
- **Truthful email-send logging** — backend was logging "Email OTP sent" even when the underlying SMTP call returned False. Now logs `email_otp_delivery_failed` when the provider rejects the send.
- **WhatsApp webhook POST handler** — Meta uses one URL for both GET (verification handshake) and POST (events). Our endpoint only had GET on `/webhooks/verify` — added POST as an alias of `/webhooks/status` so events stop returning 405.

### Frontend code fixes

- **`@types/react-dom` mismatch** (`19e06a9`) — bumped to v19 to match `@types/react`. Regenerated lockfile so `npm ci` works on Railway.
- **TS errors after React 19 type bump** (`7e3ff6b`):
  - `otp-input.tsx`: callback ref must return void in React 19 — wrapped assignment in a block.
  - `CustomDashboard.tsx`: `react-grid-layout` v2 changed component API. Switched to `react-grid-layout/legacy` (v1-compat). Updated `Layout` vs `LayoutItem` typing.
  - `Settings.tsx`: `useRef()` now requires an initial value — pass `undefined` explicitly.
- **Signup success screen never reached** (`270e37b`) — backend created the account and sent activation email, but the frontend stayed on the verify form because the step-based render branches returned before the `if (isSuccess)` check. Added a `useEffect` that flips `step` to `'success'` when `signupMutation.isSuccess` becomes true, so step-based branches fall through and the success UI renders.

### WhatsApp / Meta integration

- Verified webhook with Meta on `https://callback.stratumai.app/api/v1/whatsapp/webhooks/verify`.
- Subscribed events: `messages`, `message_template_status_update`, `account_update`, `phone_number_name_update`, `phone_number_quality_update` (+ `account_alerts`, `business_status_update` recommended for prod).
- App Review submitted; app published to Live mode.

### Email / Resend

- Resend SMTP configured: `smtp.resend.com:465` SSL, user=`resend`, password=Resend API key.
- Domain `stratumai.app` verified in Resend (DKIM + SPF live).
- **Sender env-var name mismatch identified** — code reads `EMAIL_FROM_ADDRESS` but `.env.example` documented `SMTP_FROM_EMAIL`. Fixed `.env.example` this session; the user should set `EMAIL_FROM_ADDRESS=noreply@stratumai.app` in Railway.
- ⚠️ **Resend API key was leaked in a chat message** during this session. The user must rotate it before the next deploy: Resend → API Keys → revoke → create new → update Railway `SMTP_PASSWORD`.

### `.claude/` config maturity (earlier in the session)

- 8 specialized review agents (`trust-gate-reviewer`, `migration-auditor`, `signal-auditor`, `tenancy-auditor`, `api-endpoint-reviewer`, `secret-leak-reviewer`, `celery-task-reviewer`, `frontend-reviewer`).
- 6 skills (`add-platform-integration`, `add-api-endpoint`, `add-celery-task`, `db-query-review`, `incident-response`, `upgrade-dependency`).
- 3 hooks (`format-on-write`, `block-dangerous-bash`, `rule-check`).
- All commands have proper frontmatter with `description`, `argument-hint`, `allowed-tools`.

---

## Open items the USER needs to do

1. **🔴 URGENT: Rotate Resend API key** — the previous key was pasted in chat.
   - Resend → API Keys → revoke `re_AfG73ma9_...`
   - Create new key with "Sending access" permission only
   - Railway → backend → Variables → update `SMTP_PASSWORD` with new key
2. **Set `EMAIL_FROM_ADDRESS` and `EMAIL_FROM_NAME`** in Railway backend env (currently only `SMTP_FROM_EMAIL` is set, which the code ignores).
3. **Delete `SENDGRID_API_KEY`** from Railway env if it's still set, so the SMTP path runs.
4. **Test signup again** end-to-end after rotating + re-deploying.

---

## To-do for NEXT SESSION

### Theme migration: `stratum-figma.html` → site-wide

**Source of truth**: `C:\Users\Vip\Desktop\stratum-figma.html` (on the user's local machine — needs to be brought into the repo).

**Scope**:

1. **Landing page first**: replace `frontend/public/landing.html` (and any associated CSS) with the new design from the Figma export.
2. **Reflect across the site** (auth pages, marketing pages, public-facing UI):
   - `frontend/src/views/Login.tsx`
   - `frontend/src/views/Signup.tsx`
   - Anything currently themed via the "Nebula Aurora" / dual-theme system (`frontend/index.html`, `frontend/src/views/DashboardLayout.tsx` partials that touch the public surface, etc.)
3. **Tailwind config** likely needs updates: new color tokens, fonts, animations. Compare against the current `frontend/tailwind.config.js` "Nebula Aurora" theme.
4. **Brand assets**: update logo placement, typography (currently Clash Display + Satoshi per `CLAUDE.md`).

**Explicitly out of scope for next session**:

- Dashboard interior (post-login) — keep as-is. The user said "we will se[e] for it but keep in mind don't start put it for n[e]xt session". Do NOT migrate `DashboardLayout.tsx` interior, dashboard widgets, `CustomDashboard.tsx`, etc.

**Workflow for next session**:

1. User pastes `stratum-figma.html` content (or commits it under `frontend/design/figma-reference.html` first).
2. Identify the design tokens (colors, typography, spacing, shadows, gradients).
3. Create a new Tailwind theme block (or replace existing) that mirrors the Figma palette.
4. Migrate `landing.html` first as a single-file proof.
5. Update Login/Signup to match.
6. Sweep `index.html` and shared layout primitives.
7. Visual diff with the Figma export.
8. Frontend build + smoke test on Railway.

**Estimated effort**: 4-8 hours of focused work depending on how different the new theme is. Most of the time will be in:

- Translating Figma styles → Tailwind tokens accurately
- Hunting down components that use old theme tokens
- Visual QA against the Figma reference

---

## Commits shipped to `main` today (in order)

| SHA       | Change                                                                    |
| --------- | ------------------------------------------------------------------------- |
| `6b88709` | fix(api): import drip_campaigns and push_notifications routers            |
| `19e06a9` | fix(frontend): bump @types/react-dom to v19                               |
| `7e3ff6b` | fix(frontend): React 19 + react-grid-layout v2 TS fixes                   |
| `39db578` | fix(middleware): allowlist platform webhook prefixes                      |
| `c550abe` | fix(auth): bump OTP TTL 5 min → 10 min                                    |
| `e212fae` | fix(auth): structured logs for OTP verify-miss reasons                    |
| `1a50cc6` | polish: silence frontend-dist warn + DB DNS race fix in start.sh          |
| `d75a911` | fix(railway): bump backend healthcheck timeout to 600s                    |
| `b8f34b8` | feat(docker): bake pre-trained ML models into image at build time         |
| `9d714fa` | fix(auth+whatsapp): truthful email logs + accept POST on /webhooks/verify |
| `270e37b` | fix(signup): show success screen, block re-submit of consumed OTP         |

Plus the `.env.example` and this checkpoint file from the end of the session.

---

## Branches

- `main` — production (all commits above merged here)
- `claude/dev` — working branch, in sync with main

No PRs open. All merges done directly to main per user request.
