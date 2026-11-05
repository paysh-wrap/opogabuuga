"""Day stops + pre-trade checks (§9, D7, D8, D16). Pure: every input is passed in; every check is logged with
its values in the returned result (§9 "Pre-trade checks (logged with values)")."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.engine.trade_plan import TradePlan
from app.risk.consistency import ConsistencyLimits, day_stopped, fit_contracts
from app.risk.risk_base import money
from app.risk.sizing import per_contract_risk, size_contracts
from app.risk.tiers import FloorRules, RiskCfg, RiskCtx, risk_usd, select_risk_pct


@dataclass(frozen=True)
class DayState:
    trades_today: int
    consecutive_losses_today: int
    current_win_streak_today: int
    today_pnl: Decimal  # realised + open, $
    today_profit_for_consistency: Decimal  # realised net profit today, $
    today_peak_pnl: Decimal = Decimal(0)  # best P&L (incl. open) reached today, $ (D18)


@dataclass(frozen=True)
class DayLimits:
    max_trades: int
    max_consecutive_losses: int
    one_to_one: bool = False
    extended_max_trades: int = 0
    extend_after_win_streak: int = 0


def day_stop_reason(day: DayState, lim: DayLimits, consistency: ConsistencyLimits | None) -> str | None:
    if day.consecutive_losses_today >= lim.max_consecutive_losses:
        return "CONSECUTIVE_LOSSES"
    if consistency is not None and day_stopped(day.today_profit_for_consistency, consistency):
        return "CONSISTENCY_DAY_STOP"
    # D7: in 1:1 mode trades 4–5 only while today's win streak is ≥ 3 (a loss on the 4th ends the day)
    extended = (
        lim.one_to_one
        and day.trades_today < lim.extended_max_trades
        and day.current_win_streak_today >= lim.extend_after_win_streak
    )
    if day.trades_today >= lim.max_trades and not extended:
        return "MAX_TRADES"
    return None


def dll_remaining(dll: Decimal, today_pnl: Decimal, today_peak_pnl: Decimal = Decimal(0)) -> Decimal:
    """D18 — safe under every reading of the firm's DLL: room = DLL − drop from today's best P&L.

    • If the firm measures from yesterday's close (fixed floor), this is stricter than the firm.
    • If the firm trails from today's high, this matches it.
    Profits never add room; giving profits back uses room up."""
    peak = max(Decimal(0), today_peak_pnl, today_pnl)
    return money(dll - (peak - today_pnl))


@dataclass(frozen=True)
class AccountView:
    account: str
    stage: str
    selected: bool
    armed: bool
    connected: bool
    attested: bool
    payout_pending: bool
    has_open_position: bool
    paused_reason: str | None
    equity: Decimal  # incl. open P&L
    mll: Decimal
    dll: Decimal | None  # None when DLL is off
    base: Decimal  # risk base


@dataclass(frozen=True)
class TradeLimits:
    tick: Decimal
    tick_value: Decimal
    fee_rt: Decimal
    slippage_ticks: int
    firm_max: int
    internal_max: int
    min_qty: int
    dll_safety_margin: Decimal
    pause_below_base: Decimal
    kill_switch_distance: Decimal


@dataclass
class PreTrade:
    ok: bool
    reason: str | None
    contracts: int = 0
    risk_pct: Decimal | None = None
    risk_usd: Decimal | None = None
    worst_case_usd: Decimal | None = None
    checks: list[dict[str, Any]] = field(default_factory=list)

    def log(self, name: str, ok: bool, **values: Any) -> bool:
        self.checks.append({"check": name, "ok": ok, **{k: str(v) for k, v in values.items()}})
        return ok


def pretrade(
    *,
    acct: AccountView,
    plan: TradePlan,
    score: Decimal,
    rcfg: RiskCfg,
    ctx: RiskCtx,
    floor: FloorRules,
    day: DayState,
    day_limits: DayLimits,
    consistency: ConsistencyLimits | None,
    lim: TradeLimits,
    hedge_conflict: bool,
) -> PreTrade:
    r = PreTrade(ok=False, reason=None)

    def fail(code: str) -> PreTrade:
        r.reason = code
        return r

    if not r.log(
        "account_ready",
        acct.selected and acct.armed and acct.connected,
        selected=acct.selected,
        armed=acct.armed,
        connected=acct.connected,
    ):
        return fail("ACCOUNT_NOT_READY")
    if not r.log("attestation", acct.attested):
        return fail("ATTESTATION_MISSING")
    if not r.log("not_paused", acct.paused_reason is None, paused=acct.paused_reason):
        return fail("ACCOUNT_PAUSED")
    if not r.log("payout_not_pending", not acct.payout_pending):
        return fail("PAYOUT_PENDING")
    if not r.log("one_position", not acct.has_open_position):
        return fail("POSITION_OPEN")
    if not r.log("hedge_lock", not hedge_conflict):
        return fail("HEDGE_LOCK")
    if not r.log("pause_floor", acct.base >= lim.pause_below_base, base=acct.base, floor=lim.pause_below_base):
        return fail("RISK_BASE_BELOW_PAUSE")
    dist = acct.equity - acct.mll
    if not r.log("kill_distance", dist > lim.kill_switch_distance, distance=dist):
        return fail("NEAR_MLL")
    stop = day_stop_reason(day, day_limits, consistency)
    if not r.log("day_stop", stop is None, reason=stop, trades=day.trades_today):
        return fail(stop or "DAY_STOP")
    pct = select_risk_pct(score, ctx, rcfg, floor)
    if not r.log("score_tier", pct is not None, score=score, profile=rcfg.kind):
        return fail("SCORE_BELOW_MIN")
    assert pct is not None
    usd = risk_usd(pct, acct.base, rcfg)
    r.risk_pct, r.risk_usd = pct, usd
    dll_left = dll_remaining(acct.dll, day.today_pnl, day.today_peak_pnl) if acct.dll is not None else None
    if dll_left is not None and not r.log(
        "dll_room", usd + lim.dll_safety_margin <= dll_left, risk=usd, margin=lim.dll_safety_margin, dll_left=dll_left
    ):
        return fail("DLL_LIMIT")
    stop_ticks = plan.risk_pts / lim.tick
    n = size_contracts(
        usd, stop_ticks, lim.tick_value, lim.fee_rt, lim.slippage_ticks, lim.firm_max, lim.internal_max, lim.min_qty
    )
    if not r.log("size", n > 0, risk=usd, stop_ticks=stop_ticks, min_qty=lim.min_qty):
        return fail("STOP_TOO_WIDE")
    if consistency is not None:
        reward = (plan.take_profit - plan.entry) * plan.direction.sign / lim.tick * lim.tick_value - lim.fee_rt
        fit = fit_contracts(n, day.today_profit_for_consistency, reward, consistency, lim.min_qty)
        if not r.log(
            "consistency_cap",
            fit > 0,
            today=day.today_profit_for_consistency,
            cap=consistency.cap,
            reward_per_contract=reward,
            contracts=n,
            fitted=fit,
        ):
            return fail("CONSISTENCY_CAP")
        n = fit
    per = per_contract_risk(stop_ticks, lim.tick_value, lim.fee_rt, lim.slippage_ticks)
    worst = money(n * per)
    room = min(x for x in (dll_left, dist - lim.kill_switch_distance) if x is not None)
    if not r.log("worst_case", worst + lim.dll_safety_margin <= room, worst=worst, room=room):
        return fail("WORST_CASE_EXCEEDS_LIMITS")
    r.ok, r.contracts, r.worst_case_usd = True, n, worst
    return r
