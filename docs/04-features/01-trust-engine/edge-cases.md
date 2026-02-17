# Trust Engine Edge Cases

## Overview

This document covers error handling, edge cases, and known limitations for the Trust Engine feature.

---

## Edge Cases

### 1. Missing EMQ Data

**Scenario**: Platform EMQ scores are not available (new account, API issues).

**Behavior**:
- System uses default EMQ score of 75.0
- Issue added: "No EMQ data available - using default score"
- Does not block automation

**Handling**:
```python
if not emq_scores:
    issues.append("No EMQ data available - using default score")
    return 75.0  # Default moderate score
```

**User Impact**: Trust banner shows info message suggesting EMQ check.

---

### 2. Stale Data (No Recent Sync)

**Scenario**: Data sync hasn't run for > 48 hours.

**Behavior**:
- Freshness score drops to 0
- Status transitions to DEGRADED or CRITICAL
- Automation may be blocked

**Handling**:
```python
if age_hours >= stale_data_age_hours:  # 48 hours
    issues.append(f"Data is stale ({age_hours:.1f}h old)")
    return 0.0
```

**Thresholds**:
| Data Age | Freshness Score |
|----------|-----------------|
| < 24 hours | 100 |
| 24-48 hours | Linear decay (100→0) |
| > 48 hours | 0 |

**User Impact**: Critical banner with recommendation to check data sync.

---

### 3. Extreme Attribution Variance

**Scenario**: Platform reports $10,000 revenue, GA4 reports $0.

**Behavior**:
- Variance calculated as 100%
- Variance score drops significantly
- May trigger HOLD on budget actions

**Handling**:
```python
if ga4_revenue > 0:
    variance = abs(platform_revenue - ga4_revenue) / ga4_revenue
elif platform_revenue > 0:
    variance = 1.0  # 100% variance
else:
    variance = 0.0  # Both zero = no variance
```

**User Impact**: High-priority banner recommending attribution review.

---

### 4. All Platforms Critical

**Scenario**: All connected platforms have critical signal health.

**Behavior**:
- Overall status: CRITICAL
- Automation: FROZEN
- Only `pause_all` and `emergency_stop` actions allowed

**Handling**:
```python
if all(p.status == "critical" for p in platforms):
    autopilot_mode = "frozen"
    automation_allowed = False
```

**User Impact**: Full-page alert with manual intervention required message.

---

### 5. New Account (No Historical Data)

**Scenario**: Account has < 7 days of data.

**Behavior**:
- Anomaly detection uses default score of 90.0
- Historical variance calculation limited
- Conservative thresholds applied

**Handling**:
```python
if len(historical_metrics) < 7:
    return 90.0  # Default good score with insufficient data
```

**User Impact**: Info banner explaining limited historical analysis.

---

### 6. Single Platform Connected

**Scenario**: Only one ad platform is connected.

**Behavior**:
- EMQ score based on single platform
- Cross-platform variance not applicable
- Overall score calculation adjusted

**Handling**: Weights redistributed based on available data sources.

---

### 7. CDP Data Not Available

**Scenario**: CDP is not integrated or has no data.

**Behavior**:
- CDP EMQ component excluded from calculation
- Base weights (EMQ, Freshness, Variance, Anomaly) used at full values
- Recommendation to integrate CDP (if decision is not PASS)

**Handling**:
```python
def get_weights(self, include_cdp: bool = False) -> Dict[str, float]:
    if not include_cdp:
        return {
            "emq": 0.40,
            "freshness": 0.25,
            "variance": 0.20,
            "anomaly": 0.15,
            "cdp": 0.0,
        }
```

**User Impact**: No impact on score; optional recommendation shown.

---

### 8. Conflicting Component Scores

**Scenario**: EMQ excellent (95), but Variance critical (20).

**Behavior**:
- Weighted composite calculated
- Individual component issues highlighted
- Specific recommendations provided

**Example**:
```
Overall Score: (95 × 0.40) + (100 × 0.25) + (20 × 0.20) + (85 × 0.15) = 79.75
Status: healthy
Issues: ["High attribution variance: 18.5%"]
```

**User Impact**: Component breakdown helps identify specific issues.

---

### 9. High-Risk Action During Degraded Health

**Scenario**: User requests `increase_budget` when signal health is 65.

**Behavior**:
- Action requires 80+ threshold (high-risk)
- Current score: 65 (below 80)
- Decision: HOLD

**Gate Logic**:
```python
if action_type in high_risk_actions:
    threshold = 80.0
else:
    threshold = 70.0

if score >= threshold:
    decision = GateDecision.PASS
elif score >= 40:
    decision = GateDecision.HOLD
else:
    decision = GateDecision.BLOCK
```

**User Impact**: Action queued for manual review with explanation.

---

### 10. Concurrent Trust Gate Evaluations

**Scenario**: Multiple automation actions evaluated simultaneously.

**Behavior**:
- Each action evaluated independently
- Signal health snapshot used for all
- Audit log entries created for each

