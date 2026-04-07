# Feature Documentation Index

## Overview

Stratum AI platform features organized by priority and dependency. Each feature includes specification, user flows, API contracts, and edge cases.

---

## Feature Directory

| # | Feature | Priority | Status | Dependencies |
|---|---------|----------|--------|--------------|
| 01 | [Trust Engine](./01-trust-engine/) | Core | Production | None |
| 02 | [CDP](./02-cdp/) | Major | Production | Trust Engine |
| 03 | [Audience Sync](./03-audience-sync/) | Major | Production | CDP |
| 04 | [CMS](./04-cms/) | Major | Production | None |
| 05 | [Authentication](./05-authentication/) | Core | Production | None |
| 06 | [Campaigns](./06-campaigns/) | Major | Production | Trust Engine |
| 07 | [Autopilot](./07-autopilot/) | Major | Production | Trust Engine, Campaigns |
| 08 | [Rules Engine](./08-rules-engine/) | Major | Production | Autopilot |
| 09 | [Analytics](./09-analytics/) | Major | Production | Campaigns |
| 10 | [Integrations](./10-integrations/) | Major | Production | Trust Engine |
| 11 | [Onboarding](./11-onboarding/) | Enhancement | Production | Authentication |
| 12 | [WhatsApp](./12-whatsapp/) | Enhancement | Production | Integrations |
| 13 | [Payments](./13-payments/) | Core | Production | Authentication |
| 14 | [Superadmin](./14-superadmin/) | Internal | Production | All |

---

## Feature Documents Per Feature

Each feature directory contains:

```
docs/04-features/{feature}/
├── spec.md           # Technical specification
├── user-flows.md     # User journey diagrams
├── api-contracts.md  # API endpoints & schemas
└── edge-cases.md     # Error handling & edge cases
```

### Document Purposes

| Document | Purpose |
|----------|---------|
| **spec.md** | Technical specification including architecture, data models, and implementation details |
| **user-flows.md** | Step-by-step user journeys with diagrams and state transitions |
| **api-contracts.md** | Complete API reference with request/response schemas |
| **edge-cases.md** | Error handling, edge cases, and known limitations |

---

## Feature Categories

### Core Features
Essential platform functionality that other features depend on.

- **Trust Engine** - Signal health calculation and trust gate decisions
- **Authentication** - User login, MFA, sessions
- **Payments** - Subscription and billing management

### Major Features
Primary user-facing capabilities.

- **CDP** - Customer Data Platform with profile management
- **Audience Sync** - Push segments to ad platforms
- **Campaigns** - Multi-platform campaign management
- **Autopilot** - Automated campaign optimization
- **Rules Engine** - Custom automation rules
- **Analytics** - Reporting and dashboards
- **Integrations** - Platform connections (Meta, Google, etc.)
- **CMS** - Content management for landing pages

### Enhancement Features
Additional capabilities that enhance the platform.

- **Onboarding** - Guided setup and configuration
- **WhatsApp** - WhatsApp Business integration

### Internal Features
Admin and operations tools.

- **Superadmin** - Platform administration

---

## Dependency Graph

```
                    ┌─────────────────┐
                    │ Authentication  │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌───────────┐  ┌───────────┐  ┌───────────┐
       │  Payments │  │ Onboarding│  │Trust Engine│
       └───────────┘  └───────────┘  └─────┬─────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              ▼                            ▼                            ▼
       ┌───────────┐                ┌───────────┐                ┌───────────┐
       │Integrations│               │ Campaigns │                │    CDP    │
       └─────┬─────┘                └─────┬─────┘                └─────┬─────┘
              │                            │                            │
              ▼                            ▼                            ▼
       ┌───────────┐                ┌───────────┐                ┌───────────┐
       │ WhatsApp  │                │ Autopilot │                │Audience   │
       └───────────┘                └─────┬─────┘                │  Sync     │
                                          │                      └───────────┘
                                          ▼
                                   ┌───────────┐
                                   │Rules Engine│
                                   └───────────┘
```

---

## Feature Ownership

| Feature | Team | Lead |
|---------|------|------|
| Trust Engine | Core Platform | Signal Team |
| CDP | Data Platform | CDP Team |
| Campaigns | Growth | Campaign Team |
| Autopilot | AI/ML | Automation Team |
| Integrations | Platform | Integration Team |

---

## Quick Links

### Most Used
- [Trust Engine Spec](./01-trust-engine/spec.md)
- [CDP API Contracts](./02-cdp/api-contracts.md)
- [Autopilot User Flows](./07-autopilot/user-flows.md)

### API References
- [Trust Engine API](./01-trust-engine/api-contracts.md)
- [CDP API](./02-cdp/api-contracts.md)
- [Audience Sync API](./03-audience-sync/api-contracts.md)
- [Campaigns API](./06-campaigns/api-contracts.md)
