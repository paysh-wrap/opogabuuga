from app.bias.policy import Call, LedgerStats, Policy, combine, gate, ledger_stats, score, wilson_lower

MGC, MNQ = Policy(bias_matters=True), Policy(bias_matters=False)
GOOD = LedgerStats(40, 0.75, 0.20, 0.62)


def test_combine_agreement_strong():
    c = combine("BUY", "LONG", 80, MGC)
    assert c.direction == 1 and c.agree_strong and 0.5 < c.prob_up < 0.7


def test_combine_disagreement_not_strong():
    assert not combine("BUY", "SHORT", 90, MGC).agree_strong
    assert not combine("OVERWEIGHT", "LONG", 90, MGC).agree_strong
    assert not combine("BUY", "LONG", 59, MGC).agree_strong
    assert combine(None, None, None, MGC) == Call(0, 0.5, False)


def test_gate_mnq_never_blocks():
    assert gate(Call(1, 0.6, True), GOOD, MNQ) == ("NEUTRAL", "ADVISORY_MARKET")


def test_gate_requires_agreement_warmup_and_proof():
    strong = Call(-1, 0.4, True)
    assert gate(Call(-1, 0.45, False), GOOD, MGC)[1] == "ADVISORY_NO_AGREEMENT"
    assert gate(strong, LedgerStats(29, 0.9, 0.1, 0.7), MGC)[1] == "ADVISORY_WARMUP"
    assert gate(strong, LedgerStats(40, 0.6, 0.24, 0.47), MGC)[1] == "ADVISORY_UNPROVEN"
    assert gate(strong, LedgerStats(40, 0.8, 0.26, 0.65), MGC)[1] == "ADVISORY_UNPROVEN"
    assert gate(strong, GOOD, MGC) == ("SHORT_ONLY", "GATED")


def test_score_and_ledger():
    assert score(0.6, 1, True) == (1, 0.16)
    assert score(0.5, 0, False) == (None, 0.25)
    st = ledger_stats([(1, 0.16)] * 20 + [(0, 0.36)] * 10 + [(None, 0.25)])
    assert st.n == 30 and abs(st.hit_rate - 2 / 3) < 1e-3 and st.wilson_lb < st.hit_rate
    assert ledger_stats([]).n == 0 and wilson_lower(0, 0) == 0.0


def test_wilson_needs_sample():
    assert wilson_lower(18, 30) < 0.55 < wilson_lower(180, 300) + 0.01
