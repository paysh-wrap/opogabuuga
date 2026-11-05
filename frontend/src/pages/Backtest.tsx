import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { usePageTitle } from "../components/usePageTitle";
import { api, ApiError } from "../lib/api";

interface Run {
  id: number; status: string; error: string | null;
  params: { symbol: string; stage: string; bias: string; one_to_one: boolean; scalp?: boolean; eval_mode: boolean };
  metrics: {
    stats?: { trades: number; win_rate: string | null; net: string; avg_r: string | null; profit_factor: string | null; max_drawdown: string; best_day_share: string | null; days: number };
    monte_carlo_eval?: { pass_rate: string; fail_rate: string; median_trades_to_pass: number | null };
    breakdown?: Record<string, Record<string, { trades: number; win_rate: string; pnl: string }>>;
    suggestions?: string[];
    consistency_ok?: boolean; sessions?: number; assumptions?: string[]; skips?: Record<string, number>;
  };
}
const pct = (v?: string | null) => (v == null ? "—" : `${(Number(v) * 100).toFixed(1)}%`);
const btn = "rounded-md border px-3 py-1.5 text-sm font-semibold disabled:opacity-50";

export default function Backtest() {
  usePageTitle("Backtest");
  const qc = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [opt, setOpt] = useState({ symbol: "MGC", stage: "EVAL", bias: "recorded", one_to_one: false, scalp: false, eval_mode: false });
  const [err, setErr] = useState("");
  const runs = useQuery({ queryKey: ["backtests"], queryFn: () => api<{ runs: Run[] }>("/api/backtest"), refetchInterval: 3000 });
  const start = useMutation({
    mutationFn: async () => {
      const q = new URLSearchParams({ symbol: opt.symbol, stage: opt.stage, bias: opt.bias, one_to_one: String(opt.one_to_one), scalp: String(opt.scalp), eval_mode: String(opt.eval_mode) });
      return api(`/api/backtest?${q}`, { method: "POST", body: await file!.text(), headers: { "content-type": "text/csv" } });
    },
    onMutate: () => setErr(""),
    onSuccess: () => void qc.invalidateQueries({ queryKey: ["backtests"] }),
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Upload failed"),
  });

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Backtest</h1>
      <p className="text-sm">Replays 1-minute history (Gold or Nasdaq) through the <b>same code</b> as live trading (your two indicators → gates → risk → simulated fills with fees and slippage), then runs a Monte Carlo of passing the eval.
        Get data from Databento (Connections page): dataset GLBX.MDP3, schema ohlcv-1m, CSV.</p>
      {err && <p role="alert" className="rounded-lg border border-gold p-3 text-sm text-goldLight">⚠ {err}</p>}
      <section className="flex flex-wrap items-end gap-3 rounded-xl border border-border bg-card p-4 text-sm">
        <label className="flex flex-col">1-minute CSV<input aria-label="CSV file" type="file" accept=".csv,text/csv" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label>
        <label className="flex flex-col">Market<select aria-label="Market" value={opt.symbol} onChange={(e) => setOpt({ ...opt, symbol: e.target.value })}>
          <option value="MGC">Gold (MGC)</option><option value="MNQ">Nasdaq (MNQ)</option></select></label>
        <label className="flex flex-col">Stage<select value={opt.stage} onChange={(e) => setOpt({ ...opt, stage: e.target.value })}><option>EVAL</option><option>FUNDED</option><option>LIVE</option></select></label>
        <label className="flex flex-col">Bias<select value={opt.bias} onChange={(e) => setOpt({ ...opt, bias: e.target.value })}>
          <option value="recorded">Recorded TradingAgents only</option><option>NEUTRAL</option><option>LONG_ONLY</option><option>SHORT_ONLY</option></select></label>
        <label className="flex items-center gap-1"><input type="checkbox" checked={opt.one_to_one} onChange={(e) => setOpt({ ...opt, one_to_one: e.target.checked })} />1:1 mode</label>
        <label className="flex items-center gap-1"><input type="checkbox" checked={opt.scalp} onChange={(e) => setOpt({ ...opt, scalp: e.target.checked })} />Scalp mode</label>
        <label className="flex items-center gap-1"><input type="checkbox" checked={opt.eval_mode} onChange={(e) => setOpt({ ...opt, eval_mode: e.target.checked })} />Evaluation Mode</label>
        <button className={`${btn} border-gold text-gold`} disabled={!file || start.isPending} onClick={() => start.mutate()}>{start.isPending ? "Uploading…" : "Run backtest"}</button>
      </section>

      {runs.data?.runs.map((r) => {
        const s = r.metrics.stats, mc = r.metrics.monte_carlo_eval;
        return (
          <section key={r.id} data-testid={`bt-${r.id}`} className="rounded-xl border border-border bg-card p-4 text-sm">
            <h2 className="font-semibold text-gold">#{r.id} · {r.params.symbol} · {r.params.stage} · bias {r.params.bias}{r.params.one_to_one ? " · 1:1" : ""}{r.params.scalp ? " · scalp" : ""}{r.params.eval_mode ? " · Eval Mode" : ""} — {r.status}</h2>
            {r.error && <p className="text-goldLight">⚠ {r.error}</p>}
            {s && (
              <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
                <div>Trades <b className="text-gold">{s.trades}</b> over {r.metrics.sessions} sessions</div>
                <div>Win rate <b className="text-gold">{pct(s.win_rate)}</b></div>
                <div>Net <b className="text-gold">${Number(s.net).toFixed(2)}</b></div>
                <div>Avg <b className="text-gold">{s.avg_r ?? "—"}R</b> · PF {s.profit_factor ?? "—"}</div>
                <div>Max drawdown ${Number(s.max_drawdown).toFixed(2)}</div>
                <div>Best day share {pct(s.best_day_share)} {r.metrics.consistency_ok ? "✓ consistency" : "⚠ over 40%"}</div>
                {mc && <div className="col-span-2">Monte Carlo eval: pass <b className="text-gold">{pct(mc.pass_rate)}</b> · fail {pct(mc.fail_rate)} · median {mc.median_trades_to_pass ?? "—"} days</div>}
              </div>
            )}
            {r.metrics.skips && Object.keys(r.metrics.skips).length > 0 && (
              <p className="mt-1 opacity-80">Top skips: {Object.entries(r.metrics.skips).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([k, v]) => `${k} ${v}`).join(" · ")}</p>
            )}
            {r.metrics.suggestions && r.metrics.suggestions.length > 0 && (
              <div className="mt-2 rounded-lg border border-gold p-2 text-xs"><b className="text-gold">Lab suggestions (not applied — your call):</b>
                {r.metrics.suggestions.map((s) => <p key={s}>• {s}</p>)}</div>
            )}
            {r.metrics.breakdown && (
              <details className="mt-2"><summary className="cursor-pointer text-gold">Where the edge is (hour ET, weekday, direction, profile, exit)</summary>
                <div className="mt-1 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                  {Object.entries(r.metrics.breakdown).map(([dim, rows]) => (
                    <table key={dim} className="text-xs"><caption className="text-left font-semibold">{dim}</caption><tbody>
                      {Object.entries(rows).sort((x, y) => x[0].localeCompare(y[0])).map(([k, v]) => (
                        <tr key={k}><td className="pr-2">{k}</td><td className="pr-2">{v.trades}</td><td className="pr-2">{(Number(v.win_rate) * 100).toFixed(0)}%</td>
                          <td className="text-gold">{Number(v.pnl) >= 0 ? "▲" : "▼"} ${Math.abs(Number(v.pnl)).toFixed(0)}</td></tr>
                      ))}
                    </tbody></table>
                  ))}
                </div>
              </details>
            )}
            {r.metrics.assumptions?.map((a) => <p key={a} className="text-xs text-goldLight">Assumption: {a}</p>)}
          </section>
        );
      })}
    </div>
  );
}
