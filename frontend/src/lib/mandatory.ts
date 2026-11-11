/**
 * D93 — connections that are MANDATORY to trade an EVAL or LIVE (Lucid) account, and the live checklist built from
 * existing API data only. Anything the API does not report is "unknown" (never assumed OK), and says so.
 *
 * Mandatory (spec §1.1/§1.3/§13/§15 + code):
 *   broker route   – Lucid has no API; orders + position read-back go through Tradovate (CrossTrade, D-live gate)
 *   TradingView    – the only live signal source (§1.1): heartbeat must be fresh (pre-flight heartbeat_fresh)
 *   webhook secret – webhook rejects unsigned alerts; without it no signal is accepted
 *   public HTTPS   – TradingView can only reach the app over HTTPS (ngrok permanent / Cloudflare fallback)
 *   calendar       – "no calendar = no trading" (§15, pre-flight calendar)
 *   attestation    – external-positions attestation each session before arming (§1.11)
 *   clock sync     – pre-flight clock drift < 2 s (§13)
 *   pre-flight     – the server refuses SEMI/FULL automation unless the last pre-flight passed
 * Optional (normal colour): Discord/notifications, AI keys (TradingAgents, Vibe-Trading, Alpha Vantage, FRED),
 * Trading-R1, Databento/OpenBB/Fincept data, Lucid dashboard link, GitHub updates.
 */
import type { ConnectionsResponse, WebhookStatus } from "./api";

/** Connection ids (from /api/connections) that get the mandatory highlight. Broker and URL are either/or pairs. */
export const MANDATORY_CONNECTION_IDS = ["tradingview", "crosstrade", "tradovate", "ngrok", "tunnel", "forexfactory"] as const;
export function isMandatoryConnection(id: string): boolean {
  return (MANDATORY_CONNECTION_IDS as readonly string[]).includes(id);
}

export type CheckState = "ok" | "fail" | "unknown";
export interface CheckItem { id: string; label: string; state: CheckState; detail: string }
export interface PlanSlice {
  calendar_loaded?: boolean;
  attested_today?: boolean;
  preflight?: { ok: boolean; failures: string[]; at: string } | null;
}
export interface ChecklistInput {
  conns?: ConnectionsResponse;
  webhook?: WebhookStatus;
  plan?: PlanSlice;
}
export type Readiness = "yes" | "no" | "unconfirmed";

const NO_DATA = "unknown — not available from the API right now";

function broker(conns?: ConnectionsResponse): CheckItem {
  const label = "Broker order route (Tradovate via CrossTrade)";
  if (!conns) return { id: "broker", label, state: "unknown", detail: NO_DATA };
  const ct = conns.connections.find((c) => c.id === "crosstrade");
  const tv = conns.connections.find((c) => c.id === "tradovate");
  if (ct?.status === "connected") return { id: "broker", label, state: "ok", detail: ct.detail || "CrossTrade key tested OK" };
  if (ct?.status === "failed") return { id: "broker", label, state: "fail", detail: ct.detail || "CrossTrade test failed" };
  if (tv && (tv.status === "saved" || tv.status === "connected"))
    return { id: "broker", label, state: "unknown", detail: "unknown — Tradovate credentials saved but the API cannot test them here" };
  return { id: "broker", label, state: "fail", detail: "No broker route set up (CrossTrade or Tradovate)" };
}

function heartbeat(conns?: ConnectionsResponse): CheckItem {
  const label = "TradingView webhook feed (heartbeat)";
  const c = conns?.connections.find((x) => x.id === "tradingview");
  if (!c) return { id: "heartbeat", label, state: "unknown", detail: NO_DATA };
  if (c.status === "connected") return { id: "heartbeat", label, state: "ok", detail: c.detail };
  if (c.status === "failed") return { id: "heartbeat", label, state: "fail", detail: c.detail };
  if (/market closed/i.test(c.detail)) return { id: "heartbeat", label, state: "unknown", detail: `unknown — ${c.detail}` };
  return { id: "heartbeat", label, state: "fail", detail: c.detail || "No heartbeat received yet" };
}

