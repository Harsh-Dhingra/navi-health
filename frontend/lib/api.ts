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

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("navi_token");
}

export function setToken(token: string) {
  window.localStorage.setItem("navi_token", token);
}

export function clearToken() {
  window.localStorage.removeItem("navi_token");
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status}: ${body}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string, full_name?: string) =>
    request("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password, full_name }) }),

  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  sendMessage: (message: string, journey_id?: string) =>
    request<ChatResponse>("/api/chat", { method: "POST", body: JSON.stringify({ message, journey_id }) }),

  listCareJourneys: () => request<CareJourney[]>("/api/care-journeys"),

  getCareJourney: (id: string) => request<CareJourney>(`/api/care-journeys/${id}`),
};
