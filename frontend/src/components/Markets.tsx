import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

interface M { symbol: string; name: string; enabled: boolean; contract?: string | null }

export default function Markets() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["markets"], queryFn: () => api<{ markets: M[] }>("/api/markets") });
  const set = useMutation({
    mutationFn: (m: M) => api("/api/markets", { method: "PUT", body: JSON.stringify({ symbol: m.symbol, enabled: !m.enabled }) }),
    onSuccess: () => ["markets", "strategy", "dashboard"].forEach((k) => void qc.invalidateQueries({ queryKey: [k] })),
  });
  return (
    <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Markets">
      <span className="text-sm">Trade:</span>
      {q.data?.markets.map((m) => (
        <button key={m.symbol} data-testid={`market-${m.symbol}`} disabled={set.isPending} onClick={() => set.mutate(m)}
          className={`rounded-md border px-3 py-1.5 text-sm font-semibold ${m.enabled ? "border-gold bg-gold/15 text-gold" : "border-blue text-blue"}`}>
          {m.name} ({m.contract ?? m.symbol}) {m.enabled ? "ON" : "OFF"}
        </button>
      ))}
      <span className="text-xs opacity-75">Micro futures only; orders go to the front contract shown (auto-roll).</span>
    </div>
  );
}
