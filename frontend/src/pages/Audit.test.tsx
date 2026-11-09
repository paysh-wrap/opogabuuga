// §18 audit gaps: Dashboard plan/pace/cooldown, Risk preview + Eval Mode typed phrase + versions, Backtest compare,
// Connections test alert, Accounts history.
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "./Dashboard";
import Risk from "./Risk";
import Backtest from "./Backtest";
import Accounts from "./Accounts";
import TestAlert from "../components/TestAlert";
import { compareKind } from "../components/BacktestCompare";

const impact = { kind: "standard", risk_by_tier: { "1000": { "60": "70.00", "75": "90.00", "90": "110.00" } }, worst_day_at_1000: "160.00",
  dll_test_at_max_base: { base: "3000", loss1: "330", loss2: "186.9", total: "516.9", dll: "600" }, losses_to_pause_from_1000: 8 };
let evalOn = false;

function mock(calls: string[]) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    const u = String(url);
    const m = init?.method ?? "GET";
    calls.push(`${m} ${u}${init?.body ? " " + String(init.body) : ""}`);
    const j = (o: unknown) => new Response(JSON.stringify(o));
    if (u === "/api/dashboard") return j({ session: "2026-11-06", mode: "OFF", bias: {}, accounts: [
      { id: 1, label: "E1", stage: "EVAL", paper: true, armed: false, paused: null, balance: "25200", today_pnl: "0", open_pnl: "0", trades_today: 0,
        mll: "24000", to_mll: "1200", max_loss: "1500", kill_at: "100", idle_days: 3, idle_alert_days: 21, guard_on: false, eval_mode_on: true, day_lockin: true, day_net_r: "2.1", day_lockin_r: "2" }] });
    if (u === "/api/markets") return j({ markets: [] });
    if (u === "/api/market/openbb") return j({ status: "LOADING", source: "x" });
    if (u === "/api/signals/skips") return j({ date: "2026-11-06", counts: {}, avg_20: {}, sessions_in_avg: 0 });
    if (u === "/api/plans") return j({ current: "a", plans: [] });
    if (u === "/api/live") return j({ live: false, toggle_on: false, phrase: "I ACCEPT LIVE RISK", checklist: [] });
    if (u === "/api/risk/low-risk") return j({ enabled: false, max_losses_per_day: 2, max_trades_per_day: 3 });
    if (u === "/api/plan") return j({ tracker: { year: 2026, ytd_net: "5000", target_net: "70000", floor_net: "50000", target_pct: "7.1", floor_pct: "10.0" },
      next_payout: { check_at: "2026-11-06T22:05:00+00:00", frequency: "weekly", total: "600", accounts: [{ account_id: 2, label: "F1", kind: "sweep", amount: "600" }] } });
    if (u === "/api/accounts/1/eval-pace") return j({ id: 1, label: "E1", profit: "200", target: "1250", target_left: "1050", profitable_days: 1, min_profitable_days: 3,
      sessions_used: 2, target_sessions: 10, max_sessions: 20, largest_day: "150", consistency_cap: "500", consistency_day_stop: "437.50", consistency_headroom: "350", consistency_pct: "40" });
    if (u === "/api/cooldowns") return j({ cooldowns: [{ symbol: "MNQ", profile: "TIGHT", streak: 3, until_session: "2026-11-13", active: true }] });
    if (u.startsWith("/api/cooldowns/")) return j({ cleared: 1 });
    if (u === "/api/automation") return j({ mode: "SEMI-AUTO", approvals: [{ signal_id: 4, expires: "2026-11-06T15:00:00+00:00" }] });
    if (u === "/api/bias") return j({ decisions: [{ proxy: "QQQ", raw: "OVERWEIGHT", mapped: "LONG_ONLY" }] });
    if (u === "/api/today/plan") return j({ calendar_loaded: true, news: [] });
    if (u === "/api/risk/settings") return j({ version: 3, settings: { "internal.risk_pct_floor": "0.07", "internal.day_lockin_r": "2" }, validation: { ok: true, errors: [], warnings: [] }, eval_mode_on: evalOn, error: null });
    if (u === "/api/risk/eval-mode" && m === "GET") return j({ enabled: evalOn, has_eval_accounts: true, confirm_phrase: "ENABLE EVALUATION MODE", accounts: [] });
    if (u === "/api/risk/eval-mode") { evalOn = JSON.parse(String(init?.body)).enabled; return j({}); }
    if (u === "/api/risk/eval-mode/preview") return j({ on: { ...impact, kind: "evaluation" }, off: impact });
    if (u === "/api/risk/preview") return j({ valid: true, errors: [], warnings: [], preview: impact });
    if (u === "/api/risk/versions") return j({ versions: [{ kind: "standard", version: 3, author: "admin", note: "", diff: {}, active: true, at: "2026-11-05T15:00:00+00:00" },
      { kind: "standard", version: 2, author: "admin", note: "", diff: { a: 1 }, active: false, at: "2026-11-04T15:00:00+00:00" }] });
    if (u.startsWith("/api/risk/rollback/")) return j({});
    if (u === "/api/rules") return j({ rules: { eval: { drawdown_type: "eod", daily_loss_limit: "600", consistency_max_day_pct: "40", profit_target: "1250", max_loss_limit: "1000" },
      internal: { day_lockin_r: "2", kill_switch_mll_distance: "100", pause_below_risk_base: "500", auto_flatten: "16:40" } }, verify_paths: ["eval.x"], verified_paths: [], firm_version: 1 });
    if (u.startsWith("/api/logs")) return j({ logs: [{ id: 5, at: "2026-11-05T15:00:00+00:00", actor: "admin", action: "risk.eval_mode.account", entity: "1", payload: { override: "on" } }] });
    if (u === "/api/accounts") return j({ accounts: [{ id: 1, broker_account_id: "P1", label: "E1", stage: "EVAL", paper: true, drawdown_type: "eod", drawdown_check: null, dll_enabled: true,
      eval_mode: "inherit", eval_mode_effective: false, armed: false, selected: true, priority: 0, mll_locked: false, paused_reason: null }] });
    if (u === "/api/webhook/test-alert") return j({ ok: false, code: "BAD_SECRET", detail: "secret does not match" });
    if (u === "/api/backtest") return j({ runs: [
      { id: 2, status: "done", error: null, params: { symbol: "MGC", stage: "EVAL", bias: "recorded", one_to_one: false, eval_mode: false, drawdown_type: "eod" },
        metrics: { stats: { trades: 40, win_rate: "0.5", net: "900", avg_r: "0.3", profit_factor: "1.5", max_drawdown: "300", best_day_share: "0.2", days: 20 },
          payout_sim: { weeks: [{ week: 1, profit: "700", balance: "28800", kind: "sweep", amount: "700", net: "630", reason: "x" }], total_gross: "700", total_net: "630", breached: false },
          income_mc: { runs: 10000, sessions: 252, floor: "50000", target: "70000", by_accounts: { "1": { median_net: "20000", p_floor: "0.1", p_target: "0.02", p_breach: "0.1" } } } } },
      { id: 1, status: "done", error: null, params: { symbol: "MGC", stage: "EVAL", bias: "recorded", one_to_one: false, eval_mode: false, drawdown_type: "intraday" },
        metrics: { stats: { trades: 38, win_rate: "0.55", net: "1000", avg_r: "0.35", profit_factor: "1.6", max_drawdown: "250", best_day_share: "0.2", days: 20 } } }] });
    return j({});
  });
}
function wrap(ui: JSX.Element) {
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{ui}</MemoryRouter></QueryClientProvider>);
}
afterEach(() => vi.restoreAllMocks());

