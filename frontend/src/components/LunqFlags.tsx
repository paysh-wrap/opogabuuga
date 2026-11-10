import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { StrategiesResp } from "./StrategyButtons";
import FlagToggle from "./FlagToggle";

// D80: LunqFX structure-filter flags (D76). All unproven; editable through the validated settings flow.
export default function LunqFlags() {
  const q = useQuery({ queryKey: ["strategies"], queryFn: () => api<StrategiesResp>("/api/strategies"), refetchInterval: 30000 });
  const rows = q.data?.lunqfx_flags;
  if (!rows) return null;
  return (
    <section className="rounded-xl border border-border bg-card p-4" data-testid="lunq-flags">
      <h2 className="font-semibold text-gold">Paytience · LunqFX structure filter (D76, shadow strategy)</h2>
      <p className="text-sm text-blue">Gates G2, G3, G5 and G7 and the score belong to the LunqFX engine only. These optional flags can only turn a LunqFX PASS into a SKIP.</p>
      <ul className="mt-2 space-y-1 text-sm">
        {rows.map((f) => (
          <li key={f.setting}><FlagToggle setting={f.setting} on={f.on} unproven={f.setting !== "strategy.lunqfx_structure.shadow_log"} label={f.name} /> <b className="text-gold">{f.name}</b><div className="ml-2 text-xs">{f.text}</div></li>
        ))}
      </ul>
    </section>
  );
}
