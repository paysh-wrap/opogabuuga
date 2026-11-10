import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";

const card = "rounded-xl border border-border bg-card p-4";
const btn = "rounded-md border px-3 py-1.5 text-sm font-semibold disabled:opacity-50";

interface FastCfg {
  ladder: { enabled: boolean; steps: { cushion_frac: string; extra: number }[]; max_contracts: number };
  harvest: { enabled: boolean; day_stop_pct_of_target: string };
  early: { enabled: boolean; first_trades: number; until_profit_frac: string | null; cushion_frac: string; risk_pct: string | null; extra_contracts: number };
  quality_day: { enabled: boolean; mode: string; trailing_days: number };
}
interface FastEval {
  enabled: boolean;
  has_eval_accounts: boolean;
  confirm_phrase: string;
  config: FastCfg;
  verify: string[];
  accounts: { id: number; label: string; effective: boolean }[];
}
interface StudyRow { pass_pct: number; bust_pct: number; median_sessions: number }
interface Preview {
  mechanisms: Record<string, unknown>;
  unchanged: string[];
  mechanism_notes?: Record<string, string>;
  study: { status: string; plan: string; notice: string; source: string; baseline: StudyRow | null; fast: StudyRow | null; note?: string };
}

type MechKey = "ladder" | "harvest" | "early" | "quality_day";
const MECH: { key: MechKey; title: string; text: (c: FastCfg) => string }[] = [
  { key: "ladder", title: "1 · Cushion size ladder", text: (c) => `+micros only while the cushion is above ${c.ladder.steps.map((s) => `${Number(s.cushion_frac) * 100}% of the loss limit (+${s.extra})`).join(", ") || "—"}; max ${c.ladder.max_contracts}; back to base after any loss.` },
  { key: "harvest", title: "2 · Day-cap harvesting", text: (c) => `no new entries once today's profit reaches ${c.harvest.day_stop_pct_of_target}% of the target (can only tighten the consistency day stop).` },
  { key: "early", title: "3 · Early-evaluation tier", text: (c) => `first ${c.early.first_trades || "—"} trades${c.early.until_profit_frac ? ` / until ${Number(c.early.until_profit_frac) * 100}% of target` : ""}, cushion ≥ ${Number(c.early.cushion_frac) * 100}%: risk ${c.early.risk_pct ?? "—"} or +${c.early.extra_contracts} micro; never after a loss.` },
  { key: "quality_day", title: "4 · Quality-day filter", text: (c) => (c.quality_day.mode === "prev_day" ? "skip the day after a losing day." : `skip while the last ${c.quality_day.trailing_days} days sum to a loss.`) },
];

