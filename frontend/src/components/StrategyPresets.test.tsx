import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import StrategyPresets from "./StrategyPresets";
import type { PresetsResp, StrategiesResp } from "./StrategyButtons";

const WARN = "older, likely optimistic (fade measured with hindsight ~27% rosy; honest ~57%/42%)";
const presets: PresetsResp = {
  active: null, setting: "strategy.preset", plan_account_size: "150000",
  rows: [
    { key: "pro25k_classic", label: "Pro 25K classic", summary: "NOISE $250 stop + afternoon fade ON, 1 micro", account: "Pro 25K", study: "Session 10", pass_pct: 63, bust_pct: 36, held_out: false, recommended: false, warning: WARN, fade: true, stop_usd: "250", profit_lock: null, size: [{ account_size: "25000", contracts: 1, brake_below: null, brake_contracts: null }], matches_plan: false },
    { key: "pro100k_low_risk", label: "Pro 100K low risk", summary: "NOISE + fade, 3 micros", account: "Pro 100K", study: "Session 19, 7.5 yr", pass_pct: 83, bust_pct: 15, held_out: false, recommended: false, warning: null, fade: false, stop_usd: "250", profit_lock: { trigger_pts: "100", lock_pts: "10" }, size: [{ account_size: "100000", contracts: 2, brake_below: "0.3", brake_contracts: 1 }], matches_plan: false },
    { key: "pro150k_low_risk", label: "Pro 150K low risk", summary: "NOISE + profit lock", account: "Pro 150K", study: "Session 19, 7.5 yr", pass_pct: 83, bust_pct: 15, held_out: false, recommended: true, warning: null, fade: false, stop_usd: "250", profit_lock: { trigger_pts: "100", lock_pts: "10" }, size: [{ account_size: "150000", contracts: 3, brake_below: "0.5", brake_contracts: 1 }], matches_plan: true },
  ],
};
const resp = { strategies: [], noise_warmup: { sessions: 0, needed: 10, ready: false }, ai_ledger: [], markets: {}, presets } as StrategiesResp;

function setup(r: StrategiesResp = resp) {
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    calls.push(`${init?.method ?? "GET"} ${String(url)} ${init?.body ? String(init.body) : ""}`);
    return new Response(JSON.stringify(String(url) === "/api/strategies" ? r : {}));
  });
  render(<QueryClientProvider client={new QueryClient()}><StrategyPresets /></QueryClientProvider>);
  return calls;
}

test("three presets with labels, warning badges, recommended default and audited apply", async () => {
  const calls = setup();
  expect(await screen.findByTestId("preset-rates-pro25k_classic")).toHaveTextContent("Pass 63% / bust 36%");
  expect(screen.getByTestId("preset-rates-pro100k_low_risk")).toHaveTextContent("Pass 83% / bust 15%");
  expect(screen.getByTestId("preset-rates-pro150k_low_risk")).toHaveTextContent("Pass 83% / bust 15%");
  expect(screen.getByTestId("preset-rates-pro150k_low_risk")).toHaveTextContent("Session 19");
  expect(screen.getByTestId("preset-warning-pro25k_classic")).toHaveTextContent("likely optimistic");
  expect(screen.queryByTestId("preset-warning-pro100k_low_risk")).toBeNull(); // D125: re-based on session 19
  expect(screen.queryByTestId("preset-warning-pro150k_low_risk")).toBeNull();
  expect(screen.getByTestId("preset-pro150k_low_risk")).toHaveAttribute("aria-checked", "true"); // recommended is preselected
  expect(screen.getByTestId("preset-pro150k_low_risk")).toHaveTextContent("recommended");
  expect(screen.getByTestId("preset-detail")).toHaveTextContent("profit lock: at +100 pt the stop moves to entry +10 pt");
  expect(screen.getByTestId("preset-detail")).toHaveTextContent("3 micros, 1 while the cushion is under 50%");
  expect(screen.getByTestId("preset-active")).toHaveTextContent("Custom");
  await userEvent.click(screen.getByRole("button", { name: "Apply Pro 150K low risk" }));
  await waitFor(() => expect(calls.some((c) => c.startsWith("PUT /api/risk/settings") && c.includes('"strategy.preset":"pro150k_low_risk"'))).toBe(true));
});

test("picking an older preset shows the size, the fade and a plan-size mismatch notice", async () => {
  const calls = setup();
  await userEvent.click(await screen.findByTestId("preset-pro25k_classic"));
  expect(screen.getByTestId("preset-detail")).toHaveTextContent("afternoon fade ON");
  expect(screen.getByTestId("preset-detail")).toHaveTextContent("no profit lock");
  expect(screen.getByTestId("preset-mismatch")).toHaveTextContent("150K");
  await userEvent.click(screen.getByRole("button", { name: "Apply Pro 25K classic" }));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.preset":"pro25k_classic"'))).toBe(true));
});

test("an active preset is marked and can be returned to custom", async () => {
  const calls = setup({ ...resp, presets: { ...presets, active: "pro150k_low_risk" } });
  expect(await screen.findByTestId("preset-active")).toHaveTextContent("Pro 150K low risk");
  expect(screen.getByRole("button", { name: "Applied" })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "Back to custom" }));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.preset":null'))).toBe(true));
});
