"""Builds the risk-engine inputs for one account from the database + broker (I/O → pure inputs)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import session_date
from app.config import RulesConfig
from app.models import Account, AppSetting, Attestation, DailyAccountStats, Payout, Trade, TradePlanRow
from app.phases.phase_engine import stage_rules
from app.risk.checks import DayLimits, DayState
from app.risk.consistency import ConsistencyLimits, eval_limits, funded_limits
from app.risk.fast_eval import FastCtx
from app.risk.lucid_scale import effective_dll
from app.risk.tiers import RiskCtx


@dataclass(frozen=True)
class TradeResult:
    pnl: Decimal
    net_r: Decimal
    closed_at: datetime


def streak_floor_state(results: list[TradeResult], floor_losses: int, release_wins: int) -> tuple[bool, int, int]:
    """(in_streak_floor, wins_since_floor_started, current consecutive losses) over the stage's trade sequence."""
    in_floor, wins, losses = False, 0, 0
    for r in results:
        if r.pnl < 0:
            losses += 1
            if losses >= floor_losses:
                in_floor, wins = True, 0
        else:
            losses = 0
            if in_floor:
                wins += 1
                if wins >= release_wins:
                    in_floor = False
    return in_floor, wins, losses


def closed_trades(s: Session, acct: Account) -> list[TradeResult]:
    q = select(Trade).where(Trade.account_id == acct.id, Trade.closed_at.is_not(None))
    if acct.stage_started_at is not None:
        q = q.where(Trade.opened_at >= acct.stage_started_at)
    rows = s.execute(q.order_by(Trade.closed_at)).scalars()
    return [TradeResult(r.pnl_usd or Decimal(0), r.net_r or Decimal(0), r.closed_at) for r in rows if r.closed_at]


def get_setting(s: Session, key: str, default: object = None) -> object:
    row = s.get(AppSetting, key)
    return default if row is None else row.value


def set_setting(s: Session, key: str, value: object, now: datetime) -> None:
    row = s.get(AppSetting, key)
    if row is None:
        s.add(AppSetting(key=key, value=value, updated_at=now))
    else:
        row.value, row.updated_at = value, now


def day_stats(s: Session, acct: Account, now: datetime) -> DailyAccountStats:
    sess = session_date(now)
    row = s.execute(
        select(DailyAccountStats).where(DailyAccountStats.account_id == acct.id, DailyAccountStats.session_date == sess)
    ).scalar_one_or_none()
    if row is None:
        row = DailyAccountStats(
            account_id=acct.id,
            session_date=sess,
            day_profit=Decimal(0),
            day_net_r=Decimal(0),
            trades=0,
            losses=0,
            consecutive_losses=0,
            win_streak=0,
            peak_pnl=Decimal(0),
        )
        s.add(row)
        s.flush()
    return row


def strategy_day_pnl(s: Session, acct: Account, now: datetime, mode: str) -> Decimal:
    """D92: realised P&L today of one strategy's closed trades on this account (its plan row carries the mode)."""
    sess = session_date(now)
    q = (
        select(Trade.pnl_usd, Trade.closed_at)
        .join(TradePlanRow, TradePlanRow.signal_id == Trade.signal_id)
        .where(Trade.account_id == acct.id, Trade.closed_at.is_not(None), TradePlanRow.mode == mode)
    )
    total = Decimal(0)
    for pnl, closed in s.execute(q):
        if closed is not None and session_date(closed) == sess:
            total += pnl or Decimal(0)
    return total


def risk_ctx(
    s: Session, acct: Account, base: Decimal, now: datetime, rules: RulesConfig, low_e: bool = False
) -> RiskCtx:
    res = closed_trades(s, acct)
    i = rules.internal
    in_floor, wins, cons = streak_floor_state(res, i.streak_floor_losses, i.streak_release_wins)
    sess = session_date(now)
    today = [r for r in res if session_date(r.closed_at) == sess]
    peak_key = f"acct.{acct.id}.peak_base"
    peak = Decimal(str(get_setting(s, peak_key, str(base))))
    if base > peak:
        set_setting(s, peak_key, str(base), now)
        peak = base
    dd = (peak - base) * 100 / peak if peak > 0 else Decimal(0)
    return RiskCtx(
        first_trade_today=not today,
        last_closed_was_loss=bool(res) and res[-1].pnl < 0,
        losses_today=sum(1 for r in today if r.pnl < 0),
        today_net_r=sum((r.net_r for r in today), Decimal(0)),
        dd_from_peak_base_pct=dd,
        trades_in_stage=len(res),
        consecutive_losses=cons,
        wins_since_streak_floor=wins,
        in_streak_floor=in_floor,
        low_expectancy_cap=low_e,
    )


