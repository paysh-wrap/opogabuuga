import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import OrderFlow from "./OrderFlow";
import { fmtVol, footprintWindow, profileWidths, signed, snapSignals, type FlowBar, type OrderFlowData } from "../lib/orderflow";

vi.mock("lightweight-charts", () => {
  const series = { setData: vi.fn(), createPriceLine: vi.fn(), setMarkers: vi.fn(), priceScale: () => ({ applyOptions: vi.fn() }) };
  const chart = {
    addCandlestickSeries: () => series, addHistogramSeries: () => series, addLineSeries: () => series,
    timeScale: () => ({ fitContent: vi.fn(), subscribeVisibleLogicalRangeChange: vi.fn(), setVisibleLogicalRange: vi.fn() }),
    applyOptions: vi.fn(), remove: vi.fn(),
  };
  return { createChart: () => chart, ColorType: { Solid: "solid" }, LineStyle: { Solid: 0, Dotted: 1, Dashed: 2 } };
});

const bar = (t: number, c: string, delta: string, cvd: string, levels: FlowBar["levels"]): FlowBar =>
  ({ time_ms: t, o: "100", h: "102", l: "100", c, v: "30", delta, cvd, zone: "premium", source: "estimated", levels });

const DATA: OrderFlowData = {
  symbol: "MNQ", symbols: ["MNQ", "MGC"], source: "estimated", estimated: true, note: "ESTIMATED from bars — not true order flow",
  method: "close location", tick: "0.25", row_size: "1.00", sessions: ["2026-11-04", "2026-11-05"], session: "2026-11-05",
  bars: [bar(60_000, "101", "5", "5", [{ p: "100.00", bid: "5", ask: "10" }, { p: "101.00", bid: "5", ask: "10" }]),
    bar(120_000, "102", "-3", "2", [{ p: "101.00", bid: "8", ask: "5" }, { p: "102.00", bid: "8", ask: "5" }])],
  profile: { rows: [{ p: "100.00", v: "15" }, { p: "101.00", v: "28" }, { p: "102.00", v: "13" }], poc: "101.00", vah: "102.00", val: "100.00", hvn: [], lvn: [] },
  prior: { session: "2026-11-04", rows: [], poc: "98.00", vah: "99.00", val: "97.00", hvn: [], lvn: [] },
  round_levels: ["100"], signals: [{ time_ms: 130_000, kind: "ABSORPTION", label: "Absorption", direction: "LONG",
    ar: { env: "EXPANSION", location_zone: "F0788", fib: "0.79", value_side: "BELOW_VAL", path_zone: "AVR", path_side: "BELOW", delta_source: "real", confirm_time: 70_000 } }],
  ar: { enabled: false, paper_only: true, verified: false, layers: [
    { key: "ENVIRONMENT", on: true, rule: "trade only in EXPANSION / ROTATION" }, { key: "LOCATION", on: true, rule: "fib" },
    { key: "PATH", on: false, rule: "Asia" }, { key: "CONFIRMATION", on: true, rule: "absorption" }] },
  skips: [{ time_ms: 125_000, direction: "SHORT", code: "OF_COMPRESSION", layer: "ENVIRONMENT", label: "Environment: compression", detail: null,
    ar: { env: "COMPRESSION", location_zone: null, fib: null, value_side: null, path_zone: null, path_side: null, delta_source: "est", confirm_time: null } }],
};

function wrap(data: unknown) {
  vi.spyOn(globalThis, "fetch").mockImplementation(async () => new Response(JSON.stringify(data)));
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
  render(<QueryClientProvider client={new QueryClient()}><MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><OrderFlow /></MemoryRouter></QueryClientProvider>);
}
afterEach(() => vi.restoreAllMocks());

test("Order Flow page labels every panel ESTIMATED, shows summary, profile and alerts", async () => {
  wrap(DATA);
  expect(await screen.findByTestId("of-summary")).toHaveTextContent("▲ +2");
  expect(screen.getAllByTestId("estimated-badge").length).toBeGreaterThanOrEqual(4);
  expect(screen.getAllByTestId("estimated-badge")[0]).toHaveTextContent("ESTIMATED from bars — not true order flow");
  expect(screen.getByTestId("of-zone")).toHaveTextContent("PREMIUM");
  expect(screen.getByTestId("of-profile")).toHaveTextContent("POC");
  expect(screen.getByTestId("of-signals")).toHaveTextContent("▲ LONG · Absorption · EXPANSION · F0788 BELOW_VAL · AVR below Asia · delta real");
  // D101: four AR layers, UNVERIFIED label, refused alerts with reason codes
  expect(screen.getByTestId("of-unverified")).toHaveTextContent("UNVERIFIED · PAPER ONLY");
  expect(screen.getByTestId("of-ar")).toHaveTextContent("3. PATH");
  expect(screen.getByTestId("of-ar")).toHaveTextContent("OFF (plan file switch)");
  expect(screen.getByTestId("of-skips")).toHaveTextContent("▼ SHORT · ENVIRONMENT · OF_COMPRESSION");
  expect(screen.getByTestId("of-skips")).toHaveTextContent("COMPRESSION · — · — · delta est");
  expect(screen.getByTestId("of-footprint")).toBeInTheDocument();
  expect(document.title).toBe("Paytience · Order Flow");
});

test("Order Flow page shows an empty state without bars (no mock data)", async () => {
  wrap({ ...DATA, bars: [], profile: null, prior: null, signals: [], sessions: [], session: null });
  expect(await screen.findByTestId("of-empty")).toHaveTextContent("No recorded 1-minute bars for MNQ");
});

test("pure helpers", () => {
  expect(snapSignals(DATA.bars, DATA.signals)[0]!.bar_ms).toBe(120_000);
  expect(snapSignals(DATA.bars, [{ ...DATA.signals[0]!, time_ms: 1 }])).toEqual([]);
  const w = footprintWindow(DATA.bars, 1, 1);
  expect(w.bars).toHaveLength(1);
  expect(w.rows).toEqual([102, 101]);
  expect(footprintWindow([], 5, 1).rows).toEqual([]);
  expect(footprintWindow([bar(1, "1", "0", "0", [])], 5, 1).rows).toEqual([]);
  expect(profileWidths(DATA.profile).map((r) => r.pct)).toEqual([46, 100, 54]);
  expect(profileWidths(null)).toEqual([]);
  expect([fmtVol("2500"), fmtVol("12.5"), fmtVol("2.5"), fmtVol("4")]).toEqual(["2.5k", "13", "2.5", "4"]);
  expect([signed("0"), signed("-3"), signed("4")]).toEqual(["0", "▼ −3", "▲ +4"]);
});
