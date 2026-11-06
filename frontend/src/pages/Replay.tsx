import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import ReplayChart, { type ReplayData } from "../components/ReplayChart";

interface Tr { id: number; symbol: string; direction: string; opened_at: string; pnl: string | null; net_r: string | null; exit_reason: string | null }
interface Full extends ReplayData {
  trade: ReplayData["trade"] & { id: number; symbol: string; qty: number; pnl: string | null; net_r: string | null; guard_on: boolean };
  gates: { gate: string; passed: boolean; code: string | null; detail: string | null }[];
  score: { total: string | null; items: Record<string, string> };
  signal: { id: number; profile: string; model_key: string } | null;
}

const pnl = (v: string | null) => (v == null ? "" : `${Number(v) >= 0 ? "▲ +" : "▼ −"}$${Math.abs(Number(v)).toFixed(2)}`);

export default function Replay() {
  usePageTitle("Trade Replay");
  const [params, setParams] = useSearchParams();
  const list = useQuery({ queryKey: ["trades"], queryFn: () => api<{ trades: Tr[] }>("/api/trades") });
  const tid = params.get("trade") ?? (list.data?.trades[0]?.id != null ? String(list.data.trades[0].id) : null);
  const q = useQuery({ queryKey: ["replay", tid], queryFn: () => api<Full>(`/api/trades/${tid}/replay`), enabled: tid != null });
  const d = q.data;
  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Trade Replay</h1>
      <section className="rounded-xl border border-border bg-card p-4">
        <label className="flex flex-col text-sm">Trade
          <select aria-label="Trade" value={tid ?? ""} onChange={(e) => setParams({ trade: e.target.value })}>
            {(list.data?.trades ?? []).map((t) => (
              <option key={t.id} value={t.id}>#{t.id} · {new Date(t.opened_at).toLocaleString()} · {t.symbol} {t.direction} {pnl(t.pnl)} {t.exit_reason ?? ""}</option>
            ))}
          </select>
        </label>
        {list.data && list.data.trades.length === 0 && <p className="mt-2 text-sm">No trades yet.</p>}
      </section>
      {d && (
        <>
          <section className="rounded-xl border border-border bg-card p-4">
            <h2 className="font-semibold text-gold">#{d.trade.id} {d.trade.symbol} {d.trade.direction} ×{d.trade.qty} <span className="text-sm font-normal">{d.signal ? `${d.signal.profile} · ` : "manual · "}{d.trade.guard_on ? "guard ON" : "guard OFF"}</span></h2>
            <p className="text-sm">{d.trade.entry} → {d.trade.exit ?? "open"} {d.trade.exit_reason ? `(${d.trade.exit_reason})` : ""} · <b className="text-gold">{pnl(d.trade.pnl)}</b> {d.trade.net_r ? `· ${d.trade.net_r}R net` : ""}</p>
            <div className="mt-3"><ReplayChart data={d} /></div>
          </section>
          <div className="grid gap-4 lg:grid-cols-2">
            <section className="rounded-xl border border-border bg-card p-4">
              <h2 className="font-semibold text-gold">Gates</h2>
              {d.gates.length === 0 ? <p className="text-sm">No gate record (manual trade).</p> : (
                <table className="mt-2 w-full text-sm"><tbody>
                  {d.gates.map((g) => (
                    <tr key={g.gate} className="border-t border-border"><td className="py-1 font-semibold">{g.gate}</td>
                      <td><span aria-label={g.passed ? "passed" : "failed"} className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: g.passed ? "#22C55E" : "#EF4444" }} />{g.code}</td><td className="opacity-75">{g.detail ?? ""}</td></tr>
                  ))}
                </tbody></table>
              )}
            </section>
            <section className="rounded-xl border border-border bg-card p-4">
              <h2 className="font-semibold text-gold">Score {d.score.total ?? "—"}</h2>
              <table className="mt-2 w-full text-sm"><tbody>
                {Object.entries(d.score.items).map(([k, v]) => <tr key={k} className="border-t border-border"><td className="py-1">{k.replace(/_/g, " ")}</td><td className="text-gold">{v}</td></tr>)}
              </tbody></table>
              {d.fractal && <p className="mt-2 text-xs opacity-75">Model: C1 {d.fractal.c1_low}–{d.fractal.c1_high}{d.fractal.cisd_level ? ` · CISD ${d.fractal.cisd_level}` : ""}{d.fractal.t2 ? ` · T2 ${d.fractal.t2}` : ""}</p>}
            </section>
          </div>
        </>
      )}
    </div>
  );
}
