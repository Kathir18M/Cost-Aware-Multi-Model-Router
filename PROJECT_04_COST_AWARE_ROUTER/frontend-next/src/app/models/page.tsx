"use client";

export default function ModelsPage() {
  const models = [
    {
      name: "Gemini 1.5 Flash",
      provider: "Google",
      tier: "Primary / Fast",
      costPer1kTokens: "$0.000075",
      latency: "~150ms",
      capabilities: "General QA, Summarization, Tool Calling",
      status: "Active",
    },
    {
      name: "Mistral Small / Large",
      provider: "Mistral AI",
      tier: "Escalation Target",
      costPer1kTokens: "$0.00030",
      latency: "~320ms",
      capabilities: "Complex Reasoning, Coding, Multi-step Synthesis",
      status: "Active",
    },
  ];

  return (
    <div className="space-y-6">
      <div className="kicker">/ ROUTER MODELS</div>
      <h1 className="title">Model Registry & Capability Tiers</h1>
      <p className="subtitle">Configured language models evaluated dynamically by the cost-aware routing engine.</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {models.map((model) => (
          <div key={model.name} className="glass-panel form-box">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0 }}>{model.name}</h2>
              <span className="badge">{model.status}</span>
            </div>
            <div style={{ color: "#c4b5fd", fontSize: 13, marginBottom: 12 }}>{model.provider} • {model.tier}</div>
            <div style={{ display: "grid", gap: 8, color: "#e2e8f0", fontSize: 14 }}>
              <div><strong>Cost / 1k Tokens:</strong> {model.costPer1kTokens}</div>
              <div><strong>Avg Latency:</strong> {model.latency}</div>
              <div><strong>Capabilities:</strong> {model.capabilities}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
