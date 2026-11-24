import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import IncomeProjection, { type IncomeResp } from "./IncomeProjection";
import { PlanProgress } from "./DashboardExtras";

const inc: IncomeResp = {
  plan: "lucid_pro_25k", plans: ["lucid_pro_25k"], current_plan: "lucid_pro_25k", basis: "research",
  accounts: 5, micros: 1, cadence_sessions: 10, starts: 497, horizon_sessions: 260,
  year_mean: "5239", year_median: "4500", year_p25: "0", year_p75: "16875", week_mean: "202", per_paycheck_mean: "404",
  auto: null, any_payout_pct: "58.3", bust_pct: "56.6", max_payouts_pct: "4.2", median_sessions_to_first: 70, max_possible_year: "31500",
};

test("next payout time shows the ET suffix exactly once", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({
    tracker: { year: 2026, ytd_gross: "0", ytd_net: "0", target_net: "70000", floor_net: "50000", target_pct: "0", floor_pct: "0", payouts_processed: 0 },
    projection: { basis: "trailing", monthly_net: "0", months: [] },
    next_payout: { check_at: "2026-11-06T22:05:00+00:00", frequency: "weekly", skim_mode: "half", total: "600", accounts: [] },
  })));
  render(<QueryClientProvider client={new QueryClient()}><PlanProgress /></QueryClientProvider>);
  const el = await screen.findByTestId("next-payout");
  expect(el.textContent).toContain("17:05:00 ET");
  expect(el.textContent).not.toMatch(/ET\s*ET/);
});

test("projection is a table: every row has a label cell then per-account, all-accounts net and gross values", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify(inc)));
  render(<QueryClientProvider client={new QueryClient()}><IncomeProjection /></QueryClientProvider>);
  await screen.findByTestId("income-week");
  const table = screen.getByTestId("income-table");
  expect(table.querySelectorAll("thead th").length).toBe(4);
  const rows = Array.from(table.querySelectorAll("tbody tr"));
  expect(rows.length).toBeGreaterThan(0);
  rows.forEach((r) => {
    expect(r.children[0]?.tagName).toBe("TH");
    expect(Array.from(r.children).slice(1).map((c) => c.tagName)).toEqual(["TD", "TD", "TD"]);
  });
  expect(rows[0]?.children[0]?.textContent).toContain("Per week");
  expect(screen.getByTestId("income-week").textContent).toContain("$202");
});
