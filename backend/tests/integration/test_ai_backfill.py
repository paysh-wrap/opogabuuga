"""D78: backfill is flagged + isolated from the live proof; calls-needed; tolerant scoring; retry; coverage; API."""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal as D

from app.bias import backfill as bf
from app.bias import ledger as L
from app.bias import service as svc
from app.bias.policy import LedgerStats
from app.bias.tradingagents_adapter import RunnerResult
from app.clock import ET
from app.models import Bar, BiasDecision


def _bars(s, d: date, up=True, first=(9, 33), last=(15, 58)):
    for (hh, mm), o, c in ((first, D(20000), D(20000)), (last, D(20000), D(20100) if up else D(19900))):
        s.add(
            Bar(
                symbol="MNQ",
                tf="1",
                close_time=datetime(d.year, d.month, d.day, hh, mm, tzinfo=ET),
                o=o,
                h=max(o, c),
                l=min(o, c),
                c=c,
                v=D(1),
                source="tradingview",
            )
        )


def _row(s, d, label, proxy="QQQ"):
    s.add(BiasDecision(session_date=d, proxy=proxy, raw_rating=label, mapped="NEUTRAL", reasoning="", version=""))


def test_helpers_and_calls_needed():
    assert bf.bf_proxy("QQQ") == "QQQ.BF" and bf.is_backfill("QQQ.BF") and not bf.is_backfill("QQQ")
    days = bf.last_sessions(date(2026, 11, 9), 5)  # Mon: previous Fri..Mon-before
    assert (
        days == sorted(days) and all(d.weekday() < 5 for d in days) and len(days) == 5 and max(days) < date(2026, 11, 9)
    )
    e = bf.estimate(60, True, "qwen")
    assert e["tool_runs"] == 120 and bf.estimate(10, False, "x")["tool_runs"] == 10
    n = L.calls_needed(LedgerStats(40, 0.9, 0.1, 0.8), 30, 0.7)
    assert n == {"at_current_rate": 0, "best_case": 0}
    n = L.calls_needed(LedgerStats(10, 0.6, 0.25, 0.4), 30, 0.7)
    assert n["at_current_rate"] is None and n["best_case"] is not None and n["best_case"] >= 20


def test_tolerant_scoring_and_coverage(client):
    today = date(2026, 11, 9)
    with client.app.state.sessionmaker() as s:
        d1, d2 = date(2026, 11, 5), date(2026, 11, 6)
        _bars(s, d1)  # first bar 09:33 and last 15:58, not the exact edges
        _row(s, d1, "BUY·VT LONG 80")
        _row(s, d2, "BUY")  # no bars
        s.commit()
        assert L.session_outcome(s, "MNQ", d1) is True and L.session_outcome(s, "MNQ", d2) is None
        cov = {c["day"]: c for c in L.coverage(s, "QQQ", "MNQ", today, days=4)}
        assert cov["2026-11-05"] == {"day": "2026-11-05", "ta": True, "vt": True, "scored": True}
        assert cov["2026-11-06"]["vt"] is False and cov["2026-11-06"]["scored"] is False
        assert cov["2026-11-09"]["ta"] is False


def test_retry_due():
    now = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)  # 07:00 ET Monday
    assert svc.retry_due(now, None, True) and not svc.retry_due(now, None, False)
    assert not svc.retry_due(now, (now - timedelta(minutes=10)).isoformat(), True)
    assert svc.retry_due(now, (now - timedelta(minutes=31)).isoformat(), True)
    late = datetime(2026, 11, 9, 15, 0, tzinfo=UTC)  # 10:00 ET
    assert not svc.retry_due(late, None, True)
    assert not svc.retry_due(datetime(2026, 11, 7, 12, 0, tzinfo=UTC), None, True)  # Saturday


class _Vault:
    def open(self, _c):
        return {"llm_provider": "qwen", "api_key": "k"}


class _TA:
    def __init__(self, results):
        self.results, self.dates = list(results), []

    async def run(self, ticker, day, env):
        self.dates.append(day)
        return self.results.pop(0)


def _setup(client):
    from app.models import ApiCredential

    with client.app.state.sessionmaker() as s:
        s.add(ApiCredential(provider="tradingagents", ciphertext=b"x"))
        s.commit()
    r = client.app.state.rules.rules
    return r, client.app.state.sessionmaker


