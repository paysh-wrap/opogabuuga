import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { usePageTitle } from "../components/usePageTitle";

interface Settings {
  version: number;
  settings: Record<string, unknown>;
  validation: { ok: boolean; errors: string[]; warnings: string[] };
  eval_mode_on: boolean;
  error: string | null;
}
interface EvalMode { enabled: boolean; has_eval_accounts: boolean; confirm_phrase: string }
interface Live { live: boolean; toggle_on: boolean; phrase: string; checklist: { check: string; ok: boolean; detail: string }[] }

const btn = "rounded-md border px-3 py-1.5 text-sm font-semibold disabled:opacity-50";
const show = (v: unknown) => (typeof v === "object" ? JSON.stringify(v) : String(v));

export default function Risk() {
  usePageTitle("Risk");
  const qc = useQueryClient();
  const [err, setErr] = useState("");
  const [livePhrase, setLivePhrase] = useState("");
  const [edit, setEdit] = useState<Record<string, string>>({});
  const st = useQuery({ queryKey: ["risk"], queryFn: () => api<Settings>("/api/risk/settings") });
  const em = useQuery({ queryKey: ["evalmode"], queryFn: () => api<EvalMode>("/api/risk/eval-mode") });
  const lv = useQuery({ queryKey: ["live"], queryFn: () => api<Live>("/api/live"), refetchInterval: 30000 });
  const run = useMutation({
    mutationFn: (f: () => Promise<unknown>) => f(),
    onMutate: () => setErr(""),
    onSuccess: () => { ["risk", "evalmode", "live"].forEach((k) => void qc.invalidateQueries({ queryKey: [k] })); setEdit({}); },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Request failed"),
  });
  const s = st.data;
  if (!s) return <p role="status">Loading…</p>;
  const oneToOne = s.settings["one_to_one_mode.enabled"] === true;
  const save = (changes: Record<string, unknown>) =>
    run.mutate(() => api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes }) }));

  return (
    <div className="space-y-5">
      <h1 className="text-2xl font-bold text-gold">Risk management</h1>
      {err && <p role="alert" className="rounded-lg border border-gold p-3 text-sm text-goldLight">⚠ {err}</p>}
      {s.error && <p role="alert" className="text-goldLight">⚠ {s.error}</p>}

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">1:1 mode</h2>
        <p className="text-xs">Target 1R · 50% off at 0.75R then breakeven · max 3 losses/day · never over consistency.</p>
        <button data-testid="one-to-one" className={`${btn} mt-2 ${oneToOne ? "border-gold text-gold" : "border-blue text-blue"}`}
          onClick={() => save({ "one_to_one_mode.enabled": !oneToOne })}>{oneToOne ? "ON — turn off" : "OFF — turn on"}</button>
      </section>

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">Evaluation Mode {em.data?.enabled ? "· ON" : "· OFF"}</h2>
        <p className="text-xs">EVAL accounts only. Raises risk tiers to 10/12/14% (max $140). Never changes rules or stops.</p>
        <button data-testid="eval-mode" className={`${btn} mt-2 ${em.data?.enabled ? "border-gold text-gold" : "border-blue text-blue"}`}
          onClick={() => {
            const on = !em.data?.enabled;
            if (on && !window.confirm("Turn ON Evaluation Mode? EVAL accounts risk 10/12/14% (max $140) per trade.")) return;
            run.mutate(() => api("/api/risk/eval-mode", { method: "PUT", body: JSON.stringify({ enabled: on, confirm: on ? em.data?.confirm_phrase : "" }) }));
          }}>{em.data?.enabled ? "ON — turn off" : "OFF — turn on"}</button>
        <label className="mt-3 flex items-center gap-2 text-sm">
          <input type="checkbox" data-testid="eval-1to1" checked={s.settings["eval_mode.one_to_one"] === true}
            onChange={(e) => save({ "eval_mode.one_to_one": e.target.checked })} />
          Use 1:1 mode on EVAL accounts while Evaluation Mode is on
        </label>
      </section>

      <section className="rounded-xl border border-gold bg-card p-4">
        <h2 className="font-semibold text-gold">Live trading {lv.data?.live ? "· LIVE" : "· PAPER"}</h2>
        <ul className="mt-2 grid gap-1 text-sm sm:grid-cols-2">
          {lv.data?.checklist.map((c) => (
            <li key={c.check} data-testid={`live-${c.check}`}>
              <span aria-hidden style={{ color: c.ok ? "#22C55E" : "#EF4444" }}>●</span> {c.check.replace(/_/g, " ")}
              {!c.ok && <span className="opacity-75"> — {c.detail}</span>}
            </li>
          ))}
        </ul>
        {lv.data?.toggle_on ? (
          <button className={`${btn} mt-2 border-blue text-blue`} onClick={() => run.mutate(() => api("/api/live", { method: "PUT", body: JSON.stringify({ enabled: false }) }))}>Turn live toggle off</button>
        ) : (
          <div className="mt-2 flex flex-wrap gap-2">
            <input aria-label="Live phrase" placeholder={lv.data?.phrase} value={livePhrase} onChange={(e) => setLivePhrase(e.target.value)} />
            <button disabled={livePhrase !== lv.data?.phrase} className={`${btn} border-gold text-gold`}
              onClick={() => run.mutate(() => api("/api/live", { method: "PUT", body: JSON.stringify({ enabled: true, confirm: livePhrase }) }))}>Enable live toggle</button>
          </div>
        )}
      </section>

      <section className="rounded-xl border border-border bg-card p-4">
        <h2 className="font-semibold text-gold">My settings · v{s.version}</h2>
        {!s.validation.ok && <p className="text-sm text-goldLight">{s.validation.errors.join(" · ")}</p>}
        <table className="mt-2 w-full text-sm"><tbody>
          {Object.entries(s.settings).map(([k, v]) => (
            <tr key={k} className="border-t border-border">
              <td className="py-1 pr-2">{k}</td>
              <td><input aria-label={k} className="w-full" value={edit[k] ?? show(v)} onChange={(e) => setEdit({ ...edit, [k]: e.target.value })} /></td>
            </tr>
          ))}
        </tbody></table>
        <button disabled={!Object.keys(edit).length} className={`${btn} mt-3 border-gold text-gold`} onClick={() => {
          const changes: Record<string, unknown> = {};
          for (const [k, v] of Object.entries(edit)) { try { changes[k] = JSON.parse(v); } catch { changes[k] = v; } }
          save(changes);
        }}>Save (validated)</button>
      </section>
    </div>
  );
}
