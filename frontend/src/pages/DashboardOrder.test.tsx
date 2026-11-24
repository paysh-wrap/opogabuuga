import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "./Dashboard";

test("Why no trade sits near the top of the Dashboard, before the checklist, markets and plan blocks", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) => {
    const u = String(url);
    if (u === "/api/dashboard") return new Response(JSON.stringify({ session: "2026-11-24", mode: "OFF", bias: {}, accounts: [] }));
    if (u === "/api/signals/skips") return new Response(JSON.stringify({ date: "d", counts: {}, avg_20: {}, sessions_in_avg: 0 }));
    return new Response("{}");
  });
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><Dashboard /></MemoryRouter></QueryClientProvider>);
  const why = await screen.findByTestId("why-no-trade");
  const sections = [...document.querySelectorAll("section, p")].filter((e) => e !== why);
  const idx = (el: Element) => [...document.body.querySelectorAll("*")].indexOf(el);
  const sessionLine = screen.getByText(/Session 2026-11-24/);
  expect(idx(why)).toBeLessThan(idx(sessionLine)); // above the session / bias line, the plan blocks and the projection
  expect(sections.length).toBeGreaterThan(0);
  vi.restoreAllMocks();
});
