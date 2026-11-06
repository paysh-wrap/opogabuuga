"""PUT /api/accounts/selection (§12) and GET /api/gate/purchase (§16.9)."""

from app.models import Account, BacktestRun


def _mk(authed, n):
    return [authed.post("/api/accounts", json={"label": f"A{i}", "stage": "EVAL"}).json()["id"] for i in range(n)]


def test_selection_selects_first_n_in_priority_order(authed):
    ids = _mk(authed, 3)
    r = authed.put("/api/accounts/selection", json={"count": 2, "order": [ids[2], ids[0]]})
    assert r.status_code == 200, r.text
    assert r.json() == {"count": 2, "order": [ids[2], ids[0], ids[1]], "selected": [ids[2], ids[0]]}
    with authed.app.state.sessionmaker() as s:
        assert [s.get(Account, i).selected for i in ids] == [True, False, True]
    # no order given: keeps the stored priority, only the count changes
    r = authed.put("/api/accounts/selection", json={"count": 1}).json()
    assert r["selected"] == [ids[2]]


def test_selection_validation(authed):
    ids = _mk(authed, 1)
    assert authed.put("/api/accounts/selection", json={"count": 0}).status_code == 422
    assert authed.put("/api/accounts/selection", json={"count": 6}).status_code == 422
    assert authed.put("/api/accounts/selection", json={"count": 1, "order": [999]}).status_code == 422
    assert authed.put("/api/accounts/selection", json={"count": 1, "order": [ids[0], ids[0]]}).status_code == 422


def _run(authed, metrics, status="done"):
    with authed.app.state.sessionmaker() as s:
        s.add(BacktestRun(kind="ON_DEMAND", status=status, cache_key="k", params={}, metrics=metrics))
        s.commit()


def test_gate_without_runs(authed):
    g = authed.get("/api/gate/purchase").json()
    assert g["run_id"] is None and g["passed"] is False
    assert {"violations", "demo_days", "semi_auto_sessions"} <= set(g["unmeasured"])


def test_gate_passing_metrics_still_needs_unmeasured_items(authed):
    _run(
        authed,
        {"stats": {"trades": 120, "avg_r": "0.25", "profit_factor": "1.5"}, "monte_carlo_eval": {"pass_rate": "0.6"}},
    )
    g = authed.get("/api/gate/purchase").json()
    ok = {c["key"]: c["ok"] for c in g["checks"]}
    assert ok["trades"] and ok["e_net_r"] and ok["profit_factor"] and ok["monte_carlo"]
    assert g["passed"] is False  # violations/demo/SEMI sessions cannot be measured here


def test_gate_failing_metrics(authed):
    _run(authed, {"stats": {"trades": 10, "avg_r": "0.05", "profit_factor": "1.0"}})
    _run(authed, {}, status="running")  # ignored: only finished runs count
    ok = {c["key"]: c["ok"] for c in authed.get("/api/gate/purchase").json()["checks"]}
    assert ok["trades"] is False and ok["e_net_r"] is False and ok["profit_factor"] is False
    assert ok["monte_carlo"] is False
