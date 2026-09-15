"use client";

import { useEffect, useState } from "react";
import { getTraces } from "@/lib/api";

export default function TracesPage() {
  const [traces, setTraces] = useState<Array<Record<string, unknown>>>([]);

  useEffect(() => {
    getTraces().then(setTraces).catch(() => setTraces([]));
  }, []);

  return (
    <div>
      <div className="kicker">/ LANGSMITH / TRACES</div>
      <h1 className="title">Request trace history</h1>
      <div className="glass-panel form-box">
        <table className="table">
          <thead>
            <tr>
              <th>Request ID</th>
              <th>Initial model</th>
              <th>Final model</th>
              <th>Confidence</th>
              <th>Reason</th>
            </tr>
          </thead>
          <tbody>
            {traces.length === 0 ? (
              <tr><td colSpan={5}>No trace metadata available yet.</td></tr>
            ) : (
              traces.slice(0, 12).map((trace, index) => (
                <tr key={`${String(trace.request_id ?? "trace")}-${index}`}>
                  <td>{String(trace.request_id ?? "--")}</td>
                  <td>{String(trace.initial_model ?? "--")}</td>
                  <td>{String(trace.final_model ?? "--")}</td>
                  <td>{Number(trace.confidence ?? 0).toFixed(2)}</td>
                  <td>{String(trace.escalation_reason ?? "--")}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
