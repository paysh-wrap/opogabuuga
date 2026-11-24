import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import MoreInfo from "./MoreInfo";
import EvidenceBadge from "./EvidenceBadge";
import { AdvisorCardLine, type AdvisorResp } from "./AdvisorCard";
import LoadError from "./LoadError";
import AiAdviceCard from "./AiAdvice";
import { SaveAlert, useSaveAlert } from "./useSaveAlert";

// D55: strategy on/off buttons with the TESTED results next to each (static research facts from the server, not live
// data). Each click saves a new versioned My Settings entry (rollback on the Risk page).
export interface Strat {
  key: string; name: string; source: string; verified: boolean; status: string;
  win_pct: number | null; profit_factor: number | null; usd_per_trade: number | null; trades_per_week: number | null; held_out_trades: number;
  pro25k_pass_pct: number | null; pro25k_bust_pct: number | null; period: string; note: string;
  enabled: boolean; setting: string; badge?: string; // D165: gold evidence badge text (default: rules from one transcript)
  eval_odds?: OddsView; // D137: pass / bust from config/eval_odds.yaml for the active plan, size table and EOD toggle
  also?: string[]; // D58: settings switched ON together with this one (MAIN card: NOISE + fade)
  instruments?: string[]; paper_only?: boolean; flat_at?: string; // D96: Order Flow card (plan file)
  disabled?: boolean; off_for_now?: string; // D175: Iceberg proxy card greyed out, OFF for now
  ar_side_by_side?: ArSideBySide; // D160: AR Model beside NOISE + pre-session TradingAgents runs
  ar_layers?: { key: string; on: boolean; rule: string }[]; // D101: AR Model layers (plan file)
  amt_layers?: { key: string; on: boolean; rule: string }[]; // D110: AMT+ context / location / target layers
  zone_layers?: { key: string; on: boolean; rule: string }[]; // D111: ATR-zone type (iceberg PROXY)
  jj_rules?: { key: string; on: boolean; rule: string }[]; // JJ F.P.T STRAT: his rules with the plan's live numbers
  gala_rules?: { key: string; on: boolean; rule: string }[]; // D144 GALA PRICE ACTION: rule sheet + plan numbers
  strategy_rules?: { key: string; on: boolean; rule: string }[]; // D146+: rule-sheet strategies (CONTI, OKALA)
}
export interface ArRunResult { symbol: string; status: string; side?: string | null; rating?: string | null; prob_up?: number | null; prob_down?: number | null; reason?: string | null }
export interface ArSideBySide {
  setting: string; enabled: boolean; data_source: string; evidence: string; verified: boolean; advisor_mode: string; session: string;
  runs: { minutes_before: number; at: string; results: ArRunResult[] }[];
}
const runLabel = (m: number) => (m % 60 === 0 ? `${m / 60} h` : `${m} min`);
// D137: eval pass / bust of one (plan, size table, EOD toggle) cell — numbers null + text "not measured yet" until measured
export interface OddsView { plan: string; table: string; eod_on: boolean; text: string; pass_pct: number | null; bust_pct: number | null; last12_pass_pct: number | null; last12_bust_pct: number | null }
export interface Ledger {
  proxy: string; symbol: string; state: string; badge: string; required_accuracy: number; min_calls: number;
  stats: { n: number; hit_rate: number; brier: number; wilson_lb: number };
}
export interface StrategiesResp {
  strategies: Strat[];
  noise_warmup: { sessions: number; needed: number; ready: boolean };
  ai_ledger: Ledger[];
  markets: Record<string, boolean>;
  size_profiles?: SizeProfiles;
  presets?: PresetsResp;
  ai_duo_log?: DuoRow[];
  ta_mgc?: TaMgcResp;
  toggles?: ToggleRow[];
  advisor?: AdvisorResp; // D151
  notice?: string | null; combined?: Combined; ai_advice?: AiAdvice; // D175 / D176
}
// D132 / D133: two-way toggles (My Settings keys; each save is validated, versioned and audit-logged)
export interface DdOdds { pass: number; bust: number; j_pass: number; j_bust: number }
export interface DdRow { plan: string; eod: DdOdds; intraday: DdOdds }
/** Session 22: EOD-trailing vs intraday-trailing drawdown (config/eval_odds.yaml drawdown_types). */
export interface DrawdownCompare { current: DdRow | null; rows: DdRow[]; source: string | null; text: string }
export interface ToggleRow { key: string; setting: string; title: string; value: boolean; on_label: string; off_label: string; note: string; compare?: DrawdownCompare; weekly?: WeeklyTarget | null; late?: LateOption | null }
export interface LateOption { setting: string; value: boolean; label: string; detail: string; verified?: boolean; badge?: string | null } // label carries the API's held-out PF
export interface WeeklyTarget { target: string; median_days: string; needed_week: string; sim_week: string; measured: boolean; source: string }
export interface DuoRow { symbol?: string; day: string; status: string; code: string; direction: string; label: string | null; agrees_with_noise: boolean | null; mode?: string; below_preferred_2r?: boolean }
export interface TaMgcResp {
  enabled: boolean; connected: boolean; message: string | null;
  research: { day: string; label: string; setup: { side?: string; confidence?: number; entry_low?: number; entry_high?: number; invalidation?: number; target?: number; valid_until?: string; reasons?: string[] } | null; vt: { direction: string; confidence: number; reason: string } | null; vt_note: string; error: string; report: string } | null;
  decision: { day: string; status: string; code: string; direction: string; mode: string; below_preferred_2r: boolean } | null;
}
export interface PresetRow {
  key: string; label: string; summary: string; account: string; study: string; pass_pct: number | null; bust_pct: number | null; odds_text: string;
  held_out: boolean; recommended: boolean; superseded?: boolean; warning: string | null; fade: boolean; stop_usd: string | null;
  profit_lock: { trigger_pts: string; lock_pts: string } | null; size: SizeTierRow[]; matches_plan: boolean;
}
export interface PresetsResp { active: string | null; setting: string; plan_account_size: string; rows: PresetRow[] }
export interface SizeTierRow {
  account_size: string; contracts: number; brake_below: string | null; brake_contracts: number | null;
  taper_below_remaining?: string | null; taper_contracts?: number | null; stop_usd?: string | null;
}
export interface FpStep { cushion_usd: string; contracts: number }
export interface FastPassRow {
  key: string; account_size: string; on: boolean; noise_contracts: number; noise_stop_usd: string; noise_steps: FpStep[]; noise_grow_per: string | null;
  noise_max_contracts: number | null; noise_lock_trigger_pts: string | null; candace_contracts: number; candace_steps: FpStep[]; candace_grow_per: string | null;
  candace_max_contracts: number | null; brake_inclusive: boolean; day_lock_pct: string | null; late_contracts: number | null; late_steps: FpStep[]; late_on: boolean;
}
export interface Combined {
  key: string; title: string; enabled: boolean; setting: string; settings_on: string[]; eligible_accounts: number; min_accounts: number;
  can_start: boolean; blocked_reason: string | null; guards: string[];
}
export interface AiAdviceResult { symbol: string; status: string; side?: string | null; reason?: string | null; at?: string; advice?: { main?: string; order_flow?: string; all?: string } }
export interface AiAdvice { label: string; mode: string; session: string; runs: { minutes_before: number; at: string; results: AiAdviceResult[] }[] }
export interface SizeProfiles { fast_pass_plans?: FastPassRow[]; active: "regular" | "high"; setting: string; regular: SizeTierRow[]; high: SizeTierRow[]; eval_regular?: SizeTierRow[]; eval_high?: SizeTierRow[]; suggested?: SizeTierRow[]; suggested_on?: boolean; suggested_setting?: string; odds?: Record<string, OddsView> }

