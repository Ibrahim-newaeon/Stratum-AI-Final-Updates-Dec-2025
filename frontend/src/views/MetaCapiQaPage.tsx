/**
 * Meta CAPI QA Dashboard
 * Real-time monitoring of Meta Conversion API event quality
 * Consumes:
 *   - /api/v1/meta/capi/qa/summary
 *   - /api/v1/meta/capi/qa/event-breakdown
 *   - /api/v1/meta/capi/qa/errors
 *   - /api/v1/meta/capi/qa/dedupe
 *   - /api/v1/meta/capi/qa/diagnostics
 */

import React, { useEffect, useMemo, useState } from "react";
import { FixModal } from "@/components/emq/FixModal";

type QaSummaryPoint = {
  day: string;
  events: number;
  avg_score: number;
  success_rate: number; // 0..1
  events_received: number;
  coverage: {
    em: number; ph: number; external_id: number;
    fbp: number; fbc: number; ip: number; ua: number;
  };
};

type QaSummaryResponse = {
  tenant_id: number;
  from: string;
  to: string;
  event_name: string | null;
  platform: string | null;
  series: QaSummaryPoint[];
};

type QaEventBreakdownItem = {
  event_name: string;
  events: number;
  avg_score: number;
  success_rate: number;
  events_received: number;
  coverage: {
    em: number; ph: number; external_id: number;
    fbp: number; fbc: number; ip: number; ua: number;
  };
};

type QaEventBreakdownResponse = {
  tenant_id: number;
  from: string;
  to: string;
  platform: string | null;
  items: QaEventBreakdownItem[];
};

type QaErrorsItem = {
  code: number | null;
  message: string | null;
  count: number;
  last_seen: string | null;
};

type QaErrorsResponse = {
  tenant_id: number;
  from: string;
  to: string;
  event_name: string | null;
  platform: string | null;
  items: QaErrorsItem[];
};

type QaDedupeResponse = {
  tenant_id: number;
  from: string;
  to: string;
  event_name: string | null;
  platform: string | null;
  window_minutes: number;
  total: number;
  unique_event_ids: number;
  duplicate_rows: number;
  duplicate_rate: number; // 0..1
  top_duplicates: Array<{ event_id: string; count: number; first_seen: string | null; last_seen: string | null }>;
};

type QaDiagnosticsResponse = {
  tenant_id: number;
  from: string;
  to: string;
  event_name: string | null;
  platform: string | null;
  series_points: number;
  alerts: Array<{
    severity: "info" | "warning" | "critical";
    title: string;
    metric: string;
    current: number;
    previous: number;
    delta: number;
    recommendation: string;
    day: string;
    compare_to: string;
  }>;
  series_tail: any[];
};

function fmtPct(v: number) {
  return `${Math.round(v * 100)}%`;
}
function fmt1(v: number) {
  return Math.round(v * 10) / 10;
}

async function fetchJson<T>(url: string): Promise<T> {
  const token = localStorage.getItem("access_token");
  const headers: HeadersInit = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(url, { credentials: "include", headers });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return res.json();
}

