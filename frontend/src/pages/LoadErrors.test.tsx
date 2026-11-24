import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Strategy from "./Strategy";
import Today from "./Today";
import WhyNoTrade from "../components/WhyNoTrade";
import SafetyBanners from "../components/SafetyBanners";

/** `failing` paths answer HTTP 500; everything else answers {}. Counts calls per path. */
function server(failing: string[], calls: Record<string, number> = {}) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    const u = String(url);
    calls[u] = (calls[u] ?? 0) + 1;
    if (failing.includes(u)) return new Response(JSON.stringify({ detail: "boom" }), { status: 500 });
    return new Response("{}");
  });
  return calls;
}
const wrap = (el: React.ReactElement) =>
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{el}</MemoryRouter></QueryClientProvider>);
afterEach(() => vi.restoreAllMocks());

test("SafetyBanners shows an alert (treat as NOT safe) when /api/safety fails", async () => {
  server(["/api/safety"]);
  wrap(<SafetyBanners />);
  const a = await screen.findByRole("alert");
  expect(a).toHaveTextContent("Cannot load safety status: boom");
  expect(a).toHaveTextContent("NOT safe");
});

test("Strategy page shows an error with Retry instead of endless Loading, and retry refetches", async () => {
  const calls = server(["/api/strategy"]);
  wrap(<Strategy />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Cannot load the Strategy page: boom");
  expect(screen.queryByText("Loading…")).toBeNull();
  const before = calls["/api/strategy"] ?? 0;
  await userEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByRole("alert");
  expect(calls["/api/strategy"]).toBeGreaterThan(before);
});

test("Today shows an error with Retry when /api/today fails", async () => {
  server(["/api/today"]);
  wrap(<Today />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Cannot load today: boom");
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
});

test("Why no trade shows an error with Retry when /api/signals/skips fails", async () => {
  server(["/api/signals/skips"]);
  wrap(<WhyNoTrade />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Cannot load skip reasons: boom");
  expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
});
