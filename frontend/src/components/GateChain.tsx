import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import FlagToggle from "./FlagToggle";
import type { StrategiesResp } from "./StrategyButtons";

// D77: the gates a NOISE / PM_FADE entry passes. All must pass; a gate can only block. Rows come from the server config.
const KIND: Record<string, string> = { "firm-safe": "FIRM SAFETY", pillar: "PILLAR", study: "TESTED", ai: "AI", lunqfx: "LunqFX only" };
const card = "rounded-xl border border-border bg-card p-4";

function AiThreshold({ value }: { value: number }) {
  const qc = useQueryClient();
  const [v, setV] = useState(String(Math.round(value * 100)));
  const [err, setErr] = useState("");
  const save = useMutation({
    mutationFn: () => api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { "strategy.ai_gate_min_accuracy": (Number(v) / 100).toFixed(2) }, note: `AI gate threshold ${v}%` }) }),
    onSuccess: () => setErr(""),
    onError: (e) => setErr(e instanceof Error ? e.message : "Rejected"),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  return (
    <span className="ml-10 mt-1 flex items-center gap-2 text-xs" data-testid="ai-threshold">
      Proof threshold (55–95%):
      <input aria-label="AI gate threshold percent" className="w-16 rounded border border-border bg-card px-1" type="number" min={55} max={95} value={v} onChange={(e) => setV(e.target.value)} />
      <button type="button" className="rounded border border-blue px-2 text-blue disabled:opacity-50" disabled={save.isPending} onClick={() => save.mutate()}>Save</button>
      {err && <span role="alert" className="text-gold">{err}</span>}
    </span>
  );
}

export default function GateChain() {
  const q = useQuery({ queryKey: ["strategies"], queryFn: () => api<StrategiesResp>("/api/strategies"), refetchInterval: 30000 });
  const rows = q.data?.gate_chain;
  if (!rows) return null;
  const led = q.data?.ai_ledger[0];
  const label = (g: (typeof rows)[number]) => g.state === "LUNQFX_ONLY" ? "LunqFX only" : g.state === "ADVISORY" ? "ADVISORY" : g.on ? "ON" : "OFF";
  return (
    <section className={card} data-testid="gate-chain">
      <h2 className="font-semibold text-gold">Paytience · Gates for NOISE + afternoon fade (all must pass)</h2>
      <p className="text-sm text-blue">A gate can only block a trade, never add one. Gates tested on 5 years of MNQ stay OFF unless they improved win rate AND profit on held-out data (2024–26).</p>
      <ul className="mt-2 space-y-1 text-sm">
        {rows.map((g) => (
          <li key={g.id} data-testid={`chain-${g.id}`}>
            <span className="mr-2 rounded border border-blue px-1 text-xs text-blue">{label(g)}</span>
            <b className="text-gold">{g.name}</b> <span className="text-xs text-blue">[{KIND[g.kind] ?? g.kind}{g.locked ? " · locked" : ""}]</span>
            {g.setting && g.setting.startsWith("strategy.structure_filters") && (
              <span className="ml-2"><FlagToggle setting={g.setting} on={g.on} unproven={g.unproven} label={g.name} /></span>
            )}
            <div className="ml-10">{g.text}</div>
            {g.id === "AI" && led && <AiThreshold value={led.required_accuracy} />}
          </li>
        ))}
      </ul>
      {led && (
        <p className="mt-2 text-sm" data-testid="chain-ai-status">
          AI record ({led.symbol}): <b className="text-gold">{led.badge}</b> · {led.stats.n}/{led.min_calls} scored calls · needs ≥ {Math.round(led.required_accuracy * 100)}% proven accuracy to block.
        </p>
      )}
    </section>
  );
}