**Handling**: Batch evaluation supported:
```python
def evaluate_batch(
    self,
    signal_health: SignalHealth,
    actions: List[AutomationAction],
) -> List[TrustGateResult]:
    return [self.evaluate(signal_health, action) for action in actions]
```

---

### 11. Override During Critical Health

**Scenario**: User attempts to override a BLOCK decision during critical health.

**Behavior**:
- Override denied
- Audit log records attempted override
- Alert sent to admin

**Handling**:
```python
if signal_health.status == "critical":
    raise PermissionError("Cannot override during critical signal health")
```

**User Impact**: Error message explaining critical status prevents override.

---

### 12. Timezone Edge Cases

**Scenario**: Data freshness calculation across timezone boundaries.

**Behavior**:
- All timestamps stored in UTC
- Freshness calculated from `datetime.utcnow()`
- User-facing times converted to tenant timezone

**Handling**: Consistent UTC storage and calculation.

---

## Error Handling

### API Errors

| Error | HTTP Code | Handling |
|-------|-----------|----------|
| Feature not enabled | 403 | Return error with feature name |
| Tenant access denied | 403 | Return access denied message |
| Invalid date parameter | 400 | Return validation error |
| Audit log not found | 404 | Return not found error |
| Database timeout | 500 | Retry with exponential backoff |

### Calculation Errors

| Error | Handling | Fallback |
|-------|----------|----------|
| Division by zero | Catch and handle | Return neutral score |
| Missing component | Use default | Component-specific default |
| Invalid score range | Clamp to 0-100 | `max(0, min(100, score))` |

### Recovery Strategies

```python
try:
    score = calculate_component(data)
except Exception as e:
    logger.error(f"Component calculation failed: {e}")
    score = DEFAULT_SCORE  # Safe fallback
    issues.append(f"Calculation error: using default")
```

---

## Known Limitations

### 1. Score Calculation Lag

**Limitation**: Signal health may lag behind real-time data by up to 15 minutes.

**Reason**: EMQ scores from platforms have inherent reporting delays.

**Mitigation**: Users informed via "Last updated" timestamp.

---

### 2. Cross-Platform Variance

**Limitation**: Attribution models differ between platforms, causing inherent variance.

**Reason**: Meta uses 7-day click, 1-day view; Google uses different windows.

**Mitigation**: Variance thresholds account for expected discrepancies.

---

### 3. Anomaly Detection Sensitivity

**Limitation**: May flag legitimate business changes as anomalies.

**Reason**: Z-score based detection doesn't understand business context.

**Mitigation**:
- Use historical context (7+ days)
- Allow manual override with reason
- Adjust threshold via configuration

---

### 4. EMQ Score Granularity

**Limitation**: Platform EMQ is event-level, not account-level.

**Reason**: Different events may have different match quality.

**Mitigation**: Use weighted average across events.

---

### 5. Historical Data Dependency

**Limitation**: Full functionality requires 7+ days of historical data.

**Reason**: Anomaly detection and trend analysis need baseline.

**Mitigation**: Progressive feature enablement as data accumulates.

---

## Monitoring & Alerts

### Health Check Failures

| Metric | Alert Threshold | Action |
|--------|-----------------|--------|
| Signal health rollup failure | 3 consecutive | Page on-call |
| EMQ fetch timeout | > 5 minutes | Check platform API |
| Freshness > 48h | Any tenant | Warning notification |
| Critical status | Any tenant | Immediate alert |

### Audit Log Retention

| Data Type | Retention | Archive |
|-----------|-----------|---------|
| Audit logs | 90 days | S3 archive |
| Signal health history | 365 days | S3 archive |
| Override logs | 2 years | Required for compliance |

---

## Testing Edge Cases

### Unit Test Coverage

```python
# Test cases for edge scenarios
def test_missing_emq_data():
    result = calculator.calculate(emq_scores=None)
    assert result.emq_score == 75.0
    assert "No EMQ data available" in result.issues

def test_stale_data():
    old_time = datetime.utcnow() - timedelta(hours=50)
    result = calculator.calculate(last_data_received=old_time)
    assert result.freshness_score == 0.0
    assert result.status == "critical"

def test_extreme_variance():
    result = calculator.calculate(
        platform_revenue=10000.0,
        ga4_revenue=0.0
    )
    assert result.variance_score < 30.0

def test_high_risk_action_hold():
    result = gate.evaluate(
        signal_health=SignalHealth(overall_score=65),
        action=AutomationAction(action_type="increase_budget")
    )
    assert result.decision == GateDecision.HOLD
```

### Integration Test Scenarios

1. Full cycle: healthy → degraded → critical → recovery
2. Multi-platform with mixed health
3. Override flow with audit logging
4. Batch action evaluation
5. Concurrent evaluations

---

## Related Documentation

- [Specification](./spec.md)
- [User Flows](./user-flows.md)
- [API Contracts](./api-contracts.md)
- [Monitoring Runbook](../../05-operations/runbooks.md)
