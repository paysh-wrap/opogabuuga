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


# ---------- §17.3 shadow + §17.4 auto-rollback (the self-looping part) ----------
from app.lab.cycle import auto_rollback, shadow_check, shadow_verdict  # noqa: E402
from app.models import Trade  # noqa: E402


def _si(**kw):
    from types import SimpleNamespace

    base = {"shadow_min_sessions": 10, "shadow_min_trades": 20, "shadow_max_sessions": 30}
    return SimpleNamespace(**(base | kw))


def test_shadow_verdict_rules():
    P = cycle.Perf
    assert shadow_verdict(P(20, 12, D(4)), P(20, 12, D(5)), 5, _si()) == "wait"
    assert shadow_verdict(P(20, 12, D(4)), P(10, 6, D(5)), 12, _si()) == "wait"
    assert shadow_verdict(P(20, 12, D(4)), P(10, 6, D(5)), 30, _si()) == "fail"
    assert shadow_verdict(P(20, 12, D(4)), P(20, 13, D(5)), 10, _si()) == "pass"
    assert shadow_verdict(P(20, 12, D(4)), P(20, 11, D(9)), 10, _si()) == "fail"  # lower win rate never passes


def _shadow_prop(s, created):
    p = Proposal(
        challenger_version=1,
        diff={"score.min_score": "63"},
        metrics={"symbol": "MNQ", "oos_champion_e": "0.1"},
        explanation="x",
        status="shadow",
    )
    p.created_at = created
    s.add(p)
    s.commit()
    return p


def test_shadow_check_moves_proposal_to_ready_or_failed(authed, monkeypatch):
    app = authed.app
    st = app.state
    monkeypatch.setattr("app.backtest.nightly.recorded_bars", lambda s, sym, since: _bars(12))

    def run(bars, symbol, path):
        chal = "min_score: 63" in path.read_text()
        return [{"pnl": "1", "net_r": "2" if chal else "1"}] * 15 + [{"pnl": "-1", "net_r": "-1"}] * 7

    with st.sessionmaker() as s:
        p = _shadow_prop(s, NOW - timedelta(days=20))
        rep = asyncio.run(shadow_check(app, s, NOW, run))
        assert rep == [{"proposal": p.id, "verdict": "pass", "sessions": 12}]
        s.refresh(p)
        assert p.status == "pending" and p.metrics["shadow"]["verdict"] == "pass"
        assert authed.put(f"/api/lab/proposals/{p.id}", json={"status": "approved"}).json()["status"] == "approved"
        si = st.rules.rules.self_improvement
        st.rules.rules = st.rules.rules.model_copy(
            update={"self_improvement": si.model_copy(update={"auto_promote_paper": True})}
        )
        q = _shadow_prop(s, NOW - timedelta(days=20))
        asyncio.run(shadow_check(app, s, NOW, run))
        s.refresh(q)
        assert q.status == "approved"  # paper + auto_promote_paper → self-looping without a click
        r = _shadow_prop(s, NOW - timedelta(days=20))
        asyncio.run(
            shadow_check(
                app,
                s,
                NOW,
                lambda b, sym, path: (
                    [{"pnl": "-1", "net_r": "-1"}] * 25
                    if "min_score: 63" in path.read_text()
                    else [{"pnl": "1", "net_r": "1"}] * 25
                ),
            )
        )
        s.refresh(r)
        assert r.status == "shadow_failed"


def test_auto_rollback_on_live_expectancy(authed):
    st = authed.app.state
    with st.sessionmaker() as s:
        assert auto_rollback(authed.app, s, NOW) is None
        p = Proposal(
            challenger_version=1,
            diff={"score.min_score": "63"},
            metrics={"oos_champion_e": "0.2"},
            explanation="",
            status="approved",
        )
        s.add(p)
        s.commit()
        apply_approved(s, st.rules.base, st.clock)
        st.rules.refresh(s)
        aid = authed.post("/api/accounts", json={"label": "A", "stage": "EVAL"}).json()["id"]
        t0 = datetime.now(UTC) + timedelta(minutes=1)
        for i in range(29):
            s.add(
                Trade(
                    account_id=aid,
                    symbol="MGC",
                    direction="LONG",
                    qty=1,
                    entry=D(1),
                    exit=D(1),
                    pnl_usd=D(-1),
                    risk_usd=D(50),
                    net_r=D(-1),
                    opened_at=t0,
                    closed_at=t0 + timedelta(minutes=i),
                )
            )
        s.commit()
        assert auto_rollback(authed.app, s, NOW)["status"] == "kept"  # 29 < 30 trades: too early to judge
        s.add(
            Trade(
                account_id=aid,
                symbol="MGC",
                direction="LONG",
                qty=1,
                entry=D(1),
                exit=D(1),
                pnl_usd=D(-1),
                risk_usd=D(50),
                net_r=D(-1),
                opened_at=t0,
                closed_at=t0 + timedelta(minutes=40),
            )
        )
        s.commit()
        r = auto_rollback(authed.app, s, NOW)
        assert r["status"] == "rolled_back" and r["active_version"] == 0
        s.refresh(p)
        assert p.status == "rolled_back" and st.rules.rules.score.min_score == 60


def test_nightly_runs_shadow_and_rollback(authed, monkeypatch):
    from app import main

    calls = []

    async def fake_nightly(app, s, now, days=30):
        calls.append("bt")
        return []

    monkeypatch.setattr("app.backtest.nightly.nightly", fake_nightly)
    fri = datetime(2026, 11, 6, 22, 20, tzinfo=UTC)  # Fri 17:20 ET
    with authed.app.state.sessionmaker() as s:
        asyncio.run(main._nightly(authed.app, s, fri))
        from app.automation import state as stt

        rep = stt.get_setting(s, "lab.last_nightly")
    assert calls == ["bt"] and rep["shadow"] == [] and rep["rollback"] is None


def test_invalid_candidates_are_skipped_not_crashing(tmp_path, loaded_rules):
    from app.lab.cycle import valid_rules_file

    raw = load_yaml_decimal(loaded_rules.source_text)
    assert valid_rules_file(write_rules(raw, {}, tmp_path, "ok"))
    one = raw["one_to_one_mode"]["filters"]["min_score"]
    bad = write_rules(raw, {"score.min_score": D(str(one)) + 3}, tmp_path, "bad")  # above the 1:1 minimum
    assert not valid_rules_file(bad)
    seen = []

    def run(bars, symbol, path):
        seen.append(path.name)
        return [{"pnl": "1", "net_r": "1"}]

    evaluate(raw, loaded_rules.rules, "MNQ", _bars(8), run, tmp_path)
    assert seen and all(n.startswith(("champion", "c")) for n in seen)
