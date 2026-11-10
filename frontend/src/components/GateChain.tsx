import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { StrategiesResp } from "./StrategyButtons";

// D77: the gates a NOISE / PM_FADE entry passes. All must pass; a gate can only block. Rows come from the server config.
const KIND: Record<string, string> = { "firm-safe": "FIRM SAFETY", pillar: "PILLAR", study: "TESTED", ai: "AI" };
const card = "rounded-xl border border-border bg-card p-4";

export default function GateChain() {
  const q = useQuery({ queryKey: ["strategies"], queryFn: () => api<StrategiesResp>("/api/strategies"), refetchInterval: 30000 });
  const rows = q.data?.gate_chain;
  if (!rows) return null;
  const led = q.data?.ai_ledger[0];
  return (
    <section className={card} data-testid="gate-chain">
      <h2 className="font-semibold text-gold">Paytience · Gates for NOISE + afternoon fade (all must pass)</h2>
      <p className="text-sm text-blue">A gate can only block a trade, never add one. Gates tested on 5 years of MNQ stay OFF unless they improved win rate AND profit on held-out data (2024–26).</p>
      <ul className="mt-2 space-y-1 text-sm">
        {rows.map((g) => (
          <li key={g.id} data-testid={`chain-${g.id}`}>
            <span className="mr-2 rounded border border-blue px-1 text-xs text-blue">{g.on ? "ON" : "OFF"}</span>
            <b className="text-gold">{g.name}</b> <span className="text-xs text-blue">[{KIND[g.kind] ?? g.kind}{g.locked ? " · locked" : ""}]</span>
            <div className="ml-10">{g.text}</div>
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
