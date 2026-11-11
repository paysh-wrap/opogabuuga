import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import TradingR1Card, { type Tr1Resp } from "./TradingR1Card";

const LABEL = "Information only — never triggers or gates a trade";
function show(t: Tr1Resp) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify(t)));
  render(<QueryClientProvider client={new QueryClient()}><TradingR1Card /></QueryClientProvider>);
}

test("not configured: shows the reason and the info-only label, no form, no answer", async () => {
  show({ label: LABEL, configured: false, message: "not configured — Trading-R1 is not installed (run `make tradingr1`)", running: false, last: null });
  expect(await screen.findByTestId("trading-r1-off")).toHaveTextContent("not configured");
  expect(screen.getByTestId("trading-r1-label")).toHaveTextContent("never triggers or gates a trade");
  expect(screen.queryByLabelText("Trading-R1 question")).toBeNull();
  expect(screen.queryByTestId("trading-r1-last")).toBeNull();
});

test("configured: shows the question box and the last answer", async () => {
  show({ label: LABEL, configured: true, message: "ready", running: false, last: { question: "gold?", ok: true, text: "Real yields fell.", termination: "final", error: "", rounds: 3, at: "2026-11-11T14:00:00+00:00" } });
  expect(await screen.findByTestId("trading-r1-text")).toHaveTextContent("Real yields fell.");
  expect(screen.getByLabelText("Trading-R1 question")).toBeInTheDocument();
});

test("a failed run shows its error", async () => {
  show({ label: LABEL, configured: true, message: "ready", running: false, last: { question: "gold?", ok: false, text: "", termination: "", error: "HTTP 401", rounds: 0, at: "t" } });
  expect(await screen.findByTestId("trading-r1-last")).toHaveTextContent("failed: HTTP 401");
});
