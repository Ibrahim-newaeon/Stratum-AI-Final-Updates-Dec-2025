# AI Logic Formulas (Pseudo-code)
Audience: Engineering + Analytics team. Built for Meta + Google + TikTok + Snapchat with GA4 as source-of-truth.

## 0) Shared inputs and naming

**Entities**
- platform in {"meta","google","tiktok","snap"}
- date in YYYY-MM-DD
- entity_level in {"account","campaign","adset_adgroup","creative","audience"}

**Core daily metrics**
- spend
- impressions
- clicks
- sessions (GA4)
- add_to_cart
- purchases
- revenue
- leads
- cpa = spend / max(conversions, 1)
- roas = revenue / max(spend, 1)
- cvr = conversions / max(clicks, 1)
- ctr = clicks / max(impressions, 1)
- cpm = (spend / max(impressions, 1)) * 1000
- frequency (if provided by platform)

**Quality / signal metrics**
- emq_score (0..100) if available
- event_loss_pct (0..100)
- attribution_variance_pct (see section 5)

**Time windows**
- today = D0
- baseline = last 7 complete days (D-7..D-1)
- trend = last 14 complete days (D-14..D-1)

---

## 1) Scaling Score (single number to rank opportunities)

Goal: Score each entity for "scale" vs "fix" in a consistent way.

```
function scaling_score(entity, D0):
  base = metrics(entity, baseline)
  today = metrics(entity, D0)

  # Normalize deltas vs baseline
  d_roas = pct_change(today.roas, base.roas)
  d_cpa  = pct_change(today.cpa,  base.cpa)   # lower is better
  d_cvr  = pct_change(today.cvr,  base.cvr)
  d_ctr  = pct_change(today.ctr,  base.ctr)

  # Risk penalties
  freq_penalty = clamp01( (today.frequency - freq_target(entity)) / freq_target(entity) )
  emq_penalty  = clamp01( (emq_target - today.emq_score) / emq_target )  # if emq_score missing -> 0
  vol_penalty  = clamp01( min_required_conversions(entity) / max(today.conversions, 1) )

  # Score components (weights tuned for e-commerce ROAS)
  score = 0
  score += 0.45 * clamp(-1, 1, d_roas)
  score += 0.25 * clamp(-1, 1, -d_cpa)        # invert CPA delta
  score += 0.20 * clamp(-1, 1, d_cvr)
  score += 0.10 * clamp(-1, 1, d_ctr)

  # Apply penalties (reduce score)
  score = score * (1 - 0.25*freq_penalty) * (1 - 0.20*emq_penalty) * (1 - 0.15*vol_penalty)

  return score
```

**Interpretation**
- score >= +0.25: scale candidate
- -0.25 < score < +0.25: stable / watch
- score <= -0.25: fix or pause candidate

---

## 2) Budget Reallocation (daily)

Goal: Move budget from underperformers to winners while limiting risk.

```
function reallocate_budget(account, D0):
  entities = list_entities(account, level="campaign")

  winners = []
  losers  = []

  for e in entities:
    s = scaling_score(e, D0)

    if s >= +0.25 and e.spend_today > min_spend:
      winners.append(e)
    if s <= -0.25 and e.spend_today > min_spend:
      losers.append(e)

  # Determine safe amount to move (cap to avoid oscillation)
  move_pool = sum( min(e.spend_today * 0.20, max_move_per_entity) for e in losers )

  # Distribute to winners proportional to score and capacity
  total_weight = sum( max(0.01, scaling_score(w, D0)) for w in winners )

  actions = []
  for w in winners:
    share = max(0.01, scaling_score(w, D0)) / max(total_weight, 0.01)
    inc = move_pool * share
    inc = min(inc, w.spend_today * 0.30)  # cap increases
    actions.append({ "entity": w.id, "action": "increase_budget", "amount": round(inc, 2) })

  for l in losers:
    dec = min(l.spend_today * 0.20, max_move_per_entity)
    actions.append({ "entity": l.id, "action": "decrease_budget", "amount": round(dec, 2) })

  return actions
```

**Guardrails**
- Never shift more than 10-20% of total daily spend per day.
- Respect learning phases (Meta/TikTok). If "learning" and spend < stable_threshold -> reduce aggressiveness.
- If EMQ degraded (section 6), suspend automation.

---

## 3) Creative Fatigue Score

Goal: Detect when a creative is losing efficiency due to overexposure.

