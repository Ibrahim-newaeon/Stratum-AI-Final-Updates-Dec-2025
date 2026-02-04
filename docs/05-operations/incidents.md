# Incident Management

## Overview

This document defines the incident management process, severity levels, communication protocols, and post-incident review procedures.

---

## Incident Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    INCIDENT LIFECYCLE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐     │
│  │ DETECT  │ →  │ TRIAGE  │ →  │ RESPOND │ →  │ RESOLVE │     │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘     │
│       │              │              │              │            │
│       ▼              ▼              ▼              ▼            │
│  • Alert fires  • Severity    • Investigate  • Fix applied    │
│  • User report  • Assign IC   • Communicate  • Verify fix     │
│  • Monitoring   • Page team   • Mitigate     • Close incident │
│                                                                 │
│                         ┌─────────┐                            │
│                         │ REVIEW  │                            │
│                         └─────────┘                            │
│                              │                                  │
│                              ▼                                  │
│                      • Post-mortem                             │
│                      • Action items                            │
│                      • Process improvements                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Severity Levels

### SEV-1: Critical

**Definition**: Complete service outage or data loss affecting all users.

**Examples**:
- Production API unresponsive
- Database corruption
- Security breach
- All automations failing

**Response Requirements**:
- Response time: < 5 minutes
- Page on-call and engineering lead
- All-hands until resolved
- Executive notification
- Status page update immediately

### SEV-2: Major

**Definition**: Significant degradation affecting many users or critical feature unavailable.

**Examples**:
- Error rate > 5%
- Latency > 5 seconds
- Single platform integration down
- Authentication issues

**Response Requirements**:
- Response time: < 15 minutes
- Page on-call engineer
- Notify engineering lead
- Status page update within 15 minutes

### SEV-3: Minor

**Definition**: Limited impact, workaround available, or non-critical feature affected.

**Examples**:
- Single tenant affected
- Non-critical feature degraded
- Performance degradation < 2x
- Partial data delay

**Response Requirements**:
- Response time: < 1 hour
- Notify on-call engineer
- Track in incident queue
- Status page update if customer-visible

### SEV-4: Low

**Definition**: Minimal impact, cosmetic issues, or internal tooling problems.

**Examples**:
- UI rendering issues
- Internal dashboard slow
- Non-blocking errors
- Monitoring gaps

**Response Requirements**:
- Response time: < 4 hours
- Create ticket
- Address during business hours
- No status page update needed

---

## Roles and Responsibilities

### Incident Commander (IC)

- Coordinates response efforts
- Makes decisions on mitigation strategy
- Manages communication
- Delegates tasks
- Declares incident resolved

### Technical Lead

- Leads technical investigation
- Proposes and implements fixes
- Coordinates with IC on approach
- Documents technical details

### Communications Lead

- Updates status page
- Drafts customer communications
- Manages internal updates
- Coordinates with support team

### Scribe

- Documents timeline
- Records decisions made
- Captures action items
- Prepares post-mortem draft

---

## Communication Templates

### Status Page Update (Investigating)

```
Title: [Service Name] - Investigating Issues

Body:
We are currently investigating reports of [brief description].

Impact: [What users are experiencing]
Next update: [Time, typically 30 minutes]

Posted at: [Time]
```

### Status Page Update (Identified)

```
Title: [Service Name] - Issue Identified

Body:
We have identified the cause of the [issue type] and are working on a fix.

Cause: [Brief technical description]
Expected resolution: [Estimated time]
Next update: [Time]

Posted at: [Time]
```

### Status Page Update (Resolved)

```
Title: [Service Name] - Resolved

Body:
The issue affecting [service] has been resolved.

Duration: [Start time] - [End time] ([duration])
Root cause: [Brief description]
Resolution: [What was done]

We apologize for any inconvenience caused.

Posted at: [Time]
```

### Customer Email (Major Incident)

```
Subject: Service Incident - [Brief Description]

Dear [Customer],

We are writing to inform you of a service incident that may have
affected your account.

WHAT HAPPENED
[Brief, non-technical description of the incident]

IMPACT
[Specific impact to customer's data/service]

WHAT WE'RE DOING
[Steps taken and preventive measures]

NEXT STEPS
[Any action required from customer]

If you have questions, please contact support@stratum.ai.

Sincerely,
The Stratum AI Team
```

---

## Incident Response Process

### 1. Detection

```
Alert Received
     │
     ▼
┌─────────────────┐
│ Acknowledge     │
│ within 5 min    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Initial Triage  │
│ • Assess impact │
│ • Set severity  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Open Incident   │
│ Channel         │
└─────────────────┘
```

### 2. Response

```bash
# Create incident channel
/incident create "API High Error Rate" severity=2

# Page additional help if needed
/page @backend-oncall "SEV-2: API errors spiking"

# Start incident timer
/incident timer start

# Post initial status
/status update investigating "Investigating elevated error rates"
```

### 3. Investigation

```markdown
## Investigation Checklist

- [ ] Review alert details and metrics
- [ ] Check recent deployments (< 24h)
- [ ] Review recent changes (config, infra)
- [ ] Check external dependencies
- [ ] Examine error logs
- [ ] Identify affected scope (users, tenants, features)
```

### 4. Mitigation

