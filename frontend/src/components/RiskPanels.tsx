import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "../lib/api";
import { etTime } from "../lib/time";
import { CooldownBanner } from "./DashboardExtras";

const card = "rounded-xl border border-border bg-card p-4";
const btn = "rounded-md border px-3 py-1.5 text-sm font-semibold disabled:opacity-50";

export interface Impact {
  kind: string;
  risk_by_tier: Record<string, Record<string, string>>;
  worst_day_at_1000: string;
  dll_test_at_max_base: { base: string; loss1: string; loss2: string; total: string; dll: string };
  losses_to_pause_from_1000: number | null;
}
export interface PreviewResp { valid: boolean; errors: unknown[]; warnings: string[]; needs_second_confirmation?: boolean; preview?: Impact }

const errText = (e: unknown) => (typeof e === "string" ? e : JSON.stringify(e));

/** Impact Preview table: $ risk per score tier at sample risk bases + DLL two-loss test + losses to pause. */
export function ImpactTable({ p, testid }: { p: Impact; testid: string }) {
  const tiers = Object.keys(Object.values(p.risk_by_tier)[0] ?? {});
  return (
    <div data-testid={testid} className="mt-2 overflow-x-auto text-xs">
      <table className="w-full"><thead><tr><th className="text-left">Risk base</th>{tiers.map((t) => <th key={t} className="text-left">score ≥{t}</th>)}</tr></thead>
        <tbody>{Object.entries(p.risk_by_tier).map(([b, row]) => (
          <tr key={b}><td>${b}</td>{tiers.map((t) => <td key={t} className="text-gold">${row[t]}</td>)}</tr>
        ))}</tbody></table>
      <p className="mt-1">Worst day from $1,000 (two losses): <b className="text-gold">${p.worst_day_at_1000}</b> · DLL test at max base ${p.dll_test_at_max_base.base}: ${p.dll_test_at_max_base.total} of ${p.dll_test_at_max_base.dll}
        {" "}· losses to pause from $1,000: <b className="text-gold">{p.losses_to_pause_from_1000 ?? "—"}</b></p>
    </div>
  );
}

// ---------- Evaluation Mode: Impact Preview → typed phrase → ON; OFF in one click (§11C) ----------
interface EvalMode { enabled: boolean; has_eval_accounts: boolean; confirm_phrase: string; accounts?: { id: number; label: string; override: string; effective: boolean }[] }

export function EvalModePanel() {
  const qc = useQueryClient();
  const em = useQuery({ queryKey: ["evalmode"], queryFn: () => api<EvalMode>("/api/risk/eval-mode") });
  const [preview, setPreview] = useState<{ on: Impact; off: Impact } | null>(null);
  const [typed, setTyped] = useState("");
  const [err, setErr] = useState("");
  const refresh = () => ["evalmode", "eval-mode", "risk", "accounts", "dashboard"].forEach((k) => void qc.invalidateQueries({ queryKey: [k] }));
  const loadPreview = useMutation({
    mutationFn: () => api<{ on: Impact; off: Impact }>("/api/risk/eval-mode/preview", { method: "POST" }),
    onMutate: () => setErr(""),
    onSuccess: (r) => { setPreview(r); setTyped(""); },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Preview failed"),
  });
  const set = useMutation({
    mutationFn: (on: boolean) => api("/api/risk/eval-mode", { method: "PUT", body: JSON.stringify({ enabled: on, confirm: on ? typed : "" }) }),
    onMutate: () => setErr(""),
    onSuccess: () => { setPreview(null); setTyped(""); refresh(); },
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Request failed"),
  });
  const d = em.data;
  return (
    <section className={card} data-testid="eval-panel">
      <h2 className="font-semibold text-gold">Evaluation Mode {d?.enabled ? "· ON" : "· OFF"}</h2>
      <p className="text-xs">EVAL accounts only (funded/live never change).</p>
      <ul className="mt-1 text-xs" data-testid="eval-mode-main">
        <li><b className="text-gold">MAIN strategy (NOISE + fade), Lucid Pro:</b> 150K trades 4 micros (brake to 2 below 50% cushion) — pass ≈ 19 sessions faster;
          100K starts at 2 and grows +1 per $1,200 of cushion up to 4, and stops for the day once today&apos;s profit ≥ 33% of the remaining target — ≈ 14 sessions faster;
          25K / 50K unchanged (every faster setting lost value in the 5-year test).</li>
        <li>Original LunqFX strategy: risk tiers 10/12/14% (max $140).</li>
        <li>Never changes gates, stops, DLL/MLL, day stops, kill switch or flat rules. Applies to the next new trade.</li>
      </ul>
      {err && <p role="alert" className="mt-2 text-sm text-goldLight">⚠ {err}</p>}
      {d?.enabled ? (
        <button data-testid="eval-mode-off" className={`${btn} mt-2 border-gold text-gold`} disabled={set.isPending} onClick={() => set.mutate(false)}>ON — turn off</button>
      ) : !preview ? (
        <button data-testid="eval-mode-preview" className={`${btn} mt-2 border-blue text-blue`} disabled={loadPreview.isPending || !d} onClick={() => loadPreview.mutate()}>
          {loadPreview.isPending ? "Loading preview…" : "OFF — preview turning on"}</button>
      ) : (
        <form className="mt-2" onSubmit={(e) => { e.preventDefault(); set.mutate(true); }}>
          <p className="text-sm font-semibold text-gold">Impact Preview — with Evaluation Mode</p>
          <ImpactTable p={preview.on} testid="eval-preview-on" />
          <p className="mt-2 text-sm font-semibold text-gold">Standard (now)</p>
          <ImpactTable p={preview.off} testid="eval-preview-off" />
          {!d?.has_eval_accounts && <p className="mt-2 text-xs text-goldLight">⚠ No EVAL accounts — it would have no effect.</p>}
          <label className="mt-2 flex flex-wrap items-center gap-2 text-sm">Type <b className="text-gold">{d?.confirm_phrase}</b>
            <input aria-label="Evaluation Mode confirmation" value={typed} onChange={(e) => setTyped(e.target.value)} /></label>
          <div className="mt-2 flex gap-2">
            <button type="submit" data-testid="eval-mode-enable" disabled={typed !== d?.confirm_phrase || set.isPending} className={`${btn} border-gold text-gold`}>Enable Evaluation Mode</button>
            <button type="button" className={`${btn} border-border text-blue`} onClick={() => { setPreview(null); setTyped(""); }}>Cancel</button>
          </div>
        </form>
      )}
      {d?.accounts && d.accounts.length > 0 && (
        <p className="mt-2 text-xs">EVAL accounts: {d.accounts.map((a) => `${a.label} (${a.override}${a.effective ? ", active" : ""})`).join(" · ")}</p>
      )}
    </section>
  );
}