// D137: eval pass / bust text per size table comes from the server (config/eval_odds.yaml: active plan + EOD toggle)
const oddsText = (o?: OddsView) => o?.text ?? "not measured yet";
const k$ = (v: string) => `${Math.round(Number(v) / 1000)}K`;

const pct = (x: number | null) => (x == null ? "—" : `${x.toFixed(1)}%`);
const card = "rounded-xl border border-border bg-card p-4";
/** Pick-one-of-two cards (toggles, size tables): "ON/OFF ·" read like "turn on / turn off" (user, 2026-11-14: the EOD
 *  option marked OFF looked like it switched EOD off). The chosen option says IN USE, the other one says USE THIS. */
const pickLabel = (inUse: boolean) => (inUse ? "✓ IN USE" : "USE THIS");
/** Order-flow cards fold their study note together with their setup guide (one "More info" button per card). */
const noteInSetup = (s: Strat) =>
  s.key === "order_flow" || (s.key === "order_flow_amt" && !!s.amt_layers) || (s.key === "order_flow_zone" && !!s.zone_layers);

const planName = (stem: string) => { const [kind = "", size = ""] = stem.replace(/^lucid_/, "").split("_"); return `${kind.charAt(0).toUpperCase()}${kind.slice(1)} ${size.toUpperCase()}`; }; // lucid_pro_25k → Pro 25K
const pb = (o: DdOdds, j = false) => `${Math.round(j ? o.j_pass : o.pass)}/${Math.round(j ? o.j_bust : o.bust)}`;