```markdown
## Mitigation Options

| Option | Risk | Time | Effectiveness |
|--------|------|------|---------------|
| Rollback deployment | Low | 5 min | High if deploy-related |
| Scale up resources | Low | 10 min | Medium |
| Enable circuit breaker | Medium | 2 min | High for external deps |
| Feature flag disable | Low | 1 min | High for feature-specific |
| Database failover | Medium | 15 min | High for DB issues |
```

### 5. Resolution

```bash
# Verify fix
curl -f https://api.stratum.ai/health/detailed

# Monitor for 15 minutes
watch -n 10 'curl -s http://prometheus:9090/api/v1/query --data-urlencode "query=rate(api_requests_total{status_code=~\"5..\"}[1m])"'

# Update status
/status update resolved "Issue has been resolved"

# Close incident
/incident close
```

---

## Post-Incident Review

### Timeline Template

```markdown
## Incident Timeline

**Incident ID**: INC-2024-0042
**Date**: 2024-01-18
**Duration**: 2h 15m
**Severity**: SEV-2
**IC**: Jane Engineer

### Timeline (All times UTC)

| Time | Event |
|------|-------|
| 14:00 | Alert: HighErrorRate triggered |
| 14:02 | On-call acknowledged |
| 14:05 | Incident channel created |
| 14:10 | Root cause identified: Bad deployment |
| 14:15 | Rollback initiated |
| 14:20 | Rollback complete |
| 14:25 | Error rate returning to normal |
| 14:45 | Monitoring period started |
| 16:15 | Incident resolved |
```

### Post-Mortem Template

```markdown
## Post-Incident Review: [Incident Title]

**Date**: [Date]
**Author**: [Name]
**Status**: Draft / Final

### Summary
[2-3 sentence summary of what happened]

### Impact
- **Duration**: [Time]
- **Users affected**: [Number/percentage]
- **Revenue impact**: [If applicable]
- **SLA impact**: [Error budget consumed]

### Root Cause
[Detailed technical explanation]

### Detection
- How was the incident detected?
- Could we have detected it sooner?

### Response
- What went well?
- What could be improved?

### Contributing Factors
1. [Factor 1]
2. [Factor 2]
3. [Factor 3]

### Action Items

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action 1] | [Name] | [Date] | Open |
| [Action 2] | [Name] | [Date] | Open |

### Lessons Learned
- [Lesson 1]
- [Lesson 2]

### Timeline
[Detailed timeline from above]
```

---

## Escalation Matrix

| Severity | Initial Response | 15 min | 30 min | 1 hour |
|----------|------------------|--------|--------|--------|
| SEV-1 | On-call + Lead | VP Eng | CTO | CEO |
| SEV-2 | On-call | Lead | VP Eng | - |
| SEV-3 | On-call | Lead | - | - |
| SEV-4 | Ticket | - | - | - |

### Escalation Contacts

| Role | Primary | Secondary |
|------|---------|-----------|
| Engineering Lead | @eng-lead | @eng-lead-2 |
| VP Engineering | @vp-eng | @cto |
| CTO | @cto | @ceo |
| Customer Success | @cs-lead | @cs-team |
| Legal (data breach) | @legal | @external-counsel |

---

## Incident Metrics

### Key Metrics Tracked

| Metric | Target | Current |
|--------|--------|---------|
| MTTD (Mean Time to Detect) | < 5 min | 3.2 min |
| MTTR (Mean Time to Resolve) | < 1 hour | 47 min |
| Incidents per month | < 10 | 7 |
| SEV-1 incidents per quarter | 0 | 1 |
| Post-mortem completion rate | 100% | 100% |
| Action item completion rate | > 90% | 85% |

### Monthly Review

```markdown
## Incident Review: [Month Year]

### Summary
- Total incidents: [N]
- SEV-1: [N], SEV-2: [N], SEV-3: [N], SEV-4: [N]
- MTTR average: [Time]
- Error budget remaining: [%]

### Top Incident Categories
1. [Category] - [Count]
2. [Category] - [Count]
3. [Category] - [Count]

### Outstanding Action Items
[List of incomplete items from previous incidents]

### Process Improvements
[Changes made this month based on learnings]
```

---

## Tools and Resources

### Incident Management

- **PagerDuty**: Alerting and on-call management
- **Slack**: Incident communication (#incidents channel)
- **Status Page**: External communication
- **Jira**: Action item tracking

### Investigation

- **Grafana**: Metrics dashboards
- **Loki**: Log aggregation
- **Jaeger**: Distributed tracing
- **Sentry**: Error tracking

### Documentation

- **Confluence**: Post-mortems and runbooks
- **GitHub**: Code changes and deployments

---

## On-Call Schedule

### Primary On-Call

- Rotation: Weekly, Monday 9am UTC
- Responsibilities: First responder for all alerts
- Response time: < 5 minutes for SEV-1/2

### Secondary On-Call

- Rotation: Weekly, offset by 1 day
- Responsibilities: Backup for primary, escalation
- Response time: < 15 minutes

### Handoff Procedure

```markdown
## On-Call Handoff Checklist

- [ ] Review open incidents
- [ ] Review recent alerts (last 24h)
- [ ] Check ongoing investigations
- [ ] Verify PagerDuty contact info
- [ ] Test alerting (if changed)
- [ ] Review any scheduled maintenance
- [ ] Brief on known issues
```

---

## Related Documentation

- [Monitoring](./monitoring.md) - Alerting configuration
- [Runbooks](./runbooks.md) - Response procedures
- [Security](../06-appendix/security.md) - Security incidents