// ---------- What-If: try tier / floor / cap values without saving ----------
const WHAT_IF_KEYS = ["internal.risk_pct_floor", "internal.risk_pct_middle", "internal.risk_pct_ceiling"];

export function WhatIf({ settings }: { settings: Record<string, unknown> }) {
  const keys = WHAT_IF_KEYS.filter((k) => k in settings);
  const [vals, setVals] = useState<Record<string, string>>({});
  const [res, setRes] = useState<PreviewResp | null>(null);
  const [err, setErr] = useState("");
  const go = useMutation({
    mutationFn: () => {
      const changes: Record<string, unknown> = {};
      for (const [k, v] of Object.entries(vals)) if (v !== "") changes[k] = v;
      return api<PreviewResp>("/api/risk/preview", { method: "POST", body: JSON.stringify({ changes, kind: "standard" }) });
    },
    onMutate: () => setErr(""),
    onSuccess: setRes,
    onError: (e) => setErr(e instanceof ApiError ? e.message : "What-If failed"),
  });
  return (
    <section className={card} data-testid="what-if">
      <h2 className="font-semibold text-gold">What-If (nothing is saved)</h2>
      <div className="mt-2 flex flex-wrap items-end gap-2 text-sm">
        {keys.length === 0 && <p className="text-xs">No tier settings are editable for this plan.</p>}
        {keys.map((k) => (
          <label key={k} className="flex flex-col text-xs">{k.split(".")[1]?.replace(/_/g, " ")}
            <input aria-label={`What-If ${k}`} placeholder={String(settings[k])} value={vals[k] ?? ""} onChange={(e) => setVals({ ...vals, [k]: e.target.value })} /></label>
        ))}
        <button className={`${btn} border-blue text-blue`} disabled={go.isPending} onClick={() => go.mutate()}>Run What-If</button>
      </div>
      {err && <p role="alert" className="text-sm text-goldLight">⚠ {err}</p>}
      {res && !res.valid && <p role="alert" className="mt-2 text-sm text-goldLight">⚠ Not allowed: {res.errors.map(errText).join(" · ")}</p>}
      {res?.preview && <ImpactTable p={res.preview} testid="what-if-result" />}
      {res?.warnings.map((w) => <p key={w} className="text-xs text-goldLight">{w}</p>)}
    </section>
  );
}

// ---------- Versions + rollback ----------
interface Version { kind: string; version: number; author: string; note: string; diff: unknown; active: boolean; at: string }

