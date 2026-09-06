# Paddle Cutover Runbook

Switching Stratum's billing from Stripe to Paddle, and back if needed.

The switch itself is one environment variable. Everything else in this document
exists because the things that go wrong with a payment gateway go wrong
*silently* — a webhook that never verifies, a checkout that opens onto a blank
page, a plan that stops being granted. Each step below has a check that fails
loudly instead.

## How the switch works

`PAYMENT_GATEWAY` (`stripe` | `paddle`) is read per request by
`app/services/payment_gateway.py`, which returns either `stripe_service` or
`paddle_service`. Both modules expose the same function names and the same
dataclasses, plus four aliases (`GATEWAY_NAME`, `CONFIGURED`,
`TENANT_CUSTOMER_FIELD`, `sync_tenant_customer`) that normalise where they
differ. `payments.py` therefore contains no gateway branch at all.

Both webhook routes stay mounted regardless of the setting, so a switch never
strands in-flight events from the other gateway:

- `POST /api/v1/webhooks/stripe`
- `POST /api/v1/webhooks/paddle`

Tenants carry `stripe_customer_id` **and** `paddle_customer_id`. Neither is
removed by the switch, so historical Stripe invoices stay resolvable.

## Before you flip

Everything here must be true. The first three are dashboard-only.

| # | Requirement | How to check |
|---|---|---|
| 1 | Business verification approved | Paddle dashboard shows the account verified |
| 2 | `stratumai.app` approved for checkout | Checkout > Request domain approval. Live does **not** auto-approve; sandbox does |
| 3 | Default payment link set | Checkout > Checkout settings. Without it Paddle returns `400 transaction_default_checkout_url_not_set` and refuses to create *any* transaction — checkout cannot open at all |
| 4 | Live catalog exists | `GET /products` filtered to `custom_data.app == "stratumai.app"` returns Starter, Professional, Enterprise |
| 5 | Live notification destination exists | One pointing at `https://stratumai.app/api/v1/webhooks/paddle`. **Do not recreate an existing one** — that rotates `endpoint_secret_key` and silently breaks verification of every future delivery |
| 6 | Migration applied | `067_add_paddle_billing_ids` |
| 7 | Refund policy reachable | `https://stratumai.app/refund-policy` returns 200 |

## Environment

```bash
PAYMENT_GATEWAY=paddle
PADDLE_ENVIRONMENT=production
PADDLE_API_KEY=pdl_live_...            # server-side; never reaches the browser
PADDLE_CLIENT_TOKEN=live_...           # client-side; served by GET /payments/config
PADDLE_WEBHOOK_SECRET=pdl_ntfset_...   # the destination's endpoint_secret_key
PADDLE_CHECKOUT_URL=https://stratumai.app/checkout
PADDLE_STARTER_PRICE_ID=pri_...
PADDLE_STARTER_TRIAL_PRICE_ID=pri_...
PADDLE_PROFESSIONAL_PRICE_ID=pri_...
PADDLE_PROFESSIONAL_TRIAL_PRICE_ID=pri_...
PADDLE_ENTERPRISE_PRICE_ID=            # deliberately blank: contact-sales
```

Three of these are easy to get wrong:

- **`PADDLE_WEBHOOK_SECRET` is not the API key.** It is the destination's
  `endpoint_secret_key`, shown once at creation and never retrievable again. A
  wrong value fails *every* signature, and Paddle reports only that your
  endpoint rejected the delivery.
- **`PADDLE_CHECKOUT_URL` is not a success URL.** It names the page that
  *hosts* the checkout overlay. Paddle appends `?_ptxn=<transaction_id>` and
  Paddle.js on that page opens the checkout — there is no Paddle-hosted page to
  redirect to the way Stripe has one. Point it at a page that loads Paddle.js,
  on an approved domain.
- **Price IDs are environment-scoped.** Sandbox `pri_...` values do not exist in
  production. Mixing them yields a checkout that will not load.

Leave `PADDLE_WEBHOOK_ENFORCE_IP_ALLOWLIST=false` at first. Production sits
behind Cloudflare and nginx, so the resolved peer may not be Paddle's address;
enforcing before confirming that would reject every webhook. The handler logs
`paddle_webhook_ip_not_allowlisted` on each mismatch while still processing the
event. Turn enforcement on only once that line has stopped appearing for
genuine deliveries.

## Flip

1. Set the variables above, keeping every `STRIPE_*` value in place.
2. Deploy. See `stratum-never-bare-docker-compose-on-prod` — use the hetzner
   overlay, never a bare `docker compose up`.
3. Confirm the gateway actually switched:
   ```bash
   curl -s https://stratumai.app/api/v1/payments/config | jq '{gateway, configured, environment}'
   # => {"gateway": "paddle", "configured": true, "environment": "production"}
   ```
   `configured: false` means `PADDLE_API_KEY` is missing. Settings use
   `extra="ignore"`, so a misspelled variable is dropped silently rather than
   raising — see `stratum-check-prod-config-without-ssh`.

## Sandbox rehearsal

Do this before the live cutover. It exercises the one thing unit tests cannot:
that Paddle can actually reach the webhook endpoint over the network.

Sandbox and live are separate accounts with separate credentials. Price IDs are
environment-scoped — a sandbox `pri_...` does not exist in production, and
mixing them produces a checkout that will not load.

### Test cards

Sandbox only. These are rejected in live mode, which is why the live check
below uses a real card that you then refund.

