import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import TaMgcCard from "./TaMgcCard";
import type { StrategiesResp, TaMgcResp } from "./StrategyButtons";

function show(t: TaMgcResp) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify({ strategies: [], noise_warmup: { sessions: 0, needed: 10, ready: false }, ai_ledger: [], markets: {}, ta_mgc: t } as StrategiesResp)));
  render(<QueryClientProvider client={new QueryClient()}><TaMgcCard /></QueryClientProvider>);
}

test("shows the latest MGC research, the setup, Vibe-Trading and the decision", async () => {
  show({
    enabled: true, connected: true, message: null,
    research: { day: "2026-11-10", label: "LONG 72·VT LONG 80", setup: { side: "LONG", confidence: 72, entry_low: 2700, entry_high: 2702, invalidation: 2690, target: 2724, valid_until: "09:00", reasons: ["DXY falling"] }, vt: { direction: "LONG", confidence: 80, reason: "r" }, vt_note: "", error: "", report: "x" },
    decision: { day: "2026-11-10", status: "PASS", code: "TAKEN", direction: "LONG", mode: "RESEARCH", below_preferred_2r: true },
  });
  expect(await screen.findByTestId("ta-mgc-setup")).toHaveTextContent("LONG (72%) · zone 2700–2702 · invalidation 2690 · target 2724 · valid until 09:00 ET");
  expect(screen.getByText("DXY falling")).toBeInTheDocument();
  expect(screen.getByTestId("ta-mgc-vt")).toHaveTextContent("LONG 80%");
  expect(screen.getByTestId("ta-mgc-decision")).toHaveTextContent("TRADE LONG · TAKEN · from the research setup · below preferred 2R");
  expect(screen.queryByTestId("ta-mgc-key")).toBeNull();
});

test("no key: says AI key not connected and shows nothing else", async () => {
  show({ enabled: true, connected: false, message: "AI key not connected", research: null, decision: null });
  expect(await screen.findByTestId("ta-mgc-key")).toHaveTextContent("AI key not connected");
  expect(screen.queryByTestId("ta-mgc-research")).toBeNull();
});

test("a failed run and a skip with its reason code", async () => {
  show({
    enabled: true, connected: true, message: null,
    research: { day: "2026-11-10", label: "ERR -", setup: null, vt: null, vt_note: "Vibe-Trading not connected", error: "timeout", report: "" },
    decision: { day: "2026-11-10", status: "SKIP", code: "RESEARCH_FAILED", direction: "NONE", mode: "RESEARCH", below_preferred_2r: false },
  });
  expect(await screen.findByTestId("ta-mgc-research")).toHaveTextContent("failed: timeout");
  expect(screen.getByTestId("ta-mgc-vt")).toHaveTextContent("no opinion");
  expect(screen.getByTestId("ta-mgc-decision")).toHaveTextContent("NO TRADE · RESEARCH_FAILED");
});
