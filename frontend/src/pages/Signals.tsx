import { Fragment, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";
import { etDateTime } from "../lib/time";

interface Gate { gate: string; passed: boolean; code?: string; hard?: boolean; detail?: unknown }
interface AcctResult { account_id: number; account: string; qty: number; risk_profile: string; guard_on: boolean; gross_r: string | null; net_r: string | null; pnl: string | null; exit_reason: string | null; open: boolean }
interface Plan { mode: string; entry: string; stop: string; take_profit: string; rr: string }
export interface Sig {
  id: number; symbol: string; profile: string; direction: string; status: string; skip_reason: string | null;
  score: string | null; c1_range_atr: string | null; confirmed_at: string; gates: Gate[]; plans: Plan[]; results?: AcctResult[];
}
const usd = (v: string | null) => {
  if (v == null) return "–";
  const n = Number(v);
  return (n >= 0 ? "▲ +$" : "▼ −$") + Math.abs(n).toFixed(2);
};
const GATES = ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8"];

function GateCell({ g }: { g?: Gate }) {
  if (!g) return <td className="text-center text-blueLight" title="not evaluated">–</td>;
  return (
    <td className="text-center" title={g.code ?? ""}>
      <span aria-label={g.passed ? "passed" : "failed"} className="inline-block rounded px-1 text-xs"
        style={{ background: g.passed ? "#22C55E" : "#EF4444", color: "#0A1020" }}>{g.passed ? "✓" : "✗"}</span>
    </td>
  );
}

export default function Signals() {
  usePageTitle("Signals");
  const q = useQuery({ queryKey: ["signals"], queryFn: () => api<{ signals: Sig[] }>("/api/signals?limit=100"), refetchInterval: 10_000 });
  const [open, setOpen] = useState<number | null>(null);
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gold">Signals</h1>
      <p className="text-sm">Every confirmed model and why it was taken or skipped. Gates G1–G8 are evaluated at the entry-bar close.</p>
      {q.isLoading && <p role="status">Loading…</p>}
      {q.error && <p role="alert" className="text-goldLight">⚠ Could not load signals: {String(q.error.message)}</p>}
      {q.data?.signals.length === 0 && <p className="rounded-xl border border-border bg-card p-4 text-sm">No signals yet.</p>}
      {!!q.data?.signals.length && (
        <div className="overflow-x-auto rounded-xl border border-border bg-card p-3">
          <table className="w-full text-sm">
            <thead className="text-left text-gold">
              <tr><th>Time</th><th>Symbol</th><th>Dir</th><th>Status</th><th>Score</th><th>C1/ATR</th>
                {GATES.map((g) => <th key={g} className="text-center">{g}</th>)}<th>Reason</th><th /></tr>
            </thead>
            <tbody>
              {q.data.signals.map((s) => (
                <Fragment key={s.id}>
                  <tr data-testid={`signal-${s.id}`} className="border-t border-border">
                    <td className="whitespace-nowrap py-1">{etDateTime(s.confirmed_at)}</td>
                    <td>{s.symbol} <span className="text-xs text-blueLight">{s.profile}</span></td>
                    <td>{s.direction === "LONG" ? "▲ LONG" : s.direction === "SHORT" ? "▼ SHORT" : s.direction}</td>
                    <td>{s.status}</td>
                    <td className="font-semibold text-gold">{s.score ?? "–"}</td>
                    <td>{s.c1_range_atr ?? "–"}</td>
                    {GATES.map((g) => <GateCell key={g} g={s.gates.find((x) => x.gate === g)} />)}
                    <td>{s.skip_reason ?? ""}</td>
                    <td><button className="text-blue hover:text-blueLight" aria-expanded={open === s.id}
                      onClick={() => setOpen(open === s.id ? null : s.id)}>{open === s.id ? "Hide" : "Plan"}</button></td>
                  </tr>
                  {open === s.id && (
                    <tr data-testid={`plan-${s.id}`}>
                      <td colSpan={16} className="pb-2 text-xs">
                        {s.plans.length === 0 ? "No trade plan was built." : s.plans.map((p) => (
                          <div key={p.mode}>{p.mode}: entry <b className="text-gold">{p.entry}</b> · stop <b className="text-gold">{p.stop}</b>{" "}
                            · target <b className="text-gold">{p.take_profit}</b> · R:R <b className="text-gold">{p.rr}</b></div>
                        ))}
                        {(s.results ?? []).length > 0 && (
                          <div className="mt-1" data-testid={`results-${s.id}`}>
                            {(s.results ?? []).map((r) => (
                              <div key={r.account_id}>
                                <b className="text-gold">{r.account}</b> · {r.qty} ct · {r.risk_profile} risk · guard {r.guard_on ? "ON" : "OFF"} ·{" "}
                                {r.open ? "open" : <>gross {r.gross_r ?? "–"}R · net <b className="text-gold">{r.net_r ?? "–"}R</b> · {usd(r.pnl)} · {r.exit_reason ?? ""}</>}
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
