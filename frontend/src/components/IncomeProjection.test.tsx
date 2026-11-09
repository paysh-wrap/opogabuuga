import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import IncomeProjection, { type IncomeResp } from "./IncomeProjection";

const base: IncomeResp = {
  plan: "lucid_pro_25k", plans: ["lucid_pro_25k", "lucid_pro_50k"], current_plan: "lucid_pro_25k", basis: "research",
  accounts: 5, micros: 1, cadence_sessions: 10, starts: 497, horizon_sessions: 260,
  year_mean: "8232.03", year_median: "4500.00", year_p25: "0", year_p75: "16875.30", week_mean: "158.31", per_paycheck_mean: "316.62",
  any_payout_pct: "58.3", bust_pct: "56.6", max_payouts_pct: "4.2", median_sessions_to_first: 70, max_possible_year: "31500.00",
};

test("projected income card shows weekly / paycheck numbers and re-queries on plan change", async () => {
  const urls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    urls.push(String(url));
    const fifty = String(url).includes("plan=lucid_pro_50k");
    return new Response(JSON.stringify(fifty ? { ...base, plan: "lucid_pro_50k", week_mean: "158.62", per_paycheck_mean: "317.25" } : base));
  });
  render(<QueryClientProvider client={new QueryClient()}><IncomeProjection /></QueryClientProvider>);
  expect(await screen.findByTestId("income-week")).toHaveTextContent("$158");
  expect(screen.getByTestId("income-paycheck")).toHaveTextContent("$317");
  expect(screen.getByTestId("income-median")).toHaveTextContent("$4,500");
  expect(screen.getByTestId("income-bust")).toHaveTextContent("56.6%");
  expect(screen.getByRole("option", { name: /Pro 25K \(current\)/i })).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText("Plan"), "lucid_pro_50k");
  await waitFor(() => expect(urls.some((u) => u.includes("plan=lucid_pro_50k") && u.includes("accounts=5"))).toBe(true));
  await userEvent.selectOptions(screen.getByLabelText("Micros"), "2");
  await waitFor(() => expect(urls.some((u) => u.includes("micros=2"))).toBe(true));
  await userEvent.selectOptions(screen.getByLabelText("Account growth"), "1000");
  await waitFor(() => expect(urls.some((u) => u.includes("grow=1000"))).toBe(true));
});
