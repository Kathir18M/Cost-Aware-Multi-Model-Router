# Project 04: Cost-Aware Multi-Model Router

## Project Objective

Build a production-oriented GenAI application that routes user requests to the cheapest capable model. Claude Haiku is the initial model because it is faster and lower cost; complex or unsuccessful requests will be eligible for Claude Sonnet escalation.

## Problem Statement

Different requests have different reasoning and reliability requirements. A single-model strategy can increase cost unnecessarily, while an overly aggressive low-cost strategy can reduce response quality. This project will provide an observable routing layer for classification, information extraction, summarization, and question answering.

## Planned Architecture

The planned flow is documented in [architecture.md](architecture.md): classify the request, analyze complexity, select a model, validate the Haiku response, escalate when needed, calculate cost, and log routing events. LangGraph will orchestrate the workflow, and MCP will expose selected tools and resources.

Implementation is not started. Coming in later phases.

## Planned Technologies

- Python
- LangChain and LangGraph
- Anthropic Claude Haiku and Claude Sonnet
- MCP and tool calling
- Streamlit
- Pydantic
- python-dotenv
- Evaluation, cost tracking, structured logging, retries, and fallback handling

## Planned Features

- Request classification
- Information extraction
- Summarization
- Question answering
- Cost-aware Haiku-first routing
- Confidence and validation checks
- Sonnet escalation and API fallback
- Cost analytics and evaluation datasets

All planned features are Coming in later phases.

## Project Phases

1. **Phase 0 - Structure:** Create the modular project skeleton and placeholders. This phase only.
2. **Phase 1 - Schemas and configuration:** Define validated data contracts and environment configuration.
3. **Phase 2 - Model and chain integrations:** Add Claude clients and task-specific chains.
4. **Phase 3 - Routing workflow:** Implement classification, complexity, model selection, validation, escalation, and fallback with LangGraph.
5. **Phase 4 - MCP and services:** Expose selected tools/resources and add service boundaries.
6. **Phase 5 - Streamlit dashboard:** Add the interactive application and analytics views.
7. **Phase 6 - Evaluation and hardening:** Add datasets, metrics, retries, observability, and tests.

## Folder Structure

```text
app/       Application packages for core, models, schemas, chains, routing, tools, MCP, evaluation, services, and utilities
data/     Development and held-out evaluation dataset placeholders
logs/      Router, error, and evaluation log destinations
tests/     Test module placeholders
streamlit_app.py
run.py
```

## Setup

Create a virtual environment, install the minimal placeholder dependencies from `requirements.txt`, and copy `.env.example` to a local `.env` file only when implementation begins. Never commit credentials.

The application is not runnable yet. Coming in later phases.

## Running

Run instructions will be added with the application entry points. Coming in later phases.

## Evaluation

Evaluation datasets are intentionally empty placeholders. Evaluation runners, metrics, and result reporting will be added later. Coming in later phases.
