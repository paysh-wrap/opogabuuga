import { band, meters, type MeterAcct } from "../lib/insights";

/** Rule-proximity gauges (MLL distance, DLL used, consistency headroom, inactivity) — Dashboard + Risk page. */
export default function RuleMeters({ a }: { a: MeterAcct & { id: number } }) {
  const ms = meters(a);
  if (ms.length === 0) return null;
  return (
    <div className="mt-3 space-y-2" data-testid={`meters-${a.id}`}>
      {ms.map((m) => {
        const b = band(m.used);
        return (
          <div key={m.key} data-testid={`meter-${a.id}-${m.key}`} data-band={b}>
            <div className="flex items-center justify-between text-xs">
              <span>{m.label}{b === "danger" && <span aria-label="near limit" title="80% or more used" className="ml-2 inline-block h-2 w-2 rounded-full align-middle" style={{ background: "#EF4444" }} />}</span>
              <span className={b === "safe" ? "text-blueLight" : "text-goldLight"}>{Math.round(m.used * 100)}% used · {m.detail}</span>
            </div>
            <div className="mt-1 h-1.5 rounded bg-border" role="meter" aria-label={m.label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(m.used * 100)}>
              <div className={`h-1.5 rounded ${b === "safe" ? "bg-blue" : "bg-gold"}`} style={{ width: `${Math.min(100, Math.max(0, Math.round(m.used * 100)))}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
