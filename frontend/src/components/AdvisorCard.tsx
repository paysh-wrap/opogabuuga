import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { SaveAlert, useSaveAlert } from "./useSaveAlert";

// D151: TradingAgents ADVISOR in front of the D142-D150 strategies (verdict recorded on every signal).
export type Verdict = "AGREE" | "DISAGREE" | "NEUTRAL" | "NO_CALL";
export interface AdvisorFeat { verdict: Verdict; prob_up: number | null; label: string | null; ledger_proven: boolean; mode?: string; blocks?: boolean }
export interface AdvisorCardRow { mode: string; symbol: string; skipped: boolean; call_label: string | null; call_direction: number | null; prob_up: number | null; last_verdict: Verdict | null }
export interface AdvisorResp { mode: "OFF" | "ADVISORY" | "GATE"; setting: string; skip_strategies: string[]; connected: boolean; ledger_proven: boolean; required_accuracy: number; cards: Record<string, AdvisorCardRow> }

const TEXT: Record<Verdict, string> = { AGREE: "AGREE", DISAGREE: "DISAGREE", NEUTRAL: "NEUTRAL", NO_CALL: "NO CALL" };

/** Small ADVISOR badge: gold/blue text only (§18). */
export function AdvisorBadge({ verdict, testId }: { verdict: Verdict | null | undefined; testId?: string }) {
  const v = verdict ?? "NO_CALL";
  const gold = v === "AGREE" || v === "DISAGREE";
  return (
    <span data-testid={testId} className={`rounded border px-1 text-xs font-semibold ${gold ? "border-gold text-gold" : "border-blue text-blue"}`}>
      ADVISOR · {TEXT[v]}
    </span>
  );
}

const callText = (c: AdvisorCardRow) =>
  c.call_label == null ? "no call today" : `${c.call_direction === 1 ? "▲ LONG" : c.call_direction === -1 ? "▼ SHORT" : "NEUTRAL"} (P up ${((c.prob_up ?? 0.5) * 100).toFixed(0)}%)`;

/** Per-card advisor line (strategy cards). */
export function AdvisorCardLine({ adv, cardKey }: { adv: AdvisorResp; cardKey: string }) {
  const c = adv.cards[cardKey];
  if (!c) return null;
  if (adv.mode === "OFF" || c.skipped) return <p className="mt-1 text-xs text-blue" data-testid={`advisor-${cardKey}`}>TradingAgents advisor: off for this strategy</p>;
  return (
    <p className="mt-1 text-xs text-blue" data-testid={`advisor-${cardKey}`}>
      <AdvisorBadge verdict={c.last_verdict ?? (c.call_label == null ? "NO_CALL" : null)} /> today: <b className="text-gold">{callText(c)}</b>
    </p>
  );
}

const MODES: { v: AdvisorResp["mode"]; label: string }[] = [
  { v: "OFF", label: "Off" },
  { v: "ADVISORY", label: "Advisory (record + show)" },
  { v: "GATE", label: "Gate (skip a proven DISAGREE)" },
];

/** Strategy-page control for the advisor mode. */
export default function AdvisorCard() {
  const qc = useQueryClient();
  const saved = useSaveAlert();
  const q = useQuery({ queryKey: ["strategies"], queryFn: () => api<{ advisor?: AdvisorResp }>("/api/strategies"), refetchInterval: 30000 });
  const save = useMutation({
    mutationFn: (m: string) => api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { "strategy.advisor.mode": m }, note: `TradingAgents advisor: ${m}` }) }),
    onSuccess: () => saved.ok(),
    onError: (e) => saved.fail("Advisor mode", e),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  const a = q.data?.advisor;
  if (!a) return null;
  const noCall = !a.connected || Object.values(a.cards).every((c) => c.call_label == null);
  return (
    <section className="rounded-xl border border-border bg-card p-4" data-testid="advisor-card">
      <h2 className="font-semibold text-gold">TradingAgents advisor (JJ, GALA, CONTI, OKALA, BRUNI, CANDACE, AUCTION)</h2>
      <p className="text-xs text-blue">Runs before each of these strategies' signals using today's stored TradingAgents call. It can only skip a trade (code ADVISOR_DISAGREE), never create or enlarge one. No call today never blocks.</p>
      <SaveAlert error={saved.error} />
      <div className="mt-2 flex flex-wrap gap-2" role="group" aria-label="Advisor mode">
        {MODES.map((m) => (
          <button key={m.v} type="button" aria-pressed={a.mode === m.v} disabled={save.isPending} onClick={() => save.mutate(m.v)}
            className={`rounded-md border px-3 py-1 text-sm font-semibold ${a.mode === m.v ? "border-gold text-gold" : "border-blue text-blue"} disabled:opacity-50`}>
            {a.mode === m.v ? "✓ " : ""}{m.label}
          </button>
        ))}
      </div>
      {a.mode === "GATE" && !a.ledger_proven && (
        <p className="mt-1 text-xs text-gold" data-testid="advisor-gate-unproven">Gate is not active yet: the AI ledger has not proven {(a.required_accuracy * 100).toFixed(0)}% accuracy, so it behaves like Advisory.</p>
      )}
      {!a.connected && <p className="mt-1 text-xs text-gold" data-testid="advisor-no-key">TradingAgents key not connected: no call today</p>}
      {a.connected && noCall && <p className="mt-1 text-xs text-gold" data-testid="advisor-no-call">No TradingAgents call today: the advisor records NO CALL and blocks nothing.</p>}
    </section>
  );
}
