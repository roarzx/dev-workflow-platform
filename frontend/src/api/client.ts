const API_BASE = "/api/v1";

interface ApiResponse<T = unknown> {
  code: number | string;
  data: T;
  message: string;
  detail?: unknown;
}

export class ApiError extends Error {
  code: string | number;
  constructor(code: string | number, message: string) {
    super(message);
    this.code = code;
    this.name = "ApiError";
  }
}

export async function apiGet<T = unknown>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  }
  const res = await fetch(url.toString());
  const json: ApiResponse<T> = await res.json();
  if (json.code !== 0) throw new ApiError(json.code, json.message);
  return json.data as T;
}

export async function apiPost<T = unknown>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json: ApiResponse<T> = await res.json();
  if (json.code !== 0) throw new ApiError(json.code, json.message);
  return json.data as T;
}

export async function apiPatch<T = unknown>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json: ApiResponse<T> = await res.json();
  if (json.code !== 0) throw new ApiError(json.code, json.message);
  return json.data as T;
}
