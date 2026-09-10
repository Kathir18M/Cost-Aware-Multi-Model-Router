# Project 04: Cost-Aware Multi-Model Router

## Overview

This application routes classification, extraction, summarization, and Q&A requests through a Haiku-first LangGraph workflow. It measures confidence and response validity, escalates to Sonnet when required, records token-based cost data, exposes selected support tools through an MCP boundary, and provides a Streamlit dashboard.

## Problem Statement

Different requests have different reliability and reasoning requirements. Always using Sonnet can increase cost, while always using Haiku can reduce quality. The router makes that trade-off observable by combining deterministic task/complexity analysis, bounded retry/fallback behavior, confidence checks, cost comparison, and held-out evaluation.

## Architecture

See [architecture.md](architecture.md) for component responsibilities and the end-to-end flow. LangGraph owns orchestration. LangChain provides reusable task prompts and tool adapters. MCP exposes selected cost, policy, evaluation, statistics, and logging capabilities without controlling the workflow.

## Features

- Haiku-first model selection with Sonnet escalation
- Classification, extraction, summarization, and Q&A task chains
- Structured Pydantic outputs and validation
- Measurable confidence signals
- Bounded retry and technical fallback
- Input/output token and cost accounting
- Always-Sonnet baseline and non-negative savings calculation
- MCP-compatible tools/resources and LangChain tool adapters
- Balanced 20-example held-out evaluation dataset
- Streamlit request form, KPIs, charts, and non-sensitive history
- API-key redaction and environment-based configuration

## Technologies

Python, Anthropic Claude, LangChain, LangGraph, MCP, Streamlit, Pydantic, python-dotenv, and pytest.

## Installation

```powershell
cd K:\multi_model\PROJECT_04_COST_AWARE_ROUTER
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and provide an Anthropic key and model/pricing settings. `.env` is ignored by Git and must never be committed.

## Environment Setup

Required secret:

```text
ANTHROPIC_API_KEY=
```

The remaining variables in `.env.example` have development defaults when omitted. Prices are interpreted as cost per token by the cost engine.

## Running

Validate the foundation:

```powershell
python run.py
```

Start the dashboard:

```powershell
streamlit run streamlit_app.py
```

Submit a task, inspect the selected/final model, confidence, escalation reason, latency, and cost comparison. A missing API key is reported as a user-facing error; no request is sent.

## Example Workflow

1. Enter a Q&A request in Streamlit.
2. LangGraph classifies the task and analyzes complexity.
3. The model policy selects Haiku for low/medium complexity or Sonnet for high complexity.
4. The response is validated and scored using measurable signals.
5. Low confidence, invalid output, or technical failure can trigger a bounded Sonnet path.
6. Token usage, actual cost, Sonnet baseline, savings, and routing metadata are recorded.

## Cost Calculation

Actual cost is calculated from input and output tokens using configured model prices. Escalated requests can aggregate Haiku and Sonnet usage. The baseline calculates the same token usage at Sonnet prices. Savings are `max(0, baseline - actual)`; negative comparisons are not reported as savings.

## Evaluation Methodology

The held-out dataset contains 20 fixed examples, balanced across the four task types. The evaluator compares injected `always_haiku`, `always_sonnet`, and `cost_aware_router` strategies. Classification uses label accuracy, extraction uses field-level matching, and summarization/Q&A use lexical coverage. Evaluation results are calculated at runtime and are not stored as fabricated fixtures.

## Results

The automated test suite currently passes **69 tests** on this branch. No production API evaluation numbers are claimed here because no API-backed evaluation run was performed during finalization. Run the evaluation service with real strategy runners to produce actual model, cost, savings, accuracy, and escalation results.

## Limitations

- The local token counter is an estimate, not a provider tokenizer.
- Confidence is a deterministic heuristic and is not a calibrated probability.
- The MCP layer is transport-neutral; deployment-specific MCP transport wiring remains separate.
- Dashboard history is session-scoped, while routing events are written to JSONL.
- Accuracy is shown as unavailable in the dashboard until an evaluation result is supplied.
- Real Claude evaluation requires an Anthropic API key and incurs provider charges.

## Future Improvements

Use provider tokenizers, persist analytics in a durable store, calibrate confidence against labeled outcomes, add transport-specific MCP deployment, improve semantic evaluation for summaries/answers, and add authenticated multi-user dashboard access.