| Card | Outcome |
| --- | --- |
| `4242 4242 4242 4242` | Succeeds, no 3DS |
| `4000 0038 0000 0446` | Succeeds, with a 3DS challenge |
| `4000 0000 0000 0002` | Declined |

Any future expiry date and any 3-digit CVC.

The declined card is the one worth spending time on: it is the only way to see
`transaction.payment_failed` arrive and confirm the tenant's plan is *not*
changed by it. Entitlement is meant to follow the `subscription.*` event, and
PAST_DUE deliberately stays entitling so a customer is not cut off mid-dunning.

### Steps

1. Expose the local API. Paddle must reach it from the internet; a `localhost`
   destination silently never delivers.
   ```bash
   cloudflared tunnel --url http://localhost:8000
   ```
2. Point the sandbox destination at the printed URL, suffixed
   `/api/v1/webhooks/paddle`. Update the existing destination rather than
   creating one — updating the URL keeps `endpoint_secret_key`, creating a new
   destination issues a different secret.
3. Run the API with the sandbox values (`PADDLE_ENVIRONMENT=sandbox`, sandbox
   price IDs, that destination's secret, `PAYMENT_GATEWAY=paddle`).
4. Check out at `/checkout` with `4242 4242 4242 4242`. The overlay must open
   **in place**, with no page navigation.
5. Confirm the plan was granted by the webhook, not the redirect:
   ```bash
   grep -E "paddle_webhook_received|tenant_subscription_synced" <api logs>
   ```
6. Repeat with `4000 0000 0000 0002` and confirm the plan does **not** change.

Paddle also ships a webhook simulator (Developer tools > Simulations) which can
drive the endpoint without a checkout, once the tunnel is up.

[paddle-rehearsal-findings.md](paddle-rehearsal-findings.md) records one run of
this rehearsal: what it verified, and the local prerequisites step 3 assumes
(Python 3.12, a pgvector+AGE database, Redis, uvicorn's working directory, and
cloudflared's address family).

## Verify with one real transaction

Do this yourself, on a real card, and refund it. A test card will not work in
live mode.

1. Sign in as a tenant with no subscription, go to `/checkout`, pick a plan.
2. The overlay must open **in place** — no page navigation. If the button
   spins and nothing appears, open the browser console: a CSP violation on
   `cdn.paddle.com` means `script-src` is missing the Paddle CDN.
3. Complete payment.
4. Confirm the plan was granted by the **webhook**, not the redirect:
   ```bash
   docker compose logs api | grep -E "paddle_webhook_received|tenant_subscription_synced"
   ```
   Expect `subscription.activated` followed by `tenant_subscription_synced`
   with `gateway=paddle` and the correct plan.
5. Refund the transaction in the Paddle dashboard.

If the plan did not change, check for `paddle_subscription_unmapped_price` —
that means the price on the subscription is not one of the configured
`PADDLE_*_PRICE_ID` values, and the tenant's plan was deliberately left
untouched rather than guessed at.

## Rolling back

```bash
PAYMENT_GATEWAY=stripe
```

Deploy. That is the whole rollback, and it is safe at any time:

- Stripe credentials and code were never removed.
- `stripe_customer_id` was never cleared.
- The Paddle webhook route stays mounted, so events for subscriptions created
  during the Paddle window still process and still update tenant plans.

What rollback does **not** do is migrate subscriptions. Anyone who subscribed
through Paddle keeps billing through Paddle; their plan continues to be
maintained by the Paddle webhook. Only *new* checkouts return to Stripe. There
is no supported way to move an active subscription between gateways — the
customer must cancel and resubscribe.

## Things that fail silently

Worth knowing before they happen, because none of these surface as an error to
the customer or in normal logs.

| Symptom | Cause |
|---|---|
| Every webhook rejected, Paddle shows "endpoint rejected" | Wrong `PADDLE_WEBHOOK_SECRET`, or this host's clock has drifted past the 5s signature window. Look for `paddle_webhook_signature_stale`; it logs the observed age. Fix NTP before widening `PADDLE_WEBHOOK_SIGNATURE_TOLERANCE_SECONDS` |
| Checkout button spins, nothing opens | `cdn.paddle.com` missing from CSP `script-src`, or an ad blocker |
| Checkout opens on a blank page | `PADDLE_CHECKOUT_URL` points somewhere that does not load Paddle.js |
| Payment succeeds, plan never granted | Webhook not reaching us, or the price is not a configured `PADDLE_*_PRICE_ID`. Grep `paddle_subscription_unmapped_price` |
| Trial not applied | Checkout used the base price. Trials live on the *price* in Paddle, so `PADDLE_*_TRIAL_PRICE_ID` must be set; `_trial_days_for_tenant` returns 0 for any tenant whose `trial_ends_at` is already set, which registration does at signup |
| Duplicate plan changes across workers | `PADDLE_WEBHOOK_SECRET` fine but Redis down. The handler fails closed with 503 and Paddle retries, so this should not occur — if it does, check `paddle_webhook_idempotency_unavailable` |

## Tests

```bash
cd backend && python -m pytest tests/unit/test_paddle_service.py tests/unit/test_paddle_webhook.py -q
```

`test_paddle_webhook.py` covers the full endpoint path with real HMAC
signatures: forged and tampered payloads rejected, retries deduplicated,
handler failures returning 5xx with the claim released so Paddle's retry is not
skipped, and stale out-of-order events unable to regress a newer plan.
