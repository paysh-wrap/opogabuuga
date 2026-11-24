import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import StrategyButtons, { type StrategiesResp, type Strat } from "./StrategyButtons";
import AiAdviceCard from "./AiAdvice";
import { runningNames } from "./NowRunning";

const st = (key: string, enabled: boolean, extra: Partial<Strat> = {}): Strat => ({ key, name: `${key} name`, source: "", verified: false, status: "", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: null, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "", note: "n", enabled, setting: `strategy.${key}`, ...extra });
const combined = (over = {}) => ({ key: "main_fast_pass_order_flow", title: "MAIN FAST PASS + ORDER FLOW (separate accounts)", enabled: false, setting: "strategy.order_flow_cfg.ar_side_by_side", settings_on: ["strategy.noise", "strategy.candace_ict", "strategy.order_flow", "strategy.order_flow_cfg.ar_side_by_side"], eligible_accounts: 2, min_accounts: 2, can_start: true, blocked_reason: null, guards: ["Order Flow trades only on a DIFFERENT free account than NOISE / CANDACE (one account per trade)."], ...over });
const base = (over: Partial<StrategiesResp> = {}): StrategiesResp => ({
  strategies: [st("noise", true), st("candace_ict", true), st("order_flow", false), st("order_flow_zone", false, { setting: "strategy.order_flow_cfg.zone_atr.enabled", disabled: true, off_for_now: "OFF for now" })],
  noise_warmup: { sessions: 10, needed: 10, ready: true }, ai_ledger: [], markets: { MNQ: true },
  combined: combined(), ...over,
});
function mount(resp: StrategiesResp) {
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    calls.push(`${init?.method ?? "GET"} ${String(url)} ${init?.body ? String(init.body) : ""}`);
    return new Response(JSON.stringify(String(url) === "/api/strategies" ? resp : {}));
  });
  render(<QueryClientProvider client={new QueryClient()}><StrategyButtons /></QueryClientProvider>);
  return calls;
}
afterEach(() => vi.restoreAllMocks());

test("combined option: labelled option, guards in plain words, turns the 4 settings on and other choices off", async () => {
  const resp = base({ strategies: [...base().strategies, st("jj_fpt", true)] });
  resp.strategies[0] = st("noise", false); resp.strategies[1] = st("candace_ict", false);
  const calls = mount(resp);
  const card = await screen.findByTestId("combined-choice");
  expect(card).toHaveTextContent("OPTION");
  expect(card).toHaveTextContent("default OFF");
  expect(screen.getByTestId("combined-guards")).toHaveTextContent("DIFFERENT free account");
  await userEvent.click(screen.getByTestId("combined-toggle"));
  await waitFor(() => expect(calls.some((c) => c.startsWith("PUT /api/risk/settings") && c.includes('"strategy.jj_fpt":false') && c.includes('"strategy.order_flow_cfg.ar_side_by_side":true') && c.includes('"strategy.noise":true'))).toBe(true));
});

test("combined option with fewer than 2 eligible accounts is blocked and says why", async () => {
  mount(base({ combined: combined({ can_start: false, eligible_accounts: 1, blocked_reason: "needs at least 2 eligible accounts (selected, not paused, not closed); found 1" }) }));
  expect(await screen.findByTestId("combined-blocked")).toHaveTextContent("found 1");
  expect(screen.getByTestId("combined-toggle")).toBeDisabled();
});

test("Iceberg proxy card is greyed out, disabled and says OFF for now", async () => {
  mount(base());
  const t = await screen.findByTestId("disabled-toggle-order_flow_zone");
  expect(t).toBeDisabled();
  expect(t).toHaveTextContent("OFF for now");
  expect(screen.getByTestId("strategy-order_flow_zone")).toHaveAttribute("aria-disabled", "true");
});

test("plain Order Flow on turns MAIN off and sets the combined switch off", async () => {
  const calls = mount(base());
  await userEvent.click(await screen.findByRole("button", { name: /order_flow name/ }));
  await waitFor(() => expect(calls.some((c) => c.startsWith("PUT") && c.includes('"strategy.noise":false') && c.includes('"strategy.order_flow":true') && c.includes('"strategy.order_flow_cfg.ar_side_by_side":false'))).toBe(true));
});

test("size card shows the fast-pass numbers from the API, EVAL-only note and the fallback profile", async () => {
  const fp = { key: "fast_pass_50k", account_size: "50000", on: true, noise_contracts: 2, noise_stop_usd: "75", noise_steps: [{ cushion_usd: "667", contracts: 1 }], noise_grow_per: null, noise_max_contracts: null, noise_lock_trigger_pts: "80", candace_contracts: 4, candace_steps: [{ cushion_usd: "1000", contracts: 3 }], candace_grow_per: null, candace_max_contracts: null, brake_inclusive: false, day_lock_pct: "0.4", late_contracts: null, late_steps: [], late_on: false };
  mount(base({ size_profiles: { active: "regular", setting: "strategy.high_risk", regular: [{ account_size: "25000", contracts: 1, brake_below: null, brake_contracts: null }], high: [{ account_size: "25000", contracts: 1, brake_below: null, brake_contracts: null }], fast_pass_plans: [fp] } }));
  const row = await screen.findByTestId("fp-size-fast_pass_50k");
  expect(row).toHaveTextContent("NOISE: 2 micros at a $75 stop per micro");
  expect(row).toHaveTextContent("< $667: 1");
  expect(row).toHaveTextContent("CANDACE: 4 micros");
  expect(screen.getByTestId("fast-pass-stage-note")).toHaveTextContent("EVAL accounts only");
  expect(screen.getByTestId("fast-pass-stage-note")).toHaveTextContent("FUNDED and LIVE accounts only when their own switch");
  expect(screen.getByTestId("size-fallback-title")).toHaveTextContent("Fallback profile");
  expect(screen.getByTestId("size-stop-note")).not.toHaveTextContent("$250");
});

test("a stored-combination fallback shows a banner", async () => {
  mount(base({ notice: "Stored settings had two strategy choices ON; turned OFF: order_flow (only MAIN stays; D167/D175)." }));
  expect(await screen.findByTestId("strategy-notice")).toHaveTextContent("turned OFF: order_flow");
});

test("Now running names the combined choice once, never MAIN + Order Flow separately", () => {
  const s = [st("noise", true), st("candace_ict", true), st("order_flow", true)];
  expect(runningNames(s, { enabled: true, title: "MAIN FAST PASS + ORDER FLOW (separate accounts)" })).toEqual(["MAIN FAST PASS + ORDER FLOW (separate accounts)"]);
});

test("TradingAgents advice card: advice only label, run times, NO_CALL reason", () => {
  render(<AiAdviceCard advice={{ label: "x", mode: "ADVISORY", session: "2026-11-24", runs: [
    { minutes_before: 240, at: "05:30", results: [{ symbol: "MNQ", status: "OK", side: "SHORT", at: "2026-11-24T10:30:05+00:00", advice: { main: "leans SHORT" } }] },
    { minutes_before: 60, at: "08:30", results: [{ symbol: "MNQ", status: "NO_CALL", reason: "run failed (TimeoutError)" }] },
    { minutes_before: 30, at: "09:00", results: [{ symbol: "MNQ", status: "PENDING" }] }] }} />);
  expect(screen.getByTestId("ai-advice-label")).toHaveTextContent("Advice only, never blocks trading");
  expect(screen.getByTestId("ai-advice-run-240")).toHaveTextContent("05:30");
  expect(screen.getByTestId("ai-advice-run-60")).toHaveTextContent("run failed (TimeoutError) (advice unavailable; trading unaffected)");
});
