"""§17: Lab cycle (walk-forward on recorded bars) + apply at 18:00 + rollback."""

import asyncio
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

import yaml

from app.config import load_yaml_decimal
from app.indicators.bars import Bar
from app.lab import cycle
from app.lab.cycle import apply_approved, evaluate, rollback_lab, split_sessions, write_rules
from app.models import Proposal, RiskProfile

NOW = datetime(2026, 11, 7, 13, 0, tzinfo=UTC)


def _bars(days):
    out = []
    for d in range(days):
        t0 = int(datetime(2026, 10, 1, 14, 0, tzinfo=UTC).timestamp() * 1000) + d * 86_400_000
        out += [Bar(t0 + i * 60_000, t0 + (i + 1) * 60_000, D(1), D(2), D(0), D(1)) for i in range(3)]
    return out


def test_split_is_chronological():
    b = _bars(8)
    tr, te = split_sessions(b)
    assert len(tr) == 18 and len(te) == 6 and max(x.open_ms for x in tr) < min(x.open_ms for x in te)
    assert split_sessions(_bars(1)) == (_bars(1), [])


def test_write_rules_applies_diff(tmp_path, loaded_rules):
    raw = load_yaml_decimal(loaded_rules.source_text)
    p = write_rules(raw, {"score.min_score": D(65), "filters.c1_min_range_atr": D("0.5")}, tmp_path, "x")
    got = yaml.safe_load(p.read_text())
    assert got["score"]["min_score"] == 65 and got["filters"]["c1_min_range_atr"] == 0.5


def test_evaluate_picks_a_winner_only_if_it_holds_out_of_sample(tmp_path, loaded_rules):
    raw = load_yaml_decimal(loaded_rules.source_text)
    cfg = loaded_rules.rules.model_copy(
        update={"self_improvement": loaded_rules.rules.self_improvement.model_copy(update={"min_oos_trades": 1})}
    )
    good = "c1_min_range_atr: 0.5"

    def run(bars, symbol, path: Path):
        better = good in path.read_text()
        n = 4 if len(bars) > 10 else 2
        return [{"pnl": "1", "net_r": "2" if better else "1"} for _ in range(n)] + [{"pnl": "-1", "net_r": "-1"}]

    _, _, win, why, tried = evaluate(raw, cfg, "MNQ", _bars(8), run, tmp_path)
    assert tried > 1 and win is not None and win.diff == {"filters.c1_min_range_atr": D("0.5")} and why == []

    def flat(bars, symbol, path):
        return [{"pnl": "1", "net_r": "1"}]

    _, _, win, why, _ = evaluate(raw, cfg, "MNQ", _bars(8), flat, tmp_path)
    assert win is None and "no change beat" in why[0]

    def only_train(bars, symbol, path):  # better on train, worse out of sample
        return [{"pnl": "1", "net_r": "3" if (good in path.read_text() and len(bars) > 10) else "1"}]

    _, _, win, why, _ = evaluate(raw, cfg, "MNQ", _bars(8), only_train, tmp_path)
    assert win is None and any("expectancy" in w for w in why)


def test_cycle_statuses_and_proposal(authed, monkeypatch):
    app = authed.app
    st = app.state
    with st.sessionmaker() as s:
        assert asyncio.run(cycle.run_cycle(app, s, NOW))[0]["status"] == "not_enough_data"
        s.add(Proposal(challenger_version=1, diff={}, metrics={}, explanation="x", status="pending"))
        s.commit()
        assert asyncio.run(cycle.run_cycle(app, s, NOW))[0]["status"] == "waiting"
        s.query(Proposal).delete()
        s.add(RiskProfile(kind="lab", version=1, settings={}, author="lab", note="", diff={}, active=True))
        s.commit()
        assert asyncio.run(cycle.run_cycle(app, s, NOW))[0]["status"] == "cooldown"
        s.query(RiskProfile).filter(RiskProfile.kind == "lab").delete()
        s.commit()
        monkeypatch.setattr("app.backtest.nightly.recorded_bars", lambda s, sym, since: _bars(25))
        win = cycle.Candidate({"score.min_score": D(63)}, cycle.Perf(10, 7, D(5)), cycle.Perf(5, 4, D(3)))
        champ = cycle.Perf(10, 6, D(2))
        monkeypatch.setattr(cycle, "evaluate", lambda *a: (champ, champ, win, [], 3))
        rep = asyncio.run(cycle.run_cycle(app, s, NOW))
        assert rep[0]["status"] == "proposal" and rep[0]["diff"] == {"score.min_score": "63"}
        monkeypatch.setattr(cycle, "evaluate", lambda *a: (champ, champ, None, ["no"], 3))
        s.query(Proposal).delete()
        s.commit()
        assert asyncio.run(cycle.run_cycle(app, s, NOW))[0]["status"] == "champion_kept"
        si = st.rules.rules.self_improvement
        st.rules.rules = st.rules.rules.model_copy(
            update={"self_improvement": si.model_copy(update={"enabled": False})}
        )
        assert asyncio.run(cycle.run_cycle(app, s, NOW)) == [{"status": "disabled"}]


def test_apply_at_reset_validates_then_rollback(authed):
    st = authed.app.state
    with st.sessionmaker() as s:
        s.add(
            Proposal(
                challenger_version=1, diff={"score.min_score": "63"}, metrics={}, explanation="ok", status="approved"
            )
        )
        s.add(
            Proposal(
                challenger_version=2, diff={"trade_plan.rr_min": "1"}, metrics={}, explanation="bad", status="approved"
            )
        )
        s.commit()
        assert apply_approved(s, st.rules.base, st.clock) == [1]
        st.rules.refresh(s)
        assert st.rules.rules.score.min_score == 63
        assert [p.status for p in s.query(Proposal).order_by(Proposal.id)] == ["applied", "invalid"]
        s.add(
            Proposal(
                challenger_version=3, diff={"score.min_score": "66"}, metrics={}, explanation="", status="approved"
            )
        )
        s.commit()
        assert apply_approved(s, st.rules.base, st.clock) == [3]
        assert rollback_lab(s, st.clock, "u") == 1
        st.rules.refresh(s)
        assert st.rules.rules.score.min_score == 63
        assert rollback_lab(s, st.clock, "u") == 0
        assert rollback_lab(s, st.clock, "u") == 0


def test_lab_api_cycle_and_rollback(authed):
    r = authed.post("/api/lab/cycle").json()
    assert r["report"][0]["status"] in ("not_enough_data", "disabled")
    assert authed.post("/api/lab/rollback").json() == {"active_lab_version": 0}
    body = authed.get("/api/lab").json()
    assert body["lab_layer"] is None and body["last_cycle"]["report"] and "score.min_score" in body["tunables"]


def test_scheduler_lab_job_applies_and_runs_weekly(authed, monkeypatch):
    from app import main

    st = authed.app.state
    calls = []

    async def fake_cycle(app, s, now):
        calls.append(now)
        return [{"status": "champion_kept"}]

    monkeypatch.setattr("app.lab.cycle.run_cycle", fake_cycle)
    sat = datetime(2026, 11, 7, 23, 30, tzinfo=UTC)  # Sat 18:30 ET: after reset and after Sat 08:00
    with st.sessionmaker() as s:
        s.add(
            Proposal(
                challenger_version=1, diff={"score.min_score": "63"}, metrics={}, explanation="", status="approved"
            )
        )
        s.commit()
        asyncio.run(main._lab(authed.app, s, sat))
        asyncio.run(main._lab(authed.app, s, sat + timedelta(minutes=1)))  # once per session / week
    assert len(calls) == 1 and st.rules.rules.score.min_score == 63
