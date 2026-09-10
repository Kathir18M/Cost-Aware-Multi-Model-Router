# Production Architecture

```text
Streamlit
     |
     v
Service Layer
     |
     v
LangGraph
     |
     v
Task + Complexity
     |
     v
Model Selection
     |
     v
Haiku
     |
     v
Confidence
     |
     +--> PASS --------------------+
     |                              |
     +--> FAIL --> Sonnet escalation+
                                           v
                               Cost + Evaluation
                                           |
                                           v
                                     MCP / Tools
```

## Responsibilities

- **Streamlit:** Collects a task and prompt, displays the latest result, factual KPIs, charts, and non-sensitive request history. It does not decide routing.
- **Service layer:** Provides boundaries for routing, cost, evaluation, and analytics operations.
- **LangChain:** Supplies reusable task prompts, structured parsing, Pydantic outputs, and optional tool adapters.
- **LangGraph:** Owns deterministic orchestration: classification, complexity, selection, execution, confidence, escalation, and finalization.
- **MCP:** Exposes selected cost, policy, evaluation, statistics, and logging operations as a separate tool/resource boundary. It does not control the graph.
- **Tool calling:** Makes selected support functions available to compatible LangChain model clients. The model cannot rewrite the deterministic routing graph.
- **Fallback:** Retries transient initial failures within a bounded limit, then performs one Sonnet technical fallback. Sonnet failures do not recurse.
- **Confidence engine:** Combines task certainty, validity, required fields, completeness, consistency, and a small model-confidence contribution into a normalized heuristic score.
- **Cost engine:** Calculates input/output/total token cost, compares actual cost with an Always-Sonnet baseline, and reports non-negative savings.
- **Evaluation:** Loads a fixed balanced held-out dataset and compares Always Haiku, Always Sonnet, and Cost-Aware Router strategy runners using task-aware quality metrics.

## Data and Security Boundaries

The held-out dataset is static and is not tuned from evaluation results. Routing events contain operational metadata rather than raw user prompts. API keys are loaded from environment variables, excluded from configuration representations, redacted from model errors, and ignored by Git.

## Known Boundaries

The token counter is an estimate, confidence is not calibrated, dashboard history is session-scoped, and MCP transport deployment is intentionally separate from this application-level façade.
