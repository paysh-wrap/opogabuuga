import { describe, expect, it } from "vitest";
import { replayLevels, replayMarkers, type ReplayData } from "./ReplayChart";

const d: ReplayData = {
  trade: { direction: "LONG", entry: "100", exit: "110", opened_ms: 120_000, closed_ms: 300_000, exit_reason: "TP" },
  bars: [],
  plan: { entry: "100", stop: "95", take_profit: "110", partial: null, breakeven: "100.5" },
  fractal: { c1_high: 102, c1_low: 98, cisd_level: 99, sweep_time_ms: 60_000 },
  mso_events: [{ event: "MSO_CHOCH", direction: "LONG", time_ms: 180_000 }],
};

describe("replay chart data", () => {
  it("orders markers by time: sweep, entry, CHoCH, exit", () => {
    const m = replayMarkers(d);
    expect(m.map((x) => x.text)).toEqual(["sweep", "Entry 100", "CHOCH", "Exit 110 TP"]);
    expect(m[1]?.shape).toBe("arrowUp");
  });
  it("draws plan + model levels, skipping missing ones", () => {
    expect(replayLevels(d).map((l) => l.title)).toEqual(["Entry", "Stop", "TP", "BE", "C1 high", "C1 low", "CISD"]);
    expect(replayLevels({ ...d, plan: null, fractal: null })).toEqual([]);
  });
  it("short trades point down; open trades have no exit marker", () => {
    const m = replayMarkers({ ...d, trade: { ...d.trade, direction: "SHORT", closed_ms: null }, fractal: null, mso_events: [] });
    expect(m).toHaveLength(1);
    expect(m[0]?.shape).toBe("arrowDown");
  });
});
