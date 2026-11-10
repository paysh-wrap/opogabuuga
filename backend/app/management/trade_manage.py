"""D85 trade management for AI Duo positions — one pure rule set that REUSES the existing mechanisms. PURE: Decimal.

Per position (each position is managed independently; every leg keeps its own broker stop):
  break-even  once the best price is ≥ be_r × R in profit: stop → entry + fee_cover_ticks (the guard's BE price)
  profit lock once the best price is ≥ lock_trigger_pts in profit (AI Duo: +100 pt on MNQ): stop → entry + lock_pts
              (+50 pt) — or the AI setup's own lock level when it gave one (`ai_lock_price`, used INSTEAD of the config
              level). Same `profit_lock.lock_stop` rule as NOISE's D75-P1 lock, other numbers.
  step trail  (MGC, user-set) for every step_ticks of open profit the stop is raised raise_ticks above the ORIGINAL stop
              (instead of the profit lock); the AI setup's own level still replaces it once price has passed that level
  trail       once ≥ trail_start_r × R: stop → trail_r × R behind the best price (the guard's `runner_stop`)
Every candidate is (1) capped so the stop is never at or through the current price (nearest valid tick level instead),
(2) put through `ratchet`: a stop only ever tightens. The most protective candidate wins and its rule is returned for
the log. These are broker stop modifications (protective: they never wait for the 6 s hold rule); a failed modify
flattens + pauses (order manager).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.engine.trade_plan import Direction, TradePlan, round_to_tick
from app.management.drawdown_guard import ratchet, runner_stop
from app.management.profit_lock import lock_stop


@dataclass(frozen=True)
class ManageCfg:
    be_r: Decimal
    lock_trigger_pts: Decimal | None
    lock_pts: Decimal | None
    trail_start_r: Decimal
    trail_r: Decimal
    fee_cover_ticks: int
    ai_lock_price: Decimal | None = None  # the AI setup's own lock level (None = use the config level)
    step_ticks: int | None = None  # step trail: every step_ticks of profit …
    raise_ticks: int | None = None  # … raise the stop raise_ticks (set together)


@dataclass(frozen=True)
class StopMove:
    stop: Decimal
    rule: str  # BREAKEVEN | LOCK_CONFIG | LOCK_AI | STEP_TRAIL | TRAIL; "+MARKET_CAP" = pulled back from the market


def managed_stop(
    direction: Direction,
    entry: Decimal,
    risk_pts: Decimal,
    best: Decimal,
    current_stop: Decimal,
    cfg: ManageCfg,
    tick: Decimal,
    last: Decimal | None = None,
) -> StopMove | None:
    """The tightened stop for one leg and the rule that chose it, or None when nothing moves (yet)."""
    s = direction.sign
    mfe = (best - entry) * s
    cands: list[tuple[Decimal, str]] = []
    if mfe >= cfg.be_r * risk_pts:
        cands.append((entry + s * cfg.fee_cover_ticks * tick, "BREAKEVEN"))
    ai = cfg.ai_lock_price
    # the AI's own level replaces the config rule, but only once price has passed it (a level beyond the best price
    # would put the stop at the market and cut the trade: the config rule holds until then)
    ai_ok = ai is not None and 0 < (ai - entry) * s < mfe
    if cfg.step_ticks and cfg.raise_ticks:
        steps = int(mfe // (cfg.step_ticks * tick))
        if ai_ok and ai is not None:
            cands.append((round_to_tick(ai, tick, toward=entry), "LOCK_AI"))
        elif steps > 0:
            orig = entry - s * risk_pts
            cands.append((round_to_tick(orig + s * steps * cfg.raise_ticks * tick, tick, toward=entry), "STEP_TRAIL"))
    elif cfg.lock_trigger_pts is not None and cfg.lock_pts is not None:
        locked = lock_stop(direction, entry, best, cfg.lock_trigger_pts, cfg.lock_pts, tick)
        if locked is not None:
            if ai_ok and ai is not None:
                cands.append((round_to_tick(ai, tick, toward=entry), "LOCK_AI"))
            else:
                cands.append((locked, "LOCK_CONFIG"))
    if mfe >= cfg.trail_start_r * risk_pts:
        plan = TradePlan(direction, entry, current_stop, entry, risk_pts, Decimal(0), breakeven_price=entry)
        cands.append((runner_stop(plan, best, cfg.trail_r, tick), "TRAIL"))
    cap = None if last is None else last - s * tick  # a stop is never placed at or through the current price
    new, rule = current_stop, ""
    for price, name in cands:
        capped = cap is not None and (price - cap) * s > 0
        price = cap if capped and cap is not None else price
        tightened = ratchet(new, price, direction)
        if tightened != new:
            new, rule = tightened, name + ("+MARKET_CAP" if capped else "")
    return None if new == current_stop else StopMove(new, rule)
