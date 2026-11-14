import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { badge } from "../lib/theme";
import MoreInfo from "./MoreInfo";

// D55: strategy on/off buttons with the TESTED results next to each (static research facts from the server, not live
// data). Each click saves a new versioned My Settings entry (rollback on the Risk page).
export interface Strat {
  key: string; name: string; source: string; verified: boolean; status: string;
  win_pct: number | null; profit_factor: number | null; usd_per_trade: number | null; trades_per_week: number | null; held_out_trades: number;
  pro25k_pass_pct: number | null; pro25k_bust_pct: number | null; period: string; note: string;
  enabled: boolean; setting: string;
  eval_odds?: OddsView; // D137: pass / bust from config/eval_odds.yaml for the active plan, size table and EOD toggle
  also?: string[]; // D58: settings switched ON together with this one (MAIN card: NOISE + fade)
  instruments?: string[]; paper_only?: boolean; flat_at?: string; // D96: Order Flow card (plan file)
  ar_layers?: { key: string; on: boolean; rule: string }[]; // D101: AR Model layers (plan file)
  amt_layers?: { key: string; on: boolean; rule: string }[]; // D110: AMT+ context / location / target layers
  zone_layers?: { key: string; on: boolean; rule: string }[]; // D111: ATR-zone type (iceberg PROXY)
}
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
}
// D132 / D133: two-way toggles (My Settings keys; each save is validated, versioned and audit-logged)
export interface DdOdds { pass: number; bust: number; j_pass: number; j_bust: number }
export interface DdRow { plan: string; eod: DdOdds; intraday: DdOdds }
/** Session 22: EOD-trailing vs intraday-trailing drawdown (config/eval_odds.yaml drawdown_types). */
export interface DrawdownCompare { current: DdRow | null; rows: DdRow[]; source: string | null; text: string }
export interface ToggleRow { key: string; setting: string; title: string; value: boolean; on_label: string; off_label: string; note: string; compare?: DrawdownCompare }
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
export interface SizeProfiles { active: "regular" | "high"; setting: string; regular: SizeTierRow[]; high: SizeTierRow[]; eval_regular?: SizeTierRow[]; eval_high?: SizeTierRow[]; suggested?: SizeTierRow[]; suggested_on?: boolean; suggested_setting?: string; odds?: Record<string, OddsView> }

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

