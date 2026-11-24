import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import StrategyButtons, { type StrategiesResp, type Strat } from "./StrategyButtons";
import StrategyPresets from "./StrategyPresets";
import AdvisorCard from "./AdvisorCard";
import TrailCushionCard from "./TrailCushionCard";
import FlagToggle from "./FlagToggle";

const strat = (o: Partial<Strat>): Strat => ({
  key: "x", name: "X", source: "s", verified: true, status: "VERIFIED", win_pct: 45, profit_factor: 1.3, usd_per_trade: 5, trades_per_week: 3, held_out_trades: 10,
  pro25k_pass_pct: 50, pro25k_bust_pct: 40, period: "p", note: "n", enabled: false, setting: "strategy.x", ...o,
});
const base = (strategies: Strat[]): StrategiesResp => ({
  strategies, noise_warmup: { sessions: 10, needed: 10, ready: true }, ai_ledger: [], markets: {},
  presets: { active: null, setting: "strategy.preset", plan_account_size: "25000", rows: [{ key: "p1", label: "P1", summary: "s", account: "a", study: "st", pass_pct: 1, bust_pct: 1, odds_text: "o", held_out: true, recommended: true, warning: null, fade: false, stop_usd: null, profit_lock: null, size: [], matches_plan: true }] },
  advisor: { mode: "ADVISORY", setting: "strategy.advisor.mode", skip_strategies: [], connected: true, ledger_proven: true, required_accuracy: 0.7, cards: {} },
});
const two = base([
  strat({ key: "noise", name: "NOISE", setting: "strategy.noise", enabled: true }),
  strat({ key: "gala_pa", name: "GALA PRICE ACTION", setting: "strategy.gala_pa" }),
]);

/** GET returns `data`; every PUT either fails with a 422 reason or succeeds. */
function server(data: unknown, putFails: boolean) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (_url, init) => {
    if (init?.method === "PUT") {
      return putFails ? new Response(JSON.stringify({ detail: "D167: only one strategy" }), { status: 422 }) : new Response("{}");
    }
    return new Response(JSON.stringify(data));
  });
}
const wrap = (el: React.ReactElement) => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{el}</QueryClientProvider>);
afterEach(() => vi.restoreAllMocks());

test("a rejected strategy save shows an alert with the reason and never claims a switch", async () => {
  server(two, true);
  wrap(<StrategyButtons />);
  await userEvent.click(await screen.findByRole("button", { name: /OFF · GALA PRICE ACTION/ }));
  const alert = await screen.findByTestId("save-error");
  expect(alert).toHaveAttribute("role", "alert");
  expect(alert).toHaveTextContent("GALA PRICE ACTION not saved: D167: only one strategy");
  expect(screen.queryByTestId("exclusive-note")).toBeNull();
});

test("the 'turned off' note appears only after a successful save, next to the clicked card", async () => {
  server(two, false);
  wrap(<StrategyButtons />);
  await userEvent.click(await screen.findByRole("button", { name: /OFF · GALA PRICE ACTION/ }));
  const note = await screen.findByTestId("exclusive-note");
  expect(note).toHaveTextContent("GALA PRICE ACTION is now the only strategy ON — turned off: MAIN NOISE + CANDACE.");
  expect(screen.getByTestId("strategy-gala_pa")).toContainElement(note);
  expect(screen.queryByTestId("save-error")).toBeNull();
});

test("applying a preset that the server rejects is an alert", async () => {
  server(two, true);
  wrap(<StrategyPresets />);
  await userEvent.click(await screen.findByRole("button", { name: /Apply P1/ }));
  expect(await screen.findByTestId("save-error")).toHaveTextContent("Strategy preset not saved: D167: only one strategy");
});

test("advisor mode save failure is an alert", async () => {
  server(two, true);
  wrap(<AdvisorCard />);
  await userEvent.click(await screen.findByRole("button", { name: "Off" }));
  expect(await screen.findByTestId("save-error")).toHaveTextContent("Advisor mode not saved: D167: only one strategy");
});

test("trail/cushion toggle save failure is an alert", async () => {
  server({ version: 1, settings: { "strategy.dynamic_trail.noise": false, "strategy.dynamic_trail.steps": [] } }, true);
  wrap(<TrailCushionCard />);
  await userEvent.click(await screen.findByTestId("trail-noise"));
  expect(await screen.findByTestId("save-error")).toHaveTextContent("Trail / cushion setting not saved");
});

test("flag toggle save failure is an alert", async () => {
  server({}, true);
  wrap(<FlagToggle setting="strategy.g1" on={false} label="G1" />);
  await userEvent.click(screen.getByTestId("flag-strategy.g1"));
  await waitFor(() => expect(screen.getByTestId("flag-error-strategy.g1")).toHaveTextContent("Gate toggle not saved"));
});
