import { useEffect, useRef, useState } from "react";
import { ColorType, LineStyle, createChart, type IChartApi, type SeriesMarker, type Time, type UTCTimestamp } from "lightweight-charts";
import { theme } from "../lib/theme";
import { SIGNAL_SHORT, fmtVol, footprintWindow, priceKey, profileWidths, snapSignals, type OrderFlowData } from "../lib/orderflow";

const sec = (ms: number) => Math.floor(ms / 1000) as UTCTimestamp;
const alpha = (hex: string, a: number) => `${hex}${Math.round(a * 255).toString(16).padStart(2, "0")}`;

/** Visible honesty badge on every estimated panel (D98). */
export function EstimatedBadge({ d }: { d: Pick<OrderFlowData, "estimated" | "note"> }) {
  if (!d.estimated) return <span className="rounded border border-blue px-2 py-0.5 text-xs text-blue">tick data</span>;
  return <span data-testid="estimated-badge" className="rounded border border-gold px-2 py-0.5 text-xs font-semibold text-gold">{d.note}</span>;
}

function baseChart(el: HTMLDivElement, height: number): IChartApi {
  return createChart(el, {
    height,
    width: el.clientWidth || 600,
    layout: { background: { type: ColorType.Solid, color: theme.card }, textColor: theme.blueLight },
    grid: { vertLines: { color: theme.border }, horzLines: { color: theme.border } },
    timeScale: { timeVisible: true, secondsVisible: false, borderColor: theme.border },
    rightPriceScale: { borderColor: theme.border },
  });
}

/** Candles + delta histogram (overlay scale at the bottom) + CVD line chart, with value / round / signal marks. */
export function CandleDeltaChart({ d }: { d: OrderFlowData }) {
  const box = useRef<HTMLDivElement>(null);
  const cvdBox = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!box.current || !cvdBox.current || d.bars.length === 0) return;
    const chart = baseChart(box.current, 380);
    const candles = chart.addCandlestickSeries({ upColor: theme.gold, borderUpColor: theme.gold, wickUpColor: theme.gold, downColor: theme.blue, borderDownColor: theme.blue, wickDownColor: theme.blue });
    candles.priceScale().applyOptions({ scaleMargins: { top: 0.05, bottom: 0.28 } });
    candles.setData(d.bars.map((b) => ({ time: sec(b.time_ms), open: Number(b.o), high: Number(b.h), low: Number(b.l), close: Number(b.c) })));
    const delta = chart.addHistogramSeries({ priceScaleId: "delta", priceFormat: { type: "volume" } });
    delta.priceScale().applyOptions({ scaleMargins: { top: 0.78, bottom: 0 } });
    delta.setData(d.bars.map((b) => ({ time: sec(b.time_ms), value: Number(b.delta), color: Number(b.delta) >= 0 ? theme.gold : theme.blue })));
    const line = (v: string | null | undefined, title: string, color: string, style: LineStyle) => {
      if (v != null) candles.createPriceLine({ price: Number(v), color, lineWidth: 1, lineStyle: style, axisLabelVisible: true, title });
    };
    const p = d.profile;
    if (p) { line(p.poc, "POC", theme.gold, LineStyle.Solid); line(p.vah, "VAH", theme.goldLight, LineStyle.Dashed); line(p.val, "VAL", theme.goldLight, LineStyle.Dashed); }
    const q = d.prior;
    if (q) { line(q.poc, "pPOC", theme.blueLight, LineStyle.Solid); line(q.vah, "pVAH · premium above", theme.blueLight, LineStyle.Dashed); line(q.val, "pVAL · discount below", theme.blueLight, LineStyle.Dashed); }
    for (const r of d.round_levels) line(r, "", theme.border, LineStyle.Dotted);
    const marks: SeriesMarker<Time>[] = snapSignals(d.bars, d.signals).map((s) => {
      const long = s.direction === "LONG";
      return { time: sec(s.bar_ms), position: long ? "belowBar" : "aboveBar", color: long ? theme.gold : theme.blueLight, shape: long ? "arrowUp" : "arrowDown", text: SIGNAL_SHORT[s.kind] ?? s.kind };
    });
    candles.setMarkers(marks);
    chart.timeScale().fitContent();
    const cvdChart = baseChart(cvdBox.current, 150);
    const cvd = cvdChart.addLineSeries({ color: theme.gold, lineWidth: 2 });
    cvd.setData(d.bars.map((b) => ({ time: sec(b.time_ms), value: Number(b.cvd) })));
    cvdChart.timeScale().fitContent();
    chart.timeScale().subscribeVisibleLogicalRangeChange((r) => { if (r) cvdChart.timeScale().setVisibleLogicalRange(r); });
    const el = box.current;
    const ro = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(() => { const w = el.clientWidth || 600; chart.applyOptions({ width: w }); cvdChart.applyOptions({ width: w }); });
    ro?.observe(el);
    return () => { ro?.disconnect(); chart.remove(); cvdChart.remove(); };
  }, [d]);
  return (
    <div className="space-y-3">
      <div ref={box} className="w-full" data-testid="of-candles" />
      <div className="flex flex-wrap items-center gap-2 text-sm"><span className="font-semibold text-gold">Cumulative delta (CVD)</span><EstimatedBadge d={d} /></div>
      <div ref={cvdBox} className="w-full" data-testid="of-cvd" />
    </div>
  );
}

