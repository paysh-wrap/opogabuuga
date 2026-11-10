import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Trade from "./Trade";
import Accounts from "./Accounts";
import Settings from "./Settings";

function mock(calls: string[], attested = false) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    const u = String(url);
    calls.push(`${init?.method ?? "GET"} ${u}${init?.body ? " " + String(init.body) : ""}`);
    const j = (o: unknown) => new Response(JSON.stringify(o));
    if (u === "/api/automation") return j({ mode: "SEMI-AUTO", broker: "paper", attested_today: attested, entries_blocked_by_time: false, rules_error: null,
      approvals: [{ signal_id: 9, expires: "2026-11-06T15:00:00+00:00" }] });
    if (u === "/api/automation/preflight") return j({ ok: false, checks: [{ check: "attested", ok: false, detail: "not attested" }] });
    if (u === "/api/positions") return j({ accounts: [{ account_id: 1, label: "E1", balance: "25000", open_pnl: "-12.5", mll: "24000", positions: [{ symbol: "MNQ", qty: -2, avg: "20000", exit_pending: "NOISE_TRAIL" }] }] });
    if (u === "/api/accounts") return j({ accounts: [
      { id: 1, broker_account_id: "P1", label: "E1", stage: "EVAL", paper: true, drawdown_type: "eod", drawdown_check: null, dll_enabled: true, eval_mode: "inherit", eval_mode_effective: false, armed: false, selected: true, priority: 0, mll_locked: false, paused_reason: null, mode_override: "inherit", consistency_pct: "40" },
      { id: 2, broker_account_id: "P2", label: "F1", stage: "FUNDED", paper: true, drawdown_type: "eod", drawdown_check: null, dll_enabled: true, eval_mode: "inherit", eval_mode_effective: false, armed: false, selected: false, priority: 1, mll_locked: false, paused_reason: null }] });
    if (u === "/api/orders?limit=25") return j({ orders: [{ id: 7, created_at: "2026-11-06T15:00:00+00:00", account: "E1", symbol: "MGC", kind: "bracket", side: "SELL", qty: 2, price: "4100.5", status: "FILLED", source: "MANUAL", filled_qty: 2, avg_fill: "4100.40" }] });
    if (u === "/api/dashboard") return j({ accounts: [{ id: 1, idle_days: 25, idle_alert_days: 21 }] });
    if (u === "/api/health") return j({ mode: "PAPER" });
    if (u === "/api/rules") return j({ rules: { schedule: { preflight: "02:50", sync: ["18:00", "16:50"] }, automation: { default_mode: "OFF", accounts_to_trade: 5, selection_mode: "priority", semi_auto_sessions_per_stage: 5, require_external_attestation: true, auto_resume_after_recovery: { paper: true, live: false } }, score: { weights: { cisd_before_c2_close: 25, choch_after_sweep: 20 }, min_score: 60, neutral_min_score: 60, osc_strength_min: 20 } }, verify_paths: ["a.b"] });
    if (u === "/api/connections") return j({ connections: [{ id: "x", name: "Telegram", status: "not_set", required: false }] });
    if (u === "/api/gate/purchase") return j({ run_id: null, passed: false, unmeasured: ["violations"], checks: [{ key: "trades", label: "Backtest trades", need: ">= 100", value: null, ok: null }] });
    return j({});
  });
}
function wrap(ui: JSX.Element) {
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{ui}</MemoryRouter></QueryClientProvider>);
}
afterEach(() => vi.restoreAllMocks());

