import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { etDateTime } from "../lib/time";
import type { StrategiesResp } from "./StrategyButtons";

// D106: each strategy shows ONLY the gates its own backend code checks (GET /api/strategy-gates), with live
// pass/fail from that strategy's latest decision. Firm/safety checks are shown once as "Lucid rules (always on)".
export type GateStatus = "PASS" | "FAIL" | "NOT_REACHED" | null;
export interface StratGate { id: string; name: string; text: string; codes: string[]; kind: "entry" | "exit"; status?: GateStatus }
export interface LastDecision { status: string; code: string | null; at: string | null; symbol: string; direction: string | null; source: string }
export interface StratGates { key: string; name: string; on: boolean; symbols: string[]; gates: StratGate[]; last: LastDecision | null; lucid_code: string | null }
export interface StrategyGatesResp { strategies: StratGates[]; lucid_rules: StratGate[] }

const card = "rounded-xl border border-border bg-card p-4";
const LABEL: Record<string, string> = { PASS: "✓ pass", FAIL: "✗ fail", NOT_REACHED: "not reached" };

function Badge({ s }: { s: GateStatus | undefined }) {
  if (s == null) return <span className="mr-2 inline-block w-20 rounded border border-border px-1 text-center text-xs text-blueLight">no data</span>;
  // red/green only as small badges (CLAUDE.md §18)
  const bg = s === "PASS" ? "#22C55E" : s === "FAIL" ? "#EF4444" : undefined;
  return (
    <span aria-label={s.toLowerCase()} className={`mr-2 inline-block w-20 rounded px-1 text-center text-xs ${bg ? "" : "border border-border text-blueLight"}`}
      style={bg ? { background: bg, color: "#0A1020" } : undefined}>{LABEL[s]}</span>
  );
}

function AiThreshold({ value }: { value: number }) {
  const qc = useQueryClient();
  const [v, setV] = useState(String(Math.round(value * 100)));
  const [err, setErr] = useState("");
  const save = useMutation({
    mutationFn: () => api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { "strategy.ai_gate_min_accuracy": (Number(v) / 100).toFixed(2) }, note: `AI gate threshold ${v}%` }) }),
    onSuccess: () => setErr(""),
    onError: (e) => setErr(e instanceof Error ? e.message : "Rejected"),
    onSettled: () => { void qc.invalidateQueries({ queryKey: ["strategies"] }); void qc.invalidateQueries({ queryKey: ["strategy-gates"] }); },
  });
  return (
    <span className="ml-24 mt-1 flex items-center gap-2 text-xs" data-testid="ai-threshold">
      Proof threshold (55–95%):
      <input aria-label="AI gate threshold percent" className="w-16 rounded border border-border bg-card px-1" type="number" min={55} max={95} value={v} onChange={(e) => setV(e.target.value)} />
      <button type="button" className="rounded border border-blue px-2 text-blue disabled:opacity-50" disabled={save.isPending} onClick={() => save.mutate()}>Save</button>
      {err && <span role="alert" className="text-gold">{err}</span>}
    </span>
  );
}

function Last({ l }: { l: LastDecision | null }) {
  if (!l) return <p className="text-xs text-blueLight">No decision recorded yet.</p>;
  const dir = l.direction === "LONG" ? "▲ LONG" : l.direction === "SHORT" ? "▼ SHORT" : l.direction ?? "";
  return (
    <p className="text-xs text-blue">
      Last decision{l.at ? ` ${etDateTime(l.at)}` : ""} · {l.symbol} {dir} · <b className="text-gold">{l.status === "PASS" ? "TAKEN" : l.status}</b>
      {l.code && <> · reason <b className="text-gold">{l.code}</b></>}
    </p>
  );
}

function StrategyCard({ s, aiAcc }: { s: StratGates; aiAcc?: number }) {
  const entry = s.gates.filter((g) => g.kind === "entry");
  const exits = s.gates.filter((g) => g.kind === "exit");
  return (
    <section className={`${card} ${s.on ? "" : "opacity-70"}`} data-testid={`sg-${s.key}`}>
      <h3 className="font-semibold text-gold">
        {s.name} <span className="ml-1 rounded border border-blue px-1 text-xs text-blue">{s.on ? "ON" : "OFF"}</span>
        <span className="ml-2 text-xs font-normal text-blue">{s.symbols.join(" · ")}</span>
      </h3>
      <Last l={s.last} />
      {s.lucid_code && <p className="text-xs text-goldLight" data-testid={`sg-${s.key}-lucid`}>⚠ Blocked by a Lucid rule: {s.lucid_code}</p>}
      <ul className="mt-2 space-y-1 text-sm">
        {entry.map((g) => (
          <li key={g.id} data-testid={`sg-${s.key}-${g.id}`}>
            <Badge s={g.status} /><b className="text-gold">{g.name}</b> <span className="text-xs text-blue">{g.text}</span>
            {s.key === "noise" && g.id === "AI_PROVEN" && aiAcc != null && <AiThreshold value={aiAcc} />}
          </li>
        ))}
      </ul>
      {exits.length > 0 && (
        <div className="mt-2 text-xs text-blue">
          <span className="font-semibold text-gold">Exits:</span>{" "}
          {exits.map((g, i) => <span key={g.id} data-testid={`sg-${s.key}-${g.id}`}>{i > 0 && " · "}<b>{g.name}</b> {g.text}</span>)}
        </div>
      )}
    </section>
  );
}

export default function StrategyGates() {
  const q = useQuery({ queryKey: ["strategy-gates"], queryFn: () => api<StrategyGatesResp>("/api/strategy-gates"), refetchInterval: 15000 });
  const strat = useQuery({ queryKey: ["strategies"], queryFn: () => api<StrategiesResp>("/api/strategies"), refetchInterval: 30000 });
  if (q.error) return <p role="alert" className="text-goldLight">⚠ Cannot load the strategy gates: {q.error instanceof Error ? q.error.message : "unknown error"}</p>;
  const d = q.data;
  if (!d) return <p role="status">Loading…</p>;
  const aiAcc = strat.data?.ai_ledger?.[0]?.required_accuracy;
  const rows = [...d.strategies].sort((a, b) => Number(b.on) - Number(a.on));
  return (
    <section className="space-y-3" data-testid="strategy-gates">
      <h2 className="font-semibold text-gold">Paytience · Gates per strategy</h2>
      <p className="text-sm text-blue">Each strategy lists only the checks its own code makes, in order, with the result of its latest decision. A gate can only block a trade, never add one.</p>
      <div className="grid gap-4 lg:grid-cols-2">
        {rows.map((s) => <StrategyCard key={s.key} s={s} aiAcc={aiAcc} />)}
      </div>
      <section className={card} data-testid="lucid-rules">
        <h3 className="font-semibold text-gold">Lucid rules (always on)</h3>
        <p className="text-xs text-blue">Firm and safety checks for every strategy. They cannot be switched off here.</p>
        <ul className="mt-2 space-y-1 text-sm">
          {d.lucid_rules.map((g) => (
            <li key={g.id} data-testid={`lucid-${g.id}`}><span className="mr-2 rounded border border-blue px-1 text-xs text-blue">LOCKED</span><b className="text-gold">{g.name}</b> <span className="text-xs text-blue">{g.text}</span></li>
          ))}
        </ul>
      </section>
    </section>
  );
}