function secret(webhook?: WebhookStatus): CheckItem {
  const label = "Webhook secret";
  if (!webhook) return { id: "webhook_secret", label, state: "unknown", detail: NO_DATA };
  return webhook.secret_set
    ? { id: "webhook_secret", label, state: "ok", detail: "Set — unsigned alerts are rejected" }
    : { id: "webhook_secret", label, state: "fail", detail: "Not set — no alert can be accepted" };
}

function publicUrl(conns?: ConnectionsResponse): CheckItem {
  const label = "Public HTTPS URL for TradingView";
  if (!conns) return { id: "public_url", label, state: "unknown", detail: NO_DATA };
  const t = conns.connections.find((c) => c.id === "ngrok")?.tunnel;
  const manual = conns.connections.find((c) => c.id === "tunnel");
  if (t?.mode === "ngrok") return { id: "public_url", label, state: "ok", detail: `Permanent: ${t.public_url}` };
  if (manual?.status === "connected") return { id: "public_url", label, state: "ok", detail: manual.detail || "Own tunnel tested OK" };
  if (t?.mode === "cloudflare")
    return { id: "public_url", label, state: "ok", detail: "Temporary Cloudflare link — the webhook URL changes on every restart" };
  if (t?.mode === "none") return { id: "public_url", label, state: "fail", detail: t.error || "No tunnel running" };
  return { id: "public_url", label, state: "unknown", detail: "unknown — the API reports no tunnel state" };
}

function calendar(plan?: PlanSlice): CheckItem {
  const label = "Economic calendar (news blackouts)";
  if (plan?.calendar_loaded === undefined) return { id: "calendar", label, state: "unknown", detail: NO_DATA };
  return plan.calendar_loaded
    ? { id: "calendar", label, state: "ok", detail: "Loaded for this session" }
    : { id: "calendar", label, state: "fail", detail: "Not loaded — no calendar = no trading" };
}

function attestation(plan?: PlanSlice): CheckItem {
  const label = "External-positions attestation";
  if (plan?.attested_today === undefined) return { id: "attestation", label, state: "unknown", detail: NO_DATA };
  return plan.attested_today
    ? { id: "attestation", label, state: "ok", detail: "Done for this session" }
    : { id: "attestation", label, state: "fail", detail: "Not done yet — attest on Today or Trade before arming" };
}

function clock(): CheckItem {
  // The server's pre-flight currently feeds clock_drift_s = 0.0 (not measured), so its "ok" proves nothing.
  return { id: "clock", label: "Clock sync (drift < 2 s)", state: "unknown",
    detail: "unknown — the server does not measure clock drift yet (pre-flight assumes 0 s)" };
}

function preflight(plan?: PlanSlice): CheckItem {
  const label = "Pre-flight (last run)";
  if (!plan) return { id: "preflight", label, state: "unknown", detail: NO_DATA };
  if (!plan.preflight) return { id: "preflight", label, state: "unknown", detail: "unknown — not run yet this server session" };
  return plan.preflight.ok
    ? { id: "preflight", label, state: "ok", detail: "Passed" }
    : { id: "preflight", label, state: "fail", detail: `Failed: ${plan.preflight.failures.join(", ")}` };
}

export function buildChecklist(x0: ChecklistInput): { items: CheckItem[]; ready: Readiness } {
  // A partial/odd payload (older server, error body) counts as "not available", never as OK.
  const x: ChecklistInput = {
    conns: Array.isArray(x0.conns?.connections) ? x0.conns : undefined,
    webhook: typeof x0.webhook?.secret_set === "boolean" ? x0.webhook : undefined,
    plan: x0.plan && typeof x0.plan === "object" ? x0.plan : undefined,
  };
  const items = [broker(x.conns), heartbeat(x.conns), secret(x.webhook), publicUrl(x.conns), calendar(x.plan),
    attestation(x.plan), clock(), preflight(x.plan)];
  const ready: Readiness = items.some((i) => i.state === "fail") ? "no"
    : items.some((i) => i.state === "unknown") ? "unconfirmed" : "yes";
  return { items, ready };
}
