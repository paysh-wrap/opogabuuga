import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import GateChain from "./GateChain";

test("gate chain shows each gate's state and the AI record from the server", async () => {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({
    strategies: [], noise_warmup: { sessions: 0, needed: 10, ready: false }, markets: {},
    ai_ledger: [{ proxy: "QQQ", symbol: "MNQ", state: "WARMUP", badge: "ADVISORY", required_accuracy: 0.7, min_calls: 30, stats: { n: 2, hit_rate: 0.5, brier: 0.25, wilson_lb: 0 } }],
    gate_chain: [
      { id: "G1", name: "Window", kind: "firm-safe", on: true, locked: true, text: "Entries only inside windows." },
      { id: "AI", name: "AI bias", kind: "ai", on: true, locked: false, text: "advisory" },
      { id: "OB", name: "Order-block filter", kind: "study", on: false, locked: false, text: "OFF" },
    ],
  })));
  render(<QueryClientProvider client={new QueryClient()}><GateChain /></QueryClientProvider>);
  expect(await screen.findByTestId("chain-G1")).toHaveTextContent("ON");
  expect(screen.getByTestId("chain-OB")).toHaveTextContent("OFF");
  expect(screen.getByTestId("chain-ai-status")).toHaveTextContent("2/30");
  expect(screen.getByTestId("chain-ai-status")).toHaveTextContent("70%");
});
