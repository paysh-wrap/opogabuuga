import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import IncomeProjection, { type IncomeResp, loadSaved } from "./IncomeProjection";

const base: IncomeResp = {
  plan: "lucid_pro_25k", plans: ["lucid_pro_25k", "lucid_pro_50k"], current_plan: "lucid_pro_25k", basis: "research",
  accounts: 5, funded: 3, live: 2, default_cadence: 1, live_status: "VERIFY", live_basis: "Live = funded rules.", on_demand_status: "CONFIRMED (Lucid help center)",
  totals: { per_account: { week: { net: "36", gross: "40" }, year_mean: { net: "1800", gross: "2000" }, year_median: { net: "900", gross: "1000" }, year_p25: { net: "0", gross: "0" }, year_p75: { net: "3375", gross: "3750" } } } as unknown as IncomeResp["totals"],
  micros: 1, cadence_sessions: 1, starts: 497, horizon_sessions: 260,
  year_mean: "8232.03", year_median: "4500.00", year_p25: "0", year_p75: "16875.30", week_mean: "158.31", per_paycheck_mean: "316.62",
  auto: { contracts: 1, candace: 2, noise_brake: [], candace_brake: [[333, 1]] },
  paid_year_mean_account: "1800", paid_week_mean_account: "36", per_payout_account: "300", cap_first_net: "900", cap_next_net: "1350", payout_events_max: 5,
  max_possible_account: "6300", max_possible_formula: "5 accounts x (900 first + 4 x 1,350 later payouts, net of 10% split) = 31,500", weeks_in_horizon: 52,
  incl_unpaid_year_mean: "4000", incl_unpaid_week_mean: "77", incl_unpaid_year_median: "0",
  any_payout_pct: "58.3", bust_pct: "56.6", max_payouts_pct: "4.2", median_sessions_to_first: 70, max_possible_year: "31500.00",
};

test("projected income card shows weekly / paycheck numbers and re-queries on plan change", async () => {
  const urls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    urls.push(String(url));
    const fifty = String(url).includes("plan=lucid_pro_50k");
    return new Response(JSON.stringify(fifty ? { ...base, plan: "lucid_pro_50k", week_mean: "282.00", per_paycheck_mean: "564.00", auto: { contracts: 2, candace: 4, noise_brake: [[667, 1]], candace_brake: [] } } : base));
  });
  render(<QueryClientProvider client={new QueryClient()}><IncomeProjection /></QueryClientProvider>);
  expect(await screen.findByTestId("income-week")).toHaveTextContent("$180");
  expect(screen.getByTestId("income-week-funded")).toHaveTextContent("$108");
  expect(screen.getByTestId("income-week-live")).toHaveTextContent("$72");
  expect(screen.getByTestId("income-week-gross")).toHaveTextContent("$200");
  expect(screen.getByTestId("income-live-note")).toHaveTextContent("VERIFY");
  expect(screen.getByTestId("income-paycheck")).toHaveTextContent("$1,500");
  expect(screen.getByTestId("income-median")).toHaveTextContent("$4,500");
  expect(screen.getByTestId("income-note")).toHaveTextContent("only 58.3% of accounts receive a payout and 56.6% bust in year 1");
  expect(screen.getByTestId("income-scenario")).toHaveTextContent("Profit scenario: all 5 accounts get paid (3 funded + 2 live)");
  expect(screen.getByTestId("income-formula")).toHaveTextContent("5 accounts x");
  expect(screen.getByTestId("income-note")).toHaveTextContent("Including accounts that are never paid");
  expect(screen.getByTestId("income-warning")).toHaveTextContent("UNVERIFIED");
  expect(screen.getByRole("option", { name: /Pro 25K \(current\)/i })).toBeInTheDocument();
  expect(urls[0]).toContain("micros=0");
  expect(urls[0]).not.toContain("cadence="); // the server default (best of the study) // D63: automatic size by default
  expect(screen.getByTestId("income-auto")).toHaveTextContent("NOISE 1 + CANDACE 2 micros per account");
  await userEvent.selectOptions(screen.getByLabelText("Plan"), "lucid_pro_50k");
  await waitFor(() => expect(urls.some((u) => u.includes("plan=lucid_pro_50k") && u.includes("funded=5") && u.includes("live=0"))).toBe(true));
  expect(await screen.findByText(/drops to/)).toBeInTheDocument();
  expect(screen.getByTestId("income-auto")).toHaveTextContent("NOISE 2 + CANDACE 4 micros per account");
  await userEvent.selectOptions(screen.getByLabelText("Micros"), "2");
  await waitFor(() => expect(urls.some((u) => u.includes("micros=2"))).toBe(true));
  await userEvent.selectOptions(screen.getByLabelText("Account growth"), "1000");
  await waitFor(() => expect(urls.some((u) => u.includes("grow=1000"))).toBe(true));
});

