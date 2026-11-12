"""D82 strategy presets: overlay of NOISE parameters + size table, My Settings selection, profit-lock day end."""

import asyncio
from datetime import timedelta
from decimal import Decimal as D

import pytest

from app.clock import FixedClock
from app.config import NoiseCfg, RulesConfig, load_presets, load_yaml_decimal
from app.models import AuditLog, Signal, Trade
from app.signals import strategy_service as SS
from tests.integration.test_restart_recovery import open_trade
from tests.integration.test_strategy_service import _add_day, _history, _rules, _sessions

KEYS = ("pro25k_s19", "pro50k_s19", "pro25k_classic", "pro100k_low_risk", "pro150k_low_risk")


def _with_preset(loaded_rules, key):
    raw = load_yaml_decimal(loaded_rules.source_text)
    raw.setdefault("strategy", {})["preset"] = key
    return RulesConfig.model_validate(raw)


def test_preset_file_has_the_three_user_approved_presets():
    p = load_presets()
    assert list(p) == list(KEYS)
    assert [p[k]["recommended"] for k in KEYS] == [False, False, False, False, True]
    assert [p[k].get("superseded", False) for k in KEYS] == [False, False, True, False, False]  # D134: classic kept, labelled
    assert (p["pro25k_s19"]["pass_pct"], p["pro25k_s19"]["bust_pct"]) == (72, 28)  # D134: session 19 §4
    assert (p["pro50k_s19"]["pass_pct"], p["pro50k_s19"]["bust_pct"]) == (70, 30)
    assert (p["pro25k_classic"]["pass_pct"], p["pro25k_classic"]["bust_pct"]) == (64, 36)
    assert (p["pro100k_low_risk"]["pass_pct"], p["pro100k_low_risk"]["bust_pct"]) == (85, 15)  # D125
    assert (p["pro150k_low_risk"]["pass_pct"], p["pro150k_low_risk"]["bust_pct"]) == (85, 15)  # D125
    assert all(p[k]["pass_pct"] + p[k]["bust_pct"] == 100 for k in KEYS)  # D126: user — pass + bust add up to 100
    assert p["pro25k_s19"]["warning"] is None and "94%" in p["pro50k_s19"]["warning"]
    assert (
        p["pro25k_classic"]["warning"]
        and p["pro100k_low_risk"]["warning"] is None
        and p["pro150k_low_risk"]["warning"] is None
    )
    assert "27% rosy" in p["pro25k_classic"]["warning"] and "57%/42%" in p["pro25k_classic"]["warning"]


@pytest.mark.parametrize("key,size,n", [("pro25k_s19", D(25000), 1), ("pro50k_s19", D(50000), 2)])
def test_session19_presets(loaded_rules, key, size, n):  # D134 / I2
    st = _with_preset(loaded_rules, key).strategy
    assert st.noise and not st.pm_fade and st.noise_cfg.skip_weekdays == [0]
    assert st.noise_profit_lock() == (D(100), D(10))
    assert [(t.account_size, t.contracts) for t in st.size_table] == [(size, n)] and st.size_table_high == st.size_table


def test_preset_a_classic(loaded_rules):
    st = _with_preset(loaded_rules, "pro25k_classic").strategy
    assert st.noise and st.pm_fade and st.noise_cfg.emergency_stop_usd == D(250)
    assert st.noise_cfg.profit_lock_pts is None
    assert [(t.account_size, t.contracts, t.brake_below) for t in st.size_table] == [(D(25000), 1, None)]
    assert st.size_table_high == st.size_table


def test_preset_b_low_risk_100k(loaded_rules):
    st = _with_preset(loaded_rules, "pro100k_low_risk").strategy
    assert st.noise and not st.pm_fade and st.noise_cfg.profit_lock_pts == D(10)  # D125: session-19 preset C
    (t,) = st.size_table
    assert (t.account_size, t.mll, t.contracts, t.brake_below, t.brake_contracts) == (
        D(100000),
        D(3000),
        2,
        D("0.3"),
        1,
    )


def test_preset_c_profit_lock_no_fade(loaded_rules):
    st = _with_preset(loaded_rules, "pro150k_low_risk").strategy
    assert st.noise and not st.pm_fade
    assert (st.noise_cfg.profit_lock_trigger_pts, st.noise_cfg.profit_lock_pts) == (D(100), D(10))
    assert st.noise_cfg.emergency_stop_usd == D(250)  # stop loss on every trade stays
    (t,) = st.size_table
    assert (t.contracts, t.brake_contracts, t.brake_below * t.mll) == (3, 1, D(2250))  # 1 micro under $2,250 cushion


