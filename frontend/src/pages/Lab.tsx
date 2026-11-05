import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";

interface Sess { session: string; trades: number; win_rate: number; net: string; avg_r: string | null; cum_win_rate: number; cum_net: string }
interface Bt { id: number; params: { symbol: string; stage: string; bias: string; one_to_one?: boolean; scalp?: boolean }; trades: number | null; win_rate: string | null; profit_factor: string | null; net: string | null; mc_pass: string | null }
interface Prop { id: number; text: string; status: string; at: string }
interface Lab { sessions: Sess[]; backtests: Bt[]; suggestions: string[]; proposals: Prop[] }

const card = "rounded-xl border border-border bg-card p-4";
const btn = "rounded-md border px-2 py-1 text-xs font-semibold";
const pct = (v: number | string | null | undefined) => (v == null ? "—" : `${(Number(v) * 100).toFixed(1)}%`);

/** Tiny line chart: gold line, blue grid. values in [min,max] auto-scaled. */
function Spark({ values, label, fmt }: { values: number[]; label: string; fmt: (n: number) => string }) {
  if (values.length < 2) return <p className="text-xs opacity-75">{label}: needs 2+ points</p>;
  const w = 320, h = 80, lo = Math.min(...values), hi = Math.max(...values), span = hi - lo || 1;
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * w},${h - ((v - lo) / span) * (h - 8) - 4}`).join(" ");
  const first = values[0] ?? 0, last = values[values.length - 1] ?? 0;
  const up = last >= first;
  return (
    <figure className="text-xs">
      <figcaption>{label}: <b className="text-gold">{fmt(last)}</b> {up ? "▲" : "▼"} from {fmt(first)}</figcaption>
      <svg viewBox={`0 0 ${w} ${h}`} className="mt-1 h-20 w-full max-w-sm" role="img" aria-label={label}>
        <line x1="0" y1={h - 4} x2={w} y2={h - 4} stroke="#1E3A8A" strokeWidth="1" />
        <polyline points={pts} fill="none" stroke="#D4AF37" strokeWidth="2" />
      </svg>
    </figure>
  );
}

export default function LabPage() {
  usePageTitle("Lab");
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["lab"], queryFn: () => api<Lab>("/api/lab"), refetchInterval: 30000 });
  const done = () => void qc.invalidateQueries({ queryKey: ["lab"] });
  const propose = useMutation({ mutationFn: (text: string) => api("/api/lab/proposals", { method: "POST", body: JSON.stringify({ text }) }), onSuccess: done });
  const decide = useMutation({ mutationFn: (x: { id: number; status: string }) => api(`/api/lab/proposals/${x.id}`, { method: "PUT", body: JSON.stringify({ status: x.status }) }), onSuccess: done });
  const d = q.data;
  if (!d) return <p role="status">Loading…</p>;
  const s = d.sessions;
  const pending = new Set(d.proposals.map((p) => p.text));
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Self-Learning Lab</h1>
      <p className="text-sm">Every session the app measures itself, backtests and suggests improvements. Nothing changes your rules until you approve it, and firm rules / safety pillars can never be touched.</p>

      <section className={card}>
        <h2 className="font-semibold text-gold">Progress by session</h2>
        {s.length === 0 ? <p className="text-sm">No closed trades yet — progress appears after the first session.</p> : (
          <>
            <div className="mt-2 grid gap-3 sm:grid-cols-2">
              <Spark label="Win rate (all sessions so far)" values={s.map((x) => x.cum_win_rate)} fmt={(n) => `${(n * 100).toFixed(1)}%`} />
              <Spark label="Total net P&L" values={s.map((x) => Number(x.cum_net))} fmt={(n) => `$${n.toFixed(0)}`} />
            </div>
            <table className="mt-2 w-full text-xs"><tbody>
              {s.slice().reverse().slice(0, 15).map((x) => (
                <tr key={x.session} className="border-t border-border"><td className="py-1">{x.session}</td><td>{x.trades} trades</td><td>{pct(x.win_rate)}</td><td>{x.avg_r ?? "—"}R</td>
                  <td className="text-gold">{Number(x.net) >= 0 ? "▲ +" : "▼ −"}${Math.abs(Number(x.net)).toFixed(0)}</td></tr>
              ))}
            </tbody></table>
          </>
        )}
      </section>

      <section className={card}>
        <h2 className="font-semibold text-gold">Backtest history</h2>
        {d.backtests.length === 0 ? <p className="text-sm">No backtests yet — run one on the Backtest page.</p> : (
          <>
            <Spark label="Backtest win rate" values={d.backtests.map((b) => Number(b.win_rate ?? 0))} fmt={(n) => `${(n * 100).toFixed(1)}%`} />
            <table className="mt-2 w-full text-xs"><tbody>
              {d.backtests.slice().reverse().map((b) => (
                <tr key={b.id} className="border-t border-border"><td className="py-1">#{b.id}</td><td>{b.params.symbol} {b.params.stage}{b.params.scalp ? " scalp" : ""}{b.params.one_to_one ? " 1:1" : ""}</td>
                  <td>{b.trades ?? 0} trades</td><td>{pct(b.win_rate)}</td><td>PF {b.profit_factor ?? "—"}</td><td>eval pass {pct(b.mc_pass)}</td></tr>
              ))}
            </tbody></table>
          </>
        )}
      </section>

      <section className={card}>
        <h2 className="font-semibold text-gold">Suggestions & proposals</h2>
        {d.suggestions.length === 0 && d.proposals.length === 0 && <p className="text-sm">No suggestions yet.</p>}
        {d.suggestions.filter((t) => !pending.has(t)).map((t) => (
          <p key={t} className="mt-1 text-sm">• {t} <button className={`${btn} ml-2 border-blue text-blue`} onClick={() => propose.mutate(t)}>Propose</button></p>
        ))}
        {d.proposals.map((p) => (
          <p key={p.id} data-testid={`proposal-${p.id}`} className="mt-1 text-sm">#{p.id} {p.text} — <b className={p.status === "approved" ? "text-gold" : ""}>{p.status}</b>
            {p.status === "pending" && (<>
              <button className={`${btn} ml-2 border-gold text-gold`} onClick={() => decide.mutate({ id: p.id, status: "approved" })}>Approve</button>
              <button className={`${btn} ml-1 border-border text-blue`} onClick={() => decide.mutate({ id: p.id, status: "rejected" })}>Reject</button>
            </>)}
          </p>
        ))}
        <p className="mt-2 text-xs opacity-75">Approved proposals are applied only through the guarded process: shadow-tested ≥ 10 sessions, at 18:00, max one change per 14 days, auto-rollback if worse.</p>
      </section>
    </div>
  );
}
