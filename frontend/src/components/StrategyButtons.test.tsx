import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import StrategyButtons, { type StrategiesResp } from "./StrategyButtons";

const resp: StrategiesResp = {
  strategies: [
    { key: "pm_fade", name: "MAIN — NOISE + Afternoon fade ($250 stops, MNQ)", source: "s", verified: true, status: "MAIN · fade on PAPER first", win_pct: 50, profit_factor: 1.33, usd_per_trade: 19.63, trades_per_week: 5.2, held_out_trades: 1291, pro25k_pass_pct: 65.7, pro25k_bust_pct: 32.2, period: "p", note: "n", enabled: false, setting: "strategy.pm_fade", also: ["strategy.noise"] },
    { key: "noise", name: "NOISE — intraday momentum (MNQ)", source: "Zarattini", verified: true, status: "VERIFIED", win_pct: 45, profit_factor: 1.33, usd_per_trade: 25.81, trades_per_week: 3, held_out_trades: 440, pro25k_pass_pct: 56.9, pro25k_bust_pct: 42.2, period: "held-out 2024-01 → 2026-11", note: "n", enabled: true, setting: "strategy.noise" },
    { key: "open_drive", name: "Opening-drive pullback (MNQ) — paper only", source: "s", verified: false, status: "PAPER ONLY", win_pct: 58.3, profit_factor: 1.29, usd_per_trade: 9.95, trades_per_week: 0.75, held_out_trades: 108, pro25k_pass_pct: 4.8, pro25k_bust_pct: 8.8, period: "p", note: "n", enabled: false, setting: "strategy.open_drive" },
    { key: "noise_ai_split", name: "NOISE + AI Duo — split risk 50/50 — AI Duo paper only", source: "s", verified: false, status: "PAPER ONLY", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: null, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "NOT measured", note: "n", enabled: false, setting: "strategy.noise_ai_split", also: ["strategy.noise", "strategy.ai_duo"] },
    { key: "order_flow", name: "Order Flow — TradingView order-flow alerts (MNQ + MGC) — UNVERIFIED · paper only", source: "s", verified: false, status: "UNVERIFIED · PAPER ONLY", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: null, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "NOT tested", note: "n", enabled: false, setting: "strategy.order_flow", instruments: ["MNQ", "MGC"], paper_only: true, flat_at: "16:00", ar_layers: [{ key: "ENVIRONMENT", on: true, rule: "no compression" }, { key: "PATH", on: false, rule: "Asia zones" }] },
    { key: "ai_bias", name: "AI only — TradingAgents + Vibe-Trading (MNQ) — paper only", source: "s", verified: false, status: "PAPER ONLY", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: 1.35, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "NOT back-testable", note: "n", enabled: false, setting: "strategy.ai_bias" },
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
  },
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
  expect(screen.getByTestId("win-open_drive")).toHaveTextContent("58.3%");
  expect(screen.getByTestId("win-ai_bias")).toHaveTextContent("—"); // D56: not back-testable → no fake numbers
  expect(screen.getAllByText("— (not testable)").length).toBe(3); // AI only + the D92 split card + D95 order flow
  expect(screen.getByTestId("order-flow-badge")).toHaveTextContent("UNVERIFIED · paper only"); // D95
  expect(screen.getByTestId("order-flow-setup")).toHaveTextContent("Paytience_OrderFlow.pine");
  expect(screen.getByTestId("order-flow-setup")).toHaveTextContent("1-minute MNQ1! / MGC1!"); // D96
  expect(screen.getByTestId("order-flow-markets")).toHaveTextContent("Trades: MNQ + MGC · PAPER accounts only · flat 16:00 ET · 1 micro");
  expect(screen.getByTestId("order-flow-markets")).toHaveTextContent("MGC (gold) is on for Order Flow only");
  expect(screen.getByTestId("order-flow-layers")).toHaveTextContent("ENVIRONMENT — no compression");  // D101
  expect(screen.getByTestId("order-flow-layers")).toHaveTextContent("PATH (OFF) — Asia zones");
  expect(screen.getByRole("button", { name: /OFF · Order Flow/ })).toHaveAttribute("aria-pressed", "false");
  expect(screen.getByTestId("noise-warmup")).toHaveTextContent("3/10");
  expect(screen.getByTestId("ai-ledger")).toHaveTextContent("ADVISORY");
  expect(screen.getByText(/MGC \(gold\) is off/)).toHaveTextContent("exception: Order Flow, paper only, D96");
  expect(screen.getByTestId("duo-log")).toHaveTextContent("NO TRADE · AI_DISAGREE");
  expect(screen.getByTestId("duo-log")).toHaveTextContent("TRADE LONG · TAKEN");
  expect(screen.getByTestId("duo-log")).toHaveTextContent("same side as NOISE");
  // D92: split-risk card is OFF by default, shows no invented numbers, and turns NOISE + AI Duo on with it
  expect(screen.getByTestId("win-noise_ai_split")).toHaveTextContent("—");
  await userEvent.click(screen.getByRole("button", { name: /OFF · NOISE \+ AI Duo — split risk 50\/50/ }));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.noise_ai_split":true,"strategy.noise":true,"strategy.ai_duo":true'))).toBe(true));
  // D58: the MAIN card is first and turns NOISE on with the fade
  expect(screen.getAllByRole("button")[0]).toHaveTextContent("MAIN");
  expect(screen.getByTestId("pass-pm_fade")).toHaveTextContent("65.7%");
  await userEvent.click(screen.getByRole("button", { name: /OFF · MAIN/ }));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.pm_fade":true,"strategy.noise":true'))).toBe(true));
  // D64: size profiles
  expect(screen.getByTestId("size-regular")).toHaveTextContent("150K: 3 micros → 2 when cushion < 50%");
  expect(screen.getByTestId("size-high")).toHaveTextContent("150K: 4 micros");
  expect(screen.getByTestId("eval-size-high")).toHaveTextContent("25K 3 × $150 stop → 1 once < 50% of the target is left"); // D69 / D70
  await userEvent.click(screen.getByRole("button", { name: /OFF · High risk/ }));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.high_risk":true'))).toBe(true));
});
