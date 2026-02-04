# Rules Engine Edge Cases

## Overview

This document covers error handling, edge cases, and known limitations for the Rules Engine.

---

## Edge Cases

### 1. Rule Cooldown Active

**Scenario**: Rule triggered recently, new evaluation attempted.

**Behavior**:
- Check `last_triggered_at` against `cooldown_hours`
- Skip evaluation if within cooldown

**Response**:
```json
{
  "status": "skipped",
  "reason": "Rule is in cooldown",
  "cooldown_ends": "2024-01-16T14:30:00Z",
  "remaining_hours": 12
}
```

**Handling**:
```python
if rule.last_triggered_at:
    cooldown_end = rule.last_triggered_at + timedelta(hours=rule.cooldown_hours)
    if datetime.now(timezone.utc) < cooldown_end:
        return {"status": "skipped", "reason": "In cooldown"}
```

---

### 2. No Applicable Campaigns

**Scenario**: Rule scope doesn't match any campaigns.

**Behavior**:
- Rule evaluates successfully
- No campaigns matched
- No actions taken

**Response**:
```json
{
  "status": "completed",
  "campaigns_evaluated": 0,
  "campaigns_matched": 0,
  "reason": "No campaigns match rule scope"
}
```

---

### 3. Computed Field Calculation Error

**Scenario**: Computing CPA but campaign has zero conversions.

**Behavior**:
- Division by zero handled
- Field returns `null`
- Condition does not match

**Handling**:
```python
def _get_field_value(campaign, field):
    computed_fields = {
        "cpa": lambda c: (c.total_spend_cents / c.conversions / 100)
                         if c.conversions > 0 else None,
        "cpc": lambda c: (c.total_spend_cents / c.clicks / 100)
                         if c.clicks > 0 else None,
    }

    if field in computed_fields:
        try:
            return computed_fields[field](campaign)
        except (ZeroDivisionError, TypeError):
            return None
```

**Response**:
```json
{
  "campaign_id": 101,
  "campaign_name": "New Campaign",
  "matched": false,
  "reason": "Field 'cpa' not found or null"
}
```

---

### 4. Invalid Condition Value Type

**Scenario**: Condition value can't be parsed to expected type.

**Behavior**:
- Parse attempt fails
- Evaluation returns no match with error

**Response**:
```json
{
  "campaign_id": 101,
  "campaign_name": "Summer Sale 2024",
  "matched": false,
  "reason": "Invalid condition value: could not convert 'abc' to float"
}
```

---

### 5. Slack Webhook Failure

**Scenario**: Slack webhook URL returns error.

**Behavior**:
- Condition matched, action attempted
- Action fails with webhook error
- Execution logged with failure

**Response**:
```json
{
  "action": "notify_slack",
  "success": false,
  "reason": "Webhook returned HTTP 404",
  "webhook_url": "https://hooks.slack.com/..."
}
```

---

### 6. WhatsApp Contacts Not Opted In

**Scenario**: All configured contacts have opted out.

**Behavior**:
- Filter contacts by opt-in status
- No messages sent if none opted in

**Response**:
```json
{
  "action": "notify_whatsapp",
  "success": false,
  "reason": "No opted-in contacts found",
  "contact_ids_requested": [1, 2, 3],
  "contacts_opted_in": 0
}
```

---

### 7. WhatsApp Template Not Found

**Scenario**: Configured template doesn't exist or not approved.

**Behavior**:
- WhatsApp API returns template error
- Message not sent

**Response**:
```json
{
  "action": "notify_whatsapp",
  "success": false,
  "reason": "Template 'invalid_template' not found or not approved",
  "error_code": "131045"
}
```

---

### 8. Budget Adjustment with No Current Budget

**Scenario**: Adjust budget rule triggered but campaign has no daily budget set.

**Behavior**:
- Check for existing budget
- Skip adjustment if no budget

**Response**:
```json
{
  "action": "adjust_budget",
  "success": false,
  "reason": "No daily budget set",
  "campaign_id": 101
}
```

---

### 9. Duplicate Label Application

**Scenario**: Apply label rule triggered but label already exists.

**Behavior**:
- Check existing labels
- Skip if already applied
- Still count as successful

**Handling**:
```python
if action == RuleAction.APPLY_LABEL:
    label = config.get("label", "flagged")
    if label not in campaign.labels:
        campaign.labels = campaign.labels + [label]
    return {"action": "apply_label", "label": label, "success": True}
```

---

### 10. Rule Status Changed Mid-Evaluation

**Scenario**: Rule paused while batch evaluation in progress.

**Behavior**:
- Check status at start of evaluation
- Continue current evaluation
- Won't trigger on next cycle

