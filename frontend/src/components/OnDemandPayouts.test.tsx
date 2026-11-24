import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import OnDemandCard from "./OnDemandPayouts";

const base = { limited_by: "", reason: "OK", dll_enabled: true, hedging_violation: false, paused: false };
const body = {
  status: "CONFIRMED (Lucid help center)", pause_rule: "After you request an on-demand payout, trading on that account is paused until the end of the trading day.",
  accounts: [
    { ...base, account_id: 1, label: "P1", available: true, amount: "600.00", net: "540.00", limited_by: "session_profit", message: "ok" },
    { ...base, account_id: 2, label: "P2", available: false, amount: "0", net: "0", reason: "HEDGING_VIOLATION", message: "This account has a Hedging Violation: it is not eligible for intraday payouts.", hedging_violation: true },
    { ...base, account_id: 3, label: "P3", available: false, amount: "0", net: "0", reason: "PAUSED_UNTIL_EOD", message: "paused", paused: true },
  ],
};

test("on-demand card: amount payable now, blocked reasons, pause rule, manual planning only", async () => {
  const calls: string[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url, init) => { calls.push(`${init?.method ?? "GET"} ${String(url)}`); return new Response(JSON.stringify(body)); });
  const run = vi.fn((f: () => Promise<unknown>) => void f());
  render(<QueryClientProvider client={new QueryClient()}><OnDemandCard run={run} /></QueryClientProvider>);
  expect(await screen.findByTestId("od-amount-1")).toHaveTextContent("On-demand available: $600 gross (net $540), limited by this session's profit");
  expect(screen.getByTestId("od-reason-2")).toHaveTextContent("Hedging Violation");
  expect(screen.getByTestId("od-3")).toHaveTextContent("TRADING PAUSED until the end of the trading day");
  expect(screen.getByTestId("on-demand-rule")).toHaveTextContent("until the end of the trading day");
  expect(screen.getByTestId("on-demand-rule")).toHaveTextContent("never submits a payout");
  const plan = screen.getAllByRole("button", { name: "Plan this payout" });
  expect(plan[0]).toBeEnabled(); expect(plan[1]).toBeDisabled(); expect(plan[2]).toBeDisabled();
  await userEvent.click(plan[0]!);
  await waitFor(() => expect(calls).toContain("POST /api/payouts/on-demand/1/plan"));
  await userEvent.click(screen.getAllByRole("checkbox")[0]!);
  await waitFor(() => expect(calls).toContain("PATCH /api/accounts/1"));
});
