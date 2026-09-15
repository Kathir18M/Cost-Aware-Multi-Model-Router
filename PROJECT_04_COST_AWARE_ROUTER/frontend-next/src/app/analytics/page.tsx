"use client";

import { useEffect, useState } from "react";
import { getAnalytics, type DashboardData } from "@/lib/api";
import { formatCost, formatPercent } from "@/lib/format";

export default function AnalyticsPage() {
  const [data, setData] = useState<DashboardData | null>(null);

  useEffect(() => {
    getAnalytics().then(setData).catch(() => setData(null));
  }, []);

  if (!data) {
    return (
      <div>
        <div className="kicker">/ ANALYTICS</div>
        <h1 className="title">Cost and model analytics</h1>
        <div className="glass-panel form-box">
          <p className="subtitle">Loading backend analytics...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="kicker">/ ANALYTICS</div>
      <h1 className="title">Cost and model analytics</h1>
      <div className="result-grid">
        <div className="metric-card glass-panel"><div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Total requests</div><div style={{ fontSize: 28, fontWeight: 700 }}>{data.total_requests}</div></div>
        <div className="metric-card glass-panel"><div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Average confidence</div><div style={{ fontSize: 28, fontWeight: 700 }}>{(data.average_confidence ?? 0).toFixed(2)}</div></div>
        <div className="metric-card glass-panel"><div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Avg latency</div><div style={{ fontSize: 28, fontWeight: 700 }}>{(data.average_latency ?? 0).toFixed(2)}s</div></div>
        <div className="metric-card glass-panel"><div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Savings %</div><div style={{ fontSize: 28, fontWeight: 700 }}>{formatPercent(data.savings_percentage ?? 0)}</div></div>
        <div className="metric-card glass-panel"><div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Cost</div><div style={{ fontSize: 28, fontWeight: 700 }}>{formatCost(data.total_cost ?? 0)}</div></div>
        <div className="metric-card glass-panel"><div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Baseline</div><div style={{ fontSize: 28, fontWeight: 700 }}>{formatCost(data.baseline_cost ?? 0)}</div></div>
      </div>

      <div className="glass-panel form-box" style={{ marginTop: 24 }}>
        <div className="kicker">/ EVENT FEED</div>
        <table className="table">
          <thead>
            <tr>
              <th>Request</th>
              <th>Initial</th>
              <th>Final</th>
              <th>Confidence</th>
              <th>Escalation</th>
            </tr>
          </thead>
          <tbody>
            {(data.events ?? []).slice(0, 8).map((event, index) => (
              <tr key={`${event.request_id ?? index}`}>
                <td>{String(event.request_id ?? "unknown")}</td>
                <td>{String(event.initial_model ?? "--")}</td>
                <td>{String(event.final_model ?? "--")}</td>
                <td>{Number(event.confidence ?? 0).toFixed(2)}</td>
                <td>{event.escalation_reason ? String(event.escalation_reason) : "--"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