**Handling**:
```python
async def evaluate_rule(rule, dry_run=False):
    # Check at evaluation start
    if rule.status != RuleStatus.ACTIVE and not dry_run:
        return {"status": "skipped", "reason": "Rule not active"}

    # Continue with evaluation...
```

---

### 11. Campaign Deleted During Execution

**Scenario**: Campaign soft-deleted between condition check and action.

**Behavior**:
- Action attempts on deleted campaign
- Database constraint prevents modification
- Execution logged with error

**Response**:
```json
{
  "campaign_id": 101,
  "matched": true,
  "action_result": {
    "action": "pause_campaign",
    "success": false,
    "reason": "Campaign not found or deleted"
  }
}
```

---

### 12. Circular Rule Effects

**Scenario**: Rule A pauses campaign, Rule B enables campaign with ROAS > 0.

**Behavior**:
- Both rules may trigger alternately
- Cooldown prevents rapid toggling
- Consider rule priority or mutual exclusion

**Mitigation**:
- Set appropriate cooldown periods
- Use more specific conditions
- Consider rule priorities (not currently implemented)

---

### 13. High Volume Rule Evaluation

**Scenario**: Tenant has 1000+ campaigns, rule evaluates all.

**Behavior**:
- Evaluation runs in single transaction
- May cause performance issues

**Mitigation**:
```python
# Batch processing
async def evaluate_rule_batched(rule, batch_size=100):
    campaigns = await get_applicable_campaigns(rule)

    for i in range(0, len(campaigns), batch_size):
        batch = campaigns[i:i + batch_size]
        await process_batch(rule, batch)
        await asyncio.sleep(0.1)  # Rate limiting
```

---

## Known Limitations

### 1. No Real-Time Evaluation

**Limitation**: Rules evaluated on schedule (every 15 minutes).

**Impact**: Changes may take up to 15 minutes to trigger rules.

**Workaround**: Manual rule test available for immediate evaluation.

---

### 2. No Rule Priority

**Limitation**: All rules evaluated equally, no priority ordering.

**Impact**: Conflicting rules may produce inconsistent results.

**Planned**: Add priority field for evaluation order.

---

### 3. Single Condition Per Rule

**Limitation**: Rules support only one condition.

**Impact**: Complex conditions require multiple rules.

**Planned**: Add compound conditions (AND/OR).

---

### 4. No Historical Trend Conditions

**Limitation**: Conditions evaluate current values only.

**Impact**: Cannot express "ROAS decreased by 20% week-over-week".

**Workaround**: Use `condition_duration_hours` for time-based thresholds.

---

### 5. Limited Action Chaining

**Limitation**: Cannot chain multiple actions in one rule.

**Impact**: Complex workflows require multiple rules.

**Planned**: Add action sequences.

---

## Error Recovery

### Evaluation Failures

| Error | Recovery |
|-------|----------|
| Database unavailable | Retry with exponential backoff |
| Campaign not found | Skip campaign, log warning |
| Invalid field | Log error, continue evaluation |
| Action failure | Log failure, continue to next campaign |

### Action Failures

| Action | Error | Recovery |
|--------|-------|----------|
| pause_campaign | Platform API error | Log failure, manual intervention |
| adjust_budget | No budget set | Skip, log warning |
| notify_slack | Webhook failure | Log failure, consider retry |
| notify_whatsapp | API error | Log failure, check template/contacts |

---

## Monitoring

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| Rule evaluation success rate | < 95% |
| Average evaluation time | > 30 seconds |
| Action success rate | < 90% |
| Webhook failure rate | > 10% |
| WhatsApp delivery rate | < 80% |

### Health Checks

```python
async def rules_engine_health():
    return {
        "status": "healthy",
        "checks": {
            "database": await check_db(),
            "active_rules": await count_active_rules(),
            "last_evaluation": await get_last_evaluation_time(),
            "failed_executions_24h": await count_failed_executions(hours=24),
            "slack_webhooks": await check_webhook_health(),
            "whatsapp_api": await check_whatsapp_health()
        }
    }
```

---

## Best Practices

### Rule Design

1. Use specific conditions to avoid false positives
2. Set appropriate cooldown periods (24+ hours)
3. Test rules with dry-run before activating
4. Start with advisory actions (labels, alerts) before destructive ones

### Performance

1. Limit rule scope when possible (specific platforms/campaigns)
2. Use reasonable condition durations (avoid <1 hour)
3. Monitor execution times for complex rules

### Notifications

1. Verify webhook URLs before activation
2. Ensure WhatsApp contacts are opted in
3. Use templates for WhatsApp to ensure delivery

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