const COL = 68;
const ROW_H = 16;

/** Footprint grid (canvas): last bars that fit the width; each cell = sell (bid) × buy (ask) volume at that price.
 *  Rows above the prior VAH are shaded gold (premium), below the prior VAL blue (discount). */
export function FootprintGrid({ d }: { d: OrderFlowData }) {
  const wrap = useRef<HTMLDivElement>(null);
  const cv = useRef<HTMLCanvasElement>(null);
  const [width, setWidth] = useState(640);
  useEffect(() => {
    const el = wrap.current;
    if (!el) return;
    setWidth(el.clientWidth || 640);
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth || 640));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  const axis = 64;
  const n = Math.max(1, Math.floor((width - axis) / COL));
  const row = Number(d.row_size);
  const win = footprintWindow(d.bars, n, row);
  useEffect(() => {
    const c = cv.current;
    const ctx = c?.getContext("2d");
    if (!c || !ctx || win.rows.length === 0) return;
    const dpr = window.devicePixelRatio || 1;
    const h = win.rows.length * ROW_H + 22;
    c.width = width * dpr; c.height = h * dpr; c.style.width = `${width}px`; c.style.height = `${h}px`;
    ctx.scale(dpr, dpr);
    ctx.fillStyle = theme.card; ctx.fillRect(0, 0, width, h);
    ctx.font = "11px ui-monospace, monospace"; ctx.textBaseline = "middle";
    const pvah = d.prior?.vah != null ? Number(d.prior.vah) : null;
    const pval = d.prior?.val != null ? Number(d.prior.val) : null;
    const poc = d.profile?.poc != null ? priceKey(d.profile.poc) : null;
    let maxCell = 0;
    for (const b of win.bars) for (const l of b.levels) maxCell = Math.max(maxCell, Number(l.bid) + Number(l.ask));
    win.rows.forEach((p, i) => {
      const y = i * ROW_H;
      if (pvah != null && p > pvah) { ctx.fillStyle = alpha(theme.gold, 0.07); ctx.fillRect(0, y, width, ROW_H); }
      if (pval != null && p < pval) { ctx.fillStyle = alpha(theme.blue, 0.1); ctx.fillRect(0, y, width, ROW_H); }
      ctx.fillStyle = p === poc ? theme.gold : theme.blueLight;
      ctx.fillText(String(p), 4, y + ROW_H / 2);
      if (p === poc) { ctx.strokeStyle = theme.gold; ctx.strokeRect(axis, y + 0.5, width - axis - 1, ROW_H - 1); }
    });
    win.bars.forEach((b, j) => {
      const x = axis + j * COL;
      const byP = new Map(b.levels.map((l) => [priceKey(l.p), l]));
      win.rows.forEach((p, i) => {
        const l = byP.get(p);
        if (!l) return;
        const bid = Number(l.bid), ask = Number(l.ask), y = i * ROW_H;
        const a = maxCell > 0 ? 0.12 + 0.5 * ((bid + ask) / maxCell) : 0.12;
        ctx.fillStyle = alpha(ask >= bid ? theme.gold : theme.blue, Math.min(a, 0.62));
        ctx.fillRect(x + 1, y + 1, COL - 2, ROW_H - 2);
        ctx.fillStyle = theme.blueLight; ctx.textAlign = "right"; ctx.fillText(fmtVol(bid), x + COL / 2 - 3, y + ROW_H / 2);
        ctx.fillStyle = theme.goldLight; ctx.textAlign = "left"; ctx.fillText(fmtVol(ask), x + COL / 2 + 3, y + ROW_H / 2);
        ctx.textAlign = "left";
      });
      const yb = win.rows.length * ROW_H + 11;
      const dv = Number(b.delta);
      ctx.fillStyle = dv >= 0 ? theme.gold : theme.blueLight;
      ctx.fillText(`${dv >= 0 ? "▲" : "▼"}${fmtVol(Math.abs(dv))}`, x + 4, yb);
    });
  }, [win, width, d]);
  if (win.rows.length === 0) return <p className="text-sm">No footprint rows for this session.</p>;
  const last = win.bars[win.bars.length - 1];
  return (
    <div ref={wrap} className="w-full overflow-hidden">
      <p className="mb-1 text-xs text-blue">Last {win.bars.length} bar(s) · row {d.row_size} · cell = sell × buy · bottom row = bar delta · last bar {last ? new Date(last.time_ms).toLocaleTimeString() : ""}</p>
      <div className="max-h-[480px] overflow-y-auto"><canvas ref={cv} data-testid="of-footprint" aria-label="Footprint grid" /></div>
    </div>
  );
}

