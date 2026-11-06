import { useEffect, useRef } from "react";
import { ColorType, LineStyle, createChart, type IChartApi, type SeriesMarker, type Time, type UTCTimestamp } from "lightweight-charts";
import { theme } from "../lib/theme";

export interface ReplayBar { time_ms: number; o: string; h: string; l: string; c: string }
export interface ReplayData {
  trade: { direction: string; entry: string; exit: string | null; opened_ms: number; closed_ms: number | null; exit_reason?: string | null };
  bars: ReplayBar[];
  plan: { entry: string | null; stop: string | null; take_profit: string | null; partial: string | null; breakeven: string | null } | null;
  fractal: Record<string, number> | null;
  mso_events: { event: string; direction: string; time_ms: number }[];
}

const sec = (ms: number) => Math.floor(ms / 1000) as UTCTimestamp;

/** Markers/levels for one trade (pure — tested). Colors stay blue/gold (§18). */
export function replayMarkers(d: ReplayData): SeriesMarker<Time>[] {
  const long = d.trade.direction === "LONG";
  const m: SeriesMarker<Time>[] = [
    { time: sec(d.trade.opened_ms), position: long ? "belowBar" : "aboveBar", color: theme.gold, shape: long ? "arrowUp" : "arrowDown", text: `Entry ${d.trade.entry}` },
  ];
  if (d.trade.closed_ms) m.push({ time: sec(d.trade.closed_ms), position: long ? "aboveBar" : "belowBar", color: theme.blueLight, shape: "circle", text: `Exit ${d.trade.exit ?? ""} ${d.trade.exit_reason ?? ""}`.trim() });
  for (const e of d.mso_events) m.push({ time: sec(e.time_ms), position: e.direction === "LONG" ? "belowBar" : "aboveBar", color: theme.blue, shape: "square", text: e.event.replace("MSO_", "") });
  const f = d.fractal;
  if (f?.sweep_time_ms) m.push({ time: sec(f.sweep_time_ms), position: long ? "belowBar" : "aboveBar", color: theme.goldLight, shape: "circle", text: "sweep" });
  return m.sort((a, b) => Number(a.time) - Number(b.time));
}

export function replayLevels(d: ReplayData): { price: number; title: string; color: string; dashed: boolean }[] {
  const out: { price: number; title: string; color: string; dashed: boolean }[] = [];
  const add = (v: string | number | null | undefined, title: string, color: string, dashed = false) => { if (v != null && v !== "") out.push({ price: Number(v), title, color, dashed }); };
  const p = d.plan;
  if (p) { add(p.entry, "Entry", theme.gold); add(p.stop, "Stop", theme.blue); add(p.take_profit, "TP", theme.goldLight); add(p.partial, "Partial", theme.goldLight, true); add(p.breakeven, "BE", theme.blueLight, true); }
  const f = d.fractal;
  if (f) { add(f.c1_high, "C1 high", theme.blueLight, true); add(f.c1_low, "C1 low", theme.blueLight, true); add(f.cisd_level, "CISD", theme.gold, true); add(f.t1, "T1", theme.goldLight, true); add(f.t2, "T2", theme.goldLight, true); }
  return out;
}

export default function ReplayChart({ data }: { data: ReplayData }) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!box.current || data.bars.length === 0) return;
    const chart: IChartApi = createChart(box.current, {
      height: 380,
      layout: { background: { type: ColorType.Solid, color: theme.card }, textColor: theme.blueLight },
      grid: { vertLines: { color: theme.border }, horzLines: { color: theme.border } },
      timeScale: { timeVisible: true, secondsVisible: false, borderColor: theme.border },
      rightPriceScale: { borderColor: theme.border },
    });
    const s = chart.addCandlestickSeries({ upColor: theme.gold, borderUpColor: theme.gold, wickUpColor: theme.gold, downColor: theme.blue, borderDownColor: theme.blue, wickDownColor: theme.blue });
    s.setData(data.bars.map((b) => ({ time: sec(b.time_ms), open: Number(b.o), high: Number(b.h), low: Number(b.l), close: Number(b.c) })));
    for (const l of replayLevels(data)) s.createPriceLine({ price: l.price, color: l.color, lineWidth: 1, lineStyle: l.dashed ? LineStyle.Dashed : LineStyle.Solid, axisLabelVisible: true, title: l.title });
    s.setMarkers(replayMarkers(data));
    chart.timeScale().fitContent();
    const ro = new ResizeObserver(() => chart.applyOptions({ width: box.current?.clientWidth ?? 600 }));
    ro.observe(box.current);
    return () => { ro.disconnect(); chart.remove(); };
  }, [data]);
  if (data.bars.length === 0) return <p className="text-sm">No recorded 1-minute bars for this trade yet (bars are recorded from your TradingView heartbeats).</p>;
  return <div ref={box} className="w-full" data-testid="replay-chart" />;
}
