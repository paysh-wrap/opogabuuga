import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";

const btn = "rounded-md border px-3 py-1.5 text-sm font-semibold disabled:opacity-50";

interface StageView { enabled: boolean; accounts: number; confirm_phrase: string; blocked: string | null }
interface FastPassStage { warning: string; guards: string[]; applies: string; stages: Record<"FUNDED" | "LIVE", StageView> }

/** D180: Fast Pass on FUNDED / LIVE. Two switches, default OFF, UNVERIFIED. Typed phrase to enable; one click to disable. */
export function FastPassStagePanel() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["fastpassstage"], queryFn: () => api<FastPassStage>("/api/risk/fast-pass-stage") });
  const [open, setOpen] = useState<"FUNDED" | "LIVE" | null>(null);
  const [typed, setTyped] = useState("");
  const [err, setErr] = useState("");
  const set = useMutation({
    mutationFn: (v: { stage: "FUNDED" | "LIVE"; on: boolean }) =>
      api(`/api/risk/fast-pass-stage/${v.stage}`, { method: "PUT", body: JSON.stringify({ enabled: v.on, confirm: v.on ? typed : "" }) }),
    onMutate: () => setErr(""),
    onSuccess: () => { setOpen(null); setTyped(""); ["fastpassstage", "strategies", "dashboard"].forEach((k) => void qc.invalidateQueries({ queryKey: [k] })); },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Request failed"),
  });
  const d = q.data;
  if (!d?.guards || !d.stages) return null;
  return (
    <div className="mt-2 rounded-lg border border-border p-3" data-testid="fast-pass-stage-panel">
      <h4 className="font-semibold text-gold">Fast Pass on FUNDED and LIVE accounts (UNVERIFIED, default OFF)</h4>
      <p className="mt-1 text-xs text-blue">Same per-plan sizes as above (NOISE / CANDACE micros, stops, grow, brake steps), only on accounts of that stage and of the plan's own size, and only while that plan's fast-pass switch is ON. Applies to the next NEW trade only; sizes only shrink or skip. Evaluation Mode stays EVAL only. These funded / live guards still run after the size:</p>
      <ul className="mt-1 list-disc pl-5 text-xs text-blue" data-testid="fast-pass-stage-guards">{d.guards.map((g) => <li key={g}>{g}</li>)}</ul>
      <p className="mt-2 text-xs font-semibold text-goldLight" data-testid="fast-pass-stage-warning">⚠ {d.warning}</p>
      {err && <p role="alert" className="mt-2 text-sm text-goldLight">⚠ {err}</p>}
      <div className="mt-2 grid gap-2 md:grid-cols-2">
        {(["FUNDED", "LIVE"] as const).map((s) => {
          const v = d.stages[s];
          return (
            <div key={s} className="rounded border border-border p-2 text-sm" data-testid={`fp-stage-${s}`}>
              <b className="text-gold">{s}</b> · {v.enabled ? "ON" : "OFF"} · {v.accounts} account{v.accounts === 1 ? "" : "s"}
              {s === "LIVE" && v.blocked && <p className="text-xs text-goldLight" data-testid="fp-stage-live-blocked">⚠ {v.blocked}. Turning it on needs every live gate (PAYTIENCE_ALLOW_LIVE, live toggle with typed phrase, Live-Readiness Checklist, VERIFY values, attestation).</p>}
              {v.enabled ? (
                <button data-testid={`fp-stage-off-${s}`} className={`${btn} mt-1 border-gold text-gold`} disabled={set.isPending} onClick={() => set.mutate({ stage: s, on: false })}>ON — turn off</button>
              ) : open !== s ? (
                <button data-testid={`fp-stage-preview-${s}`} className={`${btn} mt-1 border-blue text-blue`} disabled={s === "LIVE" && !!v.blocked} onClick={() => { setOpen(s); setTyped(""); setErr(""); }}>OFF — preview turning on</button>
              ) : (
                <form className="mt-1" onSubmit={(e) => { e.preventDefault(); set.mutate({ stage: s, on: true }); }}>
                  <p className="text-xs font-semibold text-gold">Impact Preview: {s} accounts get the fast-pass sizes from the next new trade. {d.warning}</p>
                  <label className="mt-1 flex flex-wrap items-center gap-2 text-xs">Type <b className="text-gold">{v.confirm_phrase}</b>
                    <input aria-label={`Fast Pass ${s} confirmation`} value={typed} onChange={(e) => setTyped(e.target.value)} /></label>
                  <div className="mt-1 flex gap-2">
                    <button type="submit" data-testid={`fp-stage-enable-${s}`} disabled={typed !== v.confirm_phrase || set.isPending} className={`${btn} border-gold text-gold`}>Enable Fast Pass {s}</button>
                    <button type="button" className={`${btn} border-border text-blue`} onClick={() => { setOpen(null); setTyped(""); }}>Cancel</button>
                  </div>
                </form>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
