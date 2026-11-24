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
  expect(note).toHaveTextContent("GALA PRICE ACTION is now the only strategy ON — turned off: NOISE + CANDACE.");
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

// ---- item 4: one MAIN radio choice, note next to the clicked control ----
const withMain = (noiseOn: boolean, candaceOn: boolean, galaOn = false) => base([
  strat({ key: "noise", name: "NOISE — momentum", setting: "strategy.noise", enabled: noiseOn }),
  strat({ key: "candace_ict", name: "CANDACE — ICT", setting: "strategy.candace_ict", enabled: candaceOn }),
  strat({ key: "gala_pa", name: "GALA PRICE ACTION — rules", setting: "strategy.gala_pa", enabled: galaOn }),
]);
function putBodies(data: unknown) {
  const puts: { changes: Record<string, boolean> }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (_url, init) => {
    if (init?.method === "PUT") { puts.push(JSON.parse(String(init.body))); return new Response("{}"); }
    return new Response(JSON.stringify(data));
  });
  return puts;
}

test("NOISE + CANDACE is one radio: OFF -> ON sets both ON and turns the other choice off", async () => {
  const puts = putBodies(withMain(false, false, true));
  wrap(<StrategyButtons />);
  const radio = await screen.findByRole("radio", { name: /NOISE \+ CANDACE/ });
  expect(radio).toHaveAttribute("aria-checked", "false");
  expect(screen.getByRole("radiogroup", { name: "Main strategy choice" })).toBeInTheDocument();
  expect(screen.getByTestId("main-choice-hint")).toHaveTextContent("Only one choice can be ON at a time");
  expect(screen.queryByRole("button", { name: /OFF · NOISE — momentum/ })).toBeNull(); // no separate NOISE / CANDACE buttons
  await userEvent.click(radio);
  await waitFor(() => expect(puts).toHaveLength(1));
  expect(puts[0]!.changes).toMatchObject({ "strategy.noise": true, "strategy.candace_ict": true, "strategy.gala_pa": false });
  expect(await screen.findByTestId("exclusive-note")).toHaveTextContent("NOISE + CANDACE is now the only strategy ON — turned off: GALA PRICE ACTION.");
  expect(screen.getByTestId("strategy-main-choice")).toContainElement(screen.getByTestId("exclusive-note"));
});

test("turning the MAIN radio OFF turns NOISE and CANDACE off together", async () => {
  const puts = putBodies(withMain(true, true));
  wrap(<StrategyButtons />);
  const radio = await screen.findByRole("radio", { name: /NOISE \+ CANDACE/ });
  expect(radio).toHaveAttribute("aria-checked", "true");
  await userEvent.click(radio);
  await waitFor(() => expect(puts).toHaveLength(1));
  expect(puts[0]!.changes).toEqual({ "strategy.noise": false, "strategy.candace_ict": false });
});

test("a half-on MAIN (CANDACE off) is flagged and one click makes it fully ON", async () => {
  const puts = putBodies(withMain(true, false));
  wrap(<StrategyButtons />);
  expect(await screen.findByTestId("main-choice-partial")).toHaveTextContent("CANDACE is off in your settings");
  await userEvent.click(screen.getByRole("radio", { name: /NOISE \+ CANDACE/ }));
  await waitFor(() => expect(puts).toHaveLength(1));
  expect(puts[0]!.changes).toMatchObject({ "strategy.noise": true, "strategy.candace_ict": true });
});

test("Lesser summary shows the current choice; the note sits in the clicked card and is mirrored while the dropdown is closed", async () => {
  putBodies(withMain(true, true));
  wrap(<StrategyButtons />);
  const summary = await screen.findByTestId("lesser-summary");
  expect(summary).toHaveTextContent("Lesser strategies (1) · none ON");
  expect(screen.getByTestId("lesser-hint")).toHaveTextContent("Only one choice can be ON at a time");
  // closed dropdown: the note shows below it
  await userEvent.click(screen.getByRole("button", { name: /OFF · GALA PRICE ACTION/ }));
  expect(await screen.findByTestId("exclusive-note-closed")).toHaveTextContent("GALA PRICE ACTION — rules is now the only strategy ON");
  // open dropdown: the note is inside the clicked card instead (no duplicate)
  await userEvent.click(summary);
  await waitFor(() => expect(screen.queryByTestId("exclusive-note-closed")).toBeNull());
  expect(screen.getByTestId("strategy-gala_pa")).toContainElement(screen.getByTestId("exclusive-note"));
});
