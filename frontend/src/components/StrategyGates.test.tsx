import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import StrategyGates from "./StrategyGates";

const gates = {
  strategies: [
    { key: "order_flow", name: "Order Flow", on: false, symbols: ["MNQ"], lucid_code: null,
      last: { status: "SKIP", code: "OF_NO_CONFIRM", at: "2026-11-05T15:00:00+00:00", symbol: "MNQ", direction: "LONG", source: "audit" },
      gates: [
        { id: "ENVIRONMENT", name: "AR · Environment", text: "Allowed: EXPANSION", codes: ["OF_COMPRESSION"], kind: "entry", status: "PASS" },
        { id: "CONFIRMATION", name: "AR · Confirmation", text: "≤ 3 min", codes: ["OF_NO_CONFIRM"], kind: "entry", status: "FAIL" },
        { id: "PLAN", name: "Stop + R:R plan", text: "2R", codes: [], kind: "entry", status: "NOT_REACHED" },
        { id: "FLAT", name: "Flat", text: "16:00", codes: [], kind: "exit", status: null },
      ] },
    { key: "noise", name: "NOISE", on: true, symbols: ["MNQ"], lucid_code: "NEWS_BLACKOUT",
      last: { status: "SKIP", code: "NEWS_BLACKOUT", at: "2026-11-05T15:00:00+00:00", symbol: "MNQ", direction: "SHORT", source: "signal" },
      gates: [
        { id: "BREAKOUT", name: "Noise-band breakout", text: "close above band", codes: [], kind: "entry", status: "PASS" },
        { id: "LUCID", name: "Lucid rules", text: "news", codes: [], kind: "entry", status: "FAIL" },
        { id: "AI_PROVEN", name: "AI block", text: "≥ 70%", codes: ["BIAS_PROVEN_AGAINST"], kind: "entry", status: "NOT_REACHED" },
      ] },
  ],
  lucid_rules: [{ id: "NEWS", name: "News + calendar", text: "No entry 15 min before", codes: ["NEWS_BLACKOUT"], kind: "entry" }],
};
const strategies = { strategies: [], noise_warmup: { sessions: 0, needed: 10, ready: false }, markets: {},
  ai_ledger: [{ proxy: "QQQ", symbol: "MNQ", state: "WARMUP", badge: "ADVISORY", required_accuracy: 0.7, min_calls: 30, stats: { n: 2, hit_rate: 0.5, brier: 0.25, wilson_lb: 0 } }] };

afterEach(() => vi.restoreAllMocks());

test("each strategy shows only its own gates with live status; Lucid rules once", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async (url) =>
    new Response(JSON.stringify(String(url).startsWith("/api/strategy-gates") ? gates : strategies)));
  render(<QueryClientProvider client={new QueryClient()}><StrategyGates /></QueryClientProvider>);
  expect(await screen.findByTestId("sg-order_flow-CONFIRMATION")).toHaveTextContent("✗ fail");
  expect(screen.getByTestId("sg-order_flow-ENVIRONMENT")).toHaveTextContent("✓ pass");
  expect(screen.getByTestId("sg-order_flow-PLAN")).toHaveTextContent("not reached");
  expect(screen.getByTestId("sg-order_flow")).toHaveTextContent("OF_NO_CONFIRM");
  expect(screen.getByTestId("sg-order_flow")).toHaveTextContent("Exits:");
  expect(screen.queryByTestId("sg-order_flow-BREAKOUT")).toBeNull(); // NOISE gates stay on the NOISE card
  expect(screen.getByTestId("sg-noise-lucid")).toHaveTextContent("NEWS_BLACKOUT");
  expect(screen.getAllByTestId("lucid-rules")).toHaveLength(1);
  expect(screen.getByTestId("lucid-NEWS")).toHaveTextContent("LOCKED");
  expect(screen.queryByText(/G[2-7]\b/)).toBeNull();
  expect(await screen.findByTestId("ai-threshold")).toBeInTheDocument();
});

test("shows an error instead of mock data when the API fails", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response("nope", { status: 500 }));
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><StrategyGates /></QueryClientProvider>);
  expect(await screen.findByRole("alert")).toHaveTextContent("Cannot load the strategy gates");
});
