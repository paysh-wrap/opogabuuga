import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { badge } from "../lib/theme";

// D55: strategy on/off buttons with the TESTED results next to each (static research facts from the server, not live
// data). Each click saves a new versioned My Settings entry (rollback on the Risk page).
export interface Strat {
  key: string; name: string; source: string; verified: boolean; status: string;
  win_pct: number; profit_factor: number; usd_per_trade: number; trades_per_week: number; held_out_trades: number;
  pro25k_pass_pct: number | null; pro25k_bust_pct: number | null; period: string; note: string;
  enabled: boolean; setting: string;
}
export interface Ledger {
  proxy: string; symbol: string; state: string; badge: string; required_accuracy: number; min_calls: number;
  stats: { n: number; hit_rate: number; brier: number; wilson_lb: number };
}
export interface StrategiesResp {
  strategies: Strat[];
  noise_warmup: { sessions: number; needed: number; ready: boolean };
  ai_ledger: Ledger[];
  markets: Record<string, boolean>;
}

const pct = (x: number | null) => (x == null ? "—" : `${x.toFixed(1)}%`);
const card = "rounded-xl border border-border bg-card p-4";

export default function StrategyButtons() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["strategies"], queryFn: () => api<StrategiesResp>("/api/strategies"), refetchInterval: 30000 });
  const toggle = useMutation({
    mutationFn: (s: Strat) =>
      api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { [s.setting]: !s.enabled }, note: `Strategy button: ${s.key} ${s.enabled ? "off" : "on"}` }) }),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  const d = q.data;
  if (!d) return <p role="status">Loading strategies…</p>;
  const w = d.noise_warmup;
  return (
    <section className={card} data-testid="strategy-buttons">
      <h2 className="font-semibold text-gold">Strategies — tap to turn on/off</h2>
      <p className="text-xs text-blue">Results are from the session 9 study on real MNQ data (picked on 2019–2023, judged unchanged on 2024–2026, 1 micro, costs included). Pro 25K = share of simulated evaluations that passed / busted. Past results do not guarantee future results.</p>
      <div className="mt-3 grid gap-3 lg:grid-cols-3">
        {d.strategies.map((s) => (
          <div key={s.key} className="rounded-lg border border-border p-3" data-testid={`strategy-${s.key}`}>
            <button
              type="button"
              aria-pressed={s.enabled}
              disabled={toggle.isPending}
              onClick={() => toggle.mutate(s)}
              className={`w-full rounded-md border px-3 py-2 text-left font-semibold ${s.enabled ? "border-gold text-gold" : "border-blue text-blue"} disabled:opacity-50`}
            >
              {s.enabled ? "ON" : "OFF"} · {s.name}
            </button>
            <p className="mt-2 text-xs"><span aria-hidden style={{ color: s.verified ? badge.ok : badge.bad }}>●</span> <b className="text-gold">{s.status}</b> <span className="text-blue">{s.period}</span></p>
            <dl className="mt-2 grid grid-cols-2 gap-x-2 text-sm">
              <dt>Win rate</dt><dd className="text-gold" data-testid={`win-${s.key}`}>{pct(s.win_pct)}</dd>
              <dt>Pro 25K pass</dt><dd className="text-gold" data-testid={`pass-${s.key}`}>{pct(s.pro25k_pass_pct)}</dd>
              <dt>Pro 25K bust</dt><dd className="text-gold">{pct(s.pro25k_bust_pct)}</dd>
              <dt>Profit factor</dt><dd className="text-gold">{s.profit_factor.toFixed(2)}</dd>
              <dt>Per trade (1 micro)</dt><dd className="text-gold">{s.usd_per_trade >= 0 ? "▲ +" : "▼ "}${Math.abs(s.usd_per_trade).toFixed(2)}</dd>
              <dt>Trades / week</dt><dd className="text-gold">{s.trades_per_week.toFixed(1)}</dd>
            </dl>
            <p className="mt-2 text-xs text-blue">{s.note}</p>
            {s.key === "noise" && !w.ready && (
              <p className="mt-1 text-xs text-gold" data-testid="noise-warmup">Warm-up: {w.sessions}/{w.needed} sessions of TradingView 1-minute MNQ bars stored — NOISE starts trading after that.</p>
            )}
          </div>
        ))}
      </div>
      <div className="mt-3 text-sm" data-testid="ai-ledger">
        <b className="text-gold">AI daily call (TradingAgents + Vibe-Trading) — scored every session:</b>
        {d.ai_ledger.map((l) => (
          <p key={l.proxy} className="text-blue">
            {l.symbol} ← {l.proxy}: <b className="text-gold">{l.badge}</b> · {l.stats.n} scored calls
            {l.stats.n > 0 && ` · hit rate ${(l.stats.hit_rate * 100).toFixed(0)}% · Brier ${l.stats.brier.toFixed(2)}`} · may block only after {l.min_calls}+ calls proven ≥ {(l.required_accuracy * 100).toFixed(0)}%
          </p>
        ))}
      </div>
      {d.markets.MGC === false && <p className="mt-2 text-xs text-blue">MGC (gold) is off — every gold strategy failed the 2019–2026 test.</p>}
    </section>
  );
}
