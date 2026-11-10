import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

// D80: one validated My Settings toggle (same PUT /api/risk/settings flow as the strategy buttons). Unproven flags
// carry a gold badge and ask for a confirmation before they are switched ON.
export default function FlagToggle({ setting, on, unproven, label }: { setting: string; on: boolean; unproven?: boolean; label: string }) {
  const qc = useQueryClient();
  const m = useMutation({
    mutationFn: () => api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { [setting]: !on }, note: `Gate toggle: ${setting} ${on ? "off" : "on"}` }) }),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  const click = () => {
    if (!on && unproven && !window.confirm(`"${label}" is UNPROVEN: it did not improve win rate and profit on held-out 2024–26 data. Turn it on anyway? It can only block trades, never add them.`)) return;
    m.mutate();
  };
  return (
    <span className="inline-flex items-center gap-2">
      <button type="button" aria-pressed={on} disabled={m.isPending} onClick={click} data-testid={`flag-${setting}`}
        className={`rounded border px-2 text-xs font-semibold ${on ? "border-gold text-gold" : "border-blue text-blue"} disabled:opacity-50`}>
        {on ? "ON" : "OFF"}
      </button>
      {unproven && <span className="rounded border border-gold px-1 text-xs text-gold" data-testid="unproven-badge">unproven</span>}
    </span>
  );
}
