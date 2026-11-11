import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import TrailCushionCard, { CushionChip, levelErrors } from "./TrailCushionCard";

const settings: Record<string, unknown> = {
  "strategy.dynamic_trail.noise": false, "strategy.dynamic_trail.order_flow": true, "strategy.cushion.noise": true,
  "strategy.dynamic_trail.activate_r": "1.0", "strategy.dynamic_trail.min_distance_ticks": 8,
  "strategy.dynamic_trail.steps": [{ until_r: "2.0", k: "2.0" }, { until_r: "3.0", k: "1.5" }, { until_r: null, k: "1.0" }],
  "strategy.cushion.normal_min": "0.75", "strategy.cushion.reduce_min": "0.50", "strategy.cushion.minimal_min": "0.25",
  "strategy.cushion.reduce_size_minus": 1, "strategy.cushion.minimal_max_trades": 1,
};

test("D122 card: per-strategy toggles save versioned settings, levels validated, UNVERIFIED shown", async () => {
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => {
    calls.push(`${init?.method ?? "GET"} ${String(url)} ${init?.body ? String(init.body) : ""}`);
    return new Response(JSON.stringify({ version: 3, settings }));
  });
  render(<QueryClientProvider client={new QueryClient()}><TrailCushionCard /></QueryClientProvider>);
  expect(await screen.findByTestId("trail-unverified")).toHaveTextContent("UNVERIFIED");
  expect(screen.getByTestId("trail-rule")).toHaveTextContent("k 2.0 until 2.0R, 1.5 until 3.0R, 1.0 after");
  expect(screen.getByTestId("trail-noise")).toHaveTextContent("OFF");
  expect(screen.getByTestId("trail-order_flow")).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByTestId("cushion-noise")).toHaveTextContent("ON");
  await userEvent.click(screen.getByTestId("trail-noise"));
  await waitFor(() => expect(calls.some((c) => c.startsWith("PUT") && c.includes('"strategy.dynamic_trail.noise":true'))).toBe(true));
  expect(screen.getByTestId("trail-cushion-save")).toBeDisabled(); // nothing edited yet
  const reduce = screen.getByLabelText("Reduce ≥");
  await userEvent.clear(reduce);
  await userEvent.type(reduce, "0.8");
  expect(screen.getByRole("alert")).toHaveTextContent("Minimal < Reduce < Normal");
  expect(screen.getByTestId("trail-cushion-save")).toBeDisabled();
  await userEvent.clear(reduce);
  await userEvent.type(reduce, "0.6");
  await userEvent.click(screen.getByTestId("trail-cushion-save"));
  await waitFor(() => expect(calls.some((c) => c.includes('"strategy.cushion.reduce_min":"0.6"') && c.includes('"strategy.cushion.minimal_max_trades":1'))).toBe(true));
});

test("level validation ranges and whole numbers", () => {
  const ok = Object.fromEntries(Object.entries(settings).filter(([, v]) => typeof v !== "object").map(([k, v]) => [k, String(v)]));
  expect(levelErrors(ok)).toEqual([]);
  expect(levelErrors({ ...ok, "strategy.dynamic_trail.min_distance_ticks": "1.5" })[0]).toContain("whole number");
  expect(levelErrors({ ...ok, "strategy.dynamic_trail.activate_r": "" }).length).toBe(1);
});

test("cushion chip shows the level and whether it applies", () => {
  const { rerender } = render(<CushionChip c={{ usd: "600", pct: "60.0", level: "REDUCE", strategies: ["NOISE"], trail_strategies: [], unverified: true }} />);
  expect(screen.getByTestId("cushion-chip")).toHaveTextContent("CUSHION REDUCE · 60.0%");
  rerender(<CushionChip c={{ usd: "1000", pct: "100.0", level: "NORMAL", strategies: [], trail_strategies: [], unverified: true }} />);
  expect(screen.getByTestId("cushion-chip")).toHaveTextContent("(off)");
  rerender(<CushionChip c={null} />);
  expect(screen.queryByTestId("cushion-chip")).toBeNull();
});
