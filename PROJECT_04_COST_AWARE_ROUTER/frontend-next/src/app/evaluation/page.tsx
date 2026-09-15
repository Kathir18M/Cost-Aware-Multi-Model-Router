"use client";

import { useEffect, useState } from "react";
import { getEvaluation, type EvaluationData } from "@/lib/api";

export default function EvaluationPage() {
  const [data, setData] = useState<EvaluationData | null>(null);

  useEffect(() => {
    getEvaluation().then(setData).catch(() => setData(null));
  }, []);

  if (!data) {
    return (
      <div>
        <div className="kicker">/ EVALUATION</div>
        <h1 className="title">Held-out evaluation</h1>
        <div className="glass-panel form-box"><p className="subtitle">Loading evaluation results...</p></div>
      </div>
    );
  }

  return (
    <div>
      <div className="kicker">/ EVALUATION</div>
      <h1 className="title">Held-out evaluation</h1>
      <div className="result-grid">
        <div className="metric-card glass-panel"><div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Total cases</div><div style={{ fontSize: 28, fontWeight: 700 }}>{data.total_test_cases ?? 0}</div></div>
        <div className="metric-card glass-panel"><div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Passed</div><div style={{ fontSize: 28, fontWeight: 700 }}>{data.passed ?? 0}</div></div>
        <div className="metric-card glass-panel"><div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Failed</div><div style={{ fontSize: 28, fontWeight: 700 }}>{data.failed ?? 0}</div></div>
        <div className="metric-card glass-panel"><div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Accuracy</div><div style={{ fontSize: 28, fontWeight: 700 }}>{((data.accuracy ?? 0) * 100).toFixed(1)}%</div></div>
        <div className="metric-card glass-panel"><div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Gemini performance</div><div style={{ fontSize: 28, fontWeight: 700 }}>{((data.gemini_performance ?? 0) * 100).toFixed(1)}%</div></div>
        <div className="metric-card glass-panel"><div style={{ color: "#c4b5fd", fontSize: 12, marginBottom: 8 }}>Mistral performance</div><div style={{ fontSize: 28, fontWeight: 700 }}>{((data.mistral_performance ?? 0) * 100).toFixed(1)}%</div></div>
      </div>

      <div className="glass-panel form-box" style={{ marginTop: 24 }}>
        <div className="kicker">/ RESULTS TABLE</div>
        <table className="table">
          <thead>
            <tr>
              <th>Case</th>
              <th>Model</th>
              <th>Score</th>
              <th>Outcome</th>
            </tr>
          </thead>
          <tbody>
            {((data.records ?? []) as Array<Record<string, unknown>>).slice(0, 10).map((record, index) => (
              <tr key={`${record.case_id ?? record.request_id ?? index}`}>
                <td>{String(record.case_id ?? record.request_id ?? index + 1)}</td>
                <td>{String(record.model ?? record.final_model ?? "--")}</td>
                <td>{String(record.score ?? record.accuracy ?? "--")}</td>
                <td>{String(record.outcome ?? record.status ?? "--")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