/** Session volume profile as horizontal bars (POC / value area / HVN / LVN marked in text, not colour alone). */
export function VolumeProfile({ d }: { d: OrderFlowData }) {
  const p = d.profile;
  const rows = profileWidths(p);
  if (!p || rows.length === 0) return <p className="text-sm">No profile yet.</p>;
  const hvn = new Set(p.hvn.map(priceKey)), lvn = new Set(p.lvn.map(priceKey));
  const poc = p.poc != null ? priceKey(p.poc) : null;
  const vah = p.vah != null ? Number(p.vah) : null, val = p.val != null ? Number(p.val) : null;
  return (
    <div data-testid="of-profile" className="max-h-[480px] overflow-y-auto text-xs">
      {rows.map((r) => {
        const k = priceKey(r.p);
        const inVa = vah != null && val != null && k <= vah && k >= val;
        const tag = k === poc ? "POC" : hvn.has(k) ? "HVN" : lvn.has(k) ? "LVN" : "";
        return (
          <div key={r.p} className="flex items-center gap-2 leading-4">
            <span className={`w-16 shrink-0 text-right ${k === poc ? "font-semibold text-gold" : "text-blue"}`}>{r.p}</span>
            <span className="relative h-3 flex-1">
              <span className="absolute inset-y-0 left-0 rounded-sm" style={{ width: `${r.pct}%`, background: alpha(inVa ? theme.gold : theme.blue, k === poc ? 0.9 : 0.45) }} />
            </span>
            <span className="w-20 shrink-0 text-gold">{fmtVol(r.v)} {tag}</span>
          </div>
        );
      })}
    </div>
  );
}
