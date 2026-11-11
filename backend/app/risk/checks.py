"""Day stops + pre-trade checks (§9, D7, D8, D16). Pure: every input is passed in; every check is logged with
its values in the returned result (§9 "Pre-trade checks (logged with values)")."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal
from typing import Any

from app.config import FastEvalCfg
from app.engine.trade_plan import TradePlan
from app.risk.consistency import ConsistencyLimits, day_stopped, fit_contracts
from app.risk.fast_eval import FastCtx, fast_risk_pct
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
    # D85 (AI Duo on 150K only, user-approved override of "max 1 open position"): how many positions the account may
    # hold at once (default 1 = unchanged for every other strategy/size), how many it holds now, and the risk still
    # open on them (stop distance × qty + fees + slippage, $) — the aggregate-risk check below uses it.
    max_open_positions: int = 1
    open_positions: int = 0
    open_risk_usd: Decimal = Decimal(0)


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
    # D36 Lower-risk mode: when the (halved) risk can't buy min_qty micros, allow exactly min_qty if that costs no
    # more than risk × this multiple (2 = the normal-mode risk). Never above normal risk; None = off.
    min_qty_cap_mult: Decimal | None = None
    # D55: fixed-size strategies (NOISE / OPEN_DRIVE, user: 1 micro on Pro 25K). No score tiers and no per-trade $ cap
    # (their broker stop is an emergency stop far beyond the typical loss); the worst case at that stop must still fit
    # the DLL left and the distance to the MLL minus the kill-switch distance (checks below), like every trade.
    fixed_contracts: int | None = None
    # D57 (user 2026-11-09): instead of pausing a fixed-size strategy below the pause floor, SCALE ITS RISK DOWN as the
    # account draws down: the emergency stop is tightened so the worst case is at most `shrink_fraction` of the room
    # (min of DLL left and distance to the MLL minus the kill-switch distance). Below `shrink_min_pct` of price the
    # stop would be noise → skip DRAWDOWN_TOO_DEEP. None = off (pause floor applies). Same-code in live/backtest.
    shrink_fraction: Decimal | None = None
    shrink_min_pct: Decimal = Decimal("0.002")
    # D85 (user 2026-11-10, AI Duo): a total per-trade risk cap in $ (stop distance × qty + fees + slippage). The fixed
    # size is reduced to what fits; if not even one contract fits → STOP_TOO_WIDE. None = off (every other strategy).
    max_risk_usd: Decimal | None = None


@dataclass
class PreTrade:
    ok: bool
    reason: str | None
    contracts: int = 0
    new_stop: Decimal | None = None  # D57: tightened emergency stop the caller must use instead of the plan's stop
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
    fast: tuple[FastEvalCfg, FastCtx] | None = None,  # D87: only passed for an EVAL account with Fast Evaluation on
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
    held = max(acct.open_positions, 1 if acct.has_open_position else 0)
    if not r.log("one_position", held < max(acct.max_open_positions, 1), held=held, allowed=acct.max_open_positions):
        return fail("POSITION_OPEN")
    if not r.log("hedge_lock", not hedge_conflict):
        return fail("HEDGE_LOCK")
    scaled = lim.fixed_contracts is not None and lim.shrink_fraction is not None  # D57: scale instead of pause
    if not r.log(
        "pause_floor",
        scaled or acct.base >= lim.pause_below_base,
        base=acct.base,
        floor=lim.pause_below_base,
        scaled=scaled,
    ):
        return fail("RISK_BASE_BELOW_PAUSE")
    dist = acct.equity - acct.mll
    if not r.log("kill_distance", dist > lim.kill_switch_distance, distance=dist):
        return fail("NEAR_MLL")
    stop = day_stop_reason(day, day_limits, consistency)
    if not r.log("day_stop", stop is None, reason=stop, trades=day.trades_today):
        return fail(stop or "DAY_STOP")
    dll_left = dll_remaining(acct.dll, day.today_pnl, day.today_peak_pnl) if acct.dll is not None else None
    stop_ticks = plan.risk_pts / lim.tick
    if lim.fixed_contracts is not None:
        n = min(lim.fixed_contracts, lim.firm_max, lim.internal_max)
        if lim.max_risk_usd is not None:
            one = per_contract_risk(stop_ticks, lim.tick_value, lim.fee_rt, lim.slippage_ticks)
            n = min(n, int(lim.max_risk_usd // one))
            r.log("trade_risk_cap", n > 0, cap=lim.max_risk_usd, per_contract=money(one), contracts=n)
        usd = money(n * per_contract_risk(stop_ticks, lim.tick_value, lim.fee_rt, lim.slippage_ticks))
        if lim.shrink_fraction is not None and n > 0:
            room0 = min(x for x in (dll_left, dist - lim.kill_switch_distance) if x is not None)
            allowed = room0 * lim.shrink_fraction
            if usd > allowed:
                per_ticks = ((allowed / n - lim.fee_rt) / lim.tick_value - lim.slippage_ticks).to_integral_value(
                    rounding=ROUND_DOWN
                )
                new_pts = per_ticks * lim.tick
                if not r.log(
                    "drawdown_scale", new_pts >= plan.entry * lim.shrink_min_pct, allowed=allowed, stop_pts=new_pts
                ):
                    return fail("DRAWDOWN_TOO_DEEP")
                stop_ticks = per_ticks
                r.new_stop = plan.entry - plan.direction.sign * new_pts
                usd = money(n * per_contract_risk(stop_ticks, lim.tick_value, lim.fee_rt, lim.slippage_ticks))
        r.risk_usd = usd
        if not r.log("fixed_size", n > 0, contracts=n, worst=usd, cap_not_applied=rcfg.max_risk_usd):
            return fail("STOP_TOO_WIDE")
        return _finish(r, plan, day, consistency, lim, n, stop_ticks, dll_left, dist, acct.open_risk_usd)
    pct = select_risk_pct(score, ctx, rcfg, floor)
    if not r.log("score_tier", pct is not None, score=score, profile=rcfg.kind):
        return fail("SCORE_BELOW_MIN")
    assert pct is not None
    if fast is not None and acct.stage == "EVAL":  # D87 mechanism 3 (raise only; caps and DLL checks below still apply)
        boosted = fast_risk_pct(fast[0], fast[1], pct)
        r.log("fast_eval_early_tier", True, before=pct, after=boosted)
        pct = boosted
    usd = risk_usd(pct, acct.base, rcfg)
    r.risk_pct, r.risk_usd = pct, usd
    if dll_left is not None and not r.log(
        "dll_room", usd + lim.dll_safety_margin <= dll_left, risk=usd, margin=lim.dll_safety_margin, dll_left=dll_left
    ):
        return fail("DLL_LIMIT")
    n = size_contracts(
        usd, stop_ticks, lim.tick_value, lim.fee_rt, lim.slippage_ticks, lim.firm_max, lim.internal_max, lim.min_qty
    )
    if n == 0 and lim.min_qty_cap_mult is not None:
        cap = usd * lim.min_qty_cap_mult
        need = per_contract_risk(stop_ticks, lim.tick_value, lim.fee_rt, lim.slippage_ticks) * lim.min_qty
        dll_ok = dll_left is None or need + lim.dll_safety_margin <= dll_left
        if need <= cap and dll_ok and lim.min_qty <= min(lim.firm_max, lim.internal_max):
            n, usd = lim.min_qty, need
            r.risk_usd = usd
            r.log("low_risk_min_qty", True, risk=usd, cap=cap)
    if not r.log("size", n > 0, risk=usd, stop_ticks=stop_ticks, min_qty=lim.min_qty):
        return fail("STOP_TOO_WIDE")
    return _finish(r, plan, day, consistency, lim, n, stop_ticks, dll_left, dist, acct.open_risk_usd)


def _finish(
    r: PreTrade,
    plan: TradePlan,
    day: DayState,
    consistency: ConsistencyLimits | None,
    lim: TradeLimits,
    n: int,
    stop_ticks: Decimal,
    dll_left: Decimal | None,
    dist: Decimal,
    open_risk: Decimal = Decimal(0),
) -> PreTrade:
    """Checks every trade passes after sizing: consistency cap, then worst case vs DLL left / MLL distance."""
    if consistency is not None and lim.fixed_contracts is not None:
        # N6 / D89: a fixed-size strategy trade exits by its own rules (NOISE: band/VWAP/hourly exits; the far TP
        # is only a 10% safety order), so "the take-profit reward must fit the cap" would reject EVERY entry. The cap is
        # enforced live instead: the controller flattens the account's strategy trades as soon as today's realised +
        # open profit reaches consistency.day_stop (< cap), and no new entry opens once the day stop is reached.
        room_ok = day.today_profit_for_consistency < consistency.cap
        if not r.log(
            "consistency_cap",
            room_ok,
            mode="live_day_stop",
            today=day.today_profit_for_consistency,
            cap=consistency.cap,
            day_stop=consistency.day_stop,
            contracts=n,
        ):
            r.reason = "CONSISTENCY_CAP"
            return r
    elif consistency is not None:
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
            r.reason = "CONSISTENCY_CAP"
            return r
        n = fit
    per = per_contract_risk(stop_ticks, lim.tick_value, lim.fee_rt, lim.slippage_ticks)
    worst = money(n * per)
    room = min(x for x in (dll_left, dist - lim.kill_switch_distance) if x is not None)
    if open_risk > 0:  # D85 aggregate: risk still open on this account's other positions + this trade + margin ≤ room
        fit = int((room - lim.dll_safety_margin - open_risk) // per) if room - lim.dll_safety_margin > open_risk else 0
        n_new = min(n, fit)
        if not r.log(
            "aggregate_risk", n_new > 0, open_risk=open_risk, room=room, margin=lim.dll_safety_margin, contracts=n_new
        ):
            r.reason = "AGGREGATE_RISK_EXCEEDS_LIMITS"
            return r
        n, worst = n_new, money(n_new * per)
    if not r.log("worst_case", worst + open_risk + lim.dll_safety_margin <= room, worst=worst, room=room):
        r.reason = "WORST_CASE_EXCEEDS_LIMITS"
        return r
    r.ok, r.contracts, r.worst_case_usd = True, n, worst
    return r
