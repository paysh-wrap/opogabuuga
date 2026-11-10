"""D84 TradingAgents MGC research: pure setup validation/plan, runner prompt/parse, shared agreement rule."""

from datetime import UTC, datetime
from decimal import Decimal as D

import pytest

from app.bias import ta_mgc_research as TR
from app.bias import ta_runner as RUN
from app.config import TaMgcCfg
from app.engine import ai_duo as DU
from app.engine import ta_mgc as TM
from app.engine.trade_plan import Direction

T = D("0.10")
LONG = {"side": "LONG", "confidence": 72, "entry_low": 2700, "entry_high": 2702, "invalidation": 2690,
        "target": 2730, "valid_until": "09:00", "reasons": ["DXY falling", "real yields down"]}  # fmt: skip
KW = {"tick": T, "buffer_ticks": 4, "min_stop_ticks": 16, "cap_pts": D("24.6"), "rr_min": D("1.5"),
      "rr_max": D("3.0"), "rr_preferred": D("2.0")}  # fmt: skip


def test_parse_valid_long_and_short():
    s = TM.parse_setup(LONG, 55)
    assert s.direction is Direction.LONG and s.confidence == 72 and s.reasons == ("DXY falling", "real yields down")
    sh = TM.parse_setup({**LONG, "side": "short", "entry_low": 2700, "entry_high": 2702, "invalidation": 2712,
                         "target": 2670}, 55)  # fmt: skip
    assert sh.direction is Direction.SHORT


@pytest.mark.parametrize(
    ("patch", "code"),
    [
        ({"side": "NONE"}, "RESEARCH_NO_TRADE"),
        ({"side": "MAYBE"}, "SETUP_MALFORMED"),
        ({"entry_low": None}, "SETUP_MALFORMED"),
        ({"target": "abc"}, "SETUP_MALFORMED"),
        ({"invalidation": -5}, "SETUP_MALFORMED"),
        ({"confidence": "high"}, "SETUP_MALFORMED"),
        ({"confidence": True}, "SETUP_MALFORMED"),
        ({"entry_low": 2703}, "SETUP_ZONE_INVALID"),
        ({"invalidation": 2701}, "SETUP_LEVELS_INVALID"),
        ({"target": 2701}, "SETUP_LEVELS_INVALID"),
        ({"confidence": 40}, "SETUP_CONF_LOW"),
    ],
)
def test_parse_rejects_with_reason(patch, code):
    assert TM.parse_setup({**LONG, **patch}, 55) == code
    assert TM.parse_setup("nope", 55) == "SETUP_MALFORMED"


def test_short_levels_and_reasons_default():
    bad = {**LONG, "side": "SHORT", "invalidation": 2699, "target": 2670}
    assert TM.parse_setup(bad, 55) == "SETUP_LEVELS_INVALID"
    ok = TM.parse_setup({**LONG, "reasons": "x"}, 55)
    assert ok.reasons == ()


def test_valid_until_and_zone_and_levels():
    day = "2026-11-10"
    assert TM.valid_until_at("09:00", day).hour == 9 and TM.valid_until_at("09:00", day).tzinfo is not None
    iso = TM.valid_until_at("2026-11-10T14:00:00+00:00", day)
    assert iso == datetime(2026, 11, 10, 14, tzinfo=UTC)
    assert TM.valid_until_at("2026-11-10T09:00:00", day).tzinfo is not None
    assert TM.valid_until_at("soon", day) is None and TM.valid_until_at("9", day) is None
    s = TM.parse_setup(LONG, 55)
    assert TM.in_zone(s, D(2701)) and not TM.in_zone(s, D(2703)) and not TM.in_zone(s, D("2699.9"))
    assert TM.past_levels(s, D(2689)) == "SETUP_INVALIDATED" and TM.past_levels(s, D(2731)) == "TARGET_REACHED"
    assert TM.past_levels(s, D(2701)) is None


def test_plan_two_r_and_floor_and_tag():
    s = TM.parse_setup(
        LONG, 55
    )  # stop = 2690 - 0.4 = 2689.6; entry 2701 → risk 11.4; target 2730 → 2.5R → capped 3.0 cap n/a
    sp = TM.build_plan(s, D(2701), **KW)
    assert sp.plan.stop == D("2689.6") and sp.plan.rr >= D("1.5") and sp.below_preferred is False
    low = TM.parse_setup({**LONG, "target": 2716}, 55)  # (2716-2701)/11.4 = 1.32R → below the 1.5R floor
    assert TM.build_plan(low, D(2701), **KW) == "RR_BELOW_MIN"
    mid = TM.parse_setup({**LONG, "target": 2721}, 55)  # 20/11.4 = 1.75R: allowed, tagged below preferred 2R
    sp = TM.build_plan(mid, D(2701), **KW)
    assert sp.below_preferred is True and sp.plan.rr < D("2.0")
    assert TM.build_plan(s, D(2701), **{**KW, "cap_pts": D(5)}) == "STOP_TOO_WIDE"
    assert TM.build_plan(s, D(2701), **{**KW, "min_stop_ticks": 500}) == "STOP_TOO_TIGHT"