def prior_day_pnls(s: Session, acct: Account, now: datetime, n: int) -> list[Decimal]:
    """D87: realised P&L of the last n PREVIOUS trading days of this stage (oldest first; days with trades only)."""
    sess = session_date(now)
    by_day: dict[object, Decimal] = {}
    for r in closed_trades(s, acct):
        d = session_date(r.closed_at)
        if d < sess:
            by_day[d] = by_day.get(d, Decimal(0)) + r.pnl
    return [by_day[d] for d in sorted(by_day, key=str)][-n:]


def fast_ctx(s: Session, acct: Account, base: Decimal, rules: RulesConfig, now: datetime, balance: Decimal) -> FastCtx:
    """D87 inputs: cushion = the risk base, mll = the plan's loss limit, profit share from the settled balance."""
    res = closed_trades(s, acct)
    sess = session_date(now)
    today = [r for r in res if session_date(r.closed_at) == sess]
    start = acct.starting_balance or rules.account_size
    done = balance - day_stats(s, acct, now).day_profit - start
    target = rules.eval.profit_target
    return FastCtx(
        cushion=base,
        mll=rules.eval.max_loss_limit,
        last_closed_was_loss=bool(res) and res[-1].pnl < 0,
        losses_today=sum(1 for r in today if r.pnl < 0),
        trades_in_stage=len(res),
        profit_frac=done / target if target > 0 else Decimal(0),
    )


def day_state(s: Session, acct: Account, open_pnl: Decimal, now: datetime) -> DayState:
    st = day_stats(s, acct, now)
    realised = st.day_profit
    pnl = realised + open_pnl
    if pnl > st.peak_pnl:
        st.peak_pnl = pnl
    return DayState(
        trades_today=st.trades,
        consecutive_losses_today=st.consecutive_losses,
        current_win_streak_today=st.win_streak,
        today_pnl=pnl,
        today_profit_for_consistency=realised,
        today_peak_pnl=st.peak_pnl,
    )


def day_limits(rules: RulesConfig, stage: str) -> DayLimits:
    o = rules.one_to_one_mode
    if o.enabled and stage in o.stages:
        return DayLimits(
            o.max_trades_per_day,
            o.max_consecutive_losses_per_day,
            True,
            o.extended_max_trades_per_day,
            o.extend_after_win_streak,
        )
    return DayLimits(rules.internal.max_trades_per_day, rules.internal.max_consecutive_losses_per_day)


def consistency(s: Session, acct: Account, rules: RulesConfig) -> ConsistencyLimits | None:
    i = rules.internal
    if acct.stage == "EVAL":
        if rules.eval.consistency_max_day_pct is None:
            return None
        return eval_limits(
            rules.eval.profit_target, rules.eval.consistency_max_day_pct, i.consistency_day_stop_buffer_pct
        )
    if acct.stage == "FUNDED" and i.consistency_on_funded:
        last_payout = s.execute(
            select(Payout.processed_at)
            .where(Payout.account_id == acct.id, Payout.status == "processed")
            .order_by(Payout.processed_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        q = select(Trade.pnl_usd).where(Trade.account_id == acct.id, Trade.closed_at.is_not(None))
        if last_payout is not None:
            q = q.where(Trade.closed_at > last_payout)
        cycle = sum((x or Decimal(0) for x in s.execute(q).scalars()), Decimal(0))
        return funded_limits(
            cycle, i.funded_consistency_reference_min, i.funded_consistency_pct, i.consistency_day_stop_buffer_pct
        )
    return None


def attested_today(s: Session, now: datetime) -> bool:
    return s.execute(select(Attestation.id).where(Attestation.session_date == session_date(now))).first() is not None


def payouts_processed(s: Session, acct: Account) -> int:
    return len(s.execute(select(Payout.id).where(Payout.account_id == acct.id, Payout.status == "processed")).all())


def payout_pending(s: Session, acct: Account) -> bool:
    return (
        s.execute(select(Payout.id).where(Payout.account_id == acct.id, Payout.status == "submitted")).first()
        is not None
    )


def stage_sessions(s: Session, acct: Account) -> int:
    q = select(DailyAccountStats.session_date).where(DailyAccountStats.account_id == acct.id)
    if acct.stage_started_at is not None:
        q = q.where(DailyAccountStats.session_date >= session_date(acct.stage_started_at))
    return len(set(s.execute(q).scalars()))


def dll_for(rules: RulesConfig, acct: Account) -> Decimal | None:
    """Effective DLL: the plan's fixed DLL, or the LucidScale DLL once the MLL has locked (risk/lucid_scale)."""
    sr = stage_rules(rules, acct.stage, acct.drawdown_type, acct.dll_enabled)
    start = acct.starting_balance or rules.account_size
    peak = acct.mll_peak if acct.mll_peak is not None else start
    return effective_dll(sr.dll, sr.dll_scale_pct, bool(acct.mll_locked), peak, start)