test("Dashboard: $50k/$70k progress, Friday estimate, badges, days since trade, consistency headroom, cooldown clear", async () => {
  const calls: string[] = [];
  mock(calls);
  wrap(<Dashboard />);
  expect(await screen.findByTestId("progress-floor")).toHaveTextContent("10.0%");
  expect(screen.getByTestId("progress-target")).toHaveTextContent("$70,000");
  expect(screen.getByTestId("next-payout")).toHaveTextContent("$600");
  expect(screen.getByTestId("badges-1")).toHaveTextContent("GUARD OFF");
  expect(screen.getByTestId("badges-1")).toHaveTextContent("EVAL MODE");
  expect(screen.getByTestId("badges-1")).toHaveTextContent("DAY LOCK-IN");
  expect(screen.getByText("Days since last trade")).toBeInTheDocument();
  expect(await screen.findByTestId("headroom-1")).toHaveTextContent("$350");
  expect(await screen.findByTestId("dash-approvals")).toHaveTextContent("Signal #4");
  expect(await screen.findByTestId("dash-bias")).toHaveTextContent("OVERWEIGHT");
  await userEvent.click(await screen.findByRole("button", { name: "Clear…" }));
  const btn = screen.getByRole("button", { name: "Clear cooldown" });
  expect(btn).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Cooldown clear confirmation"), "CLEAR COOLDOWN");
  await userEvent.click(btn);
  await waitFor(() => expect(calls).toContain('POST /api/cooldowns/TIGHT/clear {"confirm":"CLEAR COOLDOWN","symbol":"MNQ"}'));
});