export default function StrategyButtons() {
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ["strategies"], queryFn: () => api<StrategiesResp>("/api/strategies"), refetchInterval: 30000 });
  const toggle = useMutation({
    mutationFn: (s: Strat) =>
      api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { [s.setting]: !s.enabled, ...(s.enabled ? {} : Object.fromEntries((s.also ?? []).map((k) => [k, true]))) }, note: `Strategy button: ${s.key} ${s.enabled ? "off" : "on"}` }) }),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  const size = useMutation({
    mutationFn: (high: boolean) =>
      api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { "strategy.high_risk": high }, note: `Size profile: ${high ? "high risk" : "regular"}` }) }),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  const suggest = useMutation({
    mutationFn: (on: boolean) =>
      api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { "strategy.suggested_size": on }, note: `NOISE size: ${on ? "suggested" : "as configured"}` }) }),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  const flip = useMutation({
    mutationFn: ({ t, v }: { t: ToggleRow; v: boolean }) =>
      api("/api/risk/settings", { method: "PUT", body: JSON.stringify({ changes: { [t.setting]: v }, note: `${t.title}: ${v ? t.on_label : t.off_label}` }) }),
    onSettled: () => void qc.invalidateQueries({ queryKey: ["strategies"] }),
  });
  const d = q.data;
  if (!d) return <p role="status">Loading strategies…</p>;
  const w = d.noise_warmup;
  return (
    <section className={card} data-testid="strategy-buttons">
      <h2 className="font-semibold text-gold">Strategies — tap to turn on/off</h2>
      <MoreInfo label="How these numbers were measured" testId="strategy-method">
        <p className="text-blue">Results are from the study on real MNQ data (2019-05 → 2026-11, NOISE with the profit lock and Mondays off, 1 micro, costs included; AI / Order Flow cards: their own notes). Eval pass / bust = share of simulated evaluations that passed / busted for your active plan, size table and EOD toggle (\"not measured yet\" until the study is run). Past results do not guarantee future results.</p>
      </MoreInfo>
      <div className="mt-3 grid gap-3 lg:grid-cols-3">
        {d.strategies.map((s) => (
          <div key={s.key} className="rounded-lg border border-border p-3" data-testid={`strategy-${s.key}`}>
            <button
              type="button"
              aria-pressed={s.enabled}
              disabled={toggle.isPending}
              onClick={() => toggle.mutate(s)}
              className={`w-full rounded-md border px-3 py-2 text-left font-semibold ${s.enabled ? "border-gold text-gold" : "border-blue text-blue"} disabled:opacity-50`}
            >
              {s.enabled ? "ON" : "OFF"} · {s.name}
            </button>
            <p className="mt-2 text-xs"><span aria-hidden style={{ color: s.verified ? badge.ok : badge.bad }}>●</span> <b className="text-gold">{s.status}</b> <span className="text-blue">{s.period}</span></p>
            <dl className="mt-2 grid grid-cols-2 gap-x-2 text-sm">
              <dt>Win rate</dt><dd className="text-gold" data-testid={`win-${s.key}`}>{pct(s.win_pct)}</dd>
              <dt>Eval pass</dt><dd className="text-gold" data-testid={`pass-${s.key}`}>{pct(s.pro25k_pass_pct)}</dd>
              <dt>Eval bust</dt><dd className="text-gold">{pct(s.pro25k_bust_pct)}</dd>
              <dt>Profit factor</dt><dd className="text-gold">{s.profit_factor == null ? "—" : s.profit_factor.toFixed(2)}</dd>
              <dt>Per trade (1 micro)</dt><dd className="text-gold">{s.usd_per_trade == null ? "— (not testable)" : `${s.usd_per_trade >= 0 ? "▲ +" : "▼ "}$${Math.abs(s.usd_per_trade).toFixed(2)}`}</dd>
              <dt>Trades / week</dt><dd className="text-gold">{s.trades_per_week == null ? "—" : s.trades_per_week.toFixed(1)}</dd>
            </dl>
            {s.eval_odds && <p className="mt-1 text-xs text-blue" data-testid={`odds-${s.key}`}>Eval odds: {s.eval_odds.text}</p>}
            {!noteInSetup(s) && <MoreInfo testId={`more-${s.key}`}><p className="text-blue">{s.note}</p></MoreInfo>}
            {s.key === "order_flow" && (
              <div className="mt-2 text-xs" data-testid="order-flow-setup">
                <span className="rounded border border-gold px-1 font-semibold text-gold" data-testid="order-flow-badge">UNVERIFIED</span>
                <p className="mt-1 text-blue" data-testid="order-flow-markets">Trades: <b className="text-gold">{(s.instruments ?? ["MNQ"]).join(" + ")}</b>{s.paper_only === true && " · PAPER accounts only (plan file)"}{s.flat_at && ` · flat ${s.flat_at} ET`} · 1 micro{s.instruments?.includes("MGC") && " · MGC (gold) is on for Order Flow only — every other strategy keeps it off"}</p>
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
            {s.key === "order_flow_amt" && s.amt_layers && (
              <div className="mt-2 text-xs" data-testid="amt-setup">
                <span className="rounded border border-gold px-1 font-semibold text-gold">UNVERIFIED</span>
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
                <span className="rounded border border-gold px-1 font-semibold text-gold">UNVERIFIED · iceberg PROXY (no MBO data)</span>
                <MoreInfo testId={`more-${s.key}`}>
                <p className="text-blue">{s.note}</p>
                <ol className="mt-1 list-decimal pl-4 text-blue" data-testid="zone-layers">
                  {s.zone_layers.map((l) => <li key={l.key}><b className="text-gold">{l.key}</b> {l.on ? "" : "(OFF) "}— {l.rule}</li>)}
                </ol>
                </MoreInfo>
              </div>
            )}
            {s.key === "noise" && !w.ready && (
              <p className="mt-1 text-xs text-gold" data-testid="noise-warmup">Warm-up: {w.sessions}/{w.needed} sessions of TradingView 1-minute MNQ bars stored — NOISE starts trading after that.</p>
            )}
          </div>
        ))}
      </div>
      {d.toggles && d.toggles.length > 0 && (
        <div className="mt-4 grid gap-3 lg:grid-cols-3" data-testid="strategy-toggles">
          {d.toggles.map((t) => (
            <div key={t.key} className="rounded-lg border border-border p-3" data-testid={`toggle-${t.key}`}>
              <h3 className="font-semibold text-gold">{t.title}{t.note.includes("VERIFY") && <span className="ml-2 rounded border border-gold px-1 text-xs" data-testid={`verify-${t.key}`}>VERIFY</span>}</h3>
              <div className="mt-2 grid gap-2">
                {([true, false] as const).map((v) => {
                  const on = t.value === v;
                  return (
                    <button key={String(v)} type="button" aria-pressed={on} disabled={flip.isPending} onClick={() => !on && flip.mutate({ t, v })}
                      data-testid={`toggle-${t.key}-${v ? "on" : "off"}`}
                      className={`rounded-md border px-3 py-2 text-left text-sm font-semibold ${on ? "pick-in-use border-gold bg-gold/10 text-gold" : "border-blue text-blue disabled:opacity-70"}`}>
                      {pickLabel(on)} · {v ? t.on_label : t.off_label}
                    </button>
                  );
                })}
              </div>
              {t.compare && <DrawdownCompareView c={t.compare} />}
              <MoreInfo testId={`more-toggle-${t.key}`}><p className="text-blue">{t.note}</p></MoreInfo>
            </div>
          ))}
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
                      className={`rounded-md border px-3 py-2 text-left font-semibold ${on ? "pick-in-use border-gold bg-gold/10 text-gold" : "border-blue text-blue disabled:opacity-70"}`}>
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
          <div className="mt-2 grid gap-3 lg:grid-cols-2">
            {(["regular", "high"] as const).map((p) => {
              const on = d.size_profiles!.active === p;
              return (
                <div key={p} className="rounded-lg border border-border p-3">
                  <button type="button" aria-pressed={on} disabled={size.isPending} onClick={() => !on && size.mutate(p === "high")}
                    className={`w-full rounded-md border px-3 py-2 text-left font-semibold ${on ? "pick-in-use border-gold bg-gold/10 text-gold" : "border-blue text-blue disabled:opacity-70"}`}>
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
          <p className="mt-1 text-xs text-blue">NOISE keeps its hourly band/VWAP trailing exit, profit lock and $250-per-micro emergency stop in both profiles.</p>
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
            {l.stats.n > 0 && ` · hit rate ${(l.stats.hit_rate * 100).toFixed(0)}% · Brier ${l.stats.brier.toFixed(2)}`} · may block only after {l.min_calls}+ calls proven ≥ {(l.required_accuracy * 100).toFixed(0)}%
          </p>
        ))}
      </div>
      {d.markets.MGC === false && <p className="mt-2 text-xs text-blue">MGC (gold) is off — every gold strategy failed the 2019–2026 test{d.strategies.some((x) => x.key === "order_flow" && x.instruments?.includes("MGC")) && " (exception: Order Flow, D96)"}.</p>}
    </section>
  );
}
