import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import StrategyButtons, { type StrategiesResp } from "./StrategyButtons";

const resp: StrategiesResp = {
  strategies: [
    { key: "pm_fade", name: "MAIN — NOISE + Afternoon fade ($250 stops, MNQ)", source: "s", verified: true, status: "MAIN", win_pct: 50, profit_factor: 1.33, usd_per_trade: 19.63, trades_per_week: 5.2, held_out_trades: 1291, pro25k_pass_pct: 65.7, pro25k_bust_pct: 32.2, period: "p", note: "n", enabled: false, setting: "strategy.pm_fade", also: ["strategy.noise"] },
    { key: "noise", name: "NOISE — intraday momentum (MNQ)", source: "Zarattini", verified: true, status: "VERIFIED", win_pct: 45, profit_factor: 1.33, usd_per_trade: 25.81, trades_per_week: 3, held_out_trades: 440, pro25k_pass_pct: 56.9, pro25k_bust_pct: 42.2, eval_odds: { plan: "lucid_pro_25k", table: "regular", eod_on: false, text: "pass 56.9% / bust 42.2% · last 12 mo 55/45 · EOD toggle OFF", pass_pct: 56.9, bust_pct: 42.2, last12_pass_pct: 55, last12_bust_pct: 45 }, period: "held-out 2024-01 → 2026-11", note: "n", enabled: true, setting: "strategy.noise" },
    { key: "noise_ai_split", name: "NOISE + AI Duo — 50/50 risk split", source: "s", verified: false, status: "UNVERIFIED", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: null, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "NOT measured", note: "n", enabled: false, setting: "strategy.noise_ai_split", also: ["strategy.noise", "strategy.ai_duo"] },
    { key: "order_flow", name: "Order Flow — TradingView order-flow alerts (MNQ + MGC) — UNVERIFIED", source: "s", verified: false, status: "UNVERIFIED", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: null, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "NOT tested", note: "n", enabled: false, setting: "strategy.order_flow", instruments: ["MNQ", "MGC"], paper_only: false, flat_at: "16:00", ar_layers: [{ key: "ENVIRONMENT", on: true, rule: "no compression" }, { key: "PATH", on: false, rule: "Asia zones" }] },
    { key: "order_flow_amt", name: "AMT+ Order Flow — context → location → order flow last — UNVERIFIED", source: "s", verified: false, status: "UNVERIFIED", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: null, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "NOT tested", note: "n", enabled: false, setting: "strategy.order_flow_cfg.amt.enabled", also: ["strategy.order_flow"], amt_layers: [{ key: "CONTEXT", on: false, rule: "acceptance vs prior RTH value" }] },
    { key: "order_flow_zone", name: "Order Flow · ATR zones (iceberg PROXY) — UNVERIFIED", source: "s", verified: false, status: "UNVERIFIED", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: null, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "NOT tested", note: "n", enabled: false, setting: "strategy.order_flow_cfg.zone_atr.enabled", also: ["strategy.order_flow"], zone_layers: [{ key: "EVENT", on: false, rule: "footprint absorption zone" }] },
    { key: "ai_bias", name: "AI only — TradingAgents + Vibe-Trading (MNQ)", source: "s", verified: false, status: "UNVERIFIED", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: 1.35, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "NOT back-testable", note: "n", enabled: false, setting: "strategy.ai_bias" },
  ],
  noise_warmup: { sessions: 3, needed: 10, ready: false },
  ai_ledger: [{ proxy: "QQQ", symbol: "MNQ", state: "WARMUP", badge: "ADVISORY", required_accuracy: 0.7, min_calls: 30, stats: { n: 0, hit_rate: 0, brier: 0.25, wilson_lb: 0 } }],
  markets: { MNQ: true, MGC: false },
  ai_duo_log: [
    { day: "2026-11-09", status: "SKIP", code: "AI_DISAGREE", direction: "NONE", label: "BUY·VT SHORT 85", agrees_with_noise: null },
    { day: "2026-11-06", status: "PASS", code: "TAKEN", direction: "LONG", label: "BUY·VT LONG 80", agrees_with_noise: true },
  ],
  size_profiles: {
    active: "regular", setting: "strategy.high_risk",
    regular: [{ account_size: "25000", contracts: 1, brake_below: null, brake_contracts: null }, { account_size: "150000", contracts: 3, brake_below: "0.5", brake_contracts: 2 }],
    high: [{ account_size: "25000", contracts: 1, brake_below: null, brake_contracts: null }, { account_size: "150000", contracts: 4, brake_below: "0.5", brake_contracts: 2 }],
    eval_regular: [{ account_size: "25000", contracts: 1, brake_below: null, brake_contracts: null }],
    eval_high: [{ account_size: "25000", contracts: 3, brake_below: null, brake_contracts: null, stop_usd: "150", taper_below_remaining: "0.5", taper_contracts: 1 }],
    suggested: [{ account_size: "25000", contracts: 1, brake_below: null, brake_contracts: null }, { account_size: "50000", contracts: 1, brake_below: null, brake_contracts: null }],
    suggested_on: false, suggested_setting: "strategy.suggested_size",
    odds: { regular: { plan: "p", table: "regular", eod_on: false, text: "pass 70% / bust 30% · last 12 mo 60/40 · EOD toggle OFF", pass_pct: 70, bust_pct: 30, last12_pass_pct: 60, last12_bust_pct: 40 }, suggested: { plan: "p", table: "suggested", eod_on: false, text: "pass 90% / bust 10% · last 12 mo 85/15 · EOD toggle OFF", pass_pct: 90, bust_pct: 10, last12_pass_pct: 85, last12_bust_pct: 15 } },
  },
  toggles: [
    { key: "fade_eval_off", setting: "strategy.pm_fade_cfg.eval_off", title: "Afternoon fade during evaluations", value: true, on_label: "Off on EVAL accounts (default — better pass/bust)", off_label: "On everywhere", note: "EVAL stage only" },
    { key: "eod_closed_balance", setting: "strategy.eod_closed_balance", title: "EOD drawdown: open losses don't stop the account", value: false, on_label: "EOD accounts: kill switch watches the closed balance only", off_label: "Kill switch watches balance + open P&L (default, safest)", note: "VERIFY with Lucid that an open loss touching the floor does not breach an EOD account.",
      compare: { text: "x", source: "docs/results/session22/eod_vs_intraday/RESULTS.md",
        current: { plan: "lucid_pro_25k", eod: { pass: 57, bust: 43, j_pass: 40, j_bust: 60 }, intraday: { pass: 39, bust: 61, j_pass: 21, j_bust: 79 } },
        rows: [{ plan: "lucid_pro_25k", eod: { pass: 57, bust: 43, j_pass: 40, j_bust: 60 }, intraday: { pass: 39, bust: 61, j_pass: 21, j_bust: 79 } },
          { plan: "lucid_flex_150k", eod: { pass: 78, bust: 16, j_pass: 70, j_bust: 8 }, intraday: { pass: 72, bust: 22, j_pass: 56, j_bust: 15 } }] } },
    { key: "noise_lock_alt", setting: "strategy.noise_lock_alt", title: "NOISE profit-lock trigger", value: false, on_label: "80 pt — experimental, likely chance", off_label: "100 pt (default, session-19 preset C)", note: "same lock distance" },
  ],
};