def test_vibe_agreement_is_the_shared_duo_rule():
    s = TM.parse_setup(LONG, 55)
    assert TM.vibe_agrees(s, "LONG", 80, 60) == "AI_AGREE"
    assert TM.vibe_agrees(s, "SHORT", 80, 60) == "AI_DISAGREE"
    assert TM.vibe_agrees(s, "NEUTRAL", 80, 60) == "AI_NEUTRAL"
    assert TM.vibe_agrees(s, None, None, 60) == "AI_VT_MISSING"
    assert TM.vibe_agrees(s, "LONG", 40, 60) == "AI_NOT_STRONG"
    assert DU.agree(1, True, "LONG", 80, 60) == (Direction.LONG, "AI_AGREE")  # same function, same answers
    assert DU.agree(None, True, "LONG", 80, 60) == (None, "AI_TA_MISSING")
    assert DU.agree(0, False, "LONG", 80, 60) == (None, "AI_NEUTRAL")
    assert DU.ai_side("BUY", "LONG", 80, 60) == (Direction.LONG, "AI_AGREE")


def test_config_validation():
    assert TaMgcCfg().rr_preferred == D("2.0")
    for bad in (
        {"rr_preferred": D("1.2")},
        {"min_confidence": 101},
        {"research_at": "25:00"},
        {"stop_buffer_ticks": -1},
    ):
        with pytest.raises(ValueError):
            TaMgcCfg(**bad)


# ---------- runner (stdlib, runs inside .venv-ta): prompt + parsing, fake LLM ----------
def test_runner_parse_and_research_with_fake_llm():
    line = 'blah\nTA_SETUP {"side": "LONG", "confidence": 70}'
    assert RUN.parse_setup_line(line) == {"side": "LONG", "confidence": 70}
    assert RUN.parse_setup_line("no line") is None and RUN.parse_setup_line("TA_SETUP {bad json}") is None
    assert RUN.parse_setup_line("TA_SETUP [1]") is None

    class Resp:
        content = 'analysis\nTA_SETUP {"side": "NONE", "confidence": 10}'

    seen = []

    class Llm:
        def invoke(self, prompt):
            seen.append(prompt)
            return Resp()

    req = {"ticker": "GLD", "date": "2026-11-10", "market": "MGC", "context": {"calendar": ["CPI 08:30"]}}
    out = RUN.finish_research(req, {"final_trade_decision": "Buy gold", "market_report": "up"}, "Buy", Llm(), "0.7.1")
    assert out["ok"] and out["setup"] == {"side": "NONE", "confidence": 10} and out["version"] == "0.7.1"
    p = seen[0]
    for must in ("US dollar / DXY", "real yields", "Fed and CPI", "risk sentiment", "1:2 preferred", "never below 1.5R",
                 "CPI 08:30", "TA_SETUP"):  # fmt: skip
        assert must in p
    no = RUN.finish_research(req, {}, "Buy", None, "0.7.1")
    assert no["ok"] is False and "no LLM handle" in no["error"]


def test_research_due_rules():
    from datetime import timedelta
    from zoneinfo import ZoneInfo

    et = ZoneInfo("America/New_York")
    wed = datetime(2026, 11, 11, 2, 50, tzinfo=et)
    assert TR.research_due(wed, "02:45", None, False, "11:30")
    assert not TR.research_due(wed, "02:45", None, True, "11:30")  # done
    assert not TR.research_due(wed.replace(hour=2, minute=40), "02:45", None, False, "11:30")  # too early
    assert not TR.research_due(wed.replace(hour=11, minute=30), "02:45", None, False, "11:30")  # window over
    assert not TR.research_due(datetime(2026, 11, 14, 3, tzinfo=et), "02:45", None, False, "11:30")  # Saturday
    assert not TR.research_due(wed, "02:45", (wed - timedelta(minutes=10)).isoformat(), False, "11:30")
    assert TR.research_due(wed, "02:45", (wed - timedelta(minutes=31)).isoformat(), False, "11:30")
