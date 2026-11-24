import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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
    { key: "fast_pass_25k", setting: "strategy.fast_pass_25k", title: "25K fast pass (evaluations)", value: false, on_label: "on", off_label: "off", note: "n",
      weekly: { target: "1250", median_days: "56.5", needed_week: "110.62", sim_week: "74.23", measured: false, source: "docs/results/pass_fastest/final_search/RESULTS.md" },
      late: { setting: "strategy.fast_pass_late_day", value: false, label: "3rd edge: late-day momentum (UNVERIFIED, held-out PF 1.10)", detail: "MNQ, 2 micro(s)" } },
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
  // D58: NOISE is the first card; the MAIN fade card now sits under Lesser strategies
  expect(screen.getAllByRole("radio")[0]).toHaveTextContent("NOISE + CANDACE"); // one MAIN radio card (NOISE + CANDACE), not two buttons
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
  // D164: weekly profit targets on the fast-pass card
  expect(screen.getByTestId("weekly-fast_pass_25k")).toHaveTextContent("Weekly target: $111/week");
  expect(screen.getByTestId("weekly-fast_pass_25k")).toHaveTextContent("Simulated avg: $74/week");
  expect(screen.getByTestId("weekly-fast_pass_25k")).toHaveTextContent("Backtest estimate; accounts trade the same signals so they win and lose together.");
  expect(screen.getByTestId("weekly-unmeasured-fast_pass_25k")).toBeInTheDocument();
  // D166: 3rd-edge option INSIDE the fast-pass card, gold UNVERIFIED badge, own setting key
  expect(screen.getByTestId("late-badge-fast_pass_25k")).toHaveTextContent("UNVERIFIED · held-out PF 1.10");
  expect(screen.getByTestId("late-fast_pass_25k")).toHaveTextContent("3rd edge: late-day momentum (UNVERIFIED, held-out PF 1.10)");
  await userEvent.click(screen.getByTestId("late-toggle-fast_pass_25k"));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.fast_pass_late_day":true'))).toBe(true));
  // calculator: default 1 account, totals = count x per-account API figures, remembered per viewer
  expect(screen.getByTestId("calc-total")).toHaveTextContent("$111$74");
  fireEvent.change(screen.getByTestId("calc-count-fast_pass_25k"), { target: { value: "10" } });
  expect(screen.getByTestId("calc-total")).toHaveTextContent("$1,106$742");
  expect(localStorage.getItem("paytience.weekly_counts")).toContain('"fast_pass_25k":10');
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

test("JJ F.P.T STRAT card lists JJ's rules and turns on through its own setting", async () => {
  const jj = { key: "jj_fpt", name: "JJ F.P.T STRAT", source: "JJ's videos", verified: false, status: "UNVERIFIED", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: null, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "Not back-tested", note: "n", enabled: false, setting: "strategy.jj_fpt",
    jj_rules: [{ key: "SESSIONS", on: true, rule: "first 90 min of each open, ET: NY 09:30" }, { key: "NEWS", on: false, rule: "08:30 red-folder news" }] };
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    calls.push(`${init?.method ?? "GET"} ${String(url)} ${init?.body ? String(init.body) : ""}`);
    return new Response(JSON.stringify(String(url) === "/api/strategies" ? { ...resp, strategies: [...resp.strategies, jj] } : {}));
  });
  render(<QueryClientProvider client={new QueryClient()}><StrategyButtons /></QueryClientProvider>);
  const card = await screen.findByTestId("strategy-jj_fpt");
  expect(card).toHaveTextContent("OFF · JJ F.P.T STRAT");
  expect(screen.getByTestId("jj-setup")).toHaveTextContent("UNVERIFIED · rules from JJ's videos");
  expect(screen.getByTestId("jj-rules")).toHaveTextContent("SESSIONS — first 90 min of each open, ET: NY 09:30");
  expect(screen.getByTestId("jj-rules")).toHaveTextContent("NEWS (OFF) — 08:30 red-folder news");
  await userEvent.click(screen.getByRole("button", { name: /JJ F.P.T STRAT/ }));
  await waitFor(() => expect(calls.some((c) => c.startsWith("PUT /api/risk/settings") && c.includes('"strategy.jj_fpt":true'))).toBe(true));
});

test("GALA PRICE ACTION card lists the rule sheet and turns on through its own setting", async () => {
  const g = { key: "gala_pa", name: "GALA PRICE ACTION", source: "Gala", verified: false, status: "UNVERIFIED", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: null, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "Not back-tested yet.", note: "n", enabled: false, setting: "strategy.gala_pa",
    gala_rules: [{ key: "TREND", on: true, rule: "hourly highs and lows" }, { key: "OPEN LEVEL", on: false, rule: "the day's opening price" }] };
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    calls.push(`${init?.method ?? "GET"} ${String(url)} ${init?.body ? String(init.body) : ""}`);
    return new Response(JSON.stringify(String(url) === "/api/strategies" ? { ...resp, strategies: [...resp.strategies, g] } : {}));
  });
  render(<QueryClientProvider client={new QueryClient()}><StrategyButtons /></QueryClientProvider>);
  const card = await screen.findByTestId("strategy-gala_pa");
  expect(card).toHaveTextContent("OFF · GALA PRICE ACTION");
  expect(screen.getByTestId("gala-rules")).toHaveTextContent("TREND — hourly highs and lows");
  expect(screen.getByTestId("gala-rules")).toHaveTextContent("OPEN LEVEL (OFF) — the day's opening price");
  await userEvent.click(screen.getByRole("button", { name: /GALA PRICE ACTION/ }));
  await waitFor(() => expect(calls.some((c) => c.startsWith("PUT /api/risk/settings") && c.includes('"strategy.gala_pa":true'))).toBe(true));
});

