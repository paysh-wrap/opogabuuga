import type { AiAdvice } from "./StrategyButtons";

const runLabel = (m: number) => (m % 60 === 0 ? `${m / 60} h` : `${m} min`);
const stamp = (iso?: string) => (iso ? new Date(iso).toLocaleString("en-US", { timeZone: "America/New_York", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false }) + " ET" : "");

/** D176: TradingAgents advice for every strategy (3 pre-open runs, 09:30 ET open). ADVICE ONLY, never blocks trading. */
export default function AiAdviceCard({ advice, compact = false }: { advice?: AiAdvice; compact?: boolean }) {
  if (!advice) return null;
  return (
    <section className="rounded-lg border border-border p-3 text-sm" data-testid="ai-advice">
      <h3 className="font-semibold text-gold">TradingAgents advice <span className="ml-1 rounded border border-gold px-1 text-xs" data-testid="ai-advice-label">Advice only, never blocks trading</span></h3>
      {advice.mode === "OFF" ? (
        <p className="mt-1 text-xs text-blue" data-testid="ai-advice-off">Advisor is off: no runs.</p>
      ) : (
        <ul className="mt-1 text-xs text-blue" data-testid="ai-advice-runs">
          {advice.runs.map((r) => (
            <li key={r.minutes_before} data-testid={`ai-advice-run-${r.minutes_before}`}>
              <b className="text-gold">{runLabel(r.minutes_before)} before the open ({r.at} ET)</b>:{" "}
              {r.results.map((x) => (
                <span key={x.symbol} className="mr-2">
                  {x.symbol}{" "}
                  {x.status === "OK" ? <>{x.side}{x.at ? ` · ran ${stamp(x.at)}` : ""}{!compact && x.advice?.main ? ` — ${x.advice.main}` : ""}</>
                    : x.status === "NO_CALL" ? <>NO_CALL — {x.reason ?? "no call"} (advice unavailable; trading unaffected){x.at ? ` · ${stamp(x.at)}` : ""}</>
                    : "pending"}
                </span>
              ))}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