test("Risk: Eval Mode needs preview + typed phrase, OFF is one click; settings need preview before save; rollback", async () => {
  evalOn = false;
  const calls: string[] = [];
  mock(calls);
  vi.spyOn(window, "confirm").mockReturnValue(true);
  wrap(<Risk />);
  expect(await screen.findByTestId("eval-mode-main")).toHaveTextContent("150K trades 4 micros"); // D66
  await userEvent.click(await screen.findByTestId("eval-mode-preview"));
  expect(await screen.findByTestId("eval-preview-on")).toHaveTextContent("$110.00");
  const enable = screen.getByTestId("eval-mode-enable");
  expect(enable).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Evaluation Mode confirmation"), "ENABLE EVALUATION MODE");
  await userEvent.click(enable);
  await waitFor(() => expect(calls).toContain('PUT /api/risk/eval-mode {"enabled":true,"confirm":"ENABLE EVALUATION MODE"}'));
  await userEvent.click(await screen.findByTestId("eval-mode-off"));
  await waitFor(() => expect(calls).toContain('PUT /api/risk/eval-mode {"enabled":false,"confirm":""}'));

  await userEvent.click(screen.getByText(/Show all/));
  const input = screen.getByLabelText("internal.risk_pct_floor");
  await userEvent.clear(input);
  await userEvent.type(input, "0.06");
  expect(screen.getByTestId("risk-save")).toBeDisabled();
  await userEvent.click(screen.getByTestId("risk-preview"));
  expect(await screen.findByTestId("risk-impact")).toHaveTextContent("$70.00");
  await userEvent.click(screen.getByTestId("risk-save"));
  await waitFor(() => expect(calls.some((c) => c.startsWith("PUT /api/risk/settings"))).toBe(true));

  await userEvent.click(await screen.findByRole("button", { name: "Roll back to v2" }));
  await waitFor(() => expect(calls).toContain("POST /api/risk/rollback/2"));
  expect(await screen.findByTestId("firm-rules")).toHaveTextContent("EOD drawdown");
  expect(screen.getByTestId("firm-rules")).toHaveTextContent("VERIFY");
  expect(await screen.findByTestId("meter-1-mll")).toHaveTextContent("20% used · $1,200 left of $1,500");
  expect(screen.getByTestId("risk-gauges")).toHaveTextContent("E1");
});

test("Backtest: compare guard ON/OFF, payout simulation and Monte Carlo P(≥$50k)", async () => {
  mock([]);
  wrap(<Backtest />);
  expect(await screen.findByTestId("compare-kind")).toHaveTextContent("Guard ON vs OFF");
  expect(screen.getByTestId("bt-compare")).toHaveTextContent("$1,000");
  expect(screen.getByTestId("mc-n-1")).toHaveTextContent("10.0%");
  expect(screen.getAllByTestId("bt-payouts")[0]).toHaveTextContent("sweep $700");
  expect(compareKind({ symbol: "a", stage: "EVAL", bias: "recorded", one_to_one: false, eval_mode: true },
    { symbol: "a", stage: "EVAL", bias: "recorded", one_to_one: false, eval_mode: false })).toBe("Eval Mode ON vs OFF");
  expect(compareKind({ symbol: "a", stage: "EVAL", bias: "recorded", one_to_one: false, eval_mode: false },
    { symbol: "a", stage: "EVAL", bias: "NEUTRAL", one_to_one: false, eval_mode: false })).toBe("Bias ablation");
  expect(compareKind({ symbol: "a", stage: "EVAL", bias: "x", one_to_one: false, eval_mode: false },
    { symbol: "b", stage: "EVAL", bias: "y", one_to_one: false, eval_mode: false })).toBeNull();
});

test("Connections test alert is a dry run that reports the result", async () => {
  const calls: string[] = [];
  mock(calls);
  wrap(<TestAlert />);
  await userEvent.type(screen.getByLabelText("Alert message"), "x");
  await userEvent.click(screen.getByRole("button", { name: "Check alert" }));
  expect(await screen.findByTestId("test-alert-result")).toHaveTextContent("BAD_SECRET");
  expect(calls).toContain("POST /api/webhook/test-alert x");
});

test("Accounts: per-account history and Lucid link", async () => {
  mock([]);
  wrap(<Accounts />);
  expect(await screen.findByTestId("history-1")).toHaveTextContent("risk.eval_mode.account");
  expect(screen.getByRole("link", { name: /Open Lucid dashboard/ })).toHaveAttribute("target", "_blank");
});
