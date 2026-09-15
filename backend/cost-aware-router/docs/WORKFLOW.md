# 🔄 Cost-Aware Multi-Model Router — System Workflows

> **Comprehensive operational and execution workflow guide for the Cost-Aware Multi-Model Router platform.**

---

## 1. User Authentication & Identity Workflow

This workflow describes how user authentication and identity propagation occur from the Next.js frontend to the FastAPI backend and MongoDB persistence layer.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant FE as Next.js Frontend
    participant Clerk as Clerk Auth Service
    participant API as FastAPI Backend
    participant DB as MongoDB (users)

    User->>FE: Click Sign In / Enter Credentials
    FE->>Clerk: Authenticate User
    Clerk-->>FE: Return Session & Issued JWT Token (RS256)
    FE->>API: HTTP Request + Authorization: Bearer <Clerk_JWT>
    API->>Clerk: Fetch Public JWKS Keys (.well-known/jwks.json)
    API->>API: Verify RS256 Signature & Extract clerk_user_id (sub claim)
    API->>DB: UserRepository.upsert_user(clerk_user_id, identity_data)
    alt User exists
        DB-->>API: Update last_login_at & updated_at timestamp
    else New User
        DB-->>API: Create UserDocument with default preferences
    end
    API-->>FE: Return Authorized API Response
```

### Detailed Steps:
1. **User Sign-In**: The user accesses `/sign-in` rendered by `@clerk/nextjs`.
2. **JWT Issuance**: Upon authentication, Clerk issues a signed JWT token (`RS256`).
3. **API Dispatch**: The Next.js frontend attaches the token to API requests in the `Authorization: Bearer <token>` header.
4. **JWT Verification**: `app/auth/clerk.py` decodes the token using Clerk's public key retrieved from `CLERK_JWKS_URL`.
5. **Identity Extraction**: The immutable `sub` claim is extracted as `clerk_user_id`.
6. **Automatic User Upsert**: `UserRepository.upsert_user` checks MongoDB `users` collection. If the user exists, `last_login_at` is updated; if not, a new `UserDocument` is created.

---

## 2. Cost-Aware Router Execution Workflow

This workflow details how user prompts are analyzed, routed, executed, validated, escalated, and logged.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant FE as Next.js Frontend
    participant API as FastAPI (/api/router/run)
    participant Router as LangGraph Router
    participant Gemini as Gemini 2.0 Flash
    participant Mistral as Mistral Small
    participant Eval as Confidence Engine
    participant DB as MongoDB (usage_events)

    User->>FE: Submit Prompt & Select Task Type
    FE->>API: POST /api/router/run (Header: Bearer JWT)
    API->>Router: Initialize Graph & Analyze Prompt Complexity
    alt Low / Medium Complexity (<= 0.70)
        Router->>Gemini: Invoke Primary Low-Cost Model
        Gemini-->>Router: Return Model Output
    else High Complexity (> 0.70)
        Router->>Mistral: Invoke High-Capacity Model
        Mistral-->>Router: Return Model Output
    end
    Router->>Eval: Validate Output & Score Confidence
    alt Confidence >= Threshold (0.75)
        Eval-->>Router: Validation Passed
    else Confidence < Threshold OR Provider Error
        Eval->>Mistral: Escalate Request to Fallback Model
        Mistral-->>Router: Return Escalated Output
    end
    Router->>API: Compute Input/Output Tokens, Cost, & Savings %
    API->>DB: UsageRepository.save_usage_event(...)
    API-->>FE: Return Final Response JSON
```

### Detailed Steps:
1. **Request Submission**: User submits prompt and task type (e.g. `summarization`, `classification`, `extraction`).
2. **Complexity Analysis**: Router calculates input length, structure, and intent complexity score `[0.0, 1.0]`.
3. **Primary Model Dispatch**:
   - `complexity <= 0.70`: Request dispatched to **Gemini 2.0 Flash**.
   - `complexity > 0.70`: Request dispatched directly to **Mistral Small**.
4. **Confidence Evaluation**: Response is evaluated for structural completeness, schema validity, and confidence heuristics.
5. **Conditional Escalation**: If Gemini output scores below confidence threshold (`0.75`) or fails due to rate limits/errors, the query transparently escalates to **Mistral Small**.
6. **Cost & Savings Accounting**: System calculates actual execution cost against baseline, generating net savings (`baseline_cost - actual_cost`).
7. **MongoDB Logging**: `UsageRepository.save_usage_event` persists the request record to MongoDB `usage_events`.

---

## 3. MCP Tool & Autonomous Agent Workflow

This workflow describes multi-step task execution using Model Context Protocol (MCP) tools and LangGraph state management.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant FE as Next.js Frontend
    participant API as FastAPI (/api/agent/run)
    participant Agent as LangGraph Agent State Machine
    participant MCP as MCP Manager & Connectors
    participant Tool as Tool Execution (GitHub / Gmail / Drive)
    participant DB as MongoDB (usage_events)

    User->>FE: Submit Query requiring external data
    FE->>API: POST /api/agent/run (Header: Bearer JWT)
    API->>MCP: Discover Active Connectors for clerk_user_id
    MCP-->>API: Return User-Scoped Tools (e.g. search_emails, list_repos)
    API->>Agent: Initialize Agent Graph (Plan -> Select Tool -> Execute)
    loop Iterative Agent Execution Loop
        Agent->>MCP: Invoke Tool Call (e.g. list_my_repositories)
        MCP->>Tool: Execute Tool Request
        Tool-->>MCP: Return Tool Output / Payload
        MCP-->>Agent: Update State with Tool Result
    end
    Agent->>Agent: Synthesize Final Answer & Score Confidence
    API->>DB: UsageRepository.save_usage_event(...)
    API-->>FE: Return Agent Response & Tool Execution History
