export type Role = "PATIENT" | "HEALTH_AGENT" | "ADMIN";

export interface User {
  id: string;
  role: Role;
  status: string;
  email: string;
  fullName: string;
  phone: string | null;
  createdAt: string;
}

export const HOME_BY_ROLE: Record<Role, string> = {
  PATIENT: "/patient",
  HEALTH_AGENT: "/oriagent",
  ADMIN: "/oriadmin",
};

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details: Record<string, unknown> = {}) {
    super(message);
  }
}

type Options = { method?: string; body?: unknown };

/** Calls the FastAPI backend through the Next.js /api rewrite (same origin, httpOnly cookies). */
export async function api<T>(path: string, options: Options = {}, retry = true): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    method: options.method ?? "GET",
    headers: options.body !== undefined ? { "Content-Type": "application/json" } : undefined,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    credentials: "same-origin",
  });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    const error = data?.error ?? { code: "HTTP_ERROR", message: response.statusText };
    if (response.status === 401 && error.code === "TOKEN_EXPIRED" && retry) {
      const refreshed = await fetch("/api/v1/auth/refresh", { method: "POST", credentials: "same-origin" });
      if (refreshed.ok) return api<T>(path, options, false);
    }
    throw new ApiError(response.status, error.code, error.message, error.details ?? {});
  }
  return data as T;
}