test("MGC NOISE + CANDACE card shows its own gold evidence badge", async () => {
  const g = { key: "mgc_noise_candace", name: "NOISE + CANDACE · MGC", source: "30-day test", verified: false, status: "UNVERIFIED", badge: "UNVERIFIED · 30-day yfinance test only", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: null, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "30 days.", note: "n", enabled: false, setting: "strategy.mgc_noise_candace",
    strategy_rules: [{ key: "NOISE", on: true, rule: "noise-area momentum on MGC" }] };
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) =>
    new Response(JSON.stringify(String(url) === "/api/strategies" ? { ...resp, strategies: [...resp.strategies, g] } : {})));
  render(<QueryClientProvider client={new QueryClient()}><StrategyButtons /></QueryClientProvider>);
  const setup = await screen.findByTestId("mgc_noise_candace-setup");
  expect(setup).toHaveTextContent("UNVERIFIED · 30-day yfinance test only");
  expect(setup).not.toHaveTextContent("rules from one transcript");
});

test.each([["conti_orb", "CONTI ORB"], ["conti_vwap", "CONTI VWAP"], ["okala_8020", "OKALA 8020"], ["bruni_structure", "BRUNI STRUCTURE"]]) ("%s card lists its rule sheet and turns on through its own setting", async (key, name) => {
  const g = { key, name, source: "transcript", verified: false, status: "UNVERIFIED", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: null, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "Not back-tested yet.", note: "n", enabled: false, setting: `strategy.${key}`,
    strategy_rules: [{ key: "ENTRY", on: true, rule: "the entry rule" }, { key: "EXTRA", on: false, rule: "an optional rule" }] };
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    calls.push(`${init?.method ?? "GET"} ${String(url)} ${init?.body ? String(init.body) : ""}`);
    return new Response(JSON.stringify(String(url) === "/api/strategies" ? { ...resp, strategies: [...resp.strategies, g] } : {}));
  });
  render(<QueryClientProvider client={new QueryClient()}><StrategyButtons /></QueryClientProvider>);
  const card = await screen.findByTestId(`strategy-${key}`);
  expect(card).toHaveTextContent(`OFF · ${name}`);
  expect(screen.getByTestId(`${key}-rules`)).toHaveTextContent("ENTRY — the entry rule");
  expect(screen.getByTestId(`${key}-rules`)).toHaveTextContent("EXTRA (OFF) — an optional rule");
  await userEvent.click(screen.getByRole("button", { name: new RegExp(name) }));
  await waitFor(() => expect(calls.some((c) => c.startsWith("PUT /api/risk/settings") && c.includes(`"strategy.${key}":true`))).toBe(true));
});

test("ORDER FLOW · AUCTION (IMRE) card lists its rules, says delta is estimated and turns on via its own setting", async () => {
  const g = { key: "order_flow_auction", name: "ORDER FLOW · AUCTION (IMRE)", source: "Imre", verified: false, status: "UNVERIFIED", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: null, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "Not back-tested yet.", note: "n", enabled: false, setting: "strategy.order_flow_cfg.auction.enabled", also: ["strategy.order_flow"],
    strategy_rules: [{ key: "DELTA", on: true, rule: "ESTIMATED from 1-minute bars; DOM / heatmap NOT available" }] };
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    calls.push(`${init?.method ?? "GET"} ${String(url)} ${init?.body ? String(init.body) : ""}`);
    return new Response(JSON.stringify(String(url) === "/api/strategies" ? { ...resp, strategies: [...resp.strategies, g] } : {}));
  });
  render(<QueryClientProvider client={new QueryClient()}><StrategyButtons /></QueryClientProvider>);
  await screen.findByTestId("strategy-order_flow_auction");
  expect(screen.getByTestId("order_flow_auction-rules")).toHaveTextContent("DELTA — ESTIMATED from 1-minute bars; DOM / heatmap NOT available");
  await userEvent.click(screen.getByRole("button", { name: /ORDER FLOW · AUCTION/ }));
  await waitFor(() => expect(calls.some((c) => c.startsWith("PUT /api/risk/settings") && c.includes('"strategy.order_flow_cfg.auction.enabled":true'))).toBe(true));
});

