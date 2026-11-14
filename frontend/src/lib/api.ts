export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

/** The server's reason as plain text. FastAPI sends a string, {errors: [...]} (risk settings, Eval / Fast Evaluation),
 *  or a validation list [{msg}] — before, anything but a string showed as a bare "HTTP 422" (user, 2026-11-14). */
export function detailText(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => (typeof d === "string" ? d : (d as { msg?: string })?.msg ?? "")).filter(Boolean).join("; ");
  if (detail && typeof detail === "object") {
    const o = detail as { errors?: unknown; message?: unknown };
    if (Array.isArray(o.errors) && o.errors.length) return o.errors.map(String).join("; ");
    if (typeof o.message === "string") return o.message;
  }
  return "";
}

export function csrfToken(): string {
  const m = document.cookie.match(/(?:^|;\s*)pt_csrf=([^;]+)/);
  return m ? decodeURIComponent(m[1]!) : "";
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("content-type")) headers.set("content-type", "application/json");
  if (method !== "GET") headers.set("x-csrf-token", csrfToken());
  const res = await fetch(path, { ...init, method, headers, credentials: "same-origin" });
  const text = await res.text();
  const body: unknown = text ? JSON.parse(text) : null;
  if (!res.ok) {
    throw new ApiError(res.status, detailText((body as { detail?: unknown } | null)?.detail) || `HTTP ${res.status}`);
  }
  return body as T;
}

// ---------- types ----------
export type Status = "connected" | "saved" | "failed" | "not_set" | "waiting" | "link";

export interface FieldSpec {
  name: string;
  label: string;
  kind: "secret" | "text" | "select";
  required: boolean;
  placeholder: string;
  options: string[];
  help: string;
}

export interface Connection {
  id: string;
  name: string;
  category: string;
  purpose: string;
  required: boolean;
  testable: boolean;
  steps: string[];
  note: string;
  links: { label: string; url: string }[];
  fields: FieldSpec[];
  status: Status;
  detail: string;
  hints: Record<string, string>;
  tested_at: string | null;
  installed_version?: string | null;
  install_error?: string | null;
  pinned_version?: string;
  pinned_commit?: string;
  latest_tag?: string | null;
  llm_key_urls?: Record<string, string>;
  tunnel?: TunnelInfo;
}

export interface TunnelInfo {
  mode: "ngrok" | "cloudflare" | "server" | "none"; // server = own domain (PAYTIENCE_PUBLIC_URL, docs/DEPLOY.md)
  ngrok_domain?: string;
  public_url: string;
  permanent: boolean;
  error: string;
}

export interface Indicator {
  id: string;
  name: string;
  author: string;
  role: string;
  link: string;
  setting: string;
  source_on_file: boolean;
  license: string | null;
  personal_use_only: boolean | null;
  alerts_status: Status;
  alerts_detail: string;
}

export interface ConnectionsResponse {
  connections: Connection[];
  indicators: Indicator[];
  summary: { connected: number; total: number; required_ready: boolean };
  webhook_path: string;
  master_key_set: boolean;
}

export interface Health {
  app: string;
  status: string;
  time: string;
  mode: "PAPER" | "LIVE";
}

export interface WebhookStatus {
  path: string;
  secret_set: boolean;
  feeds: { symbol: string; profile: string; last_heartbeat: string | null; data_feed?: "realtime" | "delayed" | "unknown"; status: "FRESH" | "STALE" | "CLOSED" | "NO_DATA" }[];
  accepted: Record<string, number>;
  rejected: Record<string, number>;
  last_rejection: { code: string; detail: string; at: string } | null;
}
