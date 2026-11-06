import { useState } from "react";

export interface RunParams { symbol: string; stage: string; bias: string; one_to_one: boolean; scalp?: boolean; low_risk?: boolean; eval_mode: boolean; drawdown_type?: string | null }
export interface Week { week: number; profit: string; balance: string; kind: string | null; amount: string; net: string; reason: string }
export interface RunMetrics {
  stats?: { trades: number; win_rate: string | null; net: string; avg_r: string | null; profit_factor: string | null; max_drawdown: string; best_day_share: string | null; days: number };
  monte_carlo_eval?: { pass_rate: string; fail_rate: string; median_trades_to_pass: number | null };
  payout_sim?: { weeks: Week[]; total_gross: string; total_net: string; breached: boolean };
  income_mc?: { runs: number; sessions: number; floor: string; target: string; by_accounts: Record<string, { median_net: string; p_floor: string; p_target: string; p_breach: string }> };
  skips?: Record<string, number>;
}
export interface CmpRun { id: number; status: string; params: RunParams; metrics: RunMetrics }

const pct = (v?: string | null) => (v == null ? "—" : `${(Number(v) * 100).toFixed(1)}%`);
const usd = (v?: string | null) => (v == null ? "—" : `$${Number(v).toLocaleString(undefined, { maximumFractionDigits: 0 })}`);
export const guardLabel = (p: RunParams) => (p.drawdown_type === "intraday" ? "guard ON (intraday)" : p.drawdown_type === "eod" ? "guard OFF (EOD)" : "guard auto");
export function runLabel(r: CmpRun) {
  const p = r.params;
  return `#${r.id} ${p.symbol} ${p.stage} · bias ${p.bias} · ${guardLabel(p)} · Eval Mode ${p.eval_mode ? "ON" : "OFF"}`;
}

/** Which single toggle separates two runs (guard / Eval Mode / bias ablation), or null if several differ. */
export function compareKind(a: RunParams, b: RunParams): string | null {
  const keys: (keyof RunParams)[] = ["symbol", "stage", "bias", "one_to_one", "scalp", "low_risk", "eval_mode", "drawdown_type"];
  const diff = keys.filter((k) => (a[k] ?? null) !== (b[k] ?? null));
  if (diff.length !== 1) return null;
  return { drawdown_type: "Guard ON vs OFF", eval_mode: "Eval Mode ON vs OFF", bias: "Bias ablation" }[diff[0] as string] ?? `Differs in ${String(diff[0])}`;
}

const ROWS: [string, (m: RunMetrics) => string][] = [
  ["Trades", (m) => String(m.stats?.trades ?? "—")],
  ["Win rate", (m) => pct(m.stats?.win_rate)],
  ["Net", (m) => usd(m.stats?.net)],
  ["Avg R", (m) => m.stats?.avg_r ?? "—"],
  ["Profit factor", (m) => m.stats?.profit_factor ?? "—"],
  ["Max drawdown", (m) => usd(m.stats?.max_drawdown)],
  ["P(pass eval)", (m) => pct(m.monte_carlo_eval?.pass_rate)],
  ["Weekly payouts (net)", (m) => usd(m.payout_sim?.total_net)],
  ["P(≥ floor) 1 acct", (m) => pct(m.income_mc?.by_accounts["1"]?.p_floor)],
  ["P(≥ target) 5 accts", (m) => pct(m.income_mc?.by_accounts["5"]?.p_target)],
];

