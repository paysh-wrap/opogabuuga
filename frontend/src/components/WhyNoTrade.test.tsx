import { render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import WhyNoTrade from "./WhyNoTrade";

function wrap(body: unknown) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify(body)));
  render(<QueryClientProvider client={new QueryClient()}><WhyNoTrade /></QueryClientProvider>);
}
afterEach(() => vi.restoreAllMocks());

test("skips are grouped by strategy with plain labels for strategy codes", async () => {
  wrap({ date: "2026-11-24", sessions_in_avg: 2, counts: { CONSISTENCY_DAY_STOP: 4, OF_LOCATION: 2, LATE_DAY_NOT_ACTIVE: 1, RR_BELOW_MIN: 3 }, avg_20: { OF_LOCATION: 1 } });
  const of = await screen.findByTestId("skip-group-Order Flow");
  expect(of).toHaveTextContent("Order Flow · 2 skipped today");
  expect(within(of).getByText("Order Flow: price not at a good location")).toBeInTheDocument();
  expect(screen.getByTestId("skip-group-Confluence model")).toHaveTextContent("Reward:risk below minimum");
  expect(screen.getByTestId("skip-group-Any strategy")).toHaveTextContent("Consistency day stop reached — no new entries today");
  expect(screen.getByTestId("skip-group-Late-day option")).toHaveTextContent("Late-day option not active for this account");
});

test("no skips says so", async () => {
  wrap({ date: "2026-11-24", sessions_in_avg: 0, counts: {}, avg_20: {} });
  expect(await screen.findByText("No skipped signals today.")).toBeInTheDocument();
});
