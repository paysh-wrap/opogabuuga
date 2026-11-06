import time

from tests.unit.test_indicators import T0


def _csv():
    rows = ["timestamp,open,high,low,close,volume"]
    px = 20000.0
    for i in range(60):
        rows.append(f"{T0 + i * 60000},{px},{px + 1},{px - 1},{px + 0.25},5")
        px += 0.25
    return "\n".join(rows) + "\n"


def test_backtest_api_runs_in_background(authed):
    r = authed.post("/api/backtest?bias=LONG_ONLY", content=_csv(), headers={"content-type": "text/csv"})
    assert r.status_code == 200, r.text
    rid = r.json()["id"]
    for _ in range(100):
        run = next(x for x in authed.get("/api/backtest").json()["runs"] if x["id"] == rid)
        if run["status"] != "running":
            break
        time.sleep(0.1)
    assert run["status"] == "done", run
    m = run["metrics"]
    assert m["sessions"] == 1 and "stats" in m and "monte_carlo_eval" in m and m["assumptions"]
    assert authed.get(f"/api/backtest/{rid}/trades").json() == {"trades": []}


def test_backtest_rejects_bad_csv(authed):
    assert authed.post("/api/backtest", content="nope\n", headers={"content-type": "text/csv"}).status_code == 422


def test_metrics_from_trades(authed):
    from app.api.backtest import metrics

    tr = [
        {"opened_at": "2026-01-05T15:00:00+00:00", "pnl": "300", "net_r": "2", "direction": "LONG"},
        {"opened_at": "2026-01-06T15:00:00+00:00", "pnl": "-100", "net_r": "-1", "direction": "SHORT"},
        {"opened_at": "2026-01-07T15:00:00+00:00", "pnl": "250", "net_r": "2", "direction": "LONG"},
        {"opened_at": "2026-01-07T16:00:00+00:00", "pnl": "250", "net_r": "2", "direction": "LONG"},
    ]
    m = metrics(tr, authed.app.state.rules.rules, "EVAL")
    assert m["stats"]["trades"] == 4 and m["stats"]["net"] == "700" and m["consistency_ok"] is False  # 500/700 > 40%
    b = m["breakdown"]
    assert b["weekday"]["Mon"] == {"trades": 1, "wins": 1, "pnl": "300", "win_rate": "1.0"}
    assert b["hour_et"]["10"]["trades"] == 3 and b["hour_et"]["11"]["pnl"] == "250"
    assert b["direction"]["LONG"]["trades"] == 3 and b["direction"]["SHORT"]["win_rate"] == "0.0"
    assert float(m["monte_carlo_eval"]["pass_rate"]) > 0.5 and m["day_pnls"]["2026-01-05"] == "300"
    assert m["payout_sim"]["breached"] is False and m["payout_sim"]["weeks"] == []  # 3 sessions < 1 week
    inc = m["income_mc"]
    assert set(inc["by_accounts"]) == {"1", "2", "3", "4", "5"} and inc["floor"] and inc["target"]
    assert all(0 <= float(v["p_target"]) <= float(v["p_floor"]) <= 1 for v in inc["by_accounts"].values())


def test_suggestions_flag_losing_buckets():
    from app.api.backtest import suggestions

    bd = {
        "hour_et": {
            "09": {"trades": 12, "wins": 3, "pnl": "-240", "win_rate": "0.25"},
            "10": {"trades": 3, "wins": 0, "pnl": "-90", "win_rate": "0.0"},
        }
    }
    assert suggestions(bd) == ["Consider skipping hour 09 ET: 12 trades, win rate 25%, net $-240"]
