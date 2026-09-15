"use client";

import { useEffect, useState } from "react";
import { getLogs, type LogsItem } from "@/lib/api";

export default function LogsPage() {
  const [logs, setLogs] = useState<LogsItem[]>([]);

  useEffect(() => {
    getLogs().then(setLogs).catch(() => setLogs([]));
  }, []);

  return (
    <div>
      <div className="kicker">/ LOGS</div>
      <h1 className="title">Request history</h1>
      <div className="glass-panel form-box">
        <table className="table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Request</th>
              <th>Initial</th>
              <th>Final</th>
              <th>Confidence</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 ? (
              <tr><td colSpan={6}>No router events recorded yet.</td></tr>
            ) : (
              logs.slice(0, 12).map((log, index) => (
                <tr key={`${log.request_id ?? "event"}-${index}`}>
                  <td>{log.timestamp ? new Date(log.timestamp).toLocaleString() : "--"}</td>
                  <td>{log.request_id ?? "--"}</td>
                  <td>{log.initial_model ?? "--"}</td>
                  <td>{log.final_model ?? "--"}</td>
                  <td>{Number(log.confidence ?? 0).toFixed(2)}</td>
                  <td>{log.status ?? (log.escalation_reason ? "escalated" : "ok")}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