```

### Detailed Steps:
1. **Query Submission**: User inputs an agent query (e.g. *"Search my Gmail for project alerts and check open GitHub issues"*).
2. **Tool Discovery**: `MCPManager` retrieves active connectors registered for `clerk_user_id`.
3. **State Machine Loop**: LangGraph executes an iterative cycle:
   - **Plan**: Analyze query intent and state history.
   - **Select Tool**: Select required MCP tool (`list_my_repositories`, `search_emails`, `search_files`).
   - **Execute**: Invoke tool with validated parameters.
   - **Observe**: Capture tool output and append to graph state.
4. **Synthesis & Logging**: Agent synthesizes final natural language response and saves execution event to MongoDB `usage_events`.

---

## 4. OAuth & Connector Management Workflow

This workflow details how external user accounts (GitHub, Gmail, Google Drive) are connected, stored in MongoDB, and isolated per user.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant FE as Next.js Frontend
    participant API as FastAPI (/api/connectors/{provider}/*)
    participant OAuth as OAuth Provider (GitHub / Google)
    participant DB as MongoDB (connectors)

    User->>FE: Click "Connect GitHub / Gmail"
    FE->>API: GET /api/connectors/github/connect (Header: Bearer JWT)
    API->>API: Store OAuth State Token in Encrypted Session
    API-->>FE: Redirect (302) to Provider OAuth Authorization URL
    FE->>OAuth: User Authorizes Application Scope
    OAuth-->>API: Redirect Callback /api/connectors/github/callback?code=...
    API->>OAuth: Exchange Authorization Code for Tokens
    OAuth-->>API: Return Access Token & User Profile Metadata
    API->>DB: ConnectorRepository.save_connector_state(clerk_user_id, provider, "connected", metadata)
    API-->>FE: Redirect (302) to /connectors?connected=1
```

### Detailed Steps:
1. **Connect Trigger**: User clicks "Connect" on `/connectors` page.
2. **OAuth Authorization**: FastAPI generates a secure state token and redirects user to provider authorization page.
3. **User Consent**: User authorizes application permissions (e.g. `read:user repo` or `gmail.readonly`).
4. **Code Exchange**: Provider redirects to callback endpoint; FastAPI exchanges authorization code for tokens and user metadata (`login`, `email`, `avatar_url`).
5. **MongoDB Persistence**: `ConnectorRepository.save_connector_state` records connector status in MongoDB `connectors` collection bound strictly to `clerk_user_id`.
6. **User Isolation**: Disconnect requests (`POST /api/connectors/{provider}/disconnect`) update the specific user's status without affecting other users.

---

## 5. Dashboard & Cost Analytics Workflow

This workflow details how financial analytics, cost distributions, and request metrics are calculated and rendered.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant FE as Next.js Frontend
    participant API as FastAPI (/api/dashboard)
    participant DB as MongoDB (usage_events)

    User->>FE: Navigate to Dashboard / Analytics Page
    FE->>API: GET /api/dashboard (Header: Bearer JWT)
    API->>DB: UsageRepository.get_user_dashboard_metrics(clerk_user_id)
    DB->>DB: Run Aggregation Pipeline ($match clerk_user_id, $group totals)
    DB-->>API: Return Aggregated Metrics & Request History
    API-->>FE: Return JSON (total_requests, gemini_requests, total_cost, savings_pct, events)
    FE->>FE: Render Metric Cards, Cost Charts, & History Table
```

### Detailed Steps:
1. **Dashboard Navigation**: User visits `/analytics` or `/history`.
2. **Metrics Query**: Frontend requests `GET /api/dashboard` with Clerk Bearer token.
3. **MongoDB Aggregation Pipeline**: `UsageRepository.get_user_dashboard_metrics` executes:
   - `$match`: Filters `usage_events` by `clerk_user_id`.
   - `$group`: Sums `total_requests`, `gemini_requests`, `mistral_requests`, `escalations`, `total_actual_cost`, `total_baseline_cost`, `total_savings`.
4. **Data Rendering**: Next.js renders financial KPI cards (Total Savings, Savings %, Model Ratio) and request history table.

---

## 6. Failure Handling & Resilience Workflow

This workflow describes system recovery when encountering provider rate limits, model failures, or temporary database outages.

```mermaid
sequenceDiagram
    autonumber
    participant API as FastAPI Backend
    participant Provider as Gemini API
    participant Fallback as Mistral API
    participant DB as MongoDB

    API->>Provider: Invoke Gemini API Request
    alt Rate Limit (429) OR Service Outage (503)
        Provider-->>API: Provider Failure / Timeout
        API->>Fallback: Automatically Escalate to Mistral Small
        Fallback-->>API: Return Successful Escalated Response
        API->>DB: Save Usage Event with escalated=true & escalation_reason
    else MongoDB Database Temporary Offline
        API->>DB: Attempt DB Query / Save
        DB-->>API: Connection Timeout
        API->>API: Fallback to Local JSONL Log File (logs/router_events.jsonl)
        API-->>API: Return Graceful API Response (Non-blocking DB Failure)
    end
```

### Resilience Guarantees:
- **Automatic Model Escalation**: Gemini rate limits (429) or timeouts trigger immediate fallback to Mistral Small.
- **Database Fault Tolerance**: Short MongoDB connection timeouts (`2000ms`) prevent API hangs. If MongoDB is offline, operations fallback gracefully or return structured `DATABASE_UNAVAILABLE` error payloads without crashing the server.
