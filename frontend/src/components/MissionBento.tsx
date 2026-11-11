import { Link } from "react-router-dom";
import { theme, mission } from "../lib/theme";

/** D93 "mission control" hero for the Dashboard. Real /api/dashboard numbers only; empty states when absent. */
export interface BentoAcct {
  id: number; label: string; stage: string; armed: boolean; error?: string;
  balance?: string; today_pnl?: string; open_pnl?: string; to_mll?: string | null; max_loss?: string;
  dll_left?: string | null; dll_limit?: string | null; trades_today?: number; kill_at?: string;
}

const money = (n: number) => `$${Math.abs(n).toLocaleString(undefined, { minimumFractionDigits: Number.isInteger(n) ? 0 : 2, maximumFractionDigits: 2 })}`;
const signed = (n: number) => `${n > 0 ? "▲ +" : n < 0 ? "▼ −" : ""}${money(n)}`;

function Gauge({ value, max, label }: { value: number; max: number; label: string }) {
  const pct = max > 0 ? Math.max(0, Math.min(100, (100 * value) / max)) : 0;
  return (
    <svg className="mission-gauge" viewBox="0 0 220 140" role="img" aria-label={label}>
      <defs>
        <linearGradient id="mission-g" x1="0" x2="1"><stop offset="0" stopColor={theme.blue} /><stop offset="1" stopColor={theme.gold} /></linearGradient>
      </defs>
      <path d="M25 125 A85 85 0 0 1 195 125" fill="none" stroke={mission.navOn} strokeWidth="16" strokeLinecap="round" />
      <path d="M25 125 A85 85 0 0 1 195 125" fill="none" stroke="url(#mission-g)" strokeWidth="16" strokeLinecap="round"
        pathLength={100} strokeDasharray={`${pct} 100`} />
      <text x="110" y="100" textAnchor="middle" fill={theme.goldLight} fontSize="32" fontWeight="700" className="mission-num-svg">{money(value)}</text>
      <text x="110" y="120" textAnchor="middle" fill={theme.blueLight} fontSize="10" className="mission-mono-svg">OF {money(max)}</text>
    </svg>
  );
}

export default function MissionBento({ accounts, mode }: { accounts: BentoAcct[]; mode: string }) {
  const ok = accounts.filter((a) => !a.error);
  // Focus = the account closest to its drawdown limit (smallest cushion): that is the one that can break a rule.
  const focus = ok.filter((a) => a.to_mll != null).sort((a, b) => Number(a.to_mll) - Number(b.to_mll))[0];
  const today = ok.reduce((x, a) => x + Number(a.today_pnl ?? 0), 0);
  const open = ok.reduce((x, a) => x + Number(a.open_pnl ?? 0), 0);
  const trades = ok.reduce((x, a) => x + (a.trades_today ?? 0), 0);
  const balance = ok.reduce((x, a) => x + Number(a.balance ?? 0), 0);
  const armed = accounts.filter((a) => a.armed).length;

  const dllLimit = focus?.dll_limit != null ? Number(focus.dll_limit) : null;
  const fToday = Number(focus?.today_pnl ?? 0);
  // Bar runs from −DLL (left) to +DLL (right); 0 is the middle.
  const barPct = dllLimit ? Math.max(0, Math.min(100, 50 + (50 * fToday) / dllLimit)) : 50;

  return (
    <div className="mission-bento" data-testid="dash-hero">
      <section className="mission-tile mission-span-2 mission-rows-2 rounded-xl border bg-card p-4" data-testid="tile-cushion">
        <h2 className="font-semibold text-gold">Cushion to drawdown {focus && <span className="tile-aside">{focus.label} · {focus.stage}</span>}</h2>
        {focus ? (
          <>
            <Gauge value={Number(focus.to_mll)} max={Number(focus.max_loss ?? 0)}
              label={`Cushion ${money(Number(focus.to_mll))} of ${money(Number(focus.max_loss ?? 0))}`} />
            <p className="tile-sub">Closest account to its drawdown limit. Kill switch fires within {focus.kill_at ? money(Number(focus.kill_at)) : "the configured distance"} of it.</p>
          </>
        ) : <p className="tile-sub">No account reports a drawdown cushion yet.</p>}
      </section>

      <section className="mission-tile mission-span-2 rounded-xl border bg-card p-4" data-testid="tile-dll">
        <h2 className="font-semibold text-gold">Day P&amp;L vs daily loss limit {focus && <span className="tile-aside">{focus.label}</span>}</h2>
        <div className="mission-num">{focus ? signed(fToday) : "—"}</div>
        {dllLimit ? (
          <>
            <div className="mission-bar" role="img" aria-label={`Day P&L ${signed(fToday)} against a ${money(dllLimit)} daily loss limit`}>
              <i style={{ width: `${barPct}%` }} /><u style={{ left: `${barPct}%` }} />
            </div>
            <div className="mission-scale"><span>−{money(dllLimit)} limit</span><span>0</span><span>{focus?.dll_left != null ? `${money(Number(focus.dll_left))} room` : ""}</span></div>
          </>
        ) : <p className="tile-sub">{focus ? "This account has no daily loss limit." : "No account data yet."}</p>}
      </section>

      <section className="mission-tile mission-span-2 mission-safety rounded-xl border bg-card p-4" data-testid="tile-safety">
        <h2 className="font-semibold text-gold">Safety</h2>
        <p className="tile-sub">Kill switch (type KILL) is in the header on every page. Flatten all and arm/disarm live on Automation.</p>
        <Link to="/automation" className="mission-safety-link">Open safety controls</Link>
      </section>

      <section className="mission-tile mission-span-2 rounded-xl border bg-card p-4" data-testid="tile-today">
        <h2 className="font-semibold text-gold">Today <span className="tile-aside">automation {mode}</span></h2>
        <div className="mission-num">{trades} <small>trades</small></div>
        <p className="tile-sub">All accounts {signed(today)} · open <b className="text-goldLight">{signed(open)}</b></p>
      </section>

      <section className="mission-tile mission-span-2 rounded-xl border bg-card p-4" data-testid="tile-balance">
        <h2 className="font-semibold text-gold">Total balance <span className="tile-aside">{armed} / {accounts.length} armed</span></h2>
        <div className="mission-num">{money(balance)}</div>
        <p className="tile-sub">{accounts.length === 0 ? "No accounts yet — add one on the Automation page." : `${accounts.length} account(s)`}</p>
      </section>
    </div>
  );
}
