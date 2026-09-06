# Paddle Sandbox Rehearsal — 2026-09-05

A record of one partial run of the sandbox rehearsal in
[paddle-cutover.md](paddle-cutover.md), kept because it establishes which parts
of the Paddle path are verified against live Paddle traffic and which are not,
and because the local environment prerequisites the runbook's step 3 assumes
turned out to be the whole cost of the exercise.

Code under test: `2ae91e0` (#738). Sandbox account, local API behind a
cloudflared quick tunnel.

## Verified against real Paddle deliveries

Each row was observed, not inferred.

| Behaviour | Evidence |
| --- | --- |
| Route mounted at `/api/v1/webhooks/paddle` | `api/v1/__init__.py` include; route in `endpoints/paddle_webhook.py` |
| Fails closed with no secret configured | `503 Webhook secret not configured` before `.env` was loaded |
| Rejects an unsigned body | `400 Missing Paddle signature` |
| **Accepts a genuine Paddle HMAC signature** | A simulation reached the handler: `paddle_webhook_received` logged with the simulation's `event_id` |
| Redis idempotency claim is taken before processing | `paddle_webhook_received` follows the claim; no duplicate processing |
| A handler failure asks Paddle to retry | `500` plus `paddle_webhook_handler_error`, rollback, and claim release — not a silent `200` |
| Updating a destination's URL preserves its secret | Destination updated twice for new tunnel hostnames; `endpoint_secret_key` unchanged, matching the runbook's step 2 |

The signature path — the security-critical half — is confirmed end to end
against traffic Paddle actually signed.

## Not verified

| Behaviour | Why |
| --- | --- |
| Tenant resolution via `custom_data.tenant_id` / `paddle_customer_id` | blocked below |
| Plan granted on `subscription.activated` | blocked below |
| Plan unchanged on `transaction.payment_failed` | blocked below |
| Migration `067_add_paddle_billing_ids` applying | never ran against a valid database |
| Checkout overlay with a test card | sandbox `PADDLE_API_KEY` / `PADDLE_CLIENT_TOKEN` were not set |

All five are database-dependent. Nothing observed points at a defect in
`paddle_webhook.py` or `paddle_service.py`.

### What blocked them

The local database had been built by `create_all` at some earlier point and
never migrated, so it was missing columns and tables the current models expect:

```
UndefinedColumnError: column tenants.status does not exist
UndefinedTableError:  relation "tenant_encryption_keys" does not exist
```

`alembic upgrade head` cannot repair that state — with no `alembic_version`
row it replays from revision 001 against a populated database and dies on
`type "userrole" already exists`.

Rebuilding is not a plain `createdb` either: migration 049 needs **pgvector**
and migration 065 needs **Apache AGE**. A stock Postgres (Homebrew, or the
official image) has neither. This is why `docker-compose.yml` *builds* its `db`
service from `backend/Dockerfile.postgres` rather than pulling an image.

## Local prerequisites the runbook assumes

Step 3 of the rehearsal says "run the API with the sandbox values". Getting to
that point needs the following, none of which is obvious from a cold start:

- **Python 3.12.** `fastapi==0.141.1` will not resolve on macOS's system 3.9;
  pip reports it as "no matching distribution", which reads like a network
  problem and is not.
- **A database with pgvector and AGE.** `docker compose up -d db`, which needs
  a `.env` at the *repository root* — Compose does not read `backend/.env`, and
  without it interpolation fails on `POSTGRES_USER`.
- **Redis.** Startup calls `ws_manager.start()` and aborts if Redis is
  unreachable. The reload supervisor keeps holding port 8000 afterwards, so the
  port looks occupied while nothing is served — `curl` returns `000`, not a
  connection refusal.
- **Run uvicorn from `backend/`.** `Settings.model_config` sets
  `env_file=".env"`, resolved relative to the process working directory. Started
  from the repository root, every Paddle variable silently falls back to its
  default and the endpoint answers `503`.
- **Point cloudflared at `127.0.0.1`, not `localhost`.** macOS resolves
  `localhost` to `::1` first; uvicorn binds IPv4 only, so the tunnel returns
  `502` with `dial tcp [::1]:8000: connect: connection refused` in
  `~/cloudflared.log`. `--url http://127.0.0.1:8000` avoids the lookup.
- **Quick tunnels get a new hostname on every start.** Each restart means
  updating the destination URL again. The secret survives; the URL does not.

## Recommended verification order

`--reload` is a liability here: any file touch restarts the worker, and a failed
restart leaves the supervisor holding the port with nothing behind it. Run
without it and log to a file so failures can be grepped rather than scrolled.

```bash
# 1. app is up at all
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/health          # 200

# 2. config reached the process
curl -s -o /dev/null -w '%{http_code}\n' -X POST \
  http://127.0.0.1:8000/api/v1/webhooks/paddle -d '{}'                          # 400, not 503, not 404
```

`400 Missing Paddle signature` is the green light: route mounted, secret
loaded, verification active. `503` means the config never arrived. Checking
only the webhook path cannot distinguish "app down" from "app misconfigured",
which is why `/health` comes first.

## Still outstanding for the live cutover

- No **live** notification destination exists yet. Create it in the live
  dashboard, take its `endpoint_secret_key` directly into the server
  environment, and subscribe the events the handler dispatches on:
  `subscription.*`, `transaction.completed`, `transaction.paid`,
  `transaction.payment_failed`, `transaction.past_due`, `customer.created`,
  `customer.updated`.
- Apply `067_add_paddle_billing_ids` on the server.
- The three behaviours under "Not verified" still need a run against a database
  that matches the models — staging, or the live check in
  [paddle-cutover.md](paddle-cutover.md#verify-with-one-real-transaction).

The payment link is already set to `https://stratumai.app/checkout` in both
sandbox and live.