function todayISO() {
  const d = new Date();
  return d.toISOString().slice(0, 10);
}
function daysAgoISO(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

/** Tiny "sparkline" using div bars */
function SparkBars({ values }: { values: number[] }) {
  const max = Math.max(1, ...values);
  return (
    <div style={{ display: "flex", gap: 2, alignItems: "flex-end", height: 28 }}>
      {values.map((v, i) => (
        <div
          key={i}
          title={`${v}`}
          style={{
            width: 6,
            height: `${Math.round((v / max) * 28)}px`,
            borderRadius: 2,
            background: "rgba(255,255,255,0.5)",
          }}
        />
      ))}
    </div>
  );
}

export default function MetaCapiQaPage() {
  const [from, setFrom] = useState(daysAgoISO(14));
  const [to, setTo] = useState(todayISO());
  const [eventName, setEventName] = useState<string>(""); // optional filter
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string>("");
  const [fixModalOpen, setFixModalOpen] = useState(false);

  const [summary, setSummary] = useState<QaSummaryResponse | null>(null);
  const [breakdown, setBreakdown] = useState<QaEventBreakdownResponse | null>(null);
  const [errors, setErrors] = useState<QaErrorsResponse | null>(null);
  const [dedupe, setDedupe] = useState<QaDedupeResponse | null>(null);
  const [diag, setDiag] = useState<QaDiagnosticsResponse | null>(null);

  const base = "/api/v1/meta/capi/qa";

  const query = useMemo(() => {
    const p = new URLSearchParams();
    p.set("from", from);
    p.set("to", to);
    if (eventName.trim()) p.set("event_name", eventName.trim());
    return p.toString();
  }, [from, to, eventName]);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setErr("");

    Promise.all([
      fetchJson<QaSummaryResponse>(`${base}/summary?${query}`),
      fetchJson<QaEventBreakdownResponse>(`${base}/event-breakdown?from=${from}&to=${to}`),
      fetchJson<QaErrorsResponse>(`${base}/errors?${query}&limit=25`),
      fetchJson<QaDedupeResponse>(`${base}/dedupe?${query}&window_minutes=10&top=20`),
      fetchJson<QaDiagnosticsResponse>(`${base}/diagnostics?${query}`),
    ])
      .then(([s, b, e, d, g]) => {
        if (!alive) return;
        setSummary(s);
        setBreakdown(b);
        setErrors(e);
        setDedupe(d);
        setDiag(g);
      })
      .catch((e) => alive && setErr(e.message || String(e)))
      .finally(() => alive && setLoading(false));

    return () => {
      alive = false;
    };
  }, [query, from, to]);

  const kpis = useMemo(() => {
    const series = summary?.series ?? [];
    const totalEvents = series.reduce((a, x) => a + x.events, 0);
    const totalReceived = series.reduce((a, x) => a + x.events_received, 0);

    const avgScore =
      series.length ? series.reduce((a, x) => a + x.avg_score, 0) / series.length : 0;

    const avgSuccess =
      series.length ? series.reduce((a, x) => a + x.success_rate, 0) / series.length : 0;

    return { totalEvents, totalReceived, avgScore, avgSuccess };
  }, [summary]);

  const scoreSeries = (summary?.series ?? []).map((x) => x.avg_score);
  const successSeries = (summary?.series ?? []).map((x) => Math.round(x.success_rate * 100));
  const dayLabels = (summary?.series ?? []).map((x) => x.day.slice(5));

  return (
    <div style={{ padding: 20, color: "#fff", background: "#0b0f1a", minHeight: "100vh" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", gap: 16 }}>
        <div>
          <h1 style={{ margin: 0, fontSize: 22 }}>Meta CAPI QA</h1>
          <div style={{ opacity: 0.7, marginTop: 6 }}>
            Tenant: {summary?.tenant_id ?? "—"} • {from} → {to}
          </div>
        </div>

        <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "end" }}>
          <div>
            <div style={{ fontSize: 12, opacity: 0.7 }}>From</div>
            <input
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid #2b3554", background: "#0f1527", color: "#fff" }}
            />
          </div>
          <div>
            <div style={{ fontSize: 12, opacity: 0.7 }}>To</div>
            <input
              type="date"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid #2b3554", background: "#0f1527", color: "#fff" }}
            />
          </div>
          <div>
            <div style={{ fontSize: 12, opacity: 0.7 }}>Event filter</div>
            <input
              value={eventName}
              onChange={(e) => setEventName(e.target.value)}
              placeholder="Lead / Purchase / ..."
              style={{ padding: "8px 10px", borderRadius: 8, border: "1px solid #2b3554", background: "#0f1527", color: "#fff", width: 200 }}
            />
          </div>
          <button
            onClick={() => setFixModalOpen(true)}
            style={{
              padding: "10px 20px",
              borderRadius: 12,
              border: "none",
              background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
              color: "#fff",
              fontWeight: 600,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 8,
              boxShadow: "0 4px 14px rgba(99, 102, 241, 0.3)",
            }}
          >
            <span style={{ fontSize: 16 }}>&#9889;</span>
            One-Click Fix
          </button>
        </div>
      </div>

      {loading && <div style={{ marginTop: 16, opacity: 0.8 }}>Loading…</div>}
      {err && (
        <div style={{ marginTop: 16, padding: 12, background: "#2a1020", border: "1px solid #5d1f3a", borderRadius: 10 }}>
          <b>Error:</b> {err}
        </div>
      )}

      {/* KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(220px, 1fr))", gap: 12, marginTop: 16 }}>
        <KpiCard title="Total events logged" value={kpis.totalEvents.toLocaleString()} sub="From capi_qa_logs" />
        <KpiCard title="Meta events_received" value={kpis.totalReceived.toLocaleString()} sub="Should track close to total" />
        <KpiCard title="Avg match score" value={`${fmt1(kpis.avgScore)}/100`} sub="Coverage-based EMQ proxy" />
        <KpiCard title="Avg success rate" value={fmtPct(kpis.avgSuccess)} sub="meta_success" />
      </div>

      {/* Dedupe + Diagnostics Panels */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(380px, 1fr))", gap: 12, marginTop: 12 }}>
        <Panel title="Dedupe Health (CAPI)">
          <DedupeWidget data={dedupe} />
        </Panel>

        <Panel title="Auto Diagnostics (Root-cause)">
          <DiagnosticsWidget data={diag} />
        </Panel>
      </div>

      {/* Trend Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(380px, 1fr))", gap: 12, marginTop: 12 }}>
        <Panel title="Avg Match Score Trend">
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
            <div style={{ flex: 1 }}>
              <div style={{ opacity: 0.7, fontSize: 12, marginBottom: 6 }}>By day</div>
              <SparkBars values={scoreSeries.map((v) => Math.round(v))} />
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8, opacity: 0.7, fontSize: 11 }}>
                {dayLabels.map((d) => (
                  <span key={d}>{d}</span>
                ))}
              </div>
            </div>
            <div style={{ width: 220 }}>
              <CoverageMini summary={summary} />
            </div>
          </div>
        </Panel>

        <Panel title="Meta Success Rate Trend">
          <div style={{ opacity: 0.7, fontSize: 12, marginBottom: 6 }}>By day (percent)</div>
          <SparkBars values={successSeries} />
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginTop: 8, opacity: 0.7, fontSize: 11 }}>
            {dayLabels.map((d) => (
              <span key={d}>{d}</span>
            ))}
          </div>
        </Panel>
      </div>

      {/* Event Breakdown */}
      <div style={{ marginTop: 12 }}>
        <Panel title="Event Breakdown">
          <EventBreakdownTable items={breakdown?.items ?? []} />
        </Panel>
      </div>

      {/* Errors */}
      <div style={{ marginTop: 12 }}>
        <Panel title="Top Meta CAPI Errors">
          <ErrorsTable items={errors?.items ?? []} />
        </Panel>
      </div>

      {/* Fix Modal */}
      <FixModal
        open={fixModalOpen}
        onClose={() => setFixModalOpen(false)}
        platform="meta"
        from={from}
        to={to}
        eventName={eventName || undefined}
      />
    </div>
  );
}