test("strategy buttons show tested win/pass rates and toggle via versioned settings", async () => {
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    calls.push(`${init?.method ?? "GET"} ${String(url)} ${init?.body ? String(init.body) : ""}`);
    return new Response(JSON.stringify(String(url) === "/api/strategies" ? resp : {}));
  });
  render(<QueryClientProvider client={new QueryClient()}><StrategyButtons /></QueryClientProvider>);
  expect(await screen.findByTestId("win-noise")).toHaveTextContent("45.0%");
  expect(screen.getByTestId("pass-noise")).toHaveTextContent("56.9%");
  expect(screen.getByTestId("odds-noise")).toHaveTextContent("pass 56.9% / bust 42.2% · last 12 mo 55/45 · EOD toggle OFF"); // D137
  expect(screen.queryByTestId("odds-ai_bias")).toBeNull();
  expect(screen.getByTestId("win-ai_bias")).toHaveTextContent("—"); // D56: not back-testable → no fake numbers
  expect(screen.getAllByText("— (not testable)").length).toBe(5); // AI only + D92 split + D95 order flow + D110 AMT+ + D111 zones
  expect(screen.getByTestId("order-flow-badge")).toHaveTextContent("UNVERIFIED"); // D95 (D102: no paper-only label)
  expect(screen.getByTestId("order-flow-setup")).toHaveTextContent("Paytience_OrderFlow.pine");
  expect(screen.getByTestId("order-flow-setup")).toHaveTextContent("1-minute MNQ1! / MGC1!"); // D96
  expect(screen.getByTestId("order-flow-markets")).toHaveTextContent("Trades: MNQ + MGC · flat 16:00 ET · 1 micro");
  expect(screen.getByTestId("order-flow-markets")).toHaveTextContent("MGC (gold) is on for Order Flow only");
  expect(screen.getByTestId("order-flow-layers")).toHaveTextContent("ENVIRONMENT — no compression");  // D101
  expect(screen.getByTestId("order-flow-layers")).toHaveTextContent("PATH (OFF) — Asia zones");
  expect(screen.getByRole("button", { name: /OFF · Order Flow — TradingView/ })).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByTestId("noise-warmup")).toHaveTextContent("3/10");
  expect(screen.getByTestId("ai-ledger")).toHaveTextContent("ADVISORY");
  expect(screen.getByText(/MGC \(gold\) is off/)).toHaveTextContent("exception: Order Flow, D96");
  expect(screen.getByTestId("duo-log")).toHaveTextContent("NO TRADE · AI_DISAGREE");
  expect(screen.getByTestId("duo-log")).toHaveTextContent("TRADE LONG · TAKEN");
  expect(screen.getByTestId("duo-log")).toHaveTextContent("same side as NOISE");
  // D92: split-risk card is OFF by default, shows no invented numbers, and turns NOISE + AI Duo on with it
  expect(screen.getByTestId("win-noise_ai_split")).toHaveTextContent("—");
  await userEvent.click(screen.getByRole("button", { name: /OFF · NOISE \+ AI Duo — 50\/50 risk split/ }));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.noise_ai_split":true,"strategy.noise":true,"strategy.ai_duo":true'))).toBe(true));
  // D110: AMT+ button lists its layers and turns Order Flow on with it
  expect(screen.getByTestId("zone-layers")).toHaveTextContent("EVENT (OFF) — footprint absorption zone");
  expect(screen.getByTestId("amt-layers")).toHaveTextContent("CONTEXT (OFF) — acceptance vs prior RTH value");
  await userEvent.click(screen.getByRole("button", { name: /OFF · AMT\+ Order Flow/ }));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.order_flow_cfg.amt.enabled":true,"strategy.order_flow":true'))).toBe(true));
  // D58: the MAIN card is first and turns NOISE on with the fade
  expect(screen.getAllByRole("button")[0]).toHaveTextContent("MAIN");
  expect(screen.getByTestId("pass-pm_fade")).toHaveTextContent("65.7%");
  await userEvent.click(screen.getByRole("button", { name: /OFF · MAIN/ }));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.pm_fade":true,"strategy.noise":true'))).toBe(true));
  // D64: size profiles
  expect(screen.getByTestId("size-regular")).toHaveTextContent("150K: 3 micros → 2 when cushion < 50%");
  expect(screen.getByTestId("size-high")).toHaveTextContent("150K: 4 micros");
  expect(screen.getByTestId("size-profiles")).toHaveTextContent("Eval pass / bust (this plan): pass 70% / bust 30%"); // D137: server numbers
  expect(screen.getByTestId("size-profiles")).toHaveTextContent("Eval pass / bust (this plan): not measured yet"); // high: no odds sent
  expect(screen.getByTestId("eval-size-high")).toHaveTextContent("25K 3 × $150 stop → 1 once < 50% of the target is left"); // D69 / D70
  await userEvent.click(screen.getByRole("button", { name: /USE THIS · High risk/ }));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.high_risk":true'))).toBe(true));
  // D127: NOISE size toggle — Suggested (lowest bust) / As configured
  expect(screen.getByTestId("noise-size-toggle")).toHaveTextContent("50K 1");
  expect(screen.getByTestId("noise-size-toggle")).toHaveTextContent("Suggested table pass 90% / bust 10%");
  expect(screen.getByTestId("noise-size-configured")).toHaveTextContent("✓ IN USE · As configured — 50K 2 micros");
  await userEvent.click(screen.getByTestId("noise-size-suggested"));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.suggested_size":true'))).toBe(true));
  // D137: EOD toggle with its VERIFY badge
  expect(screen.getByTestId("verify-eod_closed_balance")).toHaveTextContent("VERIFY");
  expect(screen.getByTestId("toggle-eod_closed_balance-off")).toHaveTextContent("✓ IN USE · Kill switch watches balance + open P&L (default, safest)");
  // session 22: EOD vs intraday trailing comparison on the EOD card (this plan visible, all plans behind a button)
  expect(screen.getByTestId("dd-compare-current")).toHaveTextContent("EOD trailing 57/43 (last 12 mo 40/60) · intraday trailing 39/61 (last 12 mo 21/79)");
  expect(screen.getByTestId("dd-compare-table")).toHaveTextContent("Pro 25K57/4339/6140/6021/79");
  expect(screen.getByTestId("dd-compare-table")).toHaveTextContent("Flex 150K78/1672/2270/856/15");
  const inUse = screen.getByTestId("toggle-eod_closed_balance-off");
  expect(inUse).not.toBeDisabled(); // the chosen option is not a faded "not allowed" button (user 2026-11-14)
  await userEvent.click(inUse); // already in use: clicking it sends nothing
  expect(calls.some((c) => c.includes('"strategy.eod_closed_balance":false'))).toBe(false);
  await userEvent.click(screen.getByTestId("toggle-eod_closed_balance-on"));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.eod_closed_balance":true'))).toBe(true));
  // D132: session-20 toggles (fade off in evals ON by default; profit-lock trigger 100 pt by default)
  expect(screen.getByTestId("toggle-fade_eval_off-on")).toHaveTextContent("✓ IN USE · Off on EVAL accounts");
  expect(screen.getByTestId("toggle-noise_lock_alt-off")).toHaveTextContent("✓ IN USE · 100 pt (default");
  expect(screen.getByTestId("toggle-noise_lock_alt-on")).toHaveTextContent("USE THIS · 80 pt — experimental, likely chance");
  await userEvent.click(screen.getByTestId("toggle-noise_lock_alt-on"));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.noise_lock_alt":true'))).toBe(true));
});
