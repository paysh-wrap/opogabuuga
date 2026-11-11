import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { badge } from "../lib/theme";

// D55: strategy on/off buttons with the TESTED results next to each (static research facts from the server, not live
// data). Each click saves a new versioned My Settings entry (rollback on the Risk page).
export interface Strat {
  key: string; name: string; source: string; verified: boolean; status: string;
  win_pct: number | null; profit_factor: number | null; usd_per_trade: number | null; trades_per_week: number | null; held_out_trades: number;
  pro25k_pass_pct: number | null; pro25k_bust_pct: number | null; period: string; note: string;
  enabled: boolean; setting: string;
  also?: string[]; // D58: settings switched ON together with this one (MAIN card: NOISE + fade)
  instruments?: string[]; paper_only?: boolean; flat_at?: string; // D96: Order Flow card (plan file)
  ar_layers?: { key: string; on: boolean; rule: string }[]; // D101: AR Model layers (plan file)
}
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
}
export interface DuoRow { symbol?: string; day: string; status: string; code: string; direction: string; label: string | null; agrees_with_noise: boolean | null; mode?: string; below_preferred_2r?: boolean }
export interface TaMgcResp {
  enabled: boolean; connected: boolean; message: string | null;
  research: { day: string; label: string; setup: { side?: string; confidence?: number; entry_low?: number; entry_high?: number; invalidation?: number; target?: number; valid_until?: string; reasons?: string[] } | null; vt: { direction: string; confidence: number; reason: string } | null; vt_note: string; error: string; report: string } | null;
  decision: { day: string; status: string; code: string; direction: string; mode: string; below_preferred_2r: boolean } | null;
}
export interface PresetRow {
  key: string; label: string; summary: string; account: string; study: string; pass_pct: number; bust_pct: number;
  held_out: boolean; recommended: boolean; warning: string | null; fade: boolean; stop_usd: string | null;
  profit_lock: { trigger_pts: string; lock_pts: string } | null; size: SizeTierRow[]; matches_plan: boolean;
}
export interface PresetsResp { active: string | null; setting: string; plan_account_size: string; rows: PresetRow[] }
export interface SizeTierRow {
  account_size: string; contracts: number; brake_below: string | null; brake_contracts: number | null;
  taper_below_remaining?: string | null; taper_contracts?: number | null; stop_usd?: string | null;
}
export interface SizeProfiles { active: "regular" | "high"; setting: string; regular: SizeTierRow[]; high: SizeTierRow[]; eval_regular?: SizeTierRow[]; eval_high?: SizeTierRow[] }

// D64: research numbers for each profile (5 funded accounts, payout every 2 weeks, 5-year MNQ replay — README §24)
const PROFILE_NOTE: Record<string, string> = {
  regular: "150K ≈ $881 / 2 wk, typical year $21,072, bust 24% · 100K ≈ $643, $16,025, bust 26%",
  high: "150K ≈ $952 / 2 wk, typical year $23,706, bust 27% · 100K ≈ $637, $11,250, bust 24% (no gain over Regular on 100K)",
};
const k$ = (v: string) => `${Math.round(Number(v) / 1000)}K`;

const pct = (x: number | null) => (x == null ? "—" : `${x.toFixed(1)}%`);
const card = "rounded-xl border border-border bg-card p-4";

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
  const d = q.data;
  if (!d) return <p role="status">Loading strategies…</p>;
  const w = d.noise_warmup;
  return (
    <section className={card} data-testid="strategy-buttons">
      <h2 className="font-semibold text-gold">Strategies — tap to turn on/off</h2>
      <p className="text-xs text-blue">Results are from the session 9 study on real MNQ data (picked on 2019–2023, judged unchanged on 2024–2026, 1 micro, costs included). Pro 25K = share of simulated evaluations that passed / busted. Past results do not guarantee future results.</p>
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
              <dt>Pro 25K pass</dt><dd className="text-gold" data-testid={`pass-${s.key}`}>{pct(s.pro25k_pass_pct)}</dd>
              <dt>Pro 25K bust</dt><dd className="text-gold">{pct(s.pro25k_bust_pct)}</dd>
              <dt>Profit factor</dt><dd className="text-gold">{s.profit_factor == null ? "—" : s.profit_factor.toFixed(2)}</dd>
              <dt>Per trade (1 micro)</dt><dd className="text-gold">{s.usd_per_trade == null ? "— (not testable)" : `${s.usd_per_trade >= 0 ? "▲ +" : "▼ "}$${Math.abs(s.usd_per_trade).toFixed(2)}`}</dd>
              <dt>Trades / week</dt><dd className="text-gold">{s.trades_per_week == null ? "—" : s.trades_per_week.toFixed(1)}</dd>
            </dl>
            <p className="mt-2 text-xs text-blue">{s.note}</p>
            {s.key === "order_flow" && (
              <div className="mt-2 text-xs" data-testid="order-flow-setup">
                <span className="rounded border border-gold px-1 font-semibold text-gold" data-testid="order-flow-badge">UNVERIFIED</span>
                <p className="mt-1 text-blue" data-testid="order-flow-markets">Trades: <b className="text-gold">{(s.instruments ?? ["MNQ"]).join(" + ")}</b>{s.paper_only === true && " · PAPER accounts only (plan file)"}{s.flat_at && ` · flat ${s.flat_at} ET`} · 1 micro{s.instruments?.includes("MGC") && " · MGC (gold) is on for Order Flow only — every other strategy keeps it off"}</p>
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
              </div>
            )}
            {s.key === "noise" && !w.ready && (
              <p className="mt-1 text-xs text-gold" data-testid="noise-warmup">Warm-up: {w.sessions}/{w.needed} sessions of TradingView 1-minute MNQ bars stored — NOISE starts trading after that.</p>
            )}
          </div>
        ))}
      </div>
      {d.size_profiles && (
        <div className="mt-4" data-testid="size-profiles">
          <h3 className="font-semibold text-gold">Size per account (automatic by account size, drawdown brake always on)</h3>
          <div className="mt-2 grid gap-3 lg:grid-cols-2">
            {(["regular", "high"] as const).map((p) => {
              const on = d.size_profiles!.active === p;
              return (
                <div key={p} className="rounded-lg border border-border p-3">
                  <button type="button" aria-pressed={on} disabled={size.isPending || on} onClick={() => size.mutate(p === "high")}
                    className={`w-full rounded-md border px-3 py-2 text-left font-semibold ${on ? "border-gold text-gold" : "border-blue text-blue"} disabled:opacity-70`}>
                    {on ? "ON" : "OFF"} · {p === "high" ? "High risk" : "Regular"}
                  </button>
                  <ul className="mt-2 text-sm" data-testid={`size-${p}`}>
                    {d.size_profiles![p].map((t) => (
                      <li key={t.account_size}>{k$(t.account_size)}: <b className="text-gold">{t.contracts} micro{t.contracts > 1 ? "s" : ""}</b>
                        {t.brake_below && <> → {t.brake_contracts} when cushion &lt; {Math.round(Number(t.brake_below) * 100)}% of loss limit</>}</li>
                    ))}
                  </ul>
                  <p className="mt-1 text-xs text-blue">{PROFILE_NOTE[p]}</p>
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
          <p className="mt-1 text-xs text-blue">NOISE keeps its hourly band/VWAP trailing exit and $250-per-micro emergency stop in both profiles.</p>
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