export function Versions() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["risk-versions"], queryFn: () => api<{ versions: Version[] }>("/api/risk/versions") });
  const [err, setErr] = useState("");
  const rb = useMutation({
    mutationFn: (v: number) => api(`/api/risk/rollback/${v}`, { method: "POST" }),
    onMutate: () => setErr(""),
    onSuccess: () => ["risk", "risk-versions"].forEach((k) => void qc.invalidateQueries({ queryKey: [k] })),
    onError: (e) => setErr(e instanceof ApiError ? e.message : "Rollback failed"),
  });
  const list = q.data?.versions.filter((v) => v.kind === "standard") ?? [];
  return (
    <section className={card} data-testid="versions">
      <h2 className="font-semibold text-gold">My Settings versions</h2>
      {q.isLoading && <p role="status" className="text-sm">Loading…</p>}
      {q.data && list.length === 0 && <p className="text-sm">No saved versions yet — the plan file defaults apply.</p>}
      {err && <p role="alert" className="text-sm text-goldLight">⚠ {err}</p>}
      <ul className="mt-2 space-y-1 text-xs">
        {list.map((v) => (
          <li key={v.version} data-testid={`version-${v.version}`} className="flex flex-wrap items-center gap-2 border-t border-border pt-1">
            <b className="text-gold">v{v.version}</b>{v.active && <span className="rounded border border-gold px-1 text-gold">active</span>}
            <span>{new Date(v.at).toLocaleDateString()} {etTime(v.at)} · {v.author}{v.note ? ` · ${v.note}` : ""}</span>
            <span className="break-all opacity-80">{JSON.stringify(v.diff).slice(0, 160)}</span>
            {!v.active && <button className="ml-auto rounded border border-blue px-2 py-0.5 text-blue" disabled={rb.isPending}
              onClick={() => { if (window.confirm(`Roll back My Settings to v${v.version}? (saved as a new version)`)) rb.mutate(v.version); }}>Roll back to v{v.version}</button>}
          </li>
        ))}
      </ul>
    </section>
  );
}

// ---------- Firm rules (read-only, VERIFY badges), day lock-in, cooldowns, kill log ----------
interface RulesResp {
  rules: { eval: { drawdown_type: string; daily_loss_limit: string | null; consistency_max_day_pct: string | null; profit_target: string; max_loss_limit: string };
    internal: { day_lockin_r: string; kill_switch_mll_distance: string; pause_below_risk_base: string } };
  verify_paths: string[]; verified_paths: string[]; firm_version: number | null;
}
interface Log { id: number; at: string; actor: string; action: string; entity: string; payload: unknown }

export function FirmAndSafety() {
  const r = useQuery({ queryKey: ["rules-full"], queryFn: () => api<RulesResp>("/api/rules") });
  const kills = useQuery({ queryKey: ["kill-log"], queryFn: () => api<{ logs: Log[] }>("/api/logs?action=kill_switch&limit=20") });
  if (r.isLoading) return <p role="status">Loading rules…</p>;
  if (r.error || !r.data) return <p role="alert" className="text-goldLight">⚠ Cannot load firm rules.</p>;
  const { eval: e, internal: i } = r.data.rules;
  const unverified = r.data.verify_paths.filter((p) => !r.data.verified_paths.includes(p));
  return (
    <>
      <section className={card} data-testid="firm-rules">
        <h2 className="font-semibold text-gold">Firm rules{r.data.firm_version ? ` · v${r.data.firm_version}` : ""}</h2>
        <p className="text-sm">Purchase profile: <b className="text-gold">{e.drawdown_type.toUpperCase()} drawdown</b> · DLL <b className="text-gold">{e.daily_loss_limit ? `ON $${e.daily_loss_limit}` : "OFF"}</b>
          {" "}· consistency <b className="text-gold">{e.consistency_max_day_pct ? `${e.consistency_max_day_pct}%` : "none"}</b> · target ${e.profit_target} · max loss ${e.max_loss_limit}</p>
        {unverified.length > 0 && <p className="mt-1 text-xs"><span className="rounded border border-gold px-1 font-semibold text-gold">VERIFY</span> {unverified.length} rule value(s) not yet confirmed: {unverified.slice(0, 6).join(", ")}{unverified.length > 6 ? "…" : ""}</p>}
      </section>
      <section className={card} data-testid="safety">
        <h2 className="font-semibold text-gold">Day lock-in, cooldowns, kill switch</h2>
        <p className="text-sm">Day lock-in: after <b className="text-gold">+{i.day_lockin_r}R</b> net in a day the next trade uses the floor %. Kill switch within <b className="text-gold">${i.kill_switch_mll_distance}</b> of the MLL; pause below ${i.pause_below_risk_base} risk base.</p>
        <div className="mt-2"><CooldownBanner /></div>
        <h3 className="mt-2 text-sm font-semibold text-gold">Kill log</h3>
        {kills.data?.logs.length === 0 && <p className="text-xs">Kill switch never used.</p>}
        {kills.data?.logs.map((l) => <p key={l.id} className="text-xs">{new Date(l.at).toLocaleString()} · {l.actor}</p>)}
      </section>
    </>
  );
}
