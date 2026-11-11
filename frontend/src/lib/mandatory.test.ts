import type { Connection, ConnectionsResponse, WebhookStatus } from "./api";
import { buildChecklist, isMandatoryConnection } from "./mandatory";

const c = (id: string, status: Connection["status"], extra: Partial<Connection> = {}): Connection => ({
  id, name: id, category: "x", purpose: "", required: false, testable: true, steps: [], note: "", links: [], fields: [],
  status, detail: "", hints: {}, tested_at: null, ...extra,
});
const conns = (list: Connection[]): ConnectionsResponse => ({
  connections: list, indicators: [], summary: { connected: 0, total: list.length, required_ready: false },
  webhook_path: "/api/webhook/tradingview", master_key_set: true,
});
const hook = (secret_set: boolean): WebhookStatus => ({ path: "", secret_set, feeds: [], accepted: {}, rejected: {}, last_rejection: null });
const allGood = conns([
  c("crosstrade", "connected", { detail: "Key accepted" }),
  c("tradingview", "connected", { detail: "Receiving alerts" }),
  c("ngrok", "connected", { tunnel: { mode: "ngrok", ngrok_domain: "me.ngrok-free.app", public_url: "https://me.ngrok-free.app", permanent: true, error: "" } }),
]);
const goodPlan = { calendar_loaded: true, attested_today: true, preflight: { ok: true, failures: [], at: "2026-11-11T11:40:00Z" } };
const state = (r: ReturnType<typeof buildChecklist>, id: string) => r.items.find((i) => i.id === id)?.state;

test("mandatory set: broker route, TradingView, public URL, calendar — optional ones are not highlighted", () => {
  for (const id of ["tradingview", "crosstrade", "tradovate", "ngrok", "tunnel", "forexfactory"]) expect(isMandatoryConnection(id)).toBe(true);
  for (const id of ["discord", "telegram", "tradingagents", "vibetrading", "alpha_vantage", "fred", "databento", "openbb", "lucid", "github_updates", "trading_r1"])
    expect(isMandatoryConnection(id)).toBe(false);
});

test("no API data at all → every item unknown, readiness not confirmed (never YES)", () => {
  const r = buildChecklist({});
  expect(r.items.every((i) => i.state === "unknown")).toBe(true);
  expect(r.items.every((i) => i.detail.startsWith("unknown"))).toBe(true);
  expect(r.ready).toBe("unconfirmed");
});

test("everything the API reports is OK → only clock sync stays unknown (server does not measure drift)", () => {
  const r = buildChecklist({ conns: allGood, webhook: hook(true), plan: goodPlan });
  expect(r.items.filter((i) => i.state !== "ok").map((i) => i.id)).toEqual(["clock"]);
  expect(r.ready).toBe("unconfirmed");
});

test("any missing item → NO", () => {
  expect(buildChecklist({ conns: allGood, webhook: hook(false), plan: goodPlan }).ready).toBe("no");
  const noAttest = buildChecklist({ conns: allGood, webhook: hook(true), plan: { ...goodPlan, attested_today: false } });
  expect(noAttest.ready).toBe("no");
  expect(state(noAttest, "attestation")).toBe("fail");
  const pf = buildChecklist({ conns: allGood, webhook: hook(true), plan: { ...goodPlan, preflight: { ok: false, failures: ["calendar", "bias"], at: "" } } });
  expect(pf.items.find((i) => i.id === "preflight")?.detail).toBe("Failed: calendar, bias");
  expect(buildChecklist({ conns: conns([]), webhook: hook(true), plan: goodPlan }).items.find((i) => i.id === "broker")?.state).toBe("fail");
});

test("broker and feed edge cases", () => {
  const tvSaved = buildChecklist({ conns: conns([c("tradovate", "saved")]) });
  expect(state(tvSaved, "broker")).toBe("unknown");
  const ctFail = buildChecklist({ conns: conns([c("crosstrade", "failed", { detail: "401" })]) });
  expect(state(ctFail, "broker")).toBe("fail");
  const closed = buildChecklist({ conns: conns([c("tradingview", "waiting", { detail: "Market closed · MNQ TIGHT: closed (900 s ago)" })]) });
  expect(state(closed, "heartbeat")).toBe("unknown");
  const never = buildChecklist({ conns: conns([c("tradingview", "waiting", { detail: "Waiting for the first TradingView heartbeat" })]) });
  expect(state(never, "heartbeat")).toBe("fail");
  const cf = buildChecklist({ conns: conns([c("ngrok", "failed", { tunnel: { mode: "cloudflare", public_url: "https://x.trycloudflare.com", permanent: false, error: "" } })]) });
  expect(state(cf, "public_url")).toBe("ok");
  const none = buildChecklist({ conns: conns([c("ngrok", "not_set", { tunnel: { mode: "none", public_url: "", permanent: false, error: "" } })]) });
  expect(state(none, "public_url")).toBe("fail");
});

test("a malformed payload counts as unavailable, not OK", () => {
  const r = buildChecklist({ conns: {} as ConnectionsResponse, webhook: {} as WebhookStatus, plan: {} });
  expect(state(r, "broker")).toBe("unknown");
  expect(state(r, "webhook_secret")).toBe("unknown");
  expect(state(r, "calendar")).toBe("unknown");
});