export function ComparePanel({ runs }: { runs: CmpRun[] }) {
  const done = runs.filter((r) => r.status === "done" && r.metrics.stats);
  const [a, setA] = useState<number | null>(null);
  const [b, setB] = useState<number | null>(null);
  const ra = done.find((r) => r.id === (a ?? done[1]?.id)), rb = done.find((r) => r.id === (b ?? done[0]?.id));
  return (
    <section className="rounded-xl border border-border bg-card p-4 text-sm" data-testid="bt-compare">
      <h2 className="font-semibold text-gold">Compare runs (guard ON/OFF · Eval Mode ON/OFF · bias ablation)</h2>
      {done.length < 2 ? <p className="text-xs">Needs two finished runs. Use “Run comparison pair” to start both sides from one CSV.</p> : (
        <>
          <div className="mt-2 flex flex-wrap gap-2">
            <select aria-label="Compare run A" value={ra?.id} onChange={(e) => setA(Number(e.target.value))}>{done.map((r) => <option key={r.id} value={r.id}>{runLabel(r)}</option>)}</select>
            <select aria-label="Compare run B" value={rb?.id} onChange={(e) => setB(Number(e.target.value))}>{done.map((r) => <option key={r.id} value={r.id}>{runLabel(r)}</option>)}</select>
          </div>
          {ra && rb && (
            <>
              <p className="mt-2 text-xs" data-testid="compare-kind">{compareKind(ra.params, rb.params) ?? "⚠ These runs differ in more than one setting — not a clean comparison."}</p>
              <div className="overflow-x-auto"><table className="mt-1 w-full text-xs"><thead><tr><th className="text-left">Metric</th><th className="text-left">#{ra.id}</th><th className="text-left">#{rb.id}</th></tr></thead>
                <tbody>{ROWS.map(([k, f]) => <tr key={k} className="border-t border-border"><td>{k}</td><td className="text-gold">{f(ra.metrics)}</td><td className="text-gold">{f(rb.metrics)}</td></tr>)}</tbody></table></div>
            </>
          )}
        </>
      )}
    </section>
  );
}

export function PayoutAndIncome({ m }: { m: RunMetrics }) {
  const ps = m.payout_sim, inc = m.income_mc;
  if (!ps && !inc) return <p className="mt-1 text-xs opacity-80">Payout simulation / income Monte Carlo: re-run this backtest to compute them.</p>;
  return (
    <details className="mt-2" data-testid="bt-payouts">
      <summary className="cursor-pointer text-gold">Weekly payout simulation & income Monte Carlo</summary>
      {ps && (
        <div className="mt-1 text-xs">
          <p>FUNDED account replayed with the live payout rule: gross {usd(ps.total_gross)} · net after split <b className="text-gold">{usd(ps.total_net)}</b>{ps.breached ? " · ⚠ MLL breached (account lost)" : ""}</p>
          <div className="max-h-48 overflow-auto"><table className="w-full"><tbody>
            {ps.weeks.map((w) => <tr key={w.week}><td>wk {w.week}</td><td>{Number(w.profit) >= 0 ? "▲ +" : "▼ −"}${Math.abs(Number(w.profit)).toFixed(0)}</td><td>bal {usd(w.balance)}</td><td className="text-gold">{w.kind ? `${w.kind} ${usd(w.amount)}` : "—"}</td><td className="opacity-75">{w.kind ? "" : w.reason.replace(/_/g, " ").toLowerCase()}</td></tr>)}
          </tbody></table></div>
        </div>
      )}
      {inc && Object.keys(inc.by_accounts).length > 0 && (
        <div className="mt-2 overflow-x-auto text-xs">
          <p>12-month Monte Carlo ({inc.runs.toLocaleString()} block-bootstrap paths, {inc.sessions} sessions, accounts fully correlated):</p>
          <table className="w-full"><thead><tr><th className="text-left">Accounts</th><th className="text-left">Median net</th><th className="text-left">P(≥{usd(inc.floor)})</th><th className="text-left">P(≥{usd(inc.target)})</th><th className="text-left">P(breach)</th></tr></thead>
            <tbody>{Object.entries(inc.by_accounts).map(([n, v]) => <tr key={n} data-testid={`mc-n-${n}`}><td>{n}</td><td className="text-gold">{usd(v.median_net)}</td><td className="text-gold">{pct(v.p_floor)}</td><td className="text-gold">{pct(v.p_target)}</td><td>{pct(v.p_breach)}</td></tr>)}</tbody></table>
        </div>
      )}
    </details>
  );
}
