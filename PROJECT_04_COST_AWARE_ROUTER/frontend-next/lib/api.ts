export type TaskType = "classification" | "extraction" | "summarization" | "qa";

export interface RouterRequest {
  task_type: TaskType | string;
  input: string;
}

export interface RouterResponse {
  request_id?: string;
  task_type?: string;
  initial_model?: string;
  selected_model?: string;
  confidence?: number;
  complexity?: string;
  escalation_required?: boolean;
  escalation_reason?: string | null;
  actual_cost?: number;
  baseline_cost?: number;
  savings?: number;
  savings_percentage?: number;
  status?: string;
  response?: {
    content?: string;
    answer?: string;
    summary?: string;
    input_tokens?: number;
    output_tokens?: number;
    latency?: number;
    success?: boolean;
    error?: string;
  };
}

export interface AgentRunResponse {
  request_id?: string;
  answer?: string;
  model?: string;
  confidence?: number;
  tools_used?: Array<{ provider?: string; tool?: string }>;
  escalated?: boolean;
  escalation_reason?: string | null;
  actual_cost?: number;
  baseline_cost?: number;
  cost?: number;
  savings?: number;
  savings_percentage?: number;
  status?: string;
  tool_results?: Array<Record<string, unknown>>;
}

export interface DashboardData {
  total_requests: number;
  gemini_requests: number;
  mistral_requests: number;
  escalation_rate: number;
  average_confidence: number;
  average_latency: number;
  total_cost: number;
  baseline_cost: number;
  total_savings: number;
  savings_percentage: number;
  accuracy: number | null;
  events: Array<Record<string, unknown>>;
}

export interface LogsItem {
  request_id?: string;
  timestamp?: string;
  task_type?: string;
  initial_model?: string;
  final_model?: string;
  confidence?: number;
  complexity?: string;
  escalation_reason?: string | null;
  cost?: number;
  savings?: number;
  latency?: number;
  status?: string;
}

export interface EvaluationData {
  total_test_cases?: number;
  passed?: number;
  failed?: number;
  accuracy?: number;
  average_score?: number;
  gemini_performance?: number;
  mistral_performance?: number;
  escalation_rate?: number;
  records?: Array<Record<string, unknown>>;
}

export interface ConnectorStatusItem {
  id?: string;
  name: string;
  connected: boolean;
  tools: string[];
  status: string;
  provider?: string;
  account?: {
    email?: string;
    name?: string;
    login?: string;
    avatar_url?: string;
    picture?: string;
  } | null;
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function getClerkSessionToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null;
  }

  const getSessionTokenFromWindow = async (): Promise<string | null> => {
    const globalWithClerk = window as typeof window & {
      Clerk?: {
        session?: {
          getToken: () => Promise<string | null>;
        };
      };
    };

    const session = globalWithClerk.Clerk?.session;
    if (!session || typeof session.getToken !== "function") {
      return null;
    }

    try {
      return await session.getToken();
    } catch {
      return null;
    }
  };

  let token = await getSessionTokenFromWindow();
  if (token) return token;

  // Poll up to 2 seconds (20 x 100ms) to allow Clerk JS SDK to finish mounting/hydrating
  for (let i = 0; i < 20; i++) {
    await new Promise((resolve) => setTimeout(resolve, 100));
    token = await getSessionTokenFromWindow();
    if (token) return token;
  }

  return null;
}

export class ApiError extends Error {
  status: number;
  data: Record<string, unknown>;

  constructor(message: string, status: number, data: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = await getClerkSessionToken();
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
  });

  if (!response.ok) {
    const errorBody = (await response.json().catch(() => ({ detail: "Request failed" }))) as Record<string, unknown>;
    const message =
      typeof errorBody?.detail === "string"
        ? errorBody.detail
        : typeof (errorBody?.error as Record<string, unknown>)?.message === "string"
        ? String((errorBody.error as Record<string, unknown>).message)
        : "Request failed";
    throw new ApiError(message, response.status, errorBody);
  }

  return (await response.json()) as T;
}

export function runRouter(payload: RouterRequest) {
  return request<RouterResponse>("/api/router/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function runAgent(payload: { query: string; user_id?: string }) {
  return request<AgentRunResponse>("/api/agent/run", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getDashboard() {
  return request<DashboardData>("/api/dashboard");
}

export function getAnalytics() {
  return request<DashboardData>("/api/analytics");
}

export function getLogs() {
  return request<LogsItem[]>("/api/logs");
}

export function getEvaluation() {
  return request<EvaluationData>("/api/evaluation");
}

export function getTraces() {
  return request<Array<Record<string, unknown>>>("/api/traces");
}

export function listConnectors() {
  return request<{ connectors: ConnectorStatusItem[] }>("/api/connectors");
}

export function getConnectorStatus(provider: string) {
  return request<ConnectorStatusItem>(`/api/connectors/${provider}/status`);
}

export function connectConnector(provider: string) {
  return request<ConnectorStatusItem>(`/api/connectors/${provider}/connect`);
}

export function disconnectConnector(provider: string) {
  return request<ConnectorStatusItem>(`/api/connectors/${provider}/disconnect`, { method: "POST" });
}
