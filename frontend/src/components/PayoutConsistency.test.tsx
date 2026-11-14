import { act, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { PayoutConsistencyCard, PayoutConsistencyNote, type PayoutConsistencyView } from "./PayoutConsistency";

const unmet: PayoutConsistencyView = {
  pct: "60.0", limit: "35", largest_day: "600", cycle_profit: "1000", eligible: false, needed_cycle_profit: "1715.00",
  still_needed: "715.00", text: "Largest day $600.00 must be at most 35% ... $715.00 more ...", date_known: false,
  verify: "Purchase / last reset date unknown: the stricter legacy limit is used. Enter the date on the Accounts page.",
};

test("not met + unknown date shows the gold VERIFY badge, the limit and what is still needed", () => {
  render(<PayoutConsistencyNote v={unmet} id={1} />);
  const n = screen.getByTestId("pcons-1");
  expect(n).toHaveTextContent("PAYOUT CONSISTENCY NOT MET");
  expect(n).toHaveTextContent("limit 35%");
  expect(n).toHaveTextContent("$715.00 more");
  expect(n).toHaveTextContent("VERIFY");
});

test("met with a known date has no VERIFY badge", () => {
  render(<PayoutConsistencyNote v={{ ...unmet, pct: "25.0", limit: "40", eligible: true, date_known: true, verify: null, still_needed: "0" }} id={2} />);
  const n = screen.getByTestId("pcons-2");
  expect(n).toHaveTextContent("PAYOUT CONSISTENCY MET");
  expect(n).not.toHaveTextContent("VERIFY");
});

test("Payouts card lists FUNDED accounts and stays hidden when there are none", async () => {
  const f = vi.spyOn(globalThis, "fetch");
  f.mockImplementation(async () => new Response(JSON.stringify({ accounts: [{ account_id: 7, label: "P1", ...unmet }] })));
  const { unmount } = render(<QueryClientProvider client={new QueryClient()}><PayoutConsistencyCard /></QueryClientProvider>);
  expect(await screen.findByTestId("payout-consistency")).toHaveTextContent("P1");
  expect(screen.getByTestId("pcons-7")).toBeInTheDocument();
  unmount();
  f.mockImplementation(async () => new Response(JSON.stringify({ accounts: [] })));
  render(<QueryClientProvider client={new QueryClient()}><PayoutConsistencyCard /></QueryClientProvider>);
  await act(() => new Promise((r) => setTimeout(r, 50)));
  expect(screen.queryByTestId("payout-consistency")).toBeNull();
});
