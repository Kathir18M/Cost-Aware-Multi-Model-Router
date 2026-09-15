"use client";

import { useEffect, useState } from "react";
import { connectConnector, disconnectConnector, listConnectors, type ConnectorStatusItem } from "@/lib/api";

export default function ConnectorsPage() {
  const [connectors, setConnectors] = useState<ConnectorStatusItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadConnectors() {
    try {
      const data = await listConnectors();
      setConnectors(data.connectors);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load connector state.");
    }
  }

  useEffect(() => {
    loadConnectors();
  }, []);

  async function toggleConnector(name: string, connected: boolean) {
    setLoading(true);
    try {
      if (connected) {
        await disconnectConnector(name);
      } else {
        await connectConnector(name);
      }
      await loadConnectors();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update connector state.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="kicker">/ MCP CONNECTORS</div>
      <h1 className="title">Connected ecosystem</h1>
      {error && (
        <div style={{ marginBottom: 18, color: "#fca5a5", border: "1px solid rgba(248,113,113,0.25)", borderRadius: 12, padding: "10px 12px" }}>
          {error}
        </div>
      )}
      <div className="result-grid">
        {connectors.map((connector) => (
          <div key={connector.id ?? connector.name} className="glass-panel form-box">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
              <strong style={{ fontSize: 22 }}>{connector.name}</strong>
              <span className="badge">{connector.connected ? "Connected" : "Not Connected"}</span>
            </div>
            {connector.account && (
              <div style={{ color: "#e2e8f0", marginBottom: 12 }}>
                {connector.account.email ?? connector.account.name ?? connector.account.login ?? "Connected user"}
              </div>
            )}
            <div style={{ color: "#cbd5e1", marginBottom: 12 }}>
              {connector.connected ? `${connector.tools.length} MCP Tools Available` : "No tools connected"}
            </div>
            <ul style={{ paddingLeft: 18, color: "#e2e8f0", display: "grid", gap: 6 }}>
              {connector.tools.length > 0 ? (
                connector.tools.map((tool) => <li key={tool}>{tool}</li>)
              ) : (
                <li>{connector.connected ? "No tools discovered yet." : "Connect to discover tools."}</li>
              )}
            </ul>
            <div style={{ marginTop: 18 }}>
              <button type="button" className="secondary-button" onClick={() => toggleConnector(connector.id ?? connector.name, connector.connected)} disabled={loading}>
                {connector.connected ? "Disconnect" : "Connect"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