/** D87 Fast Evaluation: EVAL stage only, default OFF. Impact Preview → typed phrase → ON; OFF in one click. */
export function FastEvalPanel() {
  const qc = useQueryClient();
  const fe = useQuery({ queryKey: ["fasteval"], queryFn: () => api<FastEval>("/api/risk/fast-eval") });
  const [preview, setPreview] = useState<Preview | null>(null);
  const [typed, setTyped] = useState("");
  const [err, setErr] = useState("");
  const refresh = () => ["fasteval", "risk", "accounts", "dashboard"].forEach((k) => void qc.invalidateQueries({ queryKey: [k] }));
  const loadPreview = useMutation({
    mutationFn: () => api<Preview>("/api/risk/fast-eval/preview", { method: "POST" }),
    onMutate: () => setErr(""),
    onSuccess: (r) => { setPreview(r); setTyped(""); },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Preview failed"),
  });
  const set = useMutation({
    mutationFn: (on: boolean) => api("/api/risk/fast-eval", { method: "PUT", body: JSON.stringify({ enabled: on, confirm: on ? typed : "" }) }),
    onMutate: () => setErr(""),
    onSuccess: () => { setPreview(null); setTyped(""); refresh(); },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Request failed"),
  });
  const toggle = useMutation({
    mutationFn: (v: { key: MechKey; on: boolean }) =>
      api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { [`fast_eval.${v.key}.enabled`]: v.on }, note: `Fast Evaluation ${v.key} ${v.on ? "on" : "off"}` }) }),
    onMutate: () => setErr(""),
    onSuccess: refresh,
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Save failed"),
  });
  const d = fe.data;
  const s = preview?.study;
  return (
    <section className={card} data-testid="fast-eval-panel">
      <h2 className="font-semibold text-gold">Paytience · Fast Evaluation {d?.enabled ? "· ON" : "· OFF"}</h2>
      <p className="text-xs">EVAL accounts only (funded/live never change). Default OFF. Simulated / unproven. Day-cap harvesting and the early tier showed no measured benefit. Never changes the kill switch, DLL/MLL, gates, R:R or hedge/news/flat rules; size never rises after a loss.</p>
      {d && (
        <ul className="mt-2 text-xs" data-testid="fast-eval-mechanisms">
          {MECH.map((m) => (
            <li key={m.key} className="mt-1">
              <label className="flex flex-wrap items-center gap-2">
                <input type="checkbox" aria-label={`Fast Evaluation ${m.title}`} checked={d.config[m.key].enabled} disabled={toggle.isPending}
                  onChange={(e) => toggle.mutate({ key: m.key, on: e.target.checked })} />
                <b className="text-gold">{m.title}</b>
                {d.verify.includes(`fast_eval.${m.key}`) && <span className="rounded border border-gold px-1 text-gold" title="Placeholder numbers until the study confirms them">VERIFY</span>}
              </label>
              <span className="ml-6 block">{m.text(d.config)}</span>
            </li>
          ))}
        </ul>
      )}
      {err && <p role="alert" className="mt-2 text-sm text-goldLight">⚠ {err}</p>}
      {d?.enabled ? (
        <button data-testid="fast-eval-off" className={`${btn} mt-2 border-gold text-gold`} disabled={set.isPending} onClick={() => set.mutate(false)}>ON — turn off</button>
      ) : !preview ? (
        <button data-testid="fast-eval-preview" className={`${btn} mt-2 border-blue text-blue`} disabled={loadPreview.isPending || !d} onClick={() => loadPreview.mutate()}>
          {loadPreview.isPending ? "Loading preview…" : "OFF — preview turning on"}</button>
      ) : (
        <form className="mt-2" onSubmit={(e) => { e.preventDefault(); set.mutate(true); }}>
          <p className="text-sm font-semibold text-gold">Impact Preview — Fast Evaluation</p>
          <div data-testid="fast-eval-study" className="mt-1 text-xs">
            {s?.baseline && s.fast ? (
              <p>Study ({s.plan}): pass <b className="text-gold">{s.baseline.pass_pct}% → {s.fast.pass_pct}%</b> · bust <b className="text-gold">{s.baseline.bust_pct}% → {s.fast.bust_pct}%</b> · median sessions {s.baseline.median_sessions} → {s.fast.median_sessions}.</p>
            ) : s?.baseline ? (
              <p className="text-goldLight">Study ({s.plan}): baseline pass {s.baseline.pass_pct}% · bust {s.baseline.bust_pct}% · median {s.baseline.median_sessions} sessions. No safe speed-up found for this plan.</p>
            ) : (
              <p className="text-goldLight">No study numbers for this plan — the expected pass/bust change is unknown.</p>
            )}
            {s?.note && <p className="mt-1">{s.note}</p>}
            <ul className="mt-1 list-disc pl-4">{Object.entries(preview.mechanism_notes ?? {}).map(([k, v]) => <li key={k}><b className="text-gold">{k}</b>: {v}</li>)}</ul>
            <p className="mt-1 text-goldLight">⚠ {s?.notice}</p>
            <p className="mt-1">Unchanged: {preview.unchanged.join(", ")}.</p>
          </div>
          {!d?.has_eval_accounts && <p className="mt-2 text-xs text-goldLight">⚠ No EVAL accounts — it would have no effect.</p>}
          <label className="mt-2 flex flex-wrap items-center gap-2 text-sm">Type <b className="text-gold">{d?.confirm_phrase}</b>
            <input aria-label="Fast Evaluation confirmation" value={typed} onChange={(e) => setTyped(e.target.value)} /></label>
          <div className="mt-2 flex gap-2">
            <button type="submit" data-testid="fast-eval-enable" disabled={typed !== d?.confirm_phrase || set.isPending} className={`${btn} border-gold text-gold`}>Enable Fast Evaluation</button>
            <button type="button" className={`${btn} border-border text-blue`} onClick={() => { setPreview(null); setTyped(""); }}>Cancel</button>
          </div>
        </form>
      )}
      {d && d.accounts.length > 0 && <p className="mt-2 text-xs">EVAL accounts: {d.accounts.map((a) => `${a.label}${a.effective ? " (active)" : ""}`).join(" · ")}</p>}
    </section>
  );
}
