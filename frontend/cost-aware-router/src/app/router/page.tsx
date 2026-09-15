"use client";

import { useState } from "react";
import { useUser, UserButton } from "@clerk/nextjs";
import { runAgent, type AgentRunResponse } from "@/lib/api";
import { formatCost, formatPercent } from "@/lib/format";

const CATEGORIES = [
  "Coding",
  "Reasoning",
  "Summarization",
  "Extraction",
  "Classification",
  "General Q&A",
] as const;

export default function RouterPage() {
  const { user } = useUser();
  const [selectedCategory, setSelectedCategory] = useState<string>("Summarization");
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<AgentRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [errorInfo, setErrorInfo] = useState<{
    message: string;
    isProviderError?: boolean;
    retryAfter?: number | null;
  } | null>(null);

  async function runRequest() {
    if (!query.trim()) return;
    setResult(null);
    setError(null);
    setErrorInfo(null);
    setLoading(true);
    try {
      const data = await runAgent({ query: query.trim() });
      setResult(data);
    } catch (err: any) {
      setResult(null);
      if (err?.status === 503 || err?.data?.status === "provider_unavailable") {
        setErrorInfo({
          message: "Please check provider quota or try again later.",
          isProviderError: true,
          retryAfter: err?.data?.retry_after_seconds,
        });
      } else {
        setError(err instanceof Error ? err.message : "Unable to reach the backend agent API.");
      }
    } finally {
      setLoading(false);
    }
  }

  function handleCategorySelect(category: string) {
    setSelectedCategory(category);
    if (!query) {
      if (category === "Coding") {
        setQuery("Search my GitHub repositories for recent python code and analyze complexity.");
      } else if (category === "Reasoning") {
        setQuery("Compare Gemini 1.5 Flash and Mistral Small for high-throughput low-latency tasks.");
      } else if (category === "Summarization") {
        setQuery("Find my latest GitHub repository or emails and provide a 3-bullet summary.");
      } else if (category === "Extraction") {
        setQuery("Extract key metadata and structured topics from my recent Google Drive docs.");
      } else if (category === "Classification") {
        setQuery("Classify incoming request: 'Urgent system memory leak in cluster production-eu-west-1'.");
      } else {
        setQuery("What is the cost-aware model router and how does escalation work?");
      }
    }
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header Row */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Ask the AI router</h1>
          <p className="text-slate-400 text-sm mt-1">
            Cheapest capable model, evaluated and escalated only when needed.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {user ? (
            <UserButton />
          ) : (
            <div className="w-8 h-8 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-400 font-bold flex items-center justify-center text-sm">
              N
            </div>
          )}
        </div>
      </div>

      {/* Category Pills Bar */}
      <div className="flex items-center gap-2 flex-wrap pt-1">
        {CATEGORIES.map((category) => {
          const isSelected = selectedCategory === category;
          return (
            <button
              key={category}
              type="button"
              onClick={() => handleCategorySelect(category)}
              className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-150 border ${
                isSelected
                  ? "bg-slate-800 text-slate-100 border-slate-600 shadow-sm"
                  : "bg-slate-900/60 text-slate-400 border-slate-800/80 hover:text-slate-200 hover:border-slate-700"
              }`}
            >
              {category}
            </button>
          );
        })}
      </div>

      {/* Text Area Input Box */}
      <div className="bg-[#0f1420] border border-slate-800 rounded-2xl p-4 shadow-xl space-y-4">
        <textarea
          rows={5}
          maxLength={4000}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask anything — the router picks the cheapest capable model."
          className="w-full bg-transparent text-slate-100 placeholder-slate-500 resize-none outline-none border-none text-sm leading-relaxed"
        />

        {errorInfo?.isProviderError && (
          <div className="bg-red-950/40 border border-red-800/60 rounded-xl p-4 space-y-3">
            <div className="text-red-300 font-bold text-xs uppercase tracking-wider flex items-center gap-2">
              <span>⚠️ AI PROVIDERS TEMPORARILY UNAVAILABLE</span>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-slate-300">
                <span className="text-slate-400">Gemini:</span> <span className="text-red-400 font-semibold">Rate limited</span>
              </div>
              <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 text-slate-300">
                <span className="text-slate-400">Mistral:</span> <span className="text-red-400 font-semibold">Rate limited</span>
              </div>
            </div>
            {errorInfo.retryAfter && (
              <div className="text-amber-400 text-xs font-mono">
                Retry after {errorInfo.retryAfter} seconds
              </div>
            )}
            <p className="text-slate-400 text-xs m-0">
              {errorInfo.message}
            </p>
          </div>
        )}

        {error && !errorInfo?.isProviderError && (
          <div className="text-red-400 text-xs bg-red-950/40 border border-red-800/50 rounded-lg p-3">
            {error}
          </div>
        )}

        <div className="flex items-center justify-between pt-2 border-t border-slate-800/60">
          <span className="text-slate-500 text-xs font-mono">
            {query.length.toLocaleString()} / 4,000
          </span>
          <button
            type="button"
            onClick={runRequest}
            disabled={loading || !query.trim()}
            className="bg-amber-500 hover:bg-amber-400 disabled:opacity-50 disabled:hover:bg-amber-500 text-slate-950 font-bold text-xs px-5 py-2.5 rounded-xl transition-all shadow-md shadow-amber-500/10 cursor-pointer flex items-center gap-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-slate-950" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <span>Routing...</span>
              </>
            ) : (
              <span>Run router</span>
            )}
          </button>
        </div>
      </div>

      {/* Output / Response Card Area (Always visible below prompt box) */}
      <div className="bg-[#0b0f19] border border-slate-800/80 rounded-2xl p-6 min-h-[220px] flex flex-col justify-center relative shadow-lg">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-10 space-y-3">
            <div className="w-10 h-10 rounded-full border-2 border-amber-500/30 border-t-amber-500 animate-spin" />
            <p className="text-slate-300 text-sm font-medium animate-pulse">
              Evaluating task & routing across models & MCP tools...
            </p>
          </div>
        ) : !result ? (
          <div className="flex flex-col items-center justify-center py-12 text-center space-y-3">
            <div className="w-12 h-12 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center text-slate-500 text-xl">
              🔍
            </div>
            <p className="text-slate-400 text-sm max-w-md font-normal">
              No runs yet — submit a prompt above and the routed answer lands here.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Model & Routing Metrics Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                <div className="text-slate-400 text-[11px] uppercase tracking-wider mb-1">Model</div>
                <div className="text-white font-bold text-sm capitalize">{result.model ?? "Gemini 1.5"}</div>
              </div>
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                <div className="text-slate-400 text-[11px] uppercase tracking-wider mb-1">Confidence</div>
                <div className="text-amber-400 font-bold text-sm">{(result.confidence ?? 0).toFixed(2)}</div>
              </div>
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                <div className="text-slate-400 text-[11px] uppercase tracking-wider mb-1">Cost / Savings</div>
                <div className="text-emerald-400 font-bold text-sm">{formatCost(result.savings ?? 0)} saved</div>
              </div>
              <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-3">
                <div className="text-slate-400 text-[11px] uppercase tracking-wider mb-1">Escalated</div>
                <div className="text-slate-200 font-bold text-sm">{result.escalated ? "YES (Mistral)" : "NO (Gemini)"}</div>
              </div>
            </div>

            {/* Executed Tools Chips */}
            {result.tools_used && result.tools_used.length > 0 && (
              <div className="space-y-2">
                <div className="text-[11px] uppercase tracking-wider text-slate-400 font-semibold">
                  Executed MCP Tools
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  {result.tools_used.map((tool, idx) => (
                    <span
                      key={`${tool.provider}-${tool.tool}-${idx}`}
                      className="bg-amber-500/10 text-amber-300 border border-amber-500/30 rounded-lg px-2.5 py-1 text-xs font-mono"
                    >
                      ⚡ {tool.provider} → {tool.tool}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Routed Answer Text */}
            <div className="bg-slate-900/90 border border-amber-500/20 rounded-xl p-5 space-y-2">
              <div className="text-xs uppercase tracking-wider text-amber-400 font-bold flex items-center justify-between">
                <span>Routed Answer</span>
                <span className="text-[11px] text-slate-400 normal-case">
                  {result.status ?? "Accepted"}
                </span>
              </div>
              <p className="text-slate-100 text-sm leading-relaxed whitespace-pre-wrap font-normal">
                {result.answer}
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Footer Note */}
      <div className="text-center text-slate-500 text-xs pt-1">
        Console calls your live FastAPI backend.
      </div>
    </div>
  );
}
