import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { AlertsBell, JobsIndicator } from "./HeaderAlerts";
import ManualTicket from "./ManualTicket";
import { PayoutSettings, PlanTracker } from "./PayoutPlan";
import TradeJournal, { journalQuery } from "./TradeJournal";
import Backtest from "../pages/Backtest";
import { EVENT_QUERIES, LiveProvider, useLiveEvent } from "../app/live";
import { browserNotify, disableBrowserNotify, enableBrowserNotify } from "../lib/notify";

const j = (o: unknown) => new Response(JSON.stringify(o));
function mock(calls: string[], routes: Record<string, unknown>) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    const u = String(url);
    calls.push(`${init?.method ?? "GET"} ${u}${init?.body ? " " + String(init.body) : ""}`);
    const key = Object.keys(routes).find((k) => u.startsWith(k));
    return j(key ? routes[key] : {});
  });
}
function wrap(ui: JSX.Element, qc = new QueryClient()) {
  render(<QueryClientProvider client={qc}><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{ui}</MemoryRouter></QueryClientProvider>);
  return qc;
}
afterEach(() => vi.restoreAllMocks());

test("alerts bell: unread count, list, mark one and all read", async () => {
  const calls: string[] = [];
  mock(calls, { "/api/notifications": { unread: 2, notifications: [
    { id: 5, level: "error", kind: "kill_switch", title: "KILL SWITCH", body: "by admin", created_at: "2026-11-06T15:00:00+00:00", read: false },
    { id: 4, level: "warn", kind: "inactivity", title: "Inactivity alert", body: "", created_at: "2026-11-06T14:00:00+00:00", read: false }] } });
  wrap(<AlertsBell />);
  expect(await screen.findByTestId("alerts-count")).toHaveTextContent("2");
  await userEvent.click(screen.getByTestId("alerts"));
  expect(screen.getByTestId("alert-5")).toHaveTextContent("KILL SWITCH");
  await userEvent.click(screen.getAllByRole("button", { name: "Mark read" })[0]!);
  expect(calls).toContain('POST /api/notifications/read {"ids":[5]}');
  await userEvent.click(screen.getByRole("button", { name: "Mark all read" }));
  expect(calls).toContain("POST /api/notifications/read {}");
});

test("jobs indicator lists running jobs", async () => {
  mock([], { "/api/jobs": { jobs: [{ id: "backtest-3", kind: "backtest", label: "Backtest #3 MGC EVAL", status: "running", progress: 40, at: "" }] } });
  wrap(<JobsIndicator />);
  await waitFor(() => expect(screen.getByTestId("jobs")).toHaveTextContent("1 job"));
  await userEvent.click(screen.getByTestId("jobs"));
  expect(screen.getByTestId("job-backtest-3")).toHaveTextContent("Backtest #3");
});

test("manual ticket posts to /api/orders/manual and shows the server verdict", async () => {
  const calls: string[] = [];
  mock(calls, {
    "/api/markets": { markets: [{ symbol: "MNQ", name: "Nasdaq", enabled: true }, { symbol: "MES", name: "S&P", enabled: false }] },
    "/api/orders/manual": { signal_id: 1, plan: { entry: "20000", stop: "19980", take_profit: "20040", rr: "2" }, result: { ok: false, reason: "HEDGE_LOCK" } },
  });
  wrap(<ManualTicket accounts={[{ id: 1, label: "E1", stage: "EVAL" }]} />);
  await screen.findByRole("option", { name: "Nasdaq (MNQ)" });
  expect(screen.queryByRole("option", { name: "S&P (MES)" })).toBeNull();
  const send = screen.getByTestId("ticket-submit");
  expect(send).toBeDisabled();
  await userEvent.selectOptions(screen.getByLabelText("Ticket side"), "SHORT");
  await userEvent.type(screen.getByLabelText("Ticket stop"), "20020");
  await userEvent.type(screen.getByLabelText("Ticket target"), "19960");
  await userEvent.click(send);
  expect(calls).toContain('POST /api/orders/manual {"account_id":1,"symbol":"MNQ","direction":"SHORT","stop":"20020","take_profit":"19960"}');
  expect(await screen.findByTestId("ticket-msg")).toHaveTextContent("HEDGE_LOCK");
});

test("payout settings save and plan tracker render real numbers", async () => {
  const calls: string[] = [];
  mock(calls, {
    "/api/payouts/settings": { skim_mode: "half", frequency: "weekly", check_time: "Fri 17:05", sweep_above: "28100", buffer: "26100" },
    "/api/plan": {
      tracker: { year: 2026, ytd_gross: "900", ytd_net: "810", target_net: "70000", floor_net: "50000", target_pct: "1.2", floor_pct: "1.6", payouts_processed: 1 },
      projection: { basis: "trailing", monthly_net: "270", months: [{ month: "2026-12", net: "270", cumulative: "270" }] },
      next_payout: { check_at: "2026-11-06T22:05:00+00:00", frequency: "weekly", skim_mode: "half", total: "600",
        accounts: [{ account_id: 2, label: "F1", balance: "28700", kind: "sweep", amount: "600", net: "540", reason: "SWEEP" },
          { account_id: 3, label: "F2", error: "broker not connected" }, { account_id: 4, label: "F3", balance: "25000", kind: null, amount: "0", net: "0", reason: "NO_PROFIT" }] },
    },
  });
  wrap(<><PayoutSettings /><PlanTracker /></>);
  await userEvent.selectOptions(await screen.findByLabelText("Payout mode"), "off");
  expect(calls).toContain('PUT /api/payouts/settings {"skim_mode":"off","frequency":"weekly"}');
  expect(await screen.findByTestId("next-2")).toHaveTextContent("sweep $600.00");
  expect(screen.getByTestId("next-3")).toHaveTextContent("broker not connected");
  expect(screen.getByTestId("next-4")).toHaveTextContent("no profit");
  expect(screen.getByTestId("plan-tracker")).toHaveTextContent("$810.00");
  expect(screen.getByTestId("projection")).toHaveTextContent("2026-12");
});

