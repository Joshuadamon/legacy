import { secureGet, secureSet } from "./utils/storage";

const TOKEN_KEY = "session_token";

let memoryToken: string | null = null;

export function getMemoryToken(): string | null {
  return memoryToken;
}

export async function loadToken(): Promise<string | null> {
  memoryToken = await secureGet(TOKEN_KEY);
  return memoryToken;
}

export async function setToken(token: string | null): Promise<void> {
  memoryToken = token;
  await secureSet(TOKEN_KEY, token ?? "");
}

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const base = process.env.EXPO_PUBLIC_BACKEND_URL ?? "";
  const headers = new Headers(options.headers);
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (memoryToken) headers.set("Authorization", `Bearer ${memoryToken}`);
  const response = await fetch(`${base}${path}`, { ...options, headers });
  const text = await response.text();
  let body: { detail?: unknown } | null = null;
  if (text) {
    try {
      body = JSON.parse(text) as { detail?: unknown };
    } catch {
      body = null;
    }
  }
  if (!response.ok) {
    const detail = body?.detail;
    const message = typeof detail === "string" ? detail : "The record could not be reached.";
    throw new ApiError(response.status, message);
  }
  return body as T;
}
