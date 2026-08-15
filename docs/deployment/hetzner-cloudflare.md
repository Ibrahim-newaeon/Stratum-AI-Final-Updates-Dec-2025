# Deploying Stratum AI on Hetzner behind Cloudflare

Target topology for `stratumai.app`.

| Host | Serves | Where |
| --- | --- | --- |
| `app.stratumai.app` | React SPA | Cloudflare Pages |
| `api.stratumai.app` | FastAPI, workers, Postgres, Redis | Hetzner (Falkenstein) |
| `stratumai.app` | redirect → `app.` | Cloudflare Redirect Rule |

Everything personal stays in the EU: Hetzner Falkenstein for the live data,
Cloudflare R2 with EU jurisdiction for backups. That removes the
transfer-mechanism question rather than answering it, which matters given how
much of the product is GDPR machinery.

---

## Why this shape

**Frontend on Pages, not on the box.** The SPA is static. Serving it from
Hetzner spends origin CPU and bandwidth on files Cloudflare will cache anyway,
and couples a frontend deploy to an API restart.

**Postgres stays in-compose.** It already is, with pgbouncer in front and tuned
settings in `docker-compose.prod.yml`. Moving to managed Postgres would be a
second vendor and a second bill to solve a problem that is really about
backups — so this fixes the backups instead. Revisit if you need a read replica
or automated failover; at that point managed is worth it.

**Backups go to R2, not to the host.** `deploy-beta.sh` dumps to
`/opt/stratum-ai-backups` on the same machine as the database and only when
someone runs `update`. A host loss takes both. The `backup` service streams
compressed dumps straight to R2 on a schedule, and `deploy-hetzner.sh restore`
is a real command, because a backup nobody has restored is a guess.

---

## 1. Hetzner

A **CCX23** (4 vCPU dedicated, 16 GB) fits the memory reservations already
declared in `docker-compose.prod.yml` — Postgres alone reserves 2 GB and is
capped at 4 GB. CPX41 works if the budget is tighter; do not go below 8 GB.

Region **Falkenstein (fsn1)** or **Nuremberg (nbg1)**.

```bash
# On the host
apt update && apt install -y docker.io docker-compose-plugin git ufw
git clone <repo> /opt/stratum && cd /opt/stratum
cp .env.hetzner.template .env && chmod 600 .env
# fill in .env
```

Attach a **volume** for `/var/lib/docker/volumes` if you want database storage
independent of the server's lifecycle. Hetzner volumes can be detached and
reattached to a replacement host, which turns a rebuild into a remount.

---

## 2. Cloudflare — DNS

| Type | Name | Content | Proxy |
| --- | --- | --- | --- |
| A | `api` | *Hetzner IPv4* | **Proxied** (orange) |
| AAAA | `api` | *Hetzner IPv6* | **Proxied** |
| CNAME | `app` | *Pages target* | **Proxied** |
| CNAME | `@` | *Pages target* | **Proxied** |

`api` **must** be proxied. Grey-clouding it exposes the origin directly, which
defeats the firewall in `setup` and the origin-pull check in nginx.

---

## 3. Cloudflare — SSL/TLS

1. **Overview → Full (strict).** Not Flexible: Flexible sends plaintext to the
   origin and makes every request look like it arrived over HTTP.
2. **Origin Server → Create Certificate**, hostname `api.stratumai.app`,
   15 years. Save to `certs/origin.pem` and `certs/origin.key` on the host.
3. **Origin Server → Authenticated Origin Pulls: on.** nginx verifies the
   client certificate, so a TLS handshake from anything other than Cloudflare
   fails outright.
4. **Edge Certificates → Always Use HTTPS: on**, Minimum TLS 1.2.

---

## 4. Cloudflare — the part that is easy to get wrong

Cloudflare forwards the visitor address in `CF-Connecting-IP`, and its edge
addresses are **public**.

The application only trusts `X-Forwarded-For` when the direct peer is a private
range, so without intervention it records the Cloudflare address. That would
collapse every visitor into a handful of IPs for rate limiting, and write
Cloudflare addresses into `AuditLog.ip_address` — a column `/gdpr/export`
returns to data subjects.

`nginx/stratumai.conf` fixes this at the edge with `set_real_ip_from` +
`real_ip_header CF-Connecting-IP`. Because it rewrites `$remote_addr`, it also
fixes the five call sites that read `request.client.host` directly and never
had the trusted-proxy logic at all. See issue #652.

**The Cloudflare IP list changes.** Re-run `scripts/refresh-cf-ips.sh` and
reload nginx when it does; a stale list silently degrades to the broken
behaviour above.

---

## 5. Cloudflare Pages (frontend)

Connect the repository, then:

| Setting | Value |
| --- | --- |
| Build command | `npm ci && npm run build` |
| Build output | `frontend/dist` |
| Root directory | `frontend` |
| `VITE_API_URL` | `https://api.stratumai.app/api/v1` |

The SPA reads `window.__RUNTIME_CONFIG__?.VITE_API_URL` before the build-time
value, so a runtime config file can override it without a rebuild.

---

## 6. WAF and rate limiting

Cloudflare rules run before anything reaches Hetzner:

- **Rate limiting**: `/api/v1/auth/login` — 5 requests / minute / IP.
- **Rate limiting**: `/api/v1/cms/contact` — 3 / minute / IP. It is an
  unauthenticated write with no application-side limit.
- **WAF Managed Ruleset**: on.
- **Bot Fight Mode**: on for `app.`; leave off for `api.` — it can challenge
  legitimate API clients that cannot solve a challenge.

nginx keeps its own `limit_req` zones as defence in depth, so a Cloudflare
misconfiguration does not leave the origin unprotected.

---

## 7. Bring-up

```bash
./scripts/deploy-hetzner.sh setup     # firewall + certs
./scripts/deploy-hetzner.sh deploy    # build + start + migrate
./scripts/deploy-hetzner.sh verify    # assert the four things that matter
```

`verify` checks: the API answers through Cloudflare; a direct-to-origin request
is refused; the edge is logging **visitor** addresses rather than Cloudflare
ones; and at least one backup object exists in R2.

---

## 8. Before you call it done

- [ ] `verify` passes all four
- [ ] **Restore rehearsed** — `restore` onto a scratch host, not production.
      Until that has been done once, the backups are untested.
- [ ] `PII_ENCRYPTION_KEY` stored off-host **and outside the R2 backup bucket**.
      One compromise must not yield both ciphertext and key.
- [ ] `pii_decryption_fallback` warnings absent from logs (see #650 — their
      presence means PII is failing to decrypt and being silently dropped)
- [ ] Cloudflare IP refresh scheduled
- [ ] Sentry receiving events from the new host

---

## Rollback

DNS is the switch. Set `api` back to the previous origin and traffic moves at
Cloudflare's TTL, with no deploy needed. Keep the old host running until
`verify` has passed and a backup has been taken **from the new one** — the
first backup on the new host is the point of no return for data written after
cutover.
