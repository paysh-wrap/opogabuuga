import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { choiceOf, choiceTitle, type StrategiesResp, type Strat } from "./StrategyButtons";

/** Names of the strategies that are ON, one entry per choice (NOISE + CANDACE is one MAIN choice). Pure, from /api/strategies. */
export function runningNames(strategies: Strat[], combined?: { enabled: boolean; title: string }): string[] {
  const names: string[] = [];
  const both = !!combined?.enabled; // D175: MAIN + Order Flow together only as the combined choice (one name, never two)
  if (both) names.push(combined!.title);
  for (const s of strategies.filter((x) => x.enabled)) {
    const c = choiceOf(s.key);
    if (both && (c === "main" || c === "order_flow")) continue;
    const label = c === "main" || c === "order_flow" || c === "ai_duo" ? choiceTitle(c) : s.name.split(" — ")[0] ?? s.name;
    if (!names.includes(label)) names.push(label);
  }
  return names;
}

/** "Now running": which strategy is ON, from the settings API; a clear gold warning when nothing is ON. */
export default function NowRunning({ compact = false }: { compact?: boolean }) {
  const q = useQuery({ queryKey: ["strategies"], queryFn: () => api<StrategiesResp>("/api/strategies"), refetchInterval: 30000 });
  if (q.error && !q.data) {
    return <span role="alert" data-testid="now-running-error" className="text-xs font-semibold text-goldLight">⚠ Strategy status unavailable: {q.error instanceof Error ? q.error.message : "unknown error"}</span>;
  }
  if (!q.data || !Array.isArray(q.data.strategies)) return null;
  const names = runningNames(q.data.strategies, q.data.combined);
  if (names.length === 0) {
    return compact ? (
      <span role="alert" data-testid="now-running" className="rounded border border-gold px-2 py-0.5 text-xs font-semibold text-goldLight">No strategy ON · no trades</span>
    ) : (
      <div role="alert" data-testid="now-running" className="rounded-lg border border-gold bg-card p-3 text-sm text-goldLight">
        ⚠ <b className="text-gold">No strategy is ON</b> — Paytience will not open trades. Turn one on in the Strategy page.
      </div>
    );
  }
  return compact ? (
    <span data-testid="now-running" className="rounded border border-border px-2 py-0.5 text-xs font-semibold text-goldLight">Now running · {names.join(" + ")}</span>
  ) : (
    <div data-testid="now-running" className="rounded-lg border border-border bg-card p-3 text-sm text-blue">
      <span className="text-xs font-semibold uppercase tracking-wider">Now running</span>{" "}
      <b className="text-gold">{names.join(" + ")}</b>
    </div>
  );
}
