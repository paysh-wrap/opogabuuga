import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import NowRunning, { runningNames } from "./NowRunning";
import type { Strat } from "./StrategyButtons";

const s = (key: string, name: string, enabled: boolean): Strat => ({ key, name, source: "", verified: true, status: "", win_pct: null, profit_factor: null, usd_per_trade: null, trades_per_week: null, held_out_trades: 0, pro25k_pass_pct: null, pro25k_bust_pct: null, period: "", note: "", enabled, setting: `strategy.${key}` });
function wrap(body: unknown, status = 200, compact = false) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify(body), { status }));
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><NowRunning compact={compact} /></QueryClientProvider>);
}
afterEach(() => vi.restoreAllMocks());

test("NOISE and CANDACE collapse into one MAIN entry", () => {
  expect(runningNames([s("noise", "NOISE — x", true), s("candace_ict", "CANDACE — y", true), s("gala_pa", "GALA", false)])).toEqual(["MAIN NOISE + CANDACE"]);
  expect(runningNames([s("gala_pa", "GALA PRICE ACTION — z", true)])).toEqual(["GALA PRICE ACTION"]);
});

test("the strip names the strategy that is ON (full and compact)", async () => {
  wrap({ strategies: [s("noise", "NOISE", true), s("gala_pa", "GALA", false)] });
  expect(await screen.findByTestId("now-running")).toHaveTextContent("Now running MAIN NOISE + CANDACE");
});

test("compact header chip", async () => {
  wrap({ strategies: [s("gala_pa", "GALA PRICE ACTION — z", true)] }, 200, true);
  expect(await screen.findByTestId("now-running")).toHaveTextContent("Now running · GALA PRICE ACTION");
});

test("nothing ON is a loud warning", async () => {
  wrap({ strategies: [s("noise", "NOISE", false)] });
  const w = await screen.findByTestId("now-running");
  expect(w).toHaveAttribute("role", "alert");
  expect(w).toHaveTextContent("No strategy is ON — Paytience will not open trades");
});

test("a failed load says so instead of showing nothing", async () => {
  wrap({ detail: "down" }, 500);
  expect(await screen.findByTestId("now-running-error")).toHaveTextContent("Strategy status unavailable: down");
});