def test_preset_touches_nothing_else(loaded_rules):
    base = RulesConfig.model_validate(load_yaml_decimal(loaded_rules.source_text))
    for key in KEYS:
        r = _with_preset(loaded_rules, key)
        for f in ("internal", "eval", "funded", "drawdown_guard", "behavior", "trade_plan", "payouts", "automation"):
            assert getattr(r, f) == getattr(base, f), (key, f)
        assert r.strategy.drawdown_shrink == base.strategy.drawdown_shrink
        assert r.strategy.size_table_eval == base.strategy.size_table_eval  # Evaluation Mode tables unchanged
        assert r.strategy.noise_cfg.check_minutes == base.strategy.noise_cfg.check_minutes
        assert r.strategy.noise_cfg.flat_at == "16:00"


def test_unknown_preset_and_bad_lock_rejected(loaded_rules):
    with pytest.raises(ValueError, match="unknown strategy preset"):
        _with_preset(loaded_rules, "nope")
    with pytest.raises(ValueError, match="go together"):
        NoiseCfg(profit_lock_trigger_pts=D(100))
    with pytest.raises(ValueError, match="profit_lock_pts"):
        NoiseCfg(profit_lock_trigger_pts=D(100), profit_lock_pts=D(100))


def test_select_preset_via_my_settings_is_audited_and_shown(authed):
    d = authed.get("/api/strategies").json()["presets"]
    assert d["active"] is None and d["setting"] == "strategy.preset"
    assert [r["key"] for r in d["rows"]] == list(KEYS)
    c = next(r for r in d["rows"] if r["key"] == "pro150k_low_risk")
    assert c["recommended"] and c["profit_lock"] == {"trigger_pts": "100", "lock_pts": "10"} and c["fade"] is False
    r = authed.put("/api/risk/settings", json={"changes": {"strategy.preset": "pro150k_low_risk"}, "note": "preset"})
    assert r.status_code == 200, r.text
    d = authed.get("/api/strategies").json()
    assert d["presets"]["active"] == "pro150k_low_risk"
    assert d["strategies"][1]["enabled"] is True  # NOISE on
    with authed.app.state.sessionmaker() as s:
        assert s.query(AuditLog).filter_by(action="risk.settings_saved").count() >= 1
    bad = authed.put("/api/risk/settings", json={"changes": {"strategy.preset": "bogus"}, "note": "x"})
    assert bad.status_code == 422 or bad.status_code == 400, bad.text
    off = authed.put("/api/risk/settings", json={"changes": {"strategy.preset": None}, "note": "custom"})
    assert off.status_code == 200 and authed.get("/api/strategies").json()["presets"]["active"] is None


def test_locked_stop_exit_ends_noise_for_the_day(authed, clock):
    _aid, ref = open_trade(authed, clock)
    ctl = authed.app.state.controller
    t = ctl.om.trades[ref]
    with authed.app.state.sessionmaker() as s:
        sig = s.query(Signal).one()
        sig.features = {**sig.features, "state": "OPEN", "strategy": "NOISE"}
        s.commit()
    entry = t.legs[0].entry
    t.profit_lock = (D(5), D(1))
    now = clock.now()
    asyncio.run(ctl.on_bar("MNQ", entry, entry + 6, entry, entry + 5, now))  # +6 pts → stop to entry + 1
    assert t.profit_locked and t.legs[0].stop == entry + 1
    clock.advance(timedelta(minutes=1))
    asyncio.run(ctl.on_bar("MNQ", entry + 5, entry + 5, entry - 1, entry, clock.now()))
    with authed.app.state.sessionmaker() as s:
        row, sig = s.query(Trade).one(), s.query(Signal).one()
        assert row.exit_reason == "PROFIT_LOCK" and row.pnl_usd is not None
        assert sig.features["lock_exit"] is True and sig.features["state"] == "CLOSED"
        assert sig.features["exit_reason"] == "PROFIT_LOCK"


def test_lock_exit_blocks_new_noise_entries_that_day(client, loaded_rules):
    db = client.app.state.sessionmaker
    rules = _rules(loaded_rules, noise=True)
    days = _sessions(12)
    hist, today = days[:-1], days[-1]
    at = today + timedelta(minutes=30)
    clock = FixedClock(at)
    with db() as s:
        _history(s, hist)
        _add_day(s, today, {k: D(20000) + 3 * k for k in range(30)})
        s.add(
            Signal(
                symbol="MNQ", profile="NOISE", bar_time=today + timedelta(minutes=1), direction="LONG", status="PASS",
                model_key=f"MNQ-NOISE-{today.astimezone(SS.ET).date().isoformat()}-1",
                features={"strategy": "NOISE", "state": "CLOSED", "lock_exit": True, "exit_reason": "PROFIT_LOCK"},
            )
        )  # fmt: skip
        s.commit()
        out = SS.run(s, rules=rules, clock=clock, calendar=lambda _d: [], symbol="MNQ", tf="1", at=at)
        assert out.updates == []  # the 10:00 signal that would have entered LONG is suppressed
