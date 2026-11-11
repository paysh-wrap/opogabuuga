"""JSON snapshot of an OpenTrade (restart recovery, session 14). Pure: no I/O. Decimals travel as strings."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.engine.trade_plan import Direction, TradePlan
from app.execution.order_manager import Leg, OpenTrade
from app.management.dynamic_trail import TrailParams
from app.management.trade_manage import ManageCfg


def _d(x: Decimal | None) -> str | None:
    return None if x is None else str(x)


def _ld(x: Any) -> Decimal | None:
    return None if x is None else Decimal(str(x))


def _dt(x: datetime | None) -> str | None:
    return None if x is None else x.isoformat()


def _ldt(x: Any) -> datetime | None:
    return None if x is None else datetime.fromisoformat(str(x))


def dump(t: OpenTrade) -> dict[str, Any]:
    p = t.plan
    return {
        "v": 1,
        "trade_id": t.trade_id,
        "account": t.account,
        "symbol": t.symbol,
        "plan": {
            "direction": p.direction.value,
            "entry": _d(p.entry),
            "stop": _d(p.stop),
            "take_profit": _d(p.take_profit),
            "risk_pts": _d(p.risk_pts),
            "rr": _d(p.rr),
            "partial_price": _d(p.partial_price),
            "breakeven_price": _d(p.breakeven_price),
            "lock_price": _d(p.lock_price),
            "mode": p.mode,
        },
        "guard_on": t.guard_on,
        "tick": _d(t.tick),
        "tick_value": _d(t.tick_value),
        "opened_at": _dt(t.opened_at),
        "rr_window": [str(x) for x in t.rr_window],
        "legs": [
            {
                "name": x.name,
                "qty": x.qty,
                "take_profit": _d(x.take_profit),
                "bracket_id": x.bracket_id,
                "stop_order_id": x.stop_order_id,
                "stop": _d(x.stop),
                "entry": _d(x.entry),
                "exit": _d(x.exit),
                "fee": _d(x.fee),
                "closed": x.closed,
            }
            for x in t.legs
        ],
        "best": _d(t.best),
        "partial_done": t.partial_done,
        "locked": t.locked,
        "half_used": t.half_used,
        "runner_trail": _d(t.runner_trail),
        "closing": t.closing,
        "closing_since": _dt(t.closing_since),
        "orphan": t.orphan,
        "exit_qty": t.exit_qty,
        "exit_notional": _d(t.exit_notional),
        "exit_fee": _d(t.exit_fee),
        "pending_until": _dt(t.pending_until),
        "cancel_alerted": t.cancel_alerted,
        "profile": t.profile,
        "signal_id": t.signal_id,
        "strategy": t.strategy,
        "profit_lock": None if t.profit_lock is None else [str(x) for x in t.profit_lock],
        "profit_locked": t.profit_locked,
        "manage": None
        if t.manage is None
        else {
            **{k: str(getattr(t.manage, k)) for k in ("be_r", "trail_start_r", "trail_r")},
            **{
                k: None if getattr(t.manage, k) is None else str(getattr(t.manage, k))
                for k in ("lock_trigger_pts", "lock_pts")
            },
            "step_ticks": t.manage.step_ticks,
            "raise_ticks": t.manage.raise_ticks,
            "fee_cover_ticks": t.manage.fee_cover_ticks,
            "ai_lock_price": None if t.manage.ai_lock_price is None else str(t.manage.ai_lock_price),
        },
        "dyn_trail": None if t.dyn_trail is None else _dump_trail(t.dyn_trail),
    }


def _dump_trail(p: TrailParams) -> dict[str, Any]:
    return {
        **{k: str(getattr(p, k)) for k in ("activate_r", "low_vol_percentile", "low_vol_mult", "k_floor", "k_minus")},
        **{k: getattr(p, k) for k in ("min_distance_ticks", "atr_tf_min", "atr_period", "swing_tf_min")},
        "low_vol_lookback": p.low_vol_lookback,
        "fee_cover_ticks": p.fee_cover_ticks,
        "steps": [[_d(u), str(k)] for u, k in p.steps],
        "of_trail": None if p.of_trail is None else [p.of_trail[0], str(p.of_trail[1])],
    }


def _trail(m: dict[str, Any]) -> TrailParams:
    of = m.get("of_trail")
    return TrailParams(
        Decimal(m["activate_r"]),
        int(m["min_distance_ticks"]),
        int(m["atr_tf_min"]),
        int(m["atr_period"]),
        int(m["swing_tf_min"]),
        tuple((_ld(u), Decimal(k)) for u, k in m["steps"]),
        Decimal(m["low_vol_percentile"]),
        Decimal(m["low_vol_mult"]),
        int(m["low_vol_lookback"]),
        Decimal(m["k_floor"]),
        int(m["fee_cover_ticks"]),
        Decimal(m["k_minus"]),
        None if of is None else (int(of[0]), Decimal(of[1])),
    )


def _manage(m: dict[str, Any]) -> ManageCfg:
    return ManageCfg(
        Decimal(m["be_r"]),
        None if m.get("lock_trigger_pts") is None else Decimal(m["lock_trigger_pts"]),
        None if m.get("lock_pts") is None else Decimal(m["lock_pts"]),
        Decimal(m["trail_start_r"]),
        Decimal(m["trail_r"]),
        int(m["fee_cover_ticks"]),
        None if m.get("ai_lock_price") is None else Decimal(m["ai_lock_price"]),
        m.get("step_ticks"),
        m.get("raise_ticks"),
    )


def load(d: dict[str, Any]) -> OpenTrade:
    p = d["plan"]
    plan = TradePlan(
        Direction(p["direction"]),
        Decimal(p["entry"]),
        Decimal(p["stop"]),
        Decimal(p["take_profit"]),
        Decimal(p["risk_pts"]),
        Decimal(p["rr"]),
        _ld(p["partial_price"]),
        _ld(p["breakeven_price"]),
        _ld(p["lock_price"]),
        p["mode"],
    )
    inv, t2, rmin, rmax, buf, mst = d["rr_window"]
    legs = [
        Leg(
            x["name"],
            int(x["qty"]),
            Decimal(x["take_profit"]),
            x["bracket_id"],
            x["stop_order_id"],
            Decimal(x["stop"]),
            _ld(x["entry"]),
            _ld(x["exit"]),
            Decimal(x["fee"]),
            bool(x["closed"]),
        )
        for x in d["legs"]
    ]
    return OpenTrade(
        d["trade_id"],
        d["account"],
        d["symbol"],
        plan,
        bool(d["guard_on"]),
        Decimal(d["tick"]),
        Decimal(d["tick_value"]),
        datetime.fromisoformat(d["opened_at"]),
        legs,
        (Decimal(inv), Decimal(t2), Decimal(rmin), Decimal(rmax), int(buf), int(mst)),
        best=_ld(d["best"]),
        partial_done=bool(d["partial_done"]),
        locked=bool(d["locked"]),
        half_used=bool(d["half_used"]),
        runner_trail=_ld(d["runner_trail"]),
        closing=d["closing"],
        closing_since=_ldt(d["closing_since"]),
        orphan=bool(d["orphan"]),
        exit_qty=int(d["exit_qty"]),
        exit_notional=Decimal(d["exit_notional"]),
        exit_fee=Decimal(d["exit_fee"]),
        pending_until=_ldt(d["pending_until"]),
        cancel_alerted=bool(d["cancel_alerted"]),
        profile=d["profile"],
        signal_id=d["signal_id"],
        strategy=d["strategy"],
        profit_lock=None
        if d.get("profit_lock") is None
        else (Decimal(d["profit_lock"][0]), Decimal(d["profit_lock"][1])),
        profit_locked=bool(d.get("profit_locked", False)),
        manage=None if not d.get("manage") else _manage(d["manage"]),
        dyn_trail=None if not d.get("dyn_trail") else _trail(d["dyn_trail"]),
    )
