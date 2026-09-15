"use client";

import { useEffect, useState } from "react";
import { getDashboard, runRouter, type DashboardData, type RouterResponse } from "@/lib/api";
import { formatCost, formatPercent } from "@/lib/format";

const defaultMetrics = [
  { label: "Total Requests", value: "--" },
  { label: "Gemini Requests", value: "--" },
  { label: "Mistral Requests", value: "--" },
  { label: "Escalation Rate", value: "--" },
  { label: "Average Confidence", value: "--" },
  { label: "Total Cost", value: "--" },
  { label: "Total Savings", value: "--" },
  { label: "Accuracy", value: "N/A" },
];

export default function Home() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [taskType, setTaskType] = useState("summarization");
  const [input, setInput] = useState("");
  const [result, setResult] = useState<RouterResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorInfo, setErrorInfo] = useState<{
    message: string;
    isProviderError?: boolean;
    retryAfter?: number | null;
  } | null>(null);

  useEffect(() => {
    getDashboard().then(setDashboard).catch(() => setError("Unable to load dashboard metrics."));
  }, []);

  const metrics = dashboard
    ? [
        { label: "Total Requests", value: String(dashboard.total_requests) },
        { label: "Gemini Requests", value: String(dashboard.gemini_requests) },
        { label: "Mistral Requests", value: String(dashboard.mistral_requests) },
        { label: "Escalation Rate", value: formatPercent(dashboard.escalation_rate * 100) },
        { label: "Average Confidence", value: (dashboard.average_confidence ?? 0).toFixed(2) },
        { label: "Total Cost", value: formatCost(dashboard.total_cost ?? 0) },
        { label: "Total Savings", value: formatCost(dashboard.total_savings ?? 0) },
        { label: "Accuracy", value: dashboard.accuracy ? `${dashboard.accuracy.toFixed(2)}%` : "N/A" },
      ]
    : defaultMetrics;

  async function handleRun() {
    setResult(null);
    setError(null);
    setErrorInfo(null);
    setLoading(true);
    try {
      const data = await runRouter({ task_type: taskType, input });
      setResult(data);
      const updatedMetrics = await getDashboard().catch(() => null);
      if (updatedMetrics) {
        setDashboard(updatedMetrics);
      }
    } catch (err: any) {
      setResult(null);
      if (err?.status === 503 || err?.data?.status === "provider_unavailable") {
        setErrorInfo({
          message: "Please check provider quota or try again later.",
          isProviderError: true,
          retryAfter: err?.data?.retry_after_seconds,
        });
      } else {
        setError(err instanceof Error ? err.message : "Unable to run router request.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="content">
      <div className="kicker">/ DASHBOARD</div>
      <h1 className="title">Route intelligence across Gemini and Mistral</h1>
      <p className="subtitle">Live cost-aware routing, escalation tracking, and model selection data from the backend runtime.</p>

      <div className="result-grid" style={{ marginBottom: 30 }}>
        {metrics.map((card) => (
          <div key={card.label} className="metric-card glass-panel">
            <div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 10 }}>{card.label}</div>
            <div style={{ fontSize: 30, fontWeight: 700 }}>{card.value}</div>
          </div>
        ))}
      </div>

      <section className="glass-panel form-box" style={{ marginBottom: 24 }}>
        <div className="kicker">/ AI ROUTER</div>
        <div style={{ display: "grid", gap: 18 }}>
          <div className="field">
            <label className="label" htmlFor="task-type">Task type</label>
            <select id="task-type" value={taskType} onChange={(e) => setTaskType(e.target.value)}>
              <option value="classification">Classification</option>
              <option value="extraction">Extraction</option>
              <option value="summarization">Summarization</option>
              <option value="qa">Q&A</option>
            </select>
          </div>

          <div className="field">
            <label className="label" htmlFor="request-input">Input</label>
            <textarea id="request-input" rows={6} placeholder="Enter your request here..." value={input} onChange={(e) => setInput(e.target.value)} />
          </div>

          {errorInfo?.isProviderError && (
            <div style={{ background: "rgba(127, 29, 29, 0.4)", border: "1px solid rgba(185, 28, 28, 0.6)", borderRadius: 12, padding: 16, display: "grid", gap: 10 }}>
              <div style={{ color: "#fca5a5", fontWeight: 700, fontSize: 13, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                ⚠️ AI PROVIDERS TEMPORARILY UNAVAILABLE
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, fontSize: 12 }}>
                <div style={{ background: "rgba(15, 23, 42, 0.8)", padding: 10, borderRadius: 8, border: "1px solid rgba(51, 65, 85, 0.8)", color: "#cbd5e1" }}>
                  <span style={{ color: "#94a3b8" }}>Gemini:</span> <span style={{ color: "#f87171", fontWeight: 600 }}>Rate limited</span>
                </div>
                <div style={{ background: "rgba(15, 23, 42, 0.8)", padding: 10, borderRadius: 8, border: "1px solid rgba(51, 65, 85, 0.8)", color: "#cbd5e1" }}>
                  <span style={{ color: "#94a3b8" }}>Mistral:</span> <span style={{ color: "#f87171", fontWeight: 600 }}>Rate limited</span>
                </div>
              </div>
              {errorInfo.retryAfter && (
                <div style={{ color: "#fbbf24", fontSize: 12, fontFamily: "monospace" }}>
                  Retry after {errorInfo.retryAfter} seconds
                </div>
              )}
              <p style={{ color: "#94a3b8", fontSize: 12, margin: 0 }}>
                {errorInfo.message}
              </p>
            </div>
          )}

          {error && !errorInfo?.isProviderError && (
            <div style={{ color: "#fca5a5", border: "1px solid rgba(248,113,113,0.25)", borderRadius: 12, padding: "10px 12px" }}>
              {error}
            </div>
          )}

          <div style={{ display: "flex", justifyContent: "flex-start" }}>
            <button type="button" className="primary-button" onClick={handleRun} disabled={loading || !input.trim()}>
              {loading ? "Running..." : "Run Request"}
            </button>
          </div>
        </div>
      </section>

      {result && (
        <section className="glass-panel form-box">
          <div className="kicker">/ ROUTING RESULT</div>
          <div className="result-grid">
            <div className="metric-card">
              <div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Initial Model</div>
              <div style={{ fontWeight: 700 }}>{result.initial_model ?? "--"}</div>
            </div>
            <div className="metric-card">
              <div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Final Model</div>
              <div style={{ fontWeight: 700 }}>{result.selected_model ?? "--"}</div>
            </div>
            <div className="metric-card">
              <div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Confidence</div>
              <div style={{ fontWeight: 700 }}>{result.confidence?.toFixed(2) ?? "0.00"}</div>
            </div>
            <div className="metric-card">
              <div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Complexity</div>
              <div style={{ fontWeight: 700 }}>{result.complexity ?? "--"}</div>
            </div>
            <div className="metric-card">
              <div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Escalated</div>
              <div style={{ fontWeight: 700 }}>{result.escalation_required ? "YES" : "NO"}</div>
            </div>
            <div className="metric-card">
              <div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Savings</div>
              <div style={{ fontWeight: 700 }}>{formatCost(result.savings ?? 0)}</div>
            </div>
          </div>

          {(result.response?.content || result.response?.answer || result.response?.summary) && (
            <div style={{ marginTop: 24, padding: "18px", borderRadius: 12, background: "rgba(15, 23, 42, 0.6)", border: "1px solid rgba(139, 92, 246, 0.3)" }}>
              <div className="kicker" style={{ color: "#a78bfa", marginBottom: 8 }}>/ RESPONSE CONTENT</div>
              <p style={{ margin: 0, color: "#f8fafc", lineHeight: 1.6 }}>
                {result.response?.content || result.response?.answer || result.response?.summary}
              </p>
            </div>
          )}
        </section>
      )}
    </main>
  );
}
