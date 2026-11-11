import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

// D94: Trading-R1 (TauricResearch, Apache-2.0) research card. INFORMATION ONLY — the answer never triggers, gates,
// sizes, scores or biases a trade. Optional connection: missing venv or key → "not configured", nothing invented.
export interface Tr1Last { question: string; ok: boolean; text: string; termination: string; error: string; rounds: number; at: string }
export interface Tr1Resp { label: string; configured: boolean; message: string; running: boolean; last: Tr1Last | null }
const card = "rounded-xl border border-border bg-card p-4";

export default function TradingR1Card() {
  const qc = useQueryClient();
  const [question, setQuestion] = useState("");
  const q = useQuery({ queryKey: ["trading-r1"], queryFn: () => api<Tr1Resp>("/api/research/trading-r1"), refetchInterval: (x) => (x.state.data?.running ? 3000 : 30000) });
  const ask = useMutation({
    mutationFn: (text: string) => api<Tr1Resp>("/api/research/trading-r1", { method: "POST", body: JSON.stringify({ question: text }) }),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["trading-r1"] }),
  });
  const t = q.data;
  if (!t) return null;
  const last = t.last;
  return (
    <section className={card} data-testid="trading-r1">
      <h2 className="font-semibold text-gold">Research · Trading-R1 (optional)</h2>
      <p className="text-xs font-semibold text-gold" data-testid="trading-r1-label">{t.label}</p>
      {!t.configured ? (
        <p className="mt-2 text-sm text-blue" data-testid="trading-r1-off">{t.message}</p>
      ) : (
        <form className="mt-2 flex gap-2" onSubmit={(e) => { e.preventDefault(); if (question.trim()) ask.mutate(question); }}>
          <input aria-label="Trading-R1 question" className="flex-1 rounded border border-border bg-transparent px-2 py-1 text-sm text-blue" maxLength={1000} value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="e.g. What is driving gold this week?" />
          <button type="submit" className="rounded border border-border px-3 py-1 text-sm text-gold" disabled={t.running || ask.isPending || !question.trim()}>{t.running ? "Researching…" : "Ask"}</button>
        </form>
      )}
      {ask.error && <p className="mt-2 text-sm text-gold">{String((ask.error as Error).message)}</p>}
      {last && (
        <div className="mt-2 text-sm" data-testid="trading-r1-last">
          <p className="text-blue">Q: {last.question} · {last.at}{last.rounds > 0 && ` · ${last.rounds} rounds`}</p>
          {last.ok ? <p className="whitespace-pre-wrap text-blue" data-testid="trading-r1-text">{last.text}</p> : <p className="text-gold">failed: {last.error}</p>}
        </div>
      )}
    </section>
  );
}
