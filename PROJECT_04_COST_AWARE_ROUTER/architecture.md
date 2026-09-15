# Cost-Aware Multi-Model Router - Production Architecture

```text
                               +-----------------------------+
                               |     Next.js Frontend UI     |
                               +-----------------------------+
                                              |
                                              v (JWT Auth)
                               +-----------------------------+
                               |    Clerk Auth Provider      |
                               +-----------------------------+
                                              |
                                              v (Bearer Token)
                               +-----------------------------+
                               |     FastAPI API Gateway     |
                               +-----------------------------+
                                   /          |          \
                                  /           |           \
                                 v            v            v
                     +---------------+  +------------+  +-------------------+
                     | Users Repos.  |  |Connectors  |  | Usage Events      |
                     +---------------+  +------------+  +-------------------+
                                 \            |            /
                                  v           v           v
                               +-----------------------------+
                               |   MongoDB Database Layer    |
                               | (users, connectors, usage)  |
                               +-----------------------------+
                                              |
                                              v
                              +-------------------------------+
                              |    LangGraph Router & Agent   |
                              +-------------------------------+
                               /             |             \
                              /              |              \
                             v               v               v
                     +---------------+ +-----------+ +---------------+
                     |  Gemini 2.0   | |  Mistral  | |   MCP Tools   |
                     |  (Low Cost)   | | (High Cap)| |(GitHub,Gmail)|
                     +---------------+ +-----------+ +---------------+
                             \               /               |
                              v             v                v
                        +-----------------------------------------+
                        | Confidence Validation & Escalation Engine|
                        +-----------------------------------------+
                                             |
                                             v
                        +-----------------------------------------+
                        |       Cost & Financial Savings Engine   |
                        +-----------------------------------------+
                                             |
                                             v
                        +-----------------------------------------+
                        |  LangSmith Tracing & Observability      |
                        +-----------------------------------------+
```

## System Responsibilities

- **Next.js Frontend:** Modern TypeScript/React dashboard providing user interface for model routing, autonomous agent execution, connector setup, financial analytics, cost savings distribution, and profile settings.
- **Clerk Authentication:** Identity Provider handling user sign-in, sign-up, and JWT token issuance. Serves as the identity authority across the platform.
- **FastAPI API Gateway:** High-performance Python backend serving REST API endpoints, enforcing Clerk JWT authorization (`PyJWKClient`), handling session management, CORS policies, and error responses.
- **MongoDB Database Layer (`app/db/`):** Persistent application database managing 3 primary collections:
  - `users`: Stores application-level user details, Clerk User ID mapping, and custom routing preferences (`default_model`, `confidence_threshold`, `complexity_threshold`).
  - `connectors`: Stores user-scoped MCP connector connection status and account metadata for GitHub, Gmail, and Google Drive.
  - `usage_events`: Stores request history, model selection logs, token consumption, actual cost, baseline cost, financial savings, and tool invocation logs.
- **LangGraph Router & Agent Engine:** Orchestrates task classification, complexity scoring, model selection, execution, response validation, confidence scoring, and transparent model escalation.
- **LLM Model Provider Layer:**
  - **Gemini (Primary Low-Cost Model):** Handles simple to medium complexity tasks (e.g., summarization, extraction, simple Q&A) at minimal cost ($0.75/$3.75 per M tokens).
  - **Mistral (High-Capability / Fallback Model):** Handles complex reasoning tasks and acts as an escalation target when primary model confidence drops below threshold or provider errors occur.
- **Model Context Protocol (MCP) Manager:** Dynamically discovers, registers, and executes user-scoped tools for external services (GitHub repositories, Gmail messages, Google Drive documents) with permission boundaries.
- **Confidence & Validation Engine:** Evaluates outputs for structural validity, schema compliance, completeness, and consistency before returning responses.
- **Cost & Financial Savings Engine:** Computes exact or estimated token costs, compares actual model execution against a baseline top-tier model, and reports non-negative savings metrics (`max(0, baseline - actual)`).
- **LangSmith Tracing:** Logs complete graph execution paths, prompt payloads, model responses, tool calls, and latency profiles for end-to-end debugging and observability.

---

## Security and Isolation Boundaries

- **Server-Side Identity Verification:** The frontend never supplies user identity for database operations. All backend requests extract `clerk_user_id` strictly from verified Clerk JWT tokens.
- **Strict User Data Scoping:** All MongoDB queries for `users`, `connectors`, and `usage_events` are strictly scoped by `clerk_user_id`, ensuring absolute data isolation between users.
- **Credential Protection:** MongoDB connection URI (`MONGODB_URI`) and API keys are stored strictly in server-side environment variables and are never exposed to the client application or `NEXT_PUBLIC_*` variables. OAuth tokens are never stored in plain text or sent to the frontend.
- **Graceful Fault Tolerance:** Connection managers employ connection pooling with timeouts and health checks (`GET /health`). If MongoDB is temporarily offline, fallback mechanisms prevent application crashes.
