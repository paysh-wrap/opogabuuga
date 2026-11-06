"""Confluence gates G1–G7 + score (§6, §21)."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from app.config import load_rules
from app.engine.confluence import EvalInput, ModelView, evaluate
from app.engine.filters import (
    CooldownState,
    NewsEvent,
    add_sessions,
    c1_range_ok,
    cooldown_on_model_event,
    entry_deadline_ms,
)
from app.engine.scoring import ScoreInputs, compute_score
from app.engine.state_machine import IllegalTransition, ModelMachine
from app.engine.trade_plan import Direction
from tests.conftest import RULES_PATH

CFG = load_rules(RULES_PATH).rules
AT = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)  # 10:00 ET Thursday — inside 09:35–11:30
MS = int(AT.timestamp() * 1000)
MIN = 60_000


def model(**over):
    base = dict(
        model_key=f"MNQ-TIGHT-{MS - 30 * MIN}",
        direction=Direction.LONG,
        events=(("C1_SWEPT", MS - 10 * MIN), ("CISD", MS - 8 * MIN), ("MODEL_CONFIRMED", MS - 2 * MIN)),
        c1_high=D(20070),
        c1_low=D(19990),
        c1_time_ms=MS - 30 * MIN,
        htf_atr14=D(100),
        t1=D(20030),
        t2=D(20070),
        invalid=D(19981),
        sweep_time_ms=MS - 10 * MIN,
        cisd_level=D(19995),
        cisd_before_c2_close=True,
        t1_preticked=False,
        c3_close_time_ms=MS + 13 * MIN,
        confirm_time_ms=MS - 2 * MIN,
    )
    base.update(over)
    return ModelView(**base)


def good(**over):
    base = dict(
        symbol="MNQ",
        profile="TIGHT",
        at=AT,
        close=D(20000),
        tf_min=1,
        model=model(),
        mso_trend="BULL",
        mso_osc=D(72),
        htf_trend="BULL",
        mso_events=(("MSO_CHOCH", "LONG", MS - 5 * MIN),),
        bias="LONG_ONLY",
        feed_fresh=True,
        calendar=[],
        cooldown_active=False,
        model_traded=False,
    )
    base.update(over)
    return EvalInput(**base)


def gate(dec, g):
    return next(x for x in dec.gates if x.gate == g)


def test_all_gates_pass_full_score_and_spec_plan():
    d = evaluate(good(), CFG)
    assert d.outcome == "PASS" and d.skip_reason is None
    assert d.score.score == D(100) - D(15)  # own TP rate = 0 until 30 samples
    p = d.plan
    assert (p.entry, p.stop, p.take_profit, p.rr) == (D(20000), D(19980), D(20060), D(3))
    assert d.c1_range_atr == D("0.8")


@pytest.mark.parametrize(
    "over,gate_id,code,outcome",
    [
        ({"feed_fresh": False}, "G1", "FEED_STALE", "WAIT"),
        (
            {"at": AT.replace(hour=16, minute=31), "model": model(c3_close_time_ms=MS + 120 * MIN)},
            "G1",
            "OUTSIDE_WINDOW",
            "WAIT",
        ),  # 11:31 ET
        ({"at": AT.replace(hour=14, minute=32)}, "G1", "OUTSIDE_WINDOW", "WAIT"),  # 09:32 ET (D10 excluded)
        ({"calendar": None}, "G1", "CALENDAR_MISSING", "WAIT"),
        ({"cooldown_active": True}, "G1", "COOLDOWN", "SKIP"),
        ({"symbol": "MGC"}, "G1", "INSTRUMENT_DISABLED", "SKIP"),
        ({"bias": "NO_TRADE"}, "G2", "BIAS_NO_TRADE", "SKIP"),
        ({"bias": "SHORT_ONLY"}, "G2", "BIAS_OPPOSITE", "SKIP"),
        ({"model_traded": True}, "G3", "MODEL_ALREADY_TRADED", "SKIP"),
        ({"mso_trend": "BEAR", "mso_osc": D(30)}, "G4", "MSO_STRUCTURE_DISAGREES", "WAIT"),
        ({"mso_osc": D(50)}, "G4", "MSO_STRUCTURE_DISAGREES", "WAIT"),
        ({"mso_events": ()}, "G5", "NO_STRUCTURE_BREAK", "WAIT"),
        ({"mso_events": (("MSO_CHOCH", "LONG", MS - 11 * MIN),)}, "G5", "NO_STRUCTURE_BREAK", "WAIT"),  # before sweep
        (
            {"mso_events": (("MSO_CHOCH", "LONG", MS - 5 * MIN), ("MSO_DIV", "SHORT", MS - 3 * MIN))},
            "G6",
            "OPPOSING_DIVERGENCE",
            "WAIT",
        ),
        ({"close": D(20020)}, "G7", "RR_BELOW_MIN", "WAIT"),
    ],
)
def test_each_gate(over, gate_id, code, outcome):
    d = evaluate(good(**over), CFG)
    g = gate(d, gate_id)
    assert not g.passed and g.code == code
    assert d.outcome == outcome


def test_old_divergence_outside_lookback_is_ignored():
    lookback = CFG.score.div_lookback_bars
    evs = (("MSO_CHOCH", "LONG", MS - 5 * MIN), ("MSO_DIV", "SHORT", MS - (lookback + 1) * MIN))
    assert evaluate(good(mso_events=evs), CFG).outcome == "PASS"


def test_news_blackout():
    cal = [NewsEvent(AT + timedelta(minutes=10), "CPI")]
    d = evaluate(good(calendar=cal), CFG)
    assert gate(d, "G1").code == "NEWS_BLACKOUT" and gate(d, "G1").detail == "CPI"
    cal = [NewsEvent(AT + timedelta(minutes=20), "CPI"), NewsEvent(AT, "Fed speech", impact="medium")]
    assert evaluate(good(calendar=cal), CFG).outcome == "PASS"


def test_model_states():
    assert (
        gate(evaluate(good(model=model(events=model().events + (("MODEL_FAILED", MS - MIN),))), CFG), "G3").code
        == "MODEL_FAILED"
    )
    assert gate(evaluate(good(model=model(c3_close_time_ms=MS)), CFG), "G3").code == "C3_CLOSED"
    t1 = model(events=model().events + (("T1_HIT", MS - MIN),))
    assert gate(evaluate(good(model=t1), CFG), "G3").code == "T1_TRADED_THROUGH"
    assert evaluate(good(model=replace(t1, t1_preticked=True)), CFG).outcome == "PASS"


def test_c1_filter_spec_cases():
    # §21: range 30, ATR 60 → 0.5 < 0.6 → C1_TOO_SMALL; range 40 → 0.67 → pass
    assert c1_range_ok(D(100), D(70), D(60), D("0.6"))[0] is False
    ok, ratio = c1_range_ok(D(100), D(60), D(60), D("0.6"))
    assert ok and round(ratio, 2) == D("0.67")
    d = evaluate(good(model=model(c1_high=D(20020), c1_low=D(19990), htf_atr14=D(60))), CFG)
    assert gate(d, "G3").code == "C1_TOO_SMALL" and d.outcome == "SKIP"


def test_neutral_bias_needs_75():
    d = evaluate(good(bias="NEUTRAL"), CFG)  # loses bias_aligned (15) → 70 < 75
    assert d.score.score == D(70) and gate(d, "SCORE").code == "NEUTRAL_SCORE_LOW" and d.outcome == "WAIT"


def test_score_below_min():
    d = evaluate(good(mso_osc=D(55), htf_trend="BEAR", model=model(cisd_before_c2_close=False)), CFG)
    assert d.score.score == D(35) and gate(d, "SCORE").code == "SCORE_BELOW_MIN"


def test_short_signal_mirror():
    m = model(
        direction=Direction.SHORT,
        c1_high=D(20010),
        c1_low=D(19930),
        t1=D(19970),
        t2=D(19930),
        invalid=D(20019),
        cisd_level=D(20005),
    )
    d = evaluate(
        good(
            model=m,
            mso_trend="BEAR",
            mso_osc=D(28),
            htf_trend="BEAR",
            bias="SHORT_ONLY",
            mso_events=(("MSO_CHOCH", "SHORT", MS - 5 * MIN),),
        ),
        CFG,
    )
    assert d.outcome == "PASS" and (d.plan.stop, d.plan.take_profit) == (D(20020), D(19940))


PROVEN = {"one_to_one": True, "t1_rate": (D("0.70"), 40), "atr_pct": (D(50), 40)}


def test_one_to_one_mode_uses_1r_plan():
    d = evaluate(good(**PROVEN), CFG)
    assert d.outcome == "PASS" and d.plan_one_to_one.rr == 1 and d.plan_one_to_one.take_profit == D(20020)
    assert d.plan.rr == 3  # standard plan still computed for stages where 1:1 mode doesn't apply


def test_limit_entry_at_cisd():
    cfg = CFG.model_copy(update={"entry": CFG.entry.model_copy(update={"mode": "limit_cisd"})})
    d = evaluate(good(model=model(cisd_level=D(19998))), cfg)
    assert d.plan.entry == D(19998) and d.features["entry_mode"] == "limit_cisd"


def test_score_session_open_item_spec():
    w = CFG.score.weights
    x = ScoreInputs(True, True, False, D(70), None, True, True, session_open_c1=True)
    base = compute_score(x, w, D(15), D("0.45"), D(0), D(0))
    assert base.score == D(85) and base.max_points == 100  # weight 0 → unchanged
    withw = compute_score(x, w, D(15), D("0.45"), D(10), D(0))
    assert withw.earned["session_open_c1"] == 10 and withw.max_points == 110
    assert withw.score == (D(95) * 100 / 110).quantize(D("0.01"))


def test_score_bos_only_and_tp_rate():
    w = CFG.score.weights
    x = ScoreInputs(False, False, True, D(52), D("0.50"), False, False)
    r = compute_score(x, w, D(15), D("0.45"), D(0), D(0))
    assert r.earned["structure_after_sweep"] == 10 and r.earned["own_tp_rate"] == 15 and r.score == D(25)


def test_cooldown_spec():
    from datetime import date

    s = CooldownState()
    day = date(2026, 11, 5)  # Thursday
    for _ in range(2):
        s = cooldown_on_model_event(s, "MODEL_FAILED", day, 3, 5)
    assert s.streak == 2 and not s.active(day)
    reset = cooldown_on_model_event(s, "T1_HIT", day, 3, 5)
    assert reset.streak == 0  # a success between failures resets the streak
    s = cooldown_on_model_event(s, "MODEL_FAILED", day, 3, 5)
    assert s.active(day) and s.until_session == add_sessions(day, 5) == date(2026, 11, 12)
    assert not s.active(date(2026, 11, 13))


def test_entry_deadline_is_earlier_of_max_wait_or_half_c3():
    confirm, c3 = MS, MS + 15 * MIN
    assert entry_deadline_ms(confirm, c3, 1, 6) == MS + 6 * MIN
    assert entry_deadline_ms(confirm, MS + 60 * MIN, 5, 10) == MS + 30 * MIN


def test_state_machine():
    m = ModelMachine("k")
    m.to("SWEEP", 1)
    m.to("CONFIRMED", 2)
    m.to("ARMED", 3)
    with pytest.raises(IllegalTransition):
        m.to("MANAGING", 4)
    m.to("ENTERED", 4)
    m.to("MANAGING", 5)
    with pytest.raises(IllegalTransition):
        m.to("RESOLVED", 6)
    m.to("RESOLVED", 6, resolution="TP")
    assert m.ever_entered and m.resolution == "TP" and [x[2] for x in m.log][-1] == "RESOLVED"


@pytest.mark.parametrize(
    "over,code,outcome",
    [
        ({"close": D(20012)}, "1TO1_TARGET_BEYOND_T1", "WAIT"),  # E1: risk 32 → 1R target 20044 > T1 20030
        ({"t1_rate": (D("0.90"), 10)}, "1TO1_T1_RATE_UNPROVEN", "SKIP"),  # E2: < 30 samples
        ({"t1_rate": (D("0.60"), 50)}, "1TO1_T1_RATE_LOW", "SKIP"),
        ({"model": model(cisd_before_c2_close=False)}, "1TO1_SCORE_LOW", "WAIT"),  # E3: 60 < 75
        ({"mso_events": (("MSO_BOS", "LONG", MS - 5 * MIN),)}, "1TO1_NEEDS_CHOCH", "WAIT"),  # E4 (score is exactly 75)
        ({"htf_trend": "BEAR"}, "1TO1_BIAS_OR_HTF", "WAIT"),  # E5
        ({"atr_pct": (D(95), 40)}, "1TO1_ATR_EXTREME", "SKIP"),  # E6
        ({"atr_pct": (D(50), 5)}, "1TO1_ATR_UNPROVEN", "SKIP"),
        ({"calendar": [NewsEvent(AT - timedelta(minutes=3), "NFP")]}, "1TO1_NEWS_AFTER", "WAIT"),  # E7
    ],
)
def test_one_to_one_filters(over, code, outcome):
    d = evaluate(good(**{**PROVEN, **over}), CFG)
    g = gate(d, "F1TO1")
    assert not g.passed and g.code == code and d.outcome == outcome, (g, d.outcome)


def test_one_to_one_bos_only_fails_choch_filter_too():
    d = evaluate(good(**PROVEN, mso_events=(("MSO_BOS", "LONG", MS - 5 * MIN),)), CFG)
    assert "1TO1_NEEDS_CHOCH" in gate(d, "F1TO1").detail


def test_filters_never_apply_in_standard_mode():
    d = evaluate(good(t1_rate=(None, 0), atr_pct=(None, 0)), CFG)
    assert d.outcome == "PASS" and all(g.gate != "F1TO1" for g in d.gates)


def test_regime_tags():
    d = evaluate(good(calendar=[NewsEvent(AT + timedelta(hours=3), "FOMC")], atr_pct=(D(42), 40)), CFG)
    assert d.features["tags"] == {
        "weekday": "Thu",
        "slice": "10:00",
        "atr_pct": "42",
        "news_day": True,
        "bias": "LONG_ONLY",
        "one_to_one": False,
    }


def test_score_exclude_unknown_d35():
    w = CFG.score.weights
    # NEUTRAL day + unproven T2 rate: CISD 25 + CHoCH 20 + osc 15 + HTF 10 = 70 of 100
    x = ScoreInputs(True, True, False, D(70), None, False, True, bias_known=False)
    assert compute_score(x, w, D(15), D("0.45"), D(0), D(0)).score == D(70)
    r = compute_score(x, w, D(15), D("0.45"), D(0), D(0), exclude_unknown=True)
    assert r.max_points == 70 and r.score == D(100) and "bias_aligned" not in r.earned
    # a KNOWN miss (bias against the trade) still counts as 0
    known = ScoreInputs(True, True, False, D(70), D("0.40"), False, True, bias_known=True)
    k = compute_score(known, w, D(15), D("0.45"), D(0), D(0), exclude_unknown=True)
    assert k.max_points == 100 and k.score == D(70)


def test_soft_structure_gates_d35():
    soft = CFG.model_copy(
        update={
            "filters": CFG.filters.model_copy(update={"require_mso_agree": False, "require_structure_break": False})
        }
    )
    x = good(mso_trend="BEAR", mso_events=())
    hard = evaluate(x, CFG)
    assert hard.outcome != "PASS" and {g.code for g in hard.gates} >= {"MSO_STRUCTURE_DISAGREES", "NO_STRUCTURE_BREAK"}
    d = evaluate(x, soft)
    g4 = next(g for g in d.gates if g.gate == "G4")
    g5 = next(g for g in d.gates if g.gate == "G5")
    assert g4.passed and "soft" in g4.detail and g5.passed and "soft" in g5.detail


def test_t1_through_allowed_with_limit_entry_d35():
    x = good(model=model(cisd_level=D(19998), events=(("MODEL_CONFIRMED", MS - 10 * MIN), ("T1_HIT", MS - 2 * MIN))))
    assert any(g.code == "T1_TRADED_THROUGH" for g in evaluate(x, CFG).gates)
    cfg = CFG.model_copy(
        update={
            "entry": CFG.entry.model_copy(update={"mode": "limit_cisd"}),
            "filters": CFG.filters.model_copy(update={"t1_through_ok_with_limit": True}),
        }
    )
    assert not any(g.code == "T1_TRADED_THROUGH" for g in evaluate(x, cfg).gates)


def test_profile_disabled_d35():
    cfg = CFG.model_copy(update={"profiles": CFG.profiles.model_copy(update={"enabled": ["STD"]})})
    d = evaluate(good(), cfg)
    assert d.outcome == "SKIP" and d.skip_reason == "PROFILE_DISABLED"


def test_no_break_target_cap_d36():
    soft = CFG.filters.model_copy(update={"require_structure_break": False, "no_break_rr_cap": D(1)})
    tp = CFG.trade_plan.model_copy(update={"rr_min": D(1)})
    cfg = CFG.model_copy(update={"filters": soft, "trade_plan": tp})
    nobreak = evaluate(good(mso_events=()), cfg)
    assert nobreak.plan.rr == 1 and nobreak.features["rr_max"] == "1"
    withbreak = evaluate(good(), cfg)
    assert withbreak.plan.rr == 3 and withbreak.features["rr_max"] == "3.0"


def test_trend_filter_d44():
    """D44: switched-on trend filters block the wrong side (WAIT) and wait while warming up; off = no effect."""
    trend = CFG.filters.trend.model_copy(update={"vwap": True, "utbot_5m": True})
    on = CFG.model_copy(update={"filters": CFG.filters.model_copy(update={"trend": trend})})
    assert evaluate(good(), CFG).outcome == "PASS"  # default off
    assert evaluate(good(trend={"vwap": 1, "utbot_5m": 1}), on).outcome == "PASS"
    d = evaluate(good(trend={"vwap": -1, "utbot_5m": 1}), on)
    assert d.outcome == "WAIT" and d.skip_reason == "TREND_AGAINST"
    d = evaluate(good(trend={"vwap": 1}), on)
    assert d.outcome == "WAIT" and d.skip_reason == "TREND_WARMUP"
    assert d.features["trend"] == {"vwap": 1}


def test_squeeze_switch_d45():
    trend = CFG.filters.trend.model_copy(update={"squeeze_5m_15m": True})
    on = CFG.model_copy(update={"filters": CFG.filters.model_copy(update={"trend": trend})})
    assert evaluate(good(trend={"squeeze_5m_15m": 1}), on).outcome == "PASS"  # long setup, momentum rising up
    d = evaluate(good(trend={"squeeze_5m_15m": 0}), on)  # 5m and 15m disagree → no side → wait
    assert d.outcome == "WAIT" and d.skip_reason == "TREND_AGAINST"
    d = evaluate(good(trend={}), on)
    assert d.outcome == "WAIT" and d.skip_reason == "TREND_WARMUP"
