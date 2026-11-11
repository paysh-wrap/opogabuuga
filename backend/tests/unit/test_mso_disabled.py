"""D91: BigBeluga MSO off by default - G4-G6 do not exist, the score is renormalised to 100 without the MSO parts."""

from decimal import Decimal as D

from app.config import load_rules
from app.engine.confluence import evaluate
from app.engine.scoring import ScoreInputs, compute_score
from tests.conftest import REPO_ROOT, RULES_PATH
from tests.unit.test_confluence import good

ON = load_rules(RULES_PATH).rules  # legacy Daily plan = MSO on (regression baseline for the older tests)
OFF = ON.model_copy(
    update={
        "indicators": ON.indicators.model_copy(update={"mso": ON.indicators.mso.model_copy(update={"enabled": False})})
    }
)
W = ON.score.weights


def _score(mso_enabled, **kw):
    x = dict(
        cisd_before_c2_close=True,
        choch_after_sweep=True,
        bos_after_sweep=False,
        osc=D(72),
        own_tp_rate=D("0.9"),
        bias_aligned=True,
        htf_agrees=True,
    )
    x.update(kw)
    return compute_score(
        ScoreInputs(**x), W, ON.score.osc_strength_min, ON.score.tp_rate_min, D(0), D(0), False, mso_enabled
    )


def test_every_offered_plan_has_mso_off_and_only_the_legacy_baseline_has_it_on():
    rules_dir = REPO_ROOT / "config" / "rules"
    for f in sorted(rules_dir.glob("lucid_*.yaml")):
        assert load_rules(f).rules.indicators.mso.enabled is (f.stem == "lucid_daily_25k"), f.name


def test_gates_g4_g5_g6_are_hidden_and_the_signal_still_passes_without_any_mso_input():
    on = evaluate(good(), ON)
    assert [g.gate for g in on.gates] == ["G1", "G2", "G3", "G4", "G5", "G6", "G7", "SCORE"]
    # no MSO snapshot, no MSO events at all (a heartbeat without `mso`)
    off = evaluate(good(mso_trend=None, mso_osc=None, htf_trend=None, mso_events=()), OFF)
    assert [g.gate for g in off.gates] == ["G1", "G2", "G3", "G7", "SCORE"]
    assert off.outcome == "PASS" and off.features["choch"] is False and off.features["bos"] is False


def test_mso_disagreement_cannot_block_when_off():
    d = evaluate(good(mso_trend="BEAR", mso_osc=D(30), mso_events=(("MSO_DIV", "SHORT", 0),)), OFF)
    assert d.outcome == "PASS"  # the same input is a WAIT with MSO on (G4)
    assert evaluate(good(mso_trend="BEAR", mso_osc=D(30)), ON).outcome == "WAIT"


def test_no_break_rr_cap_is_not_applied_without_mso():
    capped = OFF.model_copy(update={"filters": OFF.filters.model_copy(update={"no_break_rr_cap": D("2")})})
    assert evaluate(good(mso_events=()), capped).features["rr_max"] == str(capped.trade_plan.rr_max)
    capped_on = ON.model_copy(update={"filters": ON.filters.model_copy(update={"no_break_rr_cap": D("2")})})
    assert evaluate(good(mso_events=()), capped_on).features["rr_max"] == "2"


def test_score_is_renormalised_to_100_without_the_mso_components():
    full = _score(True)
    assert set(full.earned) == {
        "cisd_before_c2_close",
        "structure_after_sweep",
        "osc_strength",
        "own_tp_rate",
        "bias_aligned",
        "htf_mso_agrees",
    }
    assert full.score == D(100)
    off = _score(False)
    assert set(off.earned) == {"cisd_before_c2_close", "own_tp_rate", "bias_aligned"}
    assert off.max_points == W["cisd_before_c2_close"] + W["own_tp_rate"] + W["bias_aligned"]
    assert off.score == D(100)  # everything that still exists earned → 100, not 100 minus the missing MSO points
    half = _score(False, cisd_before_c2_close=False)
    assert half.score == ((W["own_tp_rate"] + W["bias_aligned"]) * 100 / off.max_points).quantize(D("0.01"))
    # MSO inputs are ignored entirely when off
    assert _score(False, choch_after_sweep=False, osc=None, htf_agrees=False).score == D(100)
    # the optional unknown-exclusion still works on top
    r = compute_score(
        ScoreInputs(True, False, False, None, None, False, False, bias_known=False),
        W,
        ON.score.osc_strength_min,
        ON.score.tp_rate_min,
        D(0),
        D(0),
        True,
        False,
    )
    assert set(r.earned) == {"cisd_before_c2_close"} and r.score == D(100)