test("micros 9 is selectable, requests it, and the warning stays visible", async () => {
  localStorage.clear();
  const urls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => { urls.push(String(url)); return new Response(JSON.stringify(base)); });
  render(<QueryClientProvider client={new QueryClient()}><IncomeProjection /></QueryClientProvider>);
  await screen.findByTestId("income-week");
  const opts = Array.from((screen.getByLabelText("Micros") as HTMLSelectElement).options).map((o) => o.value);
  expect(opts).toEqual(["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]);
  await userEvent.selectOptions(screen.getByLabelText("Micros"), "9");
  await waitFor(() => expect(urls.some((u) => u.includes("micros=9"))).toBe(true));
  expect(screen.getByTestId("income-warning")).toHaveTextContent(/UNVERIFIED/);
  await userEvent.selectOptions(screen.getByLabelText("Payout cadence"), "0");
  await waitFor(() => expect(urls.some((u) => u.includes("cadence=0"))).toBe(true));
  expect(screen.getByRole("option", { name: /On-demand, intraday \(CONFIRMED, Lucid help center\)/ })).toBeInTheDocument();
  await userEvent.selectOptions(screen.getByLabelText("Funded accounts"), "2");
  await userEvent.selectOptions(screen.getByLabelText("Live accounts"), "4");
  await waitFor(() => expect(urls.some((u) => u.includes("funded=2") && u.includes("live=4"))).toBe(true));
  expect(Array.from((screen.getByLabelText("Live accounts") as HTMLSelectElement).options).map((o) => o.value)).toEqual(["0", "1", "2", "3", "4", "5"]);
});

test("numbers shown are exactly the server data (nothing hard-coded in the UI)", async () => {
  localStorage.clear();
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({ ...base, totals: { per_account: { ...base.totals!.per_account, week: { net: "246.9", gross: "274" } } }, bust_pct: "12.3", basis: "BASIS-FROM-DATA-FILE" })));
  render(<QueryClientProvider client={new QueryClient()}><IncomeProjection /></QueryClientProvider>);
  expect(await screen.findByTestId("income-week")).toHaveTextContent("$1,235");
  expect(screen.getByTestId("income-note")).toHaveTextContent("12.3% bust in year 1");
  expect(screen.getByText(/BASIS-FROM-DATA-FILE/)).toBeInTheDocument();
});

test("an old (v1/v2) saved calculator state still loads, bad values fall back", () => {
  expect(loadSaved(JSON.stringify({ plan: "lucid_pro_50k", accounts: 3, micros: 6, cadence: 10, grow: 1000, profile: "high" })))
    .toEqual({ plan: "lucid_pro_50k", funded: 3, live: 0, micros: 6, cadence: 10, profile: "high", grow: 1000 });
  expect(loadSaved(JSON.stringify({ funded: 2, live: 5, cadence: 0 }))).toMatchObject({ funded: 2, live: 5, cadence: 0 });
  expect(loadSaved(JSON.stringify({ funded: 0, live: 0 }))).toMatchObject({ funded: 5, live: 0 }); // at least one account
  expect(loadSaved(JSON.stringify({ accounts: 99, micros: 40, cadence: 17, grow: 7, profile: "x" })))
    .toEqual({ plan: null, funded: 5, live: 0, micros: 0, cadence: null, profile: "", grow: 0 });
  expect(loadSaved("not json").micros).toBe(0);
  expect(loadSaved(null).funded).toBe(5);
});