function KpiCard({ title, value, sub }: { title: string; value: string; sub?: string }) {
  return (
    <div style={{ padding: 14, borderRadius: 14, background: "#0f1527", border: "1px solid #2b3554" }}>
      <div style={{ opacity: 0.7, fontSize: 12 }}>{title}</div>
      <div style={{ fontSize: 22, marginTop: 6 }}>{value}</div>
      {sub && <div style={{ opacity: 0.6, fontSize: 12, marginTop: 6 }}>{sub}</div>}
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ padding: 14, borderRadius: 14, background: "#0f1527", border: "1px solid #2b3554" }}>
      <div style={{ fontSize: 14, marginBottom: 10, opacity: 0.9 }}>{title}</div>
      {children}
    </div>
  );
}

function CoverageMini({ summary }: { summary: QaSummaryResponse | null }) {
  const last = summary?.series?.[summary.series.length - 1];
  if (!last) return <div style={{ opacity: 0.7, fontSize: 12 }}>No data</div>;

  const items: Array<[string, number]> = [
    ["em", last.coverage.em],
    ["ph", last.coverage.ph],
    ["external_id", last.coverage.external_id],
    ["fbp", last.coverage.fbp],
    ["fbc", last.coverage.fbc],
    ["ip", last.coverage.ip],
    ["ua", last.coverage.ua],
  ];

  return (
    <div>
      <div style={{ opacity: 0.7, fontSize: 12, marginBottom: 6 }}>Latest coverage</div>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 70px", gap: 6 }}>
        {items.map(([k, v]) => (
          <React.Fragment key={k}>
            <div style={{ opacity: 0.8, fontSize: 12 }}>{k}</div>
            <div style={{ textAlign: "right", fontSize: 12 }}>{fmtPct(v)}</div>
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}

function EventBreakdownTable({ items }: { items: QaEventBreakdownItem[] }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr style={{ textAlign: "left", opacity: 0.8 }}>
            <th style={th}>Event</th>
            <th style={th}>Events</th>
            <th style={th}>Avg Score</th>
            <th style={th}>Success</th>
            <th style={th}>Received</th>
            <th style={th}>em</th>
            <th style={th}>ph</th>
            <th style={th}>external</th>
            <th style={th}>fbp</th>
            <th style={th}>fbc</th>
          </tr>
        </thead>
        <tbody>
          {items.map((x) => (
            <tr key={x.event_name} style={{ borderTop: "1px solid #223055" }}>
              <td style={td}>{x.event_name}</td>
              <td style={td}>{x.events.toLocaleString()}</td>
              <td style={td}>{fmt1(x.avg_score)}</td>
              <td style={td}>{fmtPct(x.success_rate)}</td>
              <td style={td}>{x.events_received.toLocaleString()}</td>
              <td style={td}>{fmtPct(x.coverage.em)}</td>
              <td style={td}>{fmtPct(x.coverage.ph)}</td>
              <td style={td}>{fmtPct(x.coverage.external_id)}</td>
              <td style={td}>{fmtPct(x.coverage.fbp)}</td>
              <td style={td}>{fmtPct(x.coverage.fbc)}</td>
            </tr>
          ))}
          {!items.length && (
            <tr>
              <td style={td} colSpan={10}>
                <span style={{ opacity: 0.7 }}>No rows</span>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function ErrorsTable({ items }: { items: QaErrorsItem[] }) {
  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
        <thead>
          <tr style={{ textAlign: "left", opacity: 0.8 }}>
            <th style={th}>Code</th>
            <th style={th}>Message</th>
            <th style={th}>Count</th>
            <th style={th}>Last seen</th>
          </tr>
        </thead>
        <tbody>
          {items.map((x, i) => (
            <tr key={`${x.code}-${i}`} style={{ borderTop: "1px solid #223055" }}>
              <td style={td}>{x.code ?? "—"}</td>
              <td style={td}>
                <span style={{ opacity: 0.9 }}>{x.message ?? "—"}</span>
              </td>
              <td style={td}>{x.count.toLocaleString()}</td>
              <td style={td}>{x.last_seen ? new Date(x.last_seen).toLocaleString() : "—"}</td>
            </tr>
          ))}
          {!items.length && (
            <tr>
              <td style={td} colSpan={4}>
                <span style={{ opacity: 0.7 }}>No errors</span>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

const th: React.CSSProperties = { padding: "10px 8px", fontWeight: 600 };
const td: React.CSSProperties = { padding: "10px 8px", verticalAlign: "top" };

function DedupeWidget({ data }: { data: QaDedupeResponse | null }) {
  if (!data) return <div style={{ opacity: 0.7, fontSize: 12 }}>No data</div>;

  const rate = data.duplicate_rate ?? 0;
  const level =
    rate > 0.05 ? "critical" : rate > 0.02 ? "warning" : "ok";

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
        <MiniStat label="Total rows" value={data.total.toLocaleString()} />
        <MiniStat label="Unique event_id" value={data.unique_event_ids.toLocaleString()} />
        <MiniStat label="Duplicate rows" value={data.duplicate_rows.toLocaleString()} />
        <MiniStat
          label="Duplicate rate"
          value={`${Math.round(rate * 1000) / 10}%`}
          badge={level}
        />
      </div>

      <div style={{ marginTop: 10, opacity: 0.7, fontSize: 12 }}>
        Top duplicate event_id (CAPI-only)
      </div>

      <div style={{ marginTop: 8, maxHeight: 220, overflow: "auto", border: "1px solid #223055", borderRadius: 10 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ textAlign: "left", opacity: 0.8 }}>
              <th style={th}>event_id</th>
              <th style={th}>count</th>
              <th style={th}>last seen</th>
            </tr>
          </thead>
          <tbody>
            {(data.top_duplicates ?? []).map((x) => (
              <tr key={x.event_id} style={{ borderTop: "1px solid #223055" }}>
                <td style={td}><code style={{ fontSize: 11 }}>{x.event_id}</code></td>
                <td style={td}>{x.count}</td>
                <td style={td}>{x.last_seen ? new Date(x.last_seen).toLocaleString() : "—"}</td>
              </tr>
            ))}
            {!data.top_duplicates?.length && (
              <tr>
                <td style={td} colSpan={3}><span style={{ opacity: 0.7 }}>No duplicates detected</span></td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DiagnosticsWidget({ data }: { data: QaDiagnosticsResponse | null }) {
  if (!data) return <div style={{ opacity: 0.7, fontSize: 12 }}>No data</div>;

  const alerts = data.alerts ?? [];
  const critical = alerts.filter((a) => a.severity === "critical").length;
  const warning = alerts.filter((a) => a.severity === "warning").length;

  return (
    <div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
        <MiniPill label="Critical" value={critical} tone="critical" />
        <MiniPill label="Warnings" value={warning} tone="warning" />
        <MiniPill label="Alerts" value={alerts.length} tone="info" />
      </div>

      <div style={{ marginTop: 10 }}>
        {alerts.length === 0 ? (
          <div style={{ opacity: 0.7, fontSize: 12 }}>No issues detected</div>
        ) : (
          <div style={{ display: "grid", gap: 10 }}>
            {alerts.slice(0, 8).map((a, i) => (
              <div
                key={i}
                style={{
                  padding: 10,
                  borderRadius: 12,
                  border: "1px solid #223055",
                  background:
                    a.severity === "critical" ? "#2a1020" :
                    a.severity === "warning" ? "#241f10" : "#101a2a"
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 10 }}>
                  <div style={{ fontWeight: 600 }}>{a.title}</div>
                  <div style={{ opacity: 0.75, fontSize: 12 }}>
                    {a.day} vs {a.compare_to}
                  </div>
                </div>

                <div style={{ marginTop: 6, opacity: 0.85, fontSize: 12 }}>
                  <b>{a.metric}</b>: {fmtNum(a.current)} (prev {fmtNum(a.previous)} | delta {fmtNum(a.delta)})
                </div>

                <div style={{ marginTop: 6, opacity: 0.75, fontSize: 12 }}>
                  {a.recommendation}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function MiniStat({ label, value, badge }: { label: string; value: string; badge?: "ok" | "warning" | "critical" }) {
  return (
    <div style={{ padding: 10, borderRadius: 12, border: "1px solid #223055" }}>
      <div style={{ opacity: 0.7, fontSize: 12 }}>{label}</div>
      <div style={{ fontSize: 18, marginTop: 6, display: "flex", gap: 8, alignItems: "center" }}>
        <span>{value}</span>
        {badge && (
          <span
            style={{
              fontSize: 11,
              padding: "2px 8px",
              borderRadius: 999,
              border: "1px solid #223055",
              background: badge === "critical" ? "#5d1f3a" : badge === "warning" ? "#5a4a1a" : "#1a3a2a"
            }}
          >
            {badge}
          </span>
        )}
      </div>
    </div>
  );
}

function MiniPill({ label, value, tone }: { label: string; value: number; tone: "info" | "warning" | "critical" }) {
  const bg =
    tone === "critical" ? "#5d1f3a" :
    tone === "warning" ? "#5a4a1a" : "#223055";

  return (
    <div style={{ padding: "6px 10px", borderRadius: 999, border: "1px solid #223055", background: bg, fontSize: 12 }}>
      <b>{label}:</b> {value}
    </div>
  );
}

function fmtNum(x: number) {
  if (Math.abs(x) <= 1 && x !== 0) return (Math.round(x * 1000) / 1000).toString();
  return (Math.round(x * 10) / 10).toString();
}