test("trade journal filters, snapshot, CSV link", async () => {
  const calls: string[] = [];
  mock(calls, { "/api/journal": { summary: { count: 1, closed: 1, wins: 1, net_pnl: "50" }, symbols: ["MNQ"], trades: [
    { id: 9, account: "E1", symbol: "MNQ", direction: "LONG", qty: 2, entry: "20000", exit: "20040", pnl_usd: "50", net_r: "1.9",
      exit_reason: "TP", opened_at: "2026-11-06T15:00:00+00:00", closed_at: "2026-11-06T15:30:00+00:00", mode: "PAPER", profile: "TIGHT", score: "72", snapshot: { invalid: "19990" } }] } });
  wrap(<TradeJournal />);
  expect(await screen.findByTestId("jt-9")).toHaveTextContent("▲ +$50.00");
  await userEvent.click(screen.getByRole("button", { name: "Snapshot" }));
  expect(screen.getByTestId("snap-9")).toHaveTextContent("19990");
  await userEvent.selectOptions(screen.getByLabelText("Journal result"), "win");
  await waitFor(() => expect(calls).toContain("GET /api/journal?result=win"));
  expect(screen.getByTestId("journal-csv")).toHaveAttribute("href", "/api/journal?result=win&format=csv");
  expect(journalQuery({ q: "", symbol: "MNQ" })).toBe("/api/journal?symbol=MNQ");
});

test("backtest delete asks for confirmation", async () => {
  const calls: string[] = [];
  mock(calls, { "/api/backtest": { runs: [{ id: 3, status: "done", error: null, params: { symbol: "MGC", stage: "EVAL", bias: "recorded", one_to_one: false, eval_mode: false }, metrics: {} },
    { id: 4, status: "running", error: null, params: { symbol: "MGC", stage: "EVAL", bias: "recorded", one_to_one: false, eval_mode: false }, metrics: {} }] } });
  const confirm = vi.spyOn(window, "confirm").mockReturnValueOnce(false).mockReturnValueOnce(true);
  wrap(<Backtest />);
  const del = await screen.findByTestId("bt-delete-3");
  expect(screen.queryByTestId("bt-delete-4")).toBeNull(); // running jobs cannot be deleted
  await userEvent.click(del);
  expect(calls.some((c) => c.startsWith("DELETE"))).toBe(false);
  await userEvent.click(del);
  expect(confirm).toHaveBeenCalledTimes(2);
  expect(calls).toContain("DELETE /api/backtest/3");
});

// ---------- shared WebSocket ----------
class FakeWS {
  static last: FakeWS | null = null;
  readyState = 1;
  onopen: (() => void) | null = null;
  onmessage: ((m: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  sent: string[] = [];
  constructor(public url: string) { FakeWS.last = this; }
  send(x: string) { this.sent.push(x); }
  close() { this.onclose?.(); }
  emit(event: string, data: unknown) { this.onmessage?.({ data: JSON.stringify({ event, data }) }); }
}

test("one shared socket on /api/ws invalidates queries per event and feeds subscribers", async () => {
  vi.stubGlobal("WebSocket", FakeWS);
  const qc = new QueryClient();
  const inv = vi.spyOn(qc, "invalidateQueries");
  const got: unknown[] = [];
  function Probe() { useLiveEvent("risk.alert", (d) => got.push(d)); return null; }
  wrap(<LiveProvider><Probe /></LiveProvider>, qc);
  const ws = FakeWS.last!;
  expect(ws.url.endsWith("/api/ws")).toBe(true);
  act(() => { ws.onopen?.(); ws.emit("risk.alert", { account: 1 }); ws.emit("job.progress", { id: "x" }); });
  expect(got).toEqual([{ account: 1 }]);
  const keys = inv.mock.calls.map((c) => (c[0] as { queryKey: string[] }).queryKey[0]);
  expect(keys).toEqual(expect.arrayContaining([...EVENT_QUERIES["risk.alert"]!, ...EVENT_QUERIES["job.progress"]!]));
  vi.unstubAllGlobals();
});

test("browser notifications are opt-in and permission-gated", async () => {
  const shown: string[] = [];
  class FakeNotification {
    static permission: NotificationPermission = "default";
    static requestPermission = vi.fn(async () => "denied" as NotificationPermission);
    constructor(title: string) { shown.push(title); }
  }
  vi.stubGlobal("Notification", FakeNotification);
  expect(browserNotify("x", "")).toBe(false); // not opted in
  expect(await enableBrowserNotify()).toBe("denied");
  expect(browserNotify("x", "")).toBe(false);
  FakeNotification.requestPermission = vi.fn(async () => { FakeNotification.permission = "granted"; return "granted" as NotificationPermission; });
  expect(await enableBrowserNotify()).toBe("granted");
  expect(browserNotify("KILL SWITCH", "by admin")).toBe(true);
  expect(shown).toEqual(["Paytience · KILL SWITCH"]);
  disableBrowserNotify();
  expect(browserNotify("y", "")).toBe(false);
  vi.unstubAllGlobals();
});
