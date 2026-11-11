import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import { CandleDeltaChart, EstimatedBadge, FootprintGrid, VolumeProfile } from "../components/OrderFlowChart";
import { signed, snapSignals, type OrderFlowData } from "../lib/orderflow";

const ZONE: Record<string, string> = { premium: "PREMIUM (above prior VAH)", discount: "DISCOUNT (below prior VAL)", value: "inside prior value", unknown: "no prior session" };

/** D98 Order Flow chart (display only). Built from the 1-minute bars Paytience already holds — buy/sell per price is
 *  ESTIMATED from OHLCV (badge on every panel); a real tick feed sets source = "tick" later. */
export default function OrderFlow() {
  usePageTitle("Order Flow");
  const [params, setParams] = useSearchParams();
  const symbol = params.get("symbol") ?? "MNQ";
  const session = params.get("session");
  const q = useQuery({
    queryKey: ["orderflow", symbol, session],
    queryFn: () => api<OrderFlowData>(`/api/orderflow?symbol=${encodeURIComponent(symbol)}${session ? `&session=${encodeURIComponent(session)}` : ""}`),
    refetchInterval: 60_000,
  });
  const d = q.data;
  const last = d?.bars[d.bars.length - 1];
  const set = (k: string, v: string) => { const n = new URLSearchParams(params); n.set(k, v); if (k === "symbol") n.delete("session"); setParams(n); };
  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-bold text-gold">Order Flow</h1>
        {d && <EstimatedBadge d={d} />}
      </div>
      <section className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-card p-4 text-sm">
        <label className="flex flex-col">Market
          <select aria-label="Market" value={symbol} onChange={(e) => set("symbol", e.target.value)}>
            {(d?.symbols ?? ["MNQ", "MGC"]).map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="flex flex-col">Session
          <select aria-label="Session" value={d?.session ?? ""} onChange={(e) => set("session", e.target.value)} disabled={!d || d.sessions.length === 0}>
            {(d?.sessions ?? []).slice().reverse().map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <p className="max-w-xl text-xs text-blue">Display only — nothing here places trades. From your recorded 1-minute bars (TradingView heartbeats). {d?.estimated ? `Method: ${d.method}.` : ""}</p>
      </section>
      {q.isLoading && <p role="status">Loading…</p>}
      {q.error && <p role="alert">Cannot load order flow: {String((q.error as Error).message)}</p>}
      {d && d.bars.length === 0 && (
        <section className="rounded-xl border border-border bg-card p-4" data-testid="of-empty">
          <p className="text-sm">No recorded 1-minute bars for {d.symbol} yet. Bars arrive with your TradingView heartbeat alerts; this page never fetches outside data.</p>
        </section>
      )}
      {d && d.bars.length > 0 && last && (
        <>
          <section className="grid gap-3 rounded-xl border border-border bg-card p-4 text-sm sm:grid-cols-2 lg:grid-cols-4" data-testid="of-summary">
            <div><div className="text-xs text-blue">Session {d.session}</div><div className="font-semibold text-gold">{d.bars.length} bars · last {last.c}</div></div>
            <div><div className="text-xs text-blue">Cumulative delta</div><div className="font-semibold text-gold">{signed(last.cvd)}</div></div>
            <div><div className="text-xs text-blue">POC / VAH / VAL</div><div className="font-semibold text-gold">{d.profile?.poc ?? "—"} / {d.profile?.vah ?? "—"} / {d.profile?.val ?? "—"}</div></div>
            <div><div className="text-xs text-blue">vs prior value {d.prior ? `(${d.prior.session}: ${d.prior.val}–${d.prior.vah}, POC ${d.prior.poc})` : ""}</div><div className="font-semibold text-gold" data-testid="of-zone">{ZONE[last.zone]}</div></div>
          </section>
          <section className="rounded-xl border border-border bg-card p-4">
            <div className="mb-2 flex flex-wrap items-center gap-2"><h2 className="font-semibold text-gold">Candles · bar delta · levels</h2><EstimatedBadge d={d} /></div>
            <CandleDeltaChart d={d} />
            <p className="mt-2 text-xs text-blue">Lines: POC/VAH/VAL (this session, gold), pPOC/pVAH/pVAL (prior session, blue), dotted round numbers {d.round_levels.join(" · ")}.</p>
          </section>
          <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
            <section className="min-w-0 rounded-xl border border-border bg-card p-4">
              <div className="mb-2 flex flex-wrap items-center gap-2"><h2 className="font-semibold text-gold">Footprint</h2><EstimatedBadge d={d} /></div>
              <FootprintGrid d={d} />
            </section>
            <section className="min-w-0 rounded-xl border border-border bg-card p-4">
              <div className="mb-2 flex flex-wrap items-center gap-2"><h2 className="font-semibold text-gold">Session volume profile</h2><EstimatedBadge d={d} /></div>
              <VolumeProfile d={d} />
            </section>
          </div>
          <section className="rounded-xl border border-border bg-card p-4">
            <h2 className="font-semibold text-gold">Order Flow strategy alerts this session</h2>
            <p className="text-xs text-blue">ORDER_FLOW webhook alerts (pine/Paytience_OrderFlow.pine, D95 — UNVERIFIED, paper only). ABS absorption · EXH exhaustion (delta divergence) · AGG aggression (stacked imbalance) · SWP sweep · POC magnet.</p>
            {d.signals.length === 0 ? <p className="mt-2 text-sm">No order-flow alerts this session.</p> : (
              <ul className="mt-2 text-sm" data-testid="of-signals">
                {snapSignals(d.bars, d.signals).map((s, i) => (
                  <li key={i} className="border-t border-border py-1">{new Date(s.time_ms).toLocaleTimeString()} · {s.direction === "LONG" ? "▲ LONG" : "▼ SHORT"} · <span className="text-gold">{s.label}</span></li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  );
}
