import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";

interface Sym { date?: string; last?: number; change?: number; change_pct?: number; series?: number[]; error?: string }
interface Feed { status: string; error: string | null; age_s: number | null; source: string; symbols: Record<string, Sym> }

const NAMES: Record<string, string> = { MGC: "Micro Gold", MNQ: "Micro Nasdaq" };

function Spark({ v }: { v: number[] }) {
  if (v.length < 2) return null;
  const w = 160, h = 40, lo = Math.min(...v), hi = Math.max(...v), span = hi - lo || 1;
  const pts = v.map((y, i) => `${(i / (v.length - 1)) * w},${h - 3 - ((y - lo) / span) * (h - 6)}`).join(" ");
  const up = v[v.length - 1]! >= v[0]!;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-10 w-40" aria-hidden>
      <defs><linearGradient id="sg" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#D4AF37" stopOpacity=".35" /><stop offset="1" stopColor="#D4AF37" stopOpacity="0" /></linearGradient></defs>
      <polygon points={`0,${h} ${pts} ${w},${h}`} fill="url(#sg)" />
      <polyline points={pts} fill="none" stroke={up ? "#D4AF37" : "#3B82F6"} strokeWidth="1.8" strokeLinejoin="round" />
    </svg>
  );
}

export default function MarketPanel() {
  const q = useQuery({ queryKey: ["openbb"], queryFn: () => api<Feed>("/api/market/openbb"), refetchInterval: 30000 });
  const d = q.data;
  return (
    <section className="rounded-xl border border-border bg-card p-4" data-testid="market-panel">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="font-semibold text-gold">Markets · OpenBB</h2>
        <span className="text-[11px] opacity-70">{d ? `${d.source}${d.age_s != null ? ` · ${Math.round(d.age_s / 60)} min ago` : ""}` : ""}</span>
      </div>
      {!d || d.status === "LOADING" ? <p className="mt-2 text-sm" role="status">Loading OpenBB… (first start can take about a minute)</p>
        : d.status === "NOT_INSTALLED" ? <p className="mt-2 text-sm text-goldLight">⚠ OpenBB needs uv/uvx on the server.</p>
        : d.status === "ERROR" ? <p className="mt-2 text-sm text-goldLight">⚠ OpenBB failed: {d.error}</p>
        : (
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            {Object.entries(d.symbols).map(([k, s]) => (
              <div key={k} className="stat-tile flex items-center justify-between gap-3">
                <div>
                  <div className="text-[11px] uppercase tracking-wider opacity-70">{NAMES[k] ?? k} · {k}</div>
                  {s.error ? <div className="text-goldLight">⚠ {s.error}</div> : (
                    <>
                      <div className="font-serif text-2xl text-gold tabular-nums">{s.last?.toLocaleString()}</div>
                      <div className="text-xs tabular-nums">{(s.change ?? 0) >= 0 ? "▲ +" : "▼ −"}{Math.abs(s.change ?? 0).toLocaleString()} ({Math.abs(s.change_pct ?? 0).toFixed(2)}%) · {s.date}</div>
                    </>
                  )}
                </div>
                <Spark v={s.series ?? []} />
              </div>
            ))}
          </div>
        )}
      {d?.status === "STALE" && <p className="mt-2 text-xs text-goldLight">⚠ Last refresh failed ({d.error}); showing older data.</p>}
      <p className="mt-2 text-[11px] opacity-60">Display only — never used for signals or orders (those come from your TradingView alerts).</p>
    </section>
  );
}