test("Trade: approvals execute/skip, positions, arming gated on attestation, FLATTEN ALL typed", async () => {
  const calls: string[] = [];
  mock(calls);
  wrap(<Trade />);
  expect(await screen.findByTestId("approval-9")).toBeInTheDocument();
  expect(await screen.findByTestId("position-1")).toHaveTextContent("▼ SHORT 2");
  expect(screen.getByTestId("exit-pending-1")).toHaveTextContent("exit pending broker confirmation");
  expect(document.title).toBe("Paytience · Trade");
  expect(await screen.findByTestId("order-7")).toHaveTextContent("▼ SELL 2 bracket");
  expect(screen.getByTestId("order-7")).toHaveTextContent("2 @ 4100.40");
  expect(await screen.findByTestId("arm-1")).toBeDisabled(); // not attested
  await userEvent.click(screen.getByRole("button", { name: "Execute all selected" }));
  expect(calls).toContain("POST /api/signals/9/execute {}");
  await userEvent.click(screen.getByRole("button", { name: "Skip" }));
  expect(calls).toContain("POST /api/signals/9/skip");
  const all = screen.getByTestId("flatten-all");
  expect(all).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Type FLATTEN ALL"), "FLATTEN ALL");
  await userEvent.click(all);
  expect(calls).toContain('POST /api/flatten-all {"confirm":"FLATTEN ALL"}');
  await userEvent.click(screen.getByLabelText(/I hold no open positions/));
  await userEvent.click(screen.getByTestId("attest"));
  expect(calls).toContain('POST /api/attestation {"confirm":true}');
});

test("Trade: arm works once attested", async () => {
  const calls: string[] = [];
  mock(calls, true);
  wrap(<Trade />);
  await userEvent.click(await screen.findByTestId("arm-1"));
  expect(calls).toContain('PATCH /api/accounts/1 {"armed":true}');
  expect(screen.getByTestId("attested")).toBeInTheDocument();
});

test("Accounts: selector, priority, drawdown, eval override (EVAL only), inactivity", async () => {
  const calls: string[] = [];
  mock(calls);
  wrap(<Accounts />);
  expect(await screen.findByTestId("trading-n")).toHaveTextContent("1 of 2");
  expect(await screen.findByTestId("idle-1")).toHaveTextContent("inactivity alert");
  expect(screen.getByTestId("eval-1")).toBeInTheDocument();
  expect(screen.queryByTestId("eval-2")).toBeNull();
  await userEvent.click(screen.getByTestId("sel-2"));
  expect(calls).toContain('PUT /api/accounts/selection {"count":2,"order":[]}');
  await userEvent.click(screen.getByRole("button", { name: "Move E1 down" }));
  expect(calls).toContain('PUT /api/accounts/selection {"count":1,"order":[2,1]}');
  await userEvent.click(screen.getByTestId("dd-1-intraday"));
  expect(calls).toContain('PATCH /api/accounts/1 {"drawdown_type":"intraday"}');
  await waitFor(() => expect(screen.getByTestId("eval-1")).toBeEnabled());
  fireEvent.change(screen.getByTestId("eval-1"), { target: { value: "off" } });
  await waitFor(() => expect(calls).toContain('PATCH /api/accounts/1/eval-mode {"override":"off"}'));
  expect(screen.getByTestId("cons-1")).toHaveTextContent("Consistency 40% max day");
  expect(screen.getByTestId("cons-2")).toHaveTextContent("Consistency none");
  await waitFor(() => expect(screen.getByTestId("override-1")).toBeEnabled());
  fireEvent.change(screen.getByTestId("override-1"), { target: { value: "SEMI" } });
  await waitFor(() => expect(calls).toContain('PATCH /api/accounts/1 {"mode_override":"SEMI"}'));
  expect(document.title).toBe("Paytience · Accounts");
});

test("Settings: mode, schedule, connections and purchase gate from the API", async () => {
  mock([]);
  wrap(<Settings />);
  expect(await screen.findByTestId("settings-mode")).toHaveTextContent("PAPER");
  expect(await screen.findByTestId("settings-schedule")).toHaveTextContent("18:00, 16:50");
  expect(await screen.findByTestId("settings-connections")).toHaveTextContent("Telegram");
  expect(await screen.findByTestId("gate-status")).toHaveTextContent("Not passed");
  expect(screen.getByTestId("gate-trades")).toHaveTextContent("not tracked");
  expect(document.title).toBe("Paytience · Settings");
  expect(await screen.findByTestId("settings-weights")).toHaveTextContent("cisd before c2 close25");
  expect(screen.getByText(/neutral-bias minimum 60/)).toBeInTheDocument();
});