```
function creative_fatigue(creative, D0):
  base = metrics(creative, baseline)
  today = metrics(creative, D0)

  # Signals (typical patterns: CTR down, CPA up, ROAS down, frequency up)
  ctr_drop  = clamp01( (base.ctr - today.ctr) / max(base.ctr, 0.0001) )
  roas_drop = clamp01( (base.roas - today.roas) / max(base.roas, 0.01) )
  cpa_rise  = clamp01( (today.cpa - base.cpa) / max(base.cpa, 0.01) )

  # Exposure factor (platform-provided frequency preferred; else approximate via impressions / unique reach)
  expo = clamp01( (today.frequency - 2.0) / 3.0 )  # 2->5 maps to 0..1

  fatigue = 0.35*ctr_drop + 0.35*roas_drop + 0.20*cpa_rise + 0.10*expo

  # Smooth with 3-day EMA to avoid noise
  fatigue = ema(fatigue, prev_ema(creative), alpha=0.4)

  return fatigue  # 0..1
```

**Interpretation**
- fatigue >= 0.65: refresh creative (new hook/visual)
- 0.45..0.65: watch, rotate variants
- < 0.45: healthy

---

## 4) Anomaly Detection (Spend/ROAS/CPA)

Goal: Catch "something broke" early.

```
function anomaly_zscore(metric_series, D0, window=14):
  x = value(metric_series, D0)
  mu = mean(metric_series[D0-window .. D0-1])
  sd = std(metric_series[D0-window .. D0-1])
  if sd <= epsilon: return 0
  return (x - mu) / sd

function detect_anomalies(account, D0):
  anomalies = []
  for m in ["spend","revenue","roas","cpa","conversions","event_loss_pct","emq_score"]:
    z = anomaly_zscore(series(account,m), D0)
    if abs(z) >= 2.5:
      anomalies.append({ "metric": m, "z": round(z,2), "severity": severity(abs(z)) })
  return anomalies
```

---

## 5) Attribution Variance (platform vs GA4)

Goal: quantify divergence; helps explain "platform says X but GA4 says Y".

```
function attribution_variance(entity, D0):
  # platform-reported conversions/revenue
  p_rev = platform_revenue(entity, D0)
  p_conv = platform_conversions(entity, D0)

  # GA4-attributed (use your chosen model: data-driven, last click, or blended)
  g_rev = ga4_revenue(entity, D0)
  g_conv = ga4_conversions(entity, D0)

  rev_var = (p_rev - g_rev) / max(g_rev, 1)
  conv_var = (p_conv - g_conv) / max(g_conv, 1)

  return { "rev_var_pct": 100*rev_var, "conv_var_pct": 100*conv_var }
```

**Use**
- If abs(rev_var_pct) > 30% consistently: show an "Attribution Noise" banner.

---

## 6) EMQ / Signal Health Logic (degrade + auto-resolve)

Goal: stop automation when data quality is compromised.

```
function signal_health(account, D0):
  emq = emq_score(account, D0)          # 0..100
  loss = event_loss_pct(account, D0)    # 0..100
  api_ok = api_health(account, D0)      # boolean

  # thresholds
  if api_ok == false: return "critical"
  if emq < 80 or loss > 10: return "degraded"
  if emq < 90 or loss > 5:  return "risk"
  return "healthy"

function auto_resolve(account, D0):
  status = signal_health(account, D0)
  if status in {"critical","degraded"}:
    suspend_automation(account)
    create_alert("emq_degraded", severity="high")
    run_diagnostics_playbook(account)
```

---

## 7) Daily Recommendations Generator (human-readable)

Goal: turn math into actions.

```
function recommendations(account, D0):
  recs = []
  anomalies = detect_anomalies(account, D0)
  if any(a.metric in {"event_loss_pct","emq_score"} and a.severity >= "high" for a in anomalies):
    recs.append("Data quality issue detected: pause automation and check pixel/CAPI.")
    return recs

  # 1) Budget moves
  actions = reallocate_budget(account, D0)
  recs += summarize_actions(actions)

  # 2) Creative refresh list
  fatigued = top_creatives_by(creative_fatigue, threshold=0.65)
  recs += [f"Refresh creative {c.id} (fatigue {creative_fatigue(c,D0):.2f})." for c in fatigued]

  # 3) Fix list
  fixes = bottom_entities_by(scaling_score, threshold=-0.25)
  recs += [f"Investigate {e.name}: ROAS down / CPA up vs baseline." for e in fixes]

  return recs
```

---

## 8) Helper functions

```
function pct_change(new, old):
  return (new - old) / max(abs(old), 1e-9)

function clamp01(x): return max(0, min(1, x))
function clamp(a,b,x): return max(a, min(b, x))

function ema(x, prev, alpha):
  return alpha*x + (1-alpha)*prev
```