/** Session 22: what the account's DRAWDOWN TYPE does to the eval odds (the toggle above only changes the kill switch). */
function DrawdownCompareView({ c }: { c: DrawdownCompare }) {
  return (
    <div className="mt-2 text-xs" data-testid="dd-compare">
      <p className="text-blue">
        <b className="text-gold">EOD vs intraday drawdown</b> (this plan, pass / bust):{" "}
        {c.current ? (
          <span data-testid="dd-compare-current">
            EOD trailing <b className="text-gold">{pb(c.current.eod)}</b> (last 12 mo {pb(c.current.eod, true)}) · intraday trailing{" "}
            <b className="text-gold">{pb(c.current.intraday)}</b> (last 12 mo {pb(c.current.intraday, true)})
          </span>
        ) : (
          <span>{c.text}</span>
        )}
      </p>
      {c.rows.length > 0 && (
        <MoreInfo label="All plans: EOD vs intraday" testId="more-dd-compare">
          <div className="overflow-x-auto">
          <table className="w-full" data-testid="dd-compare-table">
            <thead>
              <tr className="text-left text-gold"><th>Plan</th><th>EOD</th><th>Intra</th><th>EOD 1y</th><th>Intra 1y</th></tr>
            </thead>
            <tbody>
              {c.rows.map((r) => (
                <tr key={r.plan} className="border-t border-border">
                  <td className="py-0.5">{planName(r.plan)}</td><td className="text-gold">{pb(r.eod)}</td><td>{pb(r.intraday)}</td>
                  <td className="text-gold">{pb(r.eod, true)}</td><td>{pb(r.intraday, true)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
          <p className="mt-1 text-blue">Pass / bust %. 1y = the last 12 months. Same NOISE strategy and account simulator, regular size table, 2021-10 → 2026-10 (last 12 mo = 2025-11 → 2026-10). Intraday trailing raises the floor on open-profit highs that NOISE often gives back, so accounts run out of room. Past results do not guarantee future results. Source: {c.source}</p>
        </MoreInfo>
      )}
    </div>
  );
}

// D167: Strategy buttons are ONE-ON-AT-A-TIME (backend rejects two ON with 422). The main NOISE + CANDACE pair is ONE
// choice; late-day, fast-pass sizes, fade and order-flow layers are sub-options. Fast-pass plans stay independent.
export const choiceOf = (key: string): string | null =>
  ["noise", "candace_ict", "pm_fade"].includes(key) ? "main"
    : key.startsWith("order_flow") ? "order_flow"
    : key === "ai_bias" ? null : key;
const CHOICE_SETTINGS: Record<string, string[]> = {
  main: ["strategy.noise", "strategy.candace_ict"], order_flow: ["strategy.order_flow"],
};
const AR_SBS = "strategy.order_flow_cfg.ar_side_by_side"; // D175: the combined choice sets this ON; plain choices set it OFF
const MAIN_PAIR = ["noise", "candace_ict"];
const MAIN_SETTINGS = ["strategy.noise", "strategy.candace_ict"];
const settingsOfChoice = (c: string) => CHOICE_SETTINGS[c] ?? [`strategy.${c}`];
export const choiceTitle = (c: string) => (c === "main" ? "MAIN NOISE + CANDACE" : c === "order_flow" ? "Order Flow" : c === "ai_duo" ? "AI Duo" : c.replace(/_/g, " ").toUpperCase());

const usd = (v: string | number) => `$${Number(v).toLocaleString("en-US", { maximumFractionDigits: 0 })}`;
const stepsText = (steps: FpStep[], inclusive: boolean) => (steps.length ? steps.map((x) => `${inclusive ? "≤" : "<"} ${usd(x.cushion_usd)}: ${x.contracts}`).join(", ") : "no brake");

/** D175: the Fast Evaluation sizes per plan, read from the plan yamls by the API (nothing hard-coded here). */
function FastPassSizes({ rows }: { rows: FastPassRow[] }) {
  return (
    <div className="mt-2 rounded-lg border border-border p-3" data-testid="fast-pass-sizes">
      <h4 className="font-semibold text-gold">Fast Evaluation sizes (the main strategy)</h4>
      <p className="mt-1 text-xs text-blue" data-testid="fast-pass-stage-note">
        Applies to <b className="text-gold">EVAL accounts only</b>, of the plan's own size, while that plan's fast-pass switch is ON. FUNDED and LIVE accounts keep the Regular profile below; extending fast-pass sizing to them is a rules decision for the user and is NOT built. Every Lucid and Paytience check (daily loss limit, loss-limit room, consistency, news, flat times, hedge lock, one position per account, kill switch) still runs after the size and can only shrink or skip the trade.
      </p>
      <div className="mt-2 grid gap-2 md:grid-cols-2">
        {rows.map((r) => (
          <div key={r.key} className="rounded border border-border p-2 text-sm" data-testid={`fp-size-${r.key}`}>
            <b className="text-gold">{k$(r.account_size)}</b> · {r.on ? "switch ON" : "switch OFF"}
            <p className="text-xs text-blue">NOISE: <b className="text-gold">{r.noise_contracts}</b> micro{r.noise_contracts > 1 ? "s" : ""} at a <b className="text-gold">{usd(r.noise_stop_usd)}</b> stop per micro · cushion brake {stepsText(r.noise_steps, r.brake_inclusive)}
              {r.noise_grow_per && <> · grows +1 micro per {usd(r.noise_grow_per)} of cushion (max {r.noise_max_contracts})</>}
              {r.noise_lock_trigger_pts && <> · profit lock at {Number(r.noise_lock_trigger_pts)} pt</>}</p>
            <p className="text-xs text-blue">CANDACE: <b className="text-gold">{r.candace_contracts}</b> micro{r.candace_contracts > 1 ? "s" : ""} · cushion brake {stepsText(r.candace_steps, r.brake_inclusive)}
              {r.candace_grow_per && <> · grows +1 micro per {usd(r.candace_grow_per)} of cushion (max {r.candace_max_contracts})</>}</p>
            <p className="text-xs text-blue">{r.day_lock_pct ? `Day lock: no new NOISE entry once today's profit reaches ${Number(r.day_lock_pct) * 100}% of the target still to earn.` : "No day lock."} {r.late_contracts != null ? `Late-day option: ${r.late_contracts} micro(s) (cushion ${stepsText(r.late_steps, r.brake_inclusive)}), ${r.late_on ? "ON" : "OFF"}.` : "Late-day option: not available on this plan."}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function StrategyButtons() {
  const qc = useQueryClient();
  const [exNote, setExNote] = useState<{ key: string; text: string } | null>(null);
  const saved = useSaveAlert();
  const [lesserOpen, setLesserOpen] = useState(false);
  const q = useQuery({ queryKey: ["strategies"], queryFn: () => api<StrategiesResp>("/api/strategies"), refetchInterval: 30000 });
  const toggle = useMutation({
    mutationFn: async (s: Strat) => {
      const mine = choiceOf(s.key);
      const off: string[] = [];
      const offName = (c: string) => c === "main" ? "NOISE + CANDACE" : c === "order_flow" || c === "ai_duo" ? choiceTitle(c) : (q.data?.strategies ?? []).find((x) => x.enabled && choiceOf(x.key) === c)?.name.split(" — ")[0] ?? choiceTitle(c);
      let turnedOff: string[] = [];
      if (!s.enabled && mine) {
        const others = new Set((q.data?.strategies ?? []).filter((x) => x.enabled && choiceOf(x.key) && choiceOf(x.key) !== mine).map((x) => choiceOf(x.key)!));
        others.forEach((c) => off.push(...settingsOfChoice(c)));
        turnedOff = [...others].map((c) => offName(c));
      }
      const pair = !s.enabled && mine === "main" ? ["strategy.noise", "strategy.candace_ict"] : [];
      const on = s.enabled ? {} : Object.fromEntries([...(s.also ?? []).filter((k) => !mine || choiceOf(k.replace(/^strategy\./, "")) === mine), ...pair].map((k) => [k, true]));
      const mainOff = s.enabled && mine === "main" && MAIN_PAIR.includes(s.key) ? Object.fromEntries(MAIN_SETTINGS.map((k) => [k, false])) : {}; // one choice: never a half-on state
      const sbsOff = !s.enabled && mine === "order_flow" ? { [AR_SBS]: false } : {}; // plain Order Flow is never the combined choice
      const changes = { ...Object.fromEntries(off.filter((k) => k !== s.setting && !(k in on)).map((k) => [k, false])), [s.setting]: !s.enabled, ...on, ...mainOff, ...sbsOff };
      await api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes, note: `Strategy button: ${s.key} ${s.enabled ? "off" : "on"}` }) });
      return turnedOff; // D167 note: only after the server accepted the save
    },
    onSuccess: (turnedOff, s) => {
      saved.ok();
      setExNote(turnedOff.length ? { key: MAIN_PAIR.includes(s.key) ? "main" : s.key, text: `${MAIN_PAIR.includes(s.key) ? "NOISE + CANDACE" : s.name} is now the only strategy ON — turned off: ${turnedOff.join(", ")}.` } : null);
    },
    onError: (e, s) => { setExNote(null); saved.fail(s.name, e); },
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  const combo = useMutation({
    mutationFn: async (c: Combined) => {
      const changes: Record<string, boolean> = {};
      if (c.enabled) {
        for (const k of c.settings_on) changes[k] = false; // OFF: everything of the combined choice off (nothing left half-on)
      } else {
        // ON: turn every other strategy choice off (one choice at a time), then the 4 settings of the combined choice on
        for (const x of q.data?.strategies ?? []) {
          const ch = choiceOf(x.key);
          if (x.enabled && ch && ch !== "main" && ch !== "order_flow") changes[x.setting] = false;
        }
        for (const k of c.settings_on) changes[k] = true;
      }
      await api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes, note: `Combined choice: ${c.enabled ? "off" : "on"}` }) });
    },
    onSuccess: () => { saved.ok(); setExNote(null); },
    onError: (e) => saved.fail("MAIN FAST PASS + ORDER FLOW", e),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  const size = useMutation({
    mutationFn: (high: boolean) =>
      api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { "strategy.high_risk": high }, note: `Size profile: ${high ? "high risk" : "regular"}` }) }),
    onSuccess: () => saved.ok(),
    onError: (e) => saved.fail("Size profile", e),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  const suggest = useMutation({
    mutationFn: (on: boolean) =>
      api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { "strategy.suggested_size": on }, note: `NOISE size: ${on ? "suggested" : "as configured"}` }) }),
    onSuccess: () => saved.ok(),
    onError: (e) => saved.fail("NOISE size", e),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  const flip = useMutation({
    mutationFn: ({ t, v }: { t: ToggleRow; v: boolean }) =>
      api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { [t.setting]: v }, note: `${t.title}: ${v ? t.on_label : t.off_label}` }) }),
    onSuccess: () => saved.ok(),
    onError: (e) => saved.fail("Toggle", e),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  const lateFlip = useMutation({
    mutationFn: ({ late, v }: { late: LateOption; v: boolean }) =>
      api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { [late.setting]: v }, note: `${late.label}: ${v ? "on" : "off"}` }) }),
    onSuccess: () => saved.ok(),
    onError: (e) => saved.fail("Late-day option", e),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  const d = q.data;
  if (q.error && !d) return <LoadError what="strategies" error={q.error} onRetry={() => void q.refetch()} />;
  if (!d) return <p role="status">Loading strategies…</p>;
  const w = d.noise_warmup;
  const MAIN = ["noise", "candace_ict"];
  const isFlow = (k: string) => k.startsWith("order_flow");
  const mainS = MAIN.map((k) => d.strategies.find((s) => s.key === k)).filter((s): s is Strat => !!s);
  const flowS = d.strategies.filter((s) => isFlow(s.key));
  const mainOn = mainS.some((x) => x.enabled);
  const mainPartial = mainOn && mainS.some((x) => !x.enabled);
  // one choice: ON turns NOISE + CANDACE both ON (and the other choices off); OFF turns both OFF. A half-on state is re-set to both ON.
  const clickMain = () => {
    const noise = mainS.find((x) => x.key === "noise") ?? mainS[0];
    if (noise) toggle.mutate(mainOn && !mainPartial ? { ...noise, enabled: true } : { ...noise, enabled: false });
  };
  const lesserS = d.strategies.filter((s) => !MAIN.includes(s.key) && !isFlow(s.key));
  const lesserOn = lesserS.filter((x) => x.enabled).map((x) => x.name.split(" — ")[0] ?? x.name);
  const allToggles = d.toggles ?? [];
  const fastPass = allToggles.filter((t) => t.key.startsWith("fast_pass_"));
  const otherToggles = allToggles.filter((t) => !t.key.startsWith("fast_pass_"));
  const stratCard = (s: Strat, bare = false) => (
    <div key={s.key} className={`rounded-lg border p-3 ${s.disabled ? "border-dashed border-border grayscale" : "border-border"}`} aria-disabled={s.disabled || undefined} data-testid={`strategy-${s.key}`}>
      {s.disabled ? <button type="button" disabled aria-pressed={false} data-testid={`disabled-toggle-${s.key}`}
        className="w-full cursor-not-allowed rounded-md border border-border px-3 py-2 text-left font-semibold text-blueLight">
        {s.off_for_now ?? "OFF for now"} · {s.name} <span className="text-xs font-normal">(cannot be turned on)</span>
      </button> : bare ? <h4 className="font-semibold text-gold">{s.name}</h4> : <button
        type="button"
        aria-pressed={s.enabled}
        disabled={toggle.isPending}
        onClick={() => toggle.mutate(s)}
        className={`w-full rounded-md border px-3 py-2 text-left font-semibold ${s.enabled ? "toggle-on border-gold bg-gold/10 text-gold" : "toggle-off border-border text-blueLight"} disabled:opacity-50`}
      >
        {s.enabled ? "ON" : "OFF"} · {s.name}
      </button>}
      <p className="mt-2 text-xs"><EvidenceBadge verified={s.verified} text={s.verified ? s.badge ?? s.status : s.badge} testId={`evidence-${s.key}`} /> <span className="text-blue">{s.period}</span></p>
      <dl className="mt-2 grid grid-cols-2 gap-x-2 text-sm">
        <dt>Win rate</dt><dd className="text-gold" data-testid={`win-${s.key}`}>{pct(s.win_pct)}</dd>
        <dt>Eval pass</dt><dd className="text-gold" data-testid={`pass-${s.key}`}>{pct(s.pro25k_pass_pct)}</dd>
        <dt>Eval bust</dt><dd className="text-gold">{pct(s.pro25k_bust_pct)}</dd>
        <dt>Profit factor</dt><dd className="text-gold">{s.profit_factor == null ? "—" : s.profit_factor.toFixed(2)}</dd>
        <dt>Per trade (1 micro)</dt><dd className="text-gold">{s.usd_per_trade == null ? "— (not testable)" : `${s.usd_per_trade >= 0 ? "▲ +" : "▼ "}$${Math.abs(s.usd_per_trade).toFixed(2)}`}</dd>
        <dt>Trades / week</dt><dd className="text-gold">{s.trades_per_week == null ? "—" : s.trades_per_week.toFixed(1)}</dd>
      </dl>
      {s.eval_odds && <p className="mt-1 text-xs text-blue" data-testid={`odds-${s.key}`}>Eval odds: {s.eval_odds.text}</p>}
      {d.advisor && <AdvisorCardLine adv={d.advisor} cardKey={s.key} />}
      {!noteInSetup(s) && <MoreInfo testId={`more-${s.key}`}><p className="text-blue">{s.note}</p></MoreInfo>}
      {s.key === "order_flow" && (
        <div className="mt-2 text-xs" data-testid="order-flow-setup">
          <p className="text-blue" data-testid="order-flow-markets">Trades: <b className="text-gold">{(s.instruments ?? ["MNQ"]).join(" + ")}</b>{s.paper_only === true && " · PAPER accounts only (plan file)"}{s.flat_at && ` · flat ${s.flat_at} ET`} · 1 micro{s.instruments?.includes("MGC") && " · MGC (gold) is on for Order Flow only — every other strategy keeps it off"}</p>
          <MoreInfo label="More info + setup" testId={`more-${s.key}`}>
          <p className="text-blue">{s.note}</p>
          <p className="mt-1 text-blue">AR Model (D101): every layer must agree before the order-flow signal counts; stop beyond the absorption zone, 2R target. No real order-flow backtest exists.</p>
          {s.ar_layers && (
            <ol className="mt-1 list-decimal pl-4 text-blue" data-testid="order-flow-layers">
              {s.ar_layers.map((l) => <li key={l.key}><b className="text-gold">{l.key}</b> {l.on ? "" : "(OFF) "}— {l.rule}</li>)}
            </ol>
          )}
          <ol className="mt-1 list-decimal pl-4 text-blue">
            <li>TradingView: open a <b className="text-gold">1-minute {(s.instruments ?? ["MNQ"]).map((x) => `${x}1!`).join(" / ")}</b> chart (one alert per chart), add the Pine script <b className="text-gold">pine/Paytience_OrderFlow.pine</b> ("Paytience Order Flow").</li>
            <li>Paste the webhook secret (Connections page) into the indicator settings.</li>
            <li>Create an alert: Condition "Paytience Order Flow" → "Any alert() function call", once per bar close, Webhook URL = your Paytience URL /api/webhook/tradingview.</li>
            <li>Keep the Paytience_Bridge heartbeat alert on as well.</li>
          </ol>
          </MoreInfo>
        </div>
      )}
      {s.key === "order_flow" && s.ar_side_by_side && (
        <div className="mt-2 text-xs" data-testid="ar-sbs">
          <p className="text-blue" data-testid="ar-sbs-state">AR Model beside NOISE is now the separate choice <b className="text-gold">MAIN FAST PASS + ORDER FLOW (separate accounts)</b> above — {s.ar_side_by_side.enabled ? "it is set ON" : "it is OFF"}. Plain Order Flow and plain MAIN never run together.</p>
          <p className="mt-1 text-blue" data-testid="ar-sbs-source">Data: <b className="text-gold">{s.ar_side_by_side.data_source}</b> · bias runs {s.ar_side_by_side.runs.map((r) => `${runLabel(r.minutes_before)} before (${r.at} ET)`).join(", ")}</p>
          <ul className="mt-1 text-blue" data-testid="ar-sbs-runs">
            {s.ar_side_by_side.runs.map((r) => (
              <li key={r.minutes_before}>
                <b className="text-gold">{runLabel(r.minutes_before)}</b>:{" "}
                {r.results.map((x) => (
                  <span key={x.symbol} className="mr-2">
                    {x.symbol} {x.status === "OK" ? `${x.side} (${x.rating}) up ${Math.round((x.prob_up ?? 0) * 100)}% / down ${Math.round((x.prob_down ?? 0) * 100)}%` : x.status === "NO_CALL" ? `NO_CALL — ${x.reason ?? "no call"}` : "pending"}
                  </span>
                ))}
              </li>
            ))}
          </ul>
          <p className="mt-1 text-blue" data-testid="ar-sbs-evidence"><EvidenceBadge verified={s.ar_side_by_side.verified} /> {s.ar_side_by_side.evidence} TradingAgents bias is advice only and never blocks trading.</p>
        </div>
      )}
      {s.key === "order_flow_amt" && s.amt_layers && (
        <div className="mt-2 text-xs" data-testid="amt-setup">
          <MoreInfo testId={`more-${s.key}`}>
          <p className="text-blue">{s.note}</p>
          <p className="mt-1 text-blue">Top-down (D110): context first, location next, the order-flow signal LAST. Turning it on also turns Order Flow on; it only removes trades (codes OF_AMT_*).</p>
          <ol className="mt-1 list-decimal pl-4 text-blue" data-testid="amt-layers">
            {s.amt_layers.map((l) => <li key={l.key}><b className="text-gold">{l.key}</b> {l.on ? "" : "(OFF) "}— {l.rule}</li>)}
          </ol>
          </MoreInfo>
        </div>
      )}
      {s.key === "order_flow_zone" && s.zone_layers && (
        <div className="mt-2 text-xs" data-testid="zone-setup">
          <MoreInfo testId={`more-${s.key}`}>
          <p className="text-blue">{s.note}</p>
          <ol className="mt-1 list-decimal pl-4 text-blue" data-testid="zone-layers">
            {s.zone_layers.map((l) => <li key={l.key}><b className="text-gold">{l.key}</b> {l.on ? "" : "(OFF) "}— {l.rule}</li>)}
          </ol>
          </MoreInfo>
        </div>
      )}
      {s.strategy_rules && (
        <div className="mt-2 text-xs" data-testid={`${s.key}-setup`}>
          <MoreInfo label="Rules" testId={`more-${s.key}-rules`}>
          <ol className="mt-1 list-decimal pl-4 text-blue" data-testid={`${s.key}-rules`}>
            {s.strategy_rules.map((l) => <li key={l.key}><b className="text-gold">{l.key}</b> {l.on ? "" : "(OFF) "}— {l.rule}</li>)}
          </ol>
          <p className="mt-1 text-blue">* = not from the video. Every Lucid and Paytience safety check still applies (news, DLL, MLL, consistency, flat times, never hedge).</p>
          </MoreInfo>
        </div>
      )}
      {s.key === "gala_pa" && s.gala_rules && (
        <div className="mt-2 text-xs" data-testid="gala-setup">
          <MoreInfo label="Gala's rules" testId="more-gala-rules">
          <ol className="mt-1 list-decimal pl-4 text-blue" data-testid="gala-rules">
            {s.gala_rules.map((l) => <li key={l.key}><b className="text-gold">{l.key}</b> {l.on ? "" : "(OFF) "}— {l.rule}</li>)}
          </ol>
          <p className="mt-1 text-blue">Full rule sheet with video times: docs/GALA_RULES.md (* = not from the video). Every Lucid and Paytience safety check still applies (news, DLL, MLL, consistency, 1 position per account, never hedge).</p>
          </MoreInfo>
        </div>
      )}
      {s.key === "jj_fpt" && s.jj_rules && (
        <div className="mt-2 text-xs" data-testid="jj-setup">
          <MoreInfo label="JJ's rules" testId="more-jj-rules">
          <ol className="mt-1 list-decimal pl-4 text-blue" data-testid="jj-rules">
            {s.jj_rules.map((l) => <li key={l.key}><b className="text-gold">{l.key}</b> {l.on ? "" : "(OFF) "}— {l.rule}</li>)}
          </ol>
          <p className="mt-1 text-blue">Full rule sheet with video times: docs/JJ_FPT_RULES.md. Every Lucid and Paytience safety check still applies (news, DLL, MLL, consistency, 1 position per account, never hedge).</p>
          </MoreInfo>
        </div>
      )}
      {exNote?.key === s.key && !bare && <p className="mt-2 rounded border border-gold p-2 text-sm text-gold" role="status" data-testid="exclusive-note">{exNote.text}</p>}
      {s.key === "noise" && !w.ready && (
        <p className="mt-1 text-xs text-gold" data-testid="noise-warmup">Warm-up: {w.sessions}/{w.needed} sessions of TradingView 1-minute MNQ bars stored — NOISE starts trading after that.</p>
      )}
    </div>
  );
  const toggleCard = (t: ToggleRow) => (
    <div key={t.key} className="fp-card flex h-full flex-col rounded-lg border border-border p-3" data-testid={`toggle-${t.key}`}>
      <h3 className="flex flex-wrap items-center gap-2 font-semibold text-gold">{t.title}{t.note.includes("VERIFY") && <span className="rounded border border-gold px-1 text-xs" data-testid={`verify-${t.key}`}>VERIFY</span>}{t.weekly && !t.weekly.measured && <EvidenceBadge verified={false} text="not re-measured" testId={`weekly-unmeasured-${t.key}`} />}</h3>
      <p className="mt-1 text-xs text-blue">Applies to: {(t.key.match(/(\d+k)$/i)?.[1] ?? "").toUpperCase()} EVAL accounts only (never FUNDED/LIVE).</p>
      {t.weekly && (
        <div className="mt-2 text-xs text-blue" data-testid={`weekly-${t.key}`}>
          <p>Weekly target: <b className="text-gold">${Number(t.weekly.needed_week).toLocaleString("en-US", { maximumFractionDigits: 0 })}/week</b> to pass the ${Number(t.weekly.target).toLocaleString("en-US")} target in {t.weekly.median_days} days</p>
          <p>Simulated avg: <b className="text-gold">${Number(t.weekly.sim_week).toLocaleString("en-US", { maximumFractionDigits: 0 })}/week</b></p>
          {!t.weekly.measured && <p>Source: {t.weekly.source}</p>}
        </div>
      )}
      <div className="mt-2 grid gap-2">
        {([true, false] as const).map((v) => {
          const on = t.value === v;
          return (
            <button key={String(v)} type="button" aria-pressed={on} disabled={flip.isPending} onClick={() => !on && flip.mutate({ t, v })}
              data-testid={`toggle-${t.key}-${v ? "on" : "off"}`}
              className={`rounded-md border px-3 py-2 text-left text-sm font-semibold ${on ? "toggle-on pick-in-use border-gold bg-gold/10 text-gold" : "toggle-off border-border text-blueLight disabled:opacity-70"}`}>
              {(() => { const full = v ? t.on_label : t.off_label; const m = full.length > 60 ? full.match(/^([^(]*?)\s*\((.*)\)\s*$/) : null; return <>{pickLabel(on)} · {m ? m[1] : full}{m && <details className="mt-1 text-xs font-normal" onClick={(e) => e.stopPropagation()}><summary className="cursor-pointer">Formula</summary>{m[2]}</details>}</>; })()}
            </button>
          );
        })}
      </div>
      {t.late && (
        <div className="mt-3 border-t border-border pt-2 text-xs" data-testid={`late-${t.key}`}>
          <span className="mr-2"><EvidenceBadge verified={t.late.verified === true} text={t.late.badge} testId={`late-badge-${t.key}`} /></span>
          <button type="button" aria-pressed={t.late.value} disabled={flip.isPending} data-testid={`late-toggle-${t.key}`}
            onClick={() => lateFlip.mutate({ late: t.late!, v: !t.late!.value })}
            className={`rounded-md border px-2 py-1 text-left font-semibold ${t.late.value ? "toggle-on pick-in-use border-gold bg-gold/10 text-gold" : "toggle-off border-border text-blueLight"}`}>
            {t.late.value ? "✓ ON" : "OFF"} · {t.late.label}
          </button>
          <p className="mt-1 text-blue">{t.late.detail}</p>
        </div>
      )}
      {t.compare && <DrawdownCompareView c={t.compare} />}
      <div className="mt-auto pt-2"><MoreInfo testId={`more-toggle-${t.key}`}><p className="text-blue">{t.note}</p></MoreInfo></div>
    </div>
  );
  return (
    <section className={card} data-testid="strategy-buttons">
      <h2 className="font-semibold text-gold">Strategies — tap to turn on/off</h2>
      <MoreInfo label="How these numbers were measured" testId="strategy-method">
        <p className="text-blue">Results are from the study on real MNQ data (2019-05 → 2026-11, NOISE with the profit lock and Mondays off, 1 micro, costs included; AI / Order Flow cards: their own notes). Eval pass / bust = share of simulated evaluations that passed / busted for your active plan, size table and EOD toggle (\"not measured yet\" until the study is run). Past results do not guarantee future results.</p>
      </MoreInfo>
      <SaveAlert error={saved.error} />
      {d.notice && <p role="alert" className="mt-2 rounded border border-gold p-2 text-sm text-gold" data-testid="strategy-notice">⚠ {d.notice}</p>}
      <p className="mt-2 text-xs text-blue" data-testid="exclusive-hint">Only one strategy button can be ON at a time — turning one on turns the others off. The one exception is the separate option MAIN FAST PASS + ORDER FLOW (separate accounts). The fast-pass plans below are independent of each other.</p>
      <div className="mt-2"><AiAdviceCard advice={d.ai_advice} /></div>
      <div className="mt-3 space-y-4">
        <div data-testid="strategy-main-group">
          <h3 className="text-lg font-bold text-gold">MAIN strategy — NOISE + CANDACE</h3>
          <div role="radiogroup" aria-label="Main strategy choice" className="mt-2" data-testid="strategy-main-choice">
            <button
              type="button"
              role="radio"
              aria-checked={mainOn}
              disabled={toggle.isPending || mainS.length === 0}
              onClick={() => clickMain()}
              data-testid="main-choice-radio"
              className={`w-full rounded-md border px-3 py-2 text-left font-semibold ${mainOn ? "toggle-on pick-in-use border-gold bg-gold/10 text-gold" : "toggle-off border-border text-blueLight"} disabled:opacity-50`}
            >
              {mainOn ? "✓ ON" : "OFF"} · NOISE + CANDACE <span className="text-xs font-normal">(one choice — both run together)</span>
            </button>
            {mainPartial && (
              <p className="mt-1 text-xs text-goldLight" data-testid="main-choice-partial">
                {mainS.filter((x) => !x.enabled).map((x) => x.key === "candace_ict" ? "CANDACE" : "NOISE").join(" + ")} is off in your settings. Press the button above to run both.
              </p>
            )}
            <p className="mt-1 text-xs text-blue" data-testid="main-choice-hint">Only one choice can be ON at a time: turning this on turns off every other strategy below; turning it off turns off NOISE and CANDACE together.</p>
            {exNote?.key === "main" && <p className="mt-2 rounded border border-gold p-2 text-sm text-gold" role="status" data-testid="exclusive-note">{exNote.text}</p>}
            <div className="mt-2 grid gap-3 lg:grid-cols-3">{mainS.map((s) => stratCard(s, true))}</div>
          </div>
          {fastPass.length > 0 && (
            <div className="mt-3" data-testid="strategy-fast-pass">
              <h4 className="font-semibold text-gold">NOISE fast-pass sizes (evaluations)</h4>
              <WeeklyCalculator toggles={fastPass} />
              <div className="mt-2 grid gap-3 md:grid-cols-2">{fastPass.map(toggleCard)}</div>
            </div>
          )}
        </div>
        {d.combined && (
          <div className="rounded-lg border border-border p-3" data-testid="combined-choice">
            <h3 className="flex flex-wrap items-center gap-2 text-lg font-bold text-gold">OPTION — {d.combined.title} <EvidenceBadge verified={false} text="OPTION · default OFF · UNVERIFIED" testId="combined-badge" /></h3>
            <button type="button" aria-pressed={d.combined.enabled} data-testid="combined-toggle"
              disabled={combo.isPending || (!d.combined.enabled && !d.combined.can_start)}
              onClick={() => combo.mutate(d.combined!)}
              className={`mt-2 w-full rounded-md border px-3 py-2 text-left font-semibold ${d.combined.enabled ? "toggle-on pick-in-use border-gold bg-gold/10 text-gold" : "toggle-off border-border text-blueLight"} disabled:opacity-50`}>
              {d.combined.enabled ? "✓ ON" : "OFF"} · {d.combined.title}
            </button>
            {!d.combined.can_start && !d.combined.enabled && (
              <p role="alert" className="mt-1 text-sm text-gold" data-testid="combined-blocked">Cannot start: {d.combined.blocked_reason}. Nothing else will run instead.</p>
            )}
            <p className="mt-1 text-xs text-blue" data-testid="combined-accounts">Eligible accounts: <b className="text-gold">{d.combined.eligible_accounts}</b> (needs {d.combined.min_accounts}+).</p>
            <ul className="mt-1 list-disc pl-4 text-xs text-blue" data-testid="combined-guards">{d.combined.guards.map((g) => <li key={g}>{g}</li>)}</ul>
          </div>
        )}
        <div data-testid="strategy-order-flow-group">
          <h3 className="text-lg font-bold text-gold">SECONDARY strategy — ORDER FLOW (AR Model + options, UNVERIFIED)</h3>
          <div className="mt-2 grid gap-3 lg:grid-cols-3">{flowS.map((s) => stratCard(s))}</div>
        </div>
        <details className="rounded-lg border border-border p-3" data-testid="lesser-strategies" onToggle={(e) => setLesserOpen((e.currentTarget as HTMLDetailsElement).open)}>
          <summary className="more-info-btn inline-flex cursor-pointer select-none items-center gap-1 rounded-md border border-blue px-2 py-0.5 font-semibold text-blue" data-testid="lesser-summary">Lesser strategies ({lesserS.length}) · {lesserOn.length ? `${lesserOn.join(", ")} ON` : "none ON"}</summary>
          <p className="mt-2 text-xs text-blue" data-testid="lesser-hint">Only one choice can be ON at a time: turning one of these on turns off the MAIN choice and every other strategy.</p>
          <div className="mt-3 grid gap-3 lg:grid-cols-3">{lesserS.map((s) => stratCard(s))}</div>
        </details>
        {!lesserOpen && exNote && lesserS.some((x) => x.key === exNote.key) && (
          <p className="rounded border border-gold p-2 text-sm text-gold" role="status" data-testid="exclusive-note-closed">{exNote.text}</p>
        )}
      </div>
      {otherToggles.length > 0 && (
        <div className="mt-4 grid gap-3 lg:grid-cols-3" data-testid="strategy-toggles">
          {otherToggles.map(toggleCard)}
        </div>
      )}
      {d.size_profiles && (
        <div className="mt-4" data-testid="size-profiles">
          {d.size_profiles.suggested && d.size_profiles.suggested.length > 0 && (
            <div className="mb-3 rounded-lg border border-border p-3" data-testid="noise-size-toggle">
              <h3 className="font-semibold text-gold">NOISE contract size — 50K: 1 or 2 micros</h3>
              <div className="mt-2 grid gap-2 sm:grid-cols-2">
                {([false, true] as const).map((v) => {
                  const on = !!d.size_profiles!.suggested_on === v;
                  return (
                    <button key={String(v)} type="button" aria-pressed={on} disabled={suggest.isPending} onClick={() => !on && suggest.mutate(v)}
                      data-testid={v ? "noise-size-suggested" : "noise-size-configured"}
                      className={`rounded-md border px-3 py-2 text-left font-semibold ${on ? "toggle-on pick-in-use border-gold bg-gold/10 text-gold" : "toggle-off border-border text-blueLight disabled:opacity-70"}`}>
                      {pickLabel(on)} · {v ? "Suggested — 50K 1 micro (lowest bust)" : "As configured — 50K 2 micros (how it is)"}
                    </button>
                  );
                })}
              </div>
              <p className="mt-2 text-sm">Suggested: {d.size_profiles.suggested.map((t) => <span key={t.account_size} className="mr-2">{k$(t.account_size)} <b className="text-gold">{t.contracts}</b></span>)}</p>
              <MoreInfo testId="more-noise-size"><p className="text-blue">Only the 50K size differs (25K 1 · 100K 2 · 150K 3 in both). Eval pass / bust (this plan): Suggested table {oddsText(d.size_profiles.odds?.suggested)}; Regular table {oddsText(d.size_profiles.odds?.regular)}. As configured = the Regular / High-risk table below. Every safety check still applies either way.</p></MoreInfo>
            </div>
          )}
          <h3 className="font-semibold text-gold">Size per account (automatic by account size, drawdown brake always on)</h3>
          {d.size_profiles.fast_pass_plans && d.size_profiles.fast_pass_plans.length > 0 && <FastPassSizes rows={d.size_profiles.fast_pass_plans} />}
          <h4 className="mt-3 font-semibold text-gold" data-testid="size-fallback-title">Fallback profile: Regular / High risk</h4>
          <p className="text-xs text-blue" data-testid="size-fallback-note">Used for every account that is NOT on a fast-pass plan above: FUNDED and LIVE accounts, EVAL accounts of another size, and any plan whose fast-pass switch is OFF.</p>
          <div className="mt-2 grid gap-3 lg:grid-cols-2">
            {(["regular", "high"] as const).map((p) => {
              const on = d.size_profiles!.active === p;
              return (
                <div key={p} className="rounded-lg border border-border p-3">
                  <button type="button" aria-pressed={on} disabled={size.isPending} onClick={() => !on && size.mutate(p === "high")}
                    className={`w-full rounded-md border px-3 py-2 text-left font-semibold ${on ? "toggle-on pick-in-use border-gold bg-gold/10 text-gold" : "toggle-off border-border text-blueLight disabled:opacity-70"}`}>
                    {pickLabel(on)} · {p === "high" ? "High risk" : "Regular"}
                  </button>
                  <ul className="mt-2 text-sm" data-testid={`size-${p}`}>
                    {d.size_profiles![p].map((t) => (
                      <li key={t.account_size}>{k$(t.account_size)}: <b className="text-gold">{t.contracts} micro{t.contracts > 1 ? "s" : ""}</b>
                        {t.brake_below && <> → {t.brake_contracts} when cushion &lt; {Math.round(Number(t.brake_below) * 100)}% of loss limit</>}</li>
                    ))}
                  </ul>
                  <p className="mt-1 text-xs text-blue">Eval pass / bust (this plan): {oddsText(d.size_profiles!.odds?.[p])}</p>
                  {(p === "high" ? d.size_profiles!.eval_high : d.size_profiles!.eval_regular)?.length ? (
                    <p className="mt-1 text-xs" data-testid={`eval-size-${p}`}>
                      <b className="text-gold">Evaluations</b> (EVAL accounts, Evaluation Mode on):{" "}
                      {(p === "high" ? d.size_profiles!.eval_high : d.size_profiles!.eval_regular)!.map((t) => (
                        <span key={t.account_size} className="mr-2">{k$(t.account_size)} {t.contracts}{t.stop_usd ? ` × $${Math.round(Number(t.stop_usd))} stop` : ""}{t.taper_below_remaining ? ` → ${t.taper_contracts} once < ${Math.round(Number(t.taper_below_remaining) * 100)}% of the target is left` : ""}</span>
                      ))}
                    </p>
                  ) : null}
                </div>
              );
            })}
          </div>
          <p className="mt-1 text-xs text-blue" data-testid="size-stop-note">NOISE keeps its hourly band/VWAP trailing exit and profit lock in every profile. The emergency stop per micro is the plan's own stop in the Regular / High risk profiles and the stop shown in the fast-pass table above for fast-pass EVAL accounts.</p>
        </div>
      )}
      {d.ai_duo_log && d.ai_duo_log.length > 0 && (
        <div className="mt-3 text-sm" data-testid="duo-log">
          <b className="text-gold">AI Duo decisions — one per day, with the reason code:</b>
          <ul className="text-blue">
            {d.ai_duo_log.map((r) => (
              <li key={`${r.symbol}${r.day}`}>{r.day}{r.symbol ? ` ${r.symbol}` : ""}: <b className="text-gold">{r.status === "PASS" ? `TRADE ${r.direction}` : "NO TRADE"}</b> · {r.code} · {r.mode === "RESEARCH" ? "TradingAgents research setup" : `AI call ${r.label || "none"}`}{r.below_preferred_2r ? " · below preferred 2R" : ""}{r.agrees_with_noise != null && (r.agrees_with_noise ? " · same side as NOISE" : "")}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-3 text-sm" data-testid="ai-ledger">
        <b className="text-gold">AI daily call (TradingAgents + Vibe-Trading) — scored every session:</b>
        {d.ai_ledger.map((l) => (
          <p key={l.proxy} className="text-blue">
            {l.symbol} ← {l.proxy}: <b className="text-gold">{l.badge}</b> · {l.stats.n} scored calls
            {l.stats.n > 0 && ` · hit rate ${(l.stats.hit_rate * 100).toFixed(0)}% · Brier ${l.stats.brier.toFixed(2)}`} · advice only, never blocks trading (a record of {l.min_calls}+ calls ≥ {(l.required_accuracy * 100).toFixed(0)}% is just shown)
          </p>
        ))}
      </div>
      {d.markets.MGC === false && <p className="mt-2 text-xs text-blue">MGC (gold) is off — every gold strategy failed the 2019–2026 test{d.strategies.some((x) => x.key === "order_flow" && x.instruments?.includes("MGC")) && " (exception: Order Flow, D96)"}.</p>}
    </section>
  );
}

const COUNTS_KEY = "paytience.weekly_counts";
const usd0 = (n: number) => `$${n.toLocaleString("en-US", { maximumFractionDigits: 0 })}`;

/** D164: accounts per plan (0-20, default 1 each, remembered per viewer) x the API's per-account weekly figures. */
export function WeeklyCalculator({ toggles }: { toggles: ToggleRow[] }) {
  const rows = toggles.filter((t) => t.weekly);
  const [counts, setCounts] = useState<Record<string, number>>(() => {
    try {
      const raw = JSON.parse(localStorage.getItem(COUNTS_KEY) ?? "{}");
      return raw && typeof raw === "object" ? raw : {};
    } catch {
      return {};
    }
  });
  if (rows.length === 0) return null;
  const n = (k: string) => Math.min(20, Math.max(0, Math.trunc(Number.isFinite(counts[k]) ? (counts[k] as number) : 1)));
  const set = (k: string, v: string) => {
    const next = { ...counts, [k]: Math.min(20, Math.max(0, Math.trunc(Number(v) || 0))) };
    setCounts(next);
    try {
      localStorage.setItem(COUNTS_KEY, JSON.stringify(next));
    } catch {
      /* storage blocked: keep in memory only */
    }
  };
  const need = rows.reduce((a, t) => a + n(t.key) * Number(t.weekly!.needed_week), 0);
  const sim = rows.reduce((a, t) => a + n(t.key) * Number(t.weekly!.sim_week), 0);
  return (
    <div className="mt-2 rounded-lg border border-border p-3 text-sm text-blue" data-testid="weekly-calc">
      <h5 className="font-semibold text-gold">Weekly target calculator</h5>
      <div className="overflow-x-auto"><table className="mt-1 w-full min-w-[20rem] text-left text-xs">
        <thead><tr><th>Plan</th><th>Accounts</th><th>Need / wk</th><th>Sim / wk</th></tr></thead>
        <tbody>
          {rows.map((t) => (
            <tr key={t.key} data-testid={`calc-row-${t.key}`}>
              <td>{t.title.split(" ")[0]}</td>
              <td><input type="number" min={0} max={20} value={n(t.key)} aria-label={`${t.title} accounts`} data-testid={`calc-count-${t.key}`} onChange={(e) => set(t.key, e.target.value)} className="w-16 rounded border border-border bg-transparent px-1 text-gold" /></td>
              <td className="text-gold">{usd0(n(t.key) * Number(t.weekly!.needed_week))}</td>
              <td className="text-gold">{usd0(n(t.key) * Number(t.weekly!.sim_week))}</td>
            </tr>
          ))}
        </tbody>
        <tfoot><tr data-testid="calc-total"><th>Total</th><th /><th className="text-gold">{usd0(need)}</th><th className="text-gold">{usd0(sim)}</th></tr></tfoot>
      </table></div>
      <p className="mt-1 text-xs">Backtest estimate; accounts trade the same signals so they win and lose together.</p>
    </div>
  );
}