test("Order Flow card: AR beside NOISE toggle, pre-session bias runs, NO_CALL and the estimated-data label", async () => {
  const of = { key: "order_flow", name: "Order Flow", source: "s", verified: false, status: "UNVERIFIED", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: null, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "NOT tested", note: "n", enabled: true, setting: "strategy.order_flow",
    ar_side_by_side: { setting: "strategy.order_flow_cfg.ar_side_by_side", enabled: false, data_source: "ESTIMATED delta (online data)", evidence: "No edge shown on estimated data: UNVERIFIED, paper first. Evidence: docs/results/new_strategies and docs/results/session22.", verified: false, advisor_mode: "ADVISORY", session: "2026-11-23",
      runs: [{ minutes_before: 240, at: "05:30", results: [{ symbol: "MNQ", status: "OK", side: "SHORT", rating: "Sell", prob_up: 0.45, prob_down: 0.55 }] }, { minutes_before: 60, at: "08:30", results: [{ symbol: "MNQ", status: "NO_CALL", reason: "AI key not connected" }] }, { minutes_before: 30, at: "09:00", results: [{ symbol: "MNQ", status: "PENDING" }] }] } };
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    calls.push(`${init?.method ?? "GET"} ${String(url)} ${init?.body ? String(init.body) : ""}`);
    return new Response(JSON.stringify(String(url) === "/api/strategies" ? { ...resp, strategies: [...resp.strategies, of] } : {}));
  });
  render(<QueryClientProvider client={new QueryClient()}><StrategyButtons /></QueryClientProvider>);
  await screen.findByTestId("ar-sbs");
  expect(screen.getByTestId("ar-sbs-source")).toHaveTextContent("ESTIMATED delta (online data)");
  expect(screen.getByTestId("ar-sbs-source")).toHaveTextContent("4 h before (05:30 ET), 1 h before (08:30 ET), 30 min before (09:00 ET)");
  expect(screen.getByTestId("ar-sbs-runs")).toHaveTextContent("MNQ SHORT (Sell) up 45% / down 55%");
  expect(screen.getByTestId("ar-sbs-runs")).toHaveTextContent("NO_CALL — AI key not connected");
  expect(screen.getByTestId("ar-sbs-evidence")).toHaveTextContent("session22");
  await userEvent.click(screen.getByTestId("ar-sbs-toggle"));
  await waitFor(() => expect(calls.some((c) => c.startsWith("PUT /api/risk/settings") && c.includes('"strategy.order_flow_cfg.ar_side_by_side":true'))).toBe(true));
});

test("D167: main strategy first, one strategy ON at a time, four independent fast-pass cards", async () => {
  const calls: string[] = [];
  const fp = (n: string, on: boolean) => ({ key: `fast_pass_${n}`, setting: `strategy.fast_pass_${n}`, title: `${n.toUpperCase()} fast pass (evaluations)`, value: on, on_label: "on", off_label: "off", note: "n",
    weekly: { target: "1250", median_days: "56.5", needed_week: "110.62", sim_week: "74.23", measured: true, source: "s" } });
  const r2: StrategiesResp = { ...resp, toggles: [fp("25k", true), fp("50k", true), fp("100k", false), fp("150k", false)] };
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    calls.push(`${init?.method ?? "GET"} ${String(url)} ${init?.body ? String(init.body) : ""}`);
    return new Response(JSON.stringify(String(url) === "/api/strategies" ? r2 : {}));
  });
  render(<QueryClientProvider client={new QueryClient()}><StrategyButtons /></QueryClientProvider>);
  await screen.findByTestId("strategy-main-group");
  const main = screen.getByTestId("strategy-main-group");
  const flow = screen.getByTestId("strategy-order-flow-group");
  expect(main.compareDocumentPosition(flow) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  expect(main.compareDocumentPosition(screen.getByTestId("size-profiles")) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  const lesser = screen.getByTestId("lesser-strategies") as HTMLDetailsElement;
  expect(flow.compareDocumentPosition(lesser) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy(); // main → secondary → lesser
  expect(lesser.open).toBe(false); // closed by default
  expect(screen.getByTestId("strategy-order-flow-group")).toHaveTextContent("SECONDARY strategy — ORDER FLOW");
  expect(lesser).toContainElement(screen.getByTestId("strategy-noise_ai_split"));
  expect(flow).not.toContainElement(screen.getByTestId("strategy-noise_ai_split"));
  for (const n of ["25k", "50k", "100k", "150k"]) expect(screen.getByTestId(`weekly-fast_pass_${n}`)).toHaveTextContent("Weekly target");
  // two fast-pass plans ON together is fine (independent)
  expect(screen.getByTestId("toggle-fast_pass_25k-on")).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByTestId("toggle-fast_pass_50k-on")).toHaveAttribute("aria-pressed", "true");
  // NOISE is ON; turning Order Flow on turns the main pair off
  await userEvent.click(screen.getByRole("button", { name: /OFF · Order Flow — TradingView/ }));
  await waitFor(() => expect(calls.some((c) => c.startsWith("PUT") && c.includes('"strategy.noise":false') && c.includes('"strategy.candace_ict":false') && c.includes('"strategy.order_flow":true'))).toBe(true));
  expect(await screen.findByTestId("exclusive-note")).toHaveTextContent("turned off: NOISE + CANDACE");
});
