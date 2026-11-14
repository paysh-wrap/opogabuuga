import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Header from "./Header";

// the header's own widgets have their own tests; only the Live trade pill is under test here
vi.mock("./HeaderStatus", () => ({ default: () => null }));
vi.mock("./HeaderAlerts", () => ({ AlertsBell: () => null, JobsIndicator: () => null }));

function renderWith(live: boolean, lowRisk = false) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const u = String(input);
    if (u.startsWith("/api/live")) return new Response(JSON.stringify({ live, checklist: [] }));
    if (u.startsWith("/api/risk/low-risk")) return new Response(JSON.stringify({ enabled: lowRisk }));
    if (u.startsWith("/api/health")) return new Response(JSON.stringify({ app: "paytience", status: "ok", mode: live ? "LIVE" : "PAPER" }));
    return new Response(JSON.stringify({}));
  });
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Header /></MemoryRouter></QueryClientProvider>);
}
afterEach(() => vi.restoreAllMocks());

test("the header pill is 'Live trade' and says OFF while paper trading (user 2026-11-14)", async () => {
  renderWith(false, true);
  const pill = await screen.findByTestId("live-trade-pill");
  expect(pill).toHaveTextContent("Live trade · OFF · Lower risk");
  expect(pill).toHaveAttribute("href", "/risk#live-trading");
  expect(screen.queryByText(/^Intraday/)).toBeNull();
});

test("it says ON only when the live gates report live", async () => {
  renderWith(true);
  expect(await screen.findByTestId("live-trade-pill")).toHaveTextContent("Live trade · ON");
});
