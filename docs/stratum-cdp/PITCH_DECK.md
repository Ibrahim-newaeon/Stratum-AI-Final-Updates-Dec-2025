# Stratum CDP - Pitch Deck

> Client-facing presentation (12 slides)

---

## Slide 1: Title

### Stratum CDP
**Know Your Customers. Trust Your Data.**

First-party customer data platform with built-in signal health monitoring.

---

## Slide 2: The Problem

### Your Customer Data is Broken

**Platform data is siloed**
- Meta reports different numbers than Google
- No unified customer view
- Attribution wars between channels

**Tracking is degrading**
- iOS 14.5+ blocks 30-40% of conversions
- Ad blockers growing 10% YoY
- Cookie deprecation imminent

**Automation runs blind**
- Campaigns optimize on incomplete data
- ROAS calculations miss offline revenue
- Budget decisions based on guesswork

*Result: Lost revenue, wasted ad spend, frustrated teams*

---

## Slide 3: The Solution

### Stratum CDP: First-Party Customer Data Platform

**One unified customer profile**
- Collect events from web, server, CRM
- Resolve identities across devices
- Build complete customer journey

**Built-in data quality**
- EMQ (Event Match Quality) scoring
- Anomaly detection on data flows
- Trust gates before automation

**Privacy-first architecture**
- Hashed PII at ingestion
- Consent management built-in
- GDPR/PDPL compliant

---

## Slide 4: How It Works

### Event Ingestion → Identity Resolution → Unified Profile

```
[Web Pixel]  ─┐
[Server API] ─┼→ [Event Ingestion] → [Identity Graph] → [Unified Profile]
[CRM Sync]   ─┘                           ↓
                                    [EMQ Scoring]
                                          ↓
                                    [Trust Gate]
                                          ↓
                               [Automation / Export]
```

**3 Steps:**
1. **Ingest**: Send events from any source (JS, server, import)
2. **Resolve**: Match identifiers to unified customer profiles
3. **Activate**: Export to ads platforms, CRM, analytics

---

## Slide 5: Key Features

### What You Get

| Feature | Benefit |
|---------|---------|
| **Multi-Source Ingestion** | Collect from web, server, SGTM, CRM |
| **Identity Resolution** | Match email, phone, device across touchpoints |
| **Unified Profiles** | Single view of customer journey |
| **EMQ Scoring** | Know the quality of every event |
| **Consent Management** | GDPR/PDPL compliance built-in |
| **Profile API** | Lookup customers in real-time |

---

## Slide 6: Identity Resolution

### One Customer, Many Devices

**The Challenge:**
- User visits on mobile (anonymous)
- Returns on desktop (logs in with email)
- Purchases on tablet (different device ID)

**Stratum CDP Solution:**
```
anonymous_id: anon_abc123  ──┐
email: ahmed@example.com    ─┼→ [Profile #12345]
device_id: iPhone_xyz789   ──┘
```

**How it works:**
1. Hash identifiers (SHA256) for privacy
2. Link identifiers to single profile
3. Merge touchpoints into unified journey

---

## Slide 7: Event Match Quality (EMQ)

### Trust Your Data Before You Automate

**Every event gets a quality score (0-100):**

| Factor | Weight | What It Measures |
|--------|--------|------------------|
| Identifier Quality | 40% | Has email/phone (vs. anonymous) |
| Data Completeness | 25% | Properties present |
| Timeliness | 20% | Event sent in real-time |
| Context Richness | 15% | Campaign, device, geo data |

**Why it matters:**
- Score 80+: Full automation enabled
- Score 60-79: Reduced automation
- Score <60: Manual review required

*Stratum only automates when data quality is high.*

---

## Slide 8: Integration with Trust Engine

### Trust-Gated Automation

```
[Signal Health Check] → [Trust Gate] → [Automation Decision]
       ↓                    ↓                   ↓
   [HEALTHY]            [PASS]            [EXECUTE]
   [DEGRADED]           [HOLD]            [ALERT ONLY]
   [UNHEALTHY]          [BLOCK]           [MANUAL REQUIRED]
```

**CDP feeds the Trust Engine:**
- Event volume trends
- EMQ score averages
- Identity match rates
- Anomaly detection alerts

*Automation only runs when signal health passes threshold.*

---

## Slide 9: Security & Privacy

### Built for Compliance

**Data Protection:**
- PII hashed at ingestion (SHA256)
- Encrypted at rest and in transit
- Multi-tenant isolation

**Consent Management:**
- Track consent per user per type
- Honor opt-outs automatically
- Audit trail for compliance

**Compliance Ready:**
- GDPR (EU)
- PDPL (Saudi Arabia)
- Data retention policies
- Right to deletion

---

## Slide 10: ROI Impact

### What Clients See

| Metric | Before CDP | After CDP | Lift |
|--------|------------|-----------|------|
| Tracked Conversions | 60% | 85% | +42% |
| Identity Match Rate | 35% | 72% | +106% |
| Attributed Revenue | $100K | $142K | +42% |
| ROAS Accuracy | ±25% | ±8% | 3x better |

**Example: E-commerce Client (AED 500K/mo spend)**
- Recovered 15% "lost" conversions
- Identified 20% more returning customers
- Improved ROAS optimization by 18%
- **Annual impact: AED 1.2M incremental revenue**

---

## Slide 11: Implementation

### 2-Week Setup

**Week 1: Foundation**
- Configure data sources
- Install tracking pixel / server connector
- Map identifiers to profiles

**Week 2: Activation**
- Verify event flow
- Test identity resolution
- Enable Trust Engine integration

**Ongoing:**
- Monitor EMQ dashboard
- Expand to additional sources
- Activate audience exports

---

## Slide 12: Pricing

### Usage-Based Pricing

| Tier | Events/Month | Profiles | Price |
|------|--------------|----------|-------|
| **Starter** | Up to 1M | Up to 100K | $500/mo |
| **Growth** | Up to 10M | Up to 500K | $2,000/mo |
| **Enterprise** | Unlimited | Unlimited | Custom |

**All tiers include:**
- Unlimited data sources
- Identity resolution
- EMQ scoring
- Consent management
- API access

**Add-ons:**
- Dedicated support: +$500/mo
- Custom integrations: One-time fee

---

## Slide 13: Next Steps

### Start Your Pilot

**30-Day Pilot Program:**
1. Free setup consultation
2. Connect 1-2 data sources
3. Measure identity match rate improvement
4. Review EMQ dashboard
5. Decide on full rollout

**Contact:**
- Email: sales@stratum.ai
- Demo: book.stratum.ai/cdp-demo

---

## Appendix: Technical Specs

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/cdp/events` | POST | Ingest events (batch) |
| `/api/v1/cdp/profiles/{id}` | GET | Get profile by ID |
| `/api/v1/cdp/profiles` | GET | Lookup by identifier |
| `/api/v1/cdp/sources` | GET/POST | Manage data sources |

### Data Model

- **Profiles**: Unified customer records
- **Identifiers**: Email, phone, device, anonymous
- **Events**: Append-only event store (13-month retention)
- **Consents**: Privacy preference tracking

### Integration Options

- JavaScript SDK (browser)
- Server-side API (Node, Python, etc.)
- Server-side GTM connector
- CSV import
- CRM sync (HubSpot, Salesforce)