def _ok(rating):
    return RunnerResult(True, {"rating": rating, "decision": "d", "version": "0.7.1"})


def test_job_stores_backfill_apart_and_stops_on_errors(client, monkeypatch):
    r, sm = _setup(client)
    notes = []
    today = date(2026, 11, 9)
    ta = _TA([_ok("Buy"), _ok("Sell")])
    job = bf.Job(status="running")
    asyncio.run(
        bf.run_job(
            job, sm, ta, _Vault(), r, client.app.state.clock, lambda *a, **k: notes.append(a), today, 2, None, pause_s=0
        )
    )
    assert job.status == "done" and job.done == 2 and len(ta.dates) == 2 and max(ta.dates) < today  # as-of past dates
    with sm() as s:
        rows = s.query(BiasDecision).all()
        assert {x.proxy for x in rows} == {"QQQ.BF"} and all(x.version.startswith("BACKFILL:") for x in rows)
        # live ledger / live today-call never see them
        assert L.status(s, "QQQ", "MNQ", today, 0.7)["stats"]["n"] == 0 and svc._done(s, ta.dates[0], "QQQ") is False
    # resumable: nothing left to do
    ta2 = _TA([])
    job2 = bf.Job(status="running")
    asyncio.run(
        bf.run_job(job2, sm, ta2, _Vault(), r, client.app.state.clock, lambda *a, **k: None, today, 2, None, pause_s=0)
    )
    assert job2.status == "done" and job2.skipped == 2 and ta2.dates == []
    # three errors in a row → stop + banner
    ta3 = _TA([RunnerResult(False, {"error": "boom"})] * 3)
    job3 = bf.Job(status="running")
    asyncio.run(
        bf.run_job(
            job3,
            sm,
            ta3,
            _Vault(),
            r,
            client.app.state.clock,
            lambda *a, **k: notes.append(a),
            today,
            10,
            None,
            pause_s=0,
        )
    )
    assert (
        job3.status == "stopped_on_error"
        and job3.failed == 3
        and "boom" in (job3.error or "")
        and notes[-1][0] == "error"
    )


def test_job_cancel_and_missing_key(client):
    r, sm = _setup(client)
    today = date(2026, 11, 9)
    job = bf.Job(status="running", cancel=True)
    asyncio.run(
        bf.run_job(
            job, sm, _TA([]), _Vault(), r, client.app.state.clock, lambda *a, **k: None, today, 3, None, pause_s=0
        )
    )
    assert job.status == "cancelled"
    with sm() as s:
        s.query(__import__("app.models", fromlist=["ApiCredential"]).ApiCredential).delete()
        s.commit()
    notes = []
    job2 = bf.Job(status="running")
    asyncio.run(
        bf.run_job(
            job2,
            sm,
            _TA([]),
            _Vault(),
            r,
            client.app.state.clock,
            lambda *a, **k: notes.append(a),
            today,
            3,
            None,
            pause_s=0,
        )
    )
    assert job2.status == "stopped_on_error" and "key not set" in (job2.error or "") and notes


def test_api(authed, monkeypatch):
    c = authed
    g = c.get("/api/ai-ledger").json()
    assert g["live"]["state"] in ("WARMUP", "UNPROVEN") and "calls_needed" in g["live"]
    assert "badge" not in g["backfill_estimate"] and "does NOT count" in g["backfill_estimate"]["label"]
    assert g["preview"]["configured"] is False and len(g["coverage"]) == 30
    assert c.post("/api/ai-ledger/backfill", json={"days": 5}).status_code == 400  # no key
    assert c.post("/api/ai-ledger/backfill", json={"days": 0}).status_code == 422
    assert c.get("/api/ai-ledger/backfill/preview?days=7").json()["days"] == 7
    assert c.post("/api/ai-ledger/backfill/cancel").json() == {"cancelling": False}
    started = []

    async def fake(job, *a, **k):
        started.append(1)
        job.status = "done"

    monkeypatch.setattr(bf, "run_job", fake)
    monkeypatch.setattr(bf, "preview", lambda *a, **k: {"configured": True, "days": 5})
    assert c.post("/api/ai-ledger/backfill", json={"days": 5}).json()["started"] is True
    c.app.state.bf_job.status = "running"
    assert c.post("/api/ai-ledger/backfill", json={"days": 5}).status_code == 409
