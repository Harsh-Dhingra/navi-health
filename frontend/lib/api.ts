const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

export type AgentStep = {
  agent_name: string;
  step_type: string;
  status: string;
  data: Record<string, unknown>;
  requires_human_review: boolean;
};

export type ChatResponse = {
  journey_id: string;
  reply: string;
  steps: AgentStep[];
  safety_flags: string[];
  escalated: boolean;
  contains_simulated_data: boolean;
};

export type CareJourney = {
  id: string;
  title: string;
  original_request: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  steps: AgentStep[];
};

export type CurrentUser = {
  id: string;
  email: string;
  full_name: string | null;
};

// Auth lives entirely in httpOnly, Secure, SameSite cookies set by the backend —
// never in localStorage/sessionStorage, which any injected script could read.
// `credentials: "include"` sends/receives those cookies on every request.
async function request<T>(path: string, options: RequestInit = {}, retrying = false): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (response.status === 401 && !retrying) {
    const refreshed = await fetch(`${API_BASE_URL}/api/auth/refresh`, { method: "POST", credentials: "include" });
    if (refreshed.ok) {
      return request<T>(path, options, true);
    }
  }

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status}: ${body}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string, full_name?: string) =>
    request<CurrentUser>("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password, full_name }) }),

  login: (email: string, password: string) =>
    request<CurrentUser>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),

  logout: () => request<void>("/api/auth/logout", { method: "POST" }),

  deleteAccount: (password: string) =>
    request<void>("/api/account", { method: "DELETE", body: JSON.stringify({ password }) }),

  sendMessage: (message: string, journey_id?: string) =>
    request<ChatResponse>("/api/chat", { method: "POST", body: JSON.stringify({ message, journey_id }) }),

  listCareJourneys: () => request<CareJourney[]>("/api/care-journeys"),

  getCareJourney: (id: string) => request<CareJourney>(`/api/care-journeys/${id}`),
};
