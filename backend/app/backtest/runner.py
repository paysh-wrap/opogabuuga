"""Backtest = replay through the SAME live code (§16): 1-minute bars → Python ports of the LunqFX fractal + BigBeluga
MSO → bridge-format alerts → the real webhook → confluence gates → risk → order manager → simulator (fees, slippage,
stop-first). Runs in a throwaway app instance + database; nothing touches the real app.

Inputs the past can't supply, set explicitly and reported with the result:
- bias: "recorded" (stored TradingAgents decisions only; missing days = NO_TRADE) or a fixed value for every day
  (LONG_ONLY / SHORT_ONLY / NEUTRAL) — fixed bias is an assumption, not the live system.
- news: no historical calendar → each session is treated as having no high-impact events (assumption, flagged).
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from app.backtest.parity import replay_payloads
from app.indicators.bars import Bar

MIN_MS = 60_000


@dataclass
class BacktestConfig:
    symbol: str = "MNQ"
    stage: str = "EVAL"
    drawdown_type: str | None = None
    balance: Decimal = Decimal(25000)
    bias: str = "recorded"  # recorded | LONG_ONLY | SHORT_ONLY | NEUTRAL
    recorded_bias: dict[str, str] = field(default_factory=dict)  # session iso date → mapped
    one_to_one: bool = False
    scalp: bool = False
    low_risk: bool = False  # Lower-risk mode button (half risk, more trades allowed)
    eval_mode: bool = False
    profiles: tuple[str, ...] = ("TIGHT", "STD")
    data_source: str = "futures"  # "futures" (MGC/MNQ contracts) | "spot" (e.g. XAUUSD: NOT what Lucid trades)


@dataclass
class BacktestResult:
    trades: list[dict[str, Any]]
    signals: dict[str, int]
    skips: dict[str, int]
    sessions: int
    assumptions: list[str]
    final_balance: str
    mll: str | None
    rejects: dict[str, int] = field(default_factory=dict)  # webhook payloads the app refused (diagnostics)


def aggregate(bars: list[Bar], minutes: int) -> list[Bar]:
    """1-minute bars → N-minute bars aligned to clock boundaries (only complete buckets)."""
    out: list[Bar] = []
    bucket: list[Bar] = []
    for b in bars:
        start = b.open_ms - b.open_ms % (minutes * MIN_MS)
        if bucket and bucket[0].open_ms - bucket[0].open_ms % (minutes * MIN_MS) != start:
            out += _flush(bucket, minutes)
            bucket = []
        bucket.append(b)
    out += _flush(bucket, minutes)
    return out


def _flush(bucket: list[Bar], minutes: int) -> list[Bar]:
    if len(bucket) != minutes:
        return []
    s = bucket[0].open_ms - bucket[0].open_ms % (minutes * MIN_MS)
    return [
        Bar(
            s,
            s + minutes * MIN_MS,
            bucket[0].o,
            max(b.h for b in bucket),
            min(b.l for b in bucket),
            bucket[-1].c,
            sum((b.v for b in bucket), Decimal(0)),
        )
    ]


def run_backtest(bars_1m: Iterable[Bar], cfg: BacktestConfig, rules_path: Path | None = None) -> BacktestResult:
    from fastapi.testclient import TestClient
    from pydantic import SecretStr

    from app.clock import FixedClock, session_date
    from app.config import load_rules
    from app.crypto import new_master_key
    from app.main import create_app
    from app.models import Account, BiasDecision, Signal, Trade
    from app.settings import Settings, get_settings

    bars = sorted(bars_1m, key=lambda b: b.open_ms)
    if not bars:
        raise ValueError("no bars")
    secret = "backtest-" + new_master_key()[:24]
    tmp = tempfile.TemporaryDirectory()
    rp = rules_path or get_settings().rules_path
    settings = Settings(
        database_url=f"sqlite:///{tmp.name}/bt.db",
        master_key=SecretStr(new_master_key()),
        webhook_secret=SecretStr(secret),
        rules_path=rp,
        web_dist=Path(tmp.name) / "none",
        ta_python=str(Path(tmp.name) / "none"),
        scheduler_enabled=False,
    )
    rules = load_rules(rp).rules
    inst = rules.instruments[cfg.symbol]
    m = rules.indicators.mso
    clock = FixedClock(datetime.fromtimestamp(bars[0].open_ms / 1000, tz=UTC))
    app = create_app(settings, clock)
    from sqlalchemy import event as _sa_event

    @_sa_event.listens_for(app.state.engine, "connect")
    def _fast(dbapi_conn: Any, _rec: Any) -> None:  # throwaway DB: durability not needed
        dbapi_conn.execute("PRAGMA synchronous=OFF")

    payloads: list[dict[str, Any]] = []
    for prof in [x for x in cfg.profiles if x in rules.profiles.enabled]:  # replay only profiles that may trade
        p = getattr(rules.profiles, prof)
        ltf, htf = int(p.ltf), int(p.htf)
        series = bars if ltf == 1 else aggregate(bars, ltf)
        payloads += replay_payloads(
            series,
            symbol=inst.tv_symbol,
            profile=prof,
            tf=str(ltf),
            htf_min=htf,
            tick=inst.tick,
            atr_period=14,
            pivot_left=m.pivot_left,
            pivot_right=m.pivot_right,
            mom_length=m.mom_length,
            smooth_length=m.smooth_length,
            div_pivot_left=m.div_pivot_left,
            div_pivot_right=m.div_pivot_right,
        )
    payloads.sort(key=lambda p: (p["bar_time_ms"], p["event"] != "HEARTBEAT"))
    assumptions = ["no historical news calendar: sessions treated as having no high-impact USD events"]
    if cfg.data_source != "futures":
        assumptions.append(
            f"DATA IS {cfg.data_source.upper()}, NOT {cfg.symbol} FUTURES: prices, ranges and fills differ from the "
            "contract Lucid trades; use for signal counts only, not for P&L decisions"
        )
    if cfg.bias != "recorded":
        assumptions.append(f"bias fixed to {cfg.bias} every session (not the live TradingAgents decision)")
    with TestClient(app) as c:
        st = app.state
        from app.webhook.service import SlidingWindow

        # Replay pushes a whole day in seconds: the live per-minute webhook rate limit (wall-clock) must not apply.
        st.webhook_limiter = SlidingWindow(10**9, 60)
        st.calendar = lambda d: []
        with st.sessionmaker() as s:
            from app.auth import create_user

            create_user(s, "bt", secret)
            s.commit()
        r = c.post("/api/auth/login", json={"username": "bt", "password": secret})
        c.headers["x-csrf-token"] = r.json()["csrf"]
        # D43: Scalp / 1:1 are retired (forced OFF by the rules holder); cfg.one_to_one / cfg.scalp are ignored.
        c.put("/api/markets", json={"symbol": cfg.symbol, "enabled": True})  # backtest the chosen market
        if cfg.low_risk:
            c.put("/api/risk/low-risk", json={"enabled": True})
        body = {"label": "BT", "stage": cfg.stage, "balance": str(cfg.balance)}
        if cfg.drawdown_type:
            body["drawdown_type"] = cfg.drawdown_type
        aid = c.post("/api/accounts", json=body).json()["id"]
        if cfg.eval_mode:
            c.put("/api/risk/eval-mode", json={"enabled": True, "confirm": "ENABLE EVALUATION MODE"})
        c.patch(f"/api/accounts/{aid}", json={"armed": True, "selected": True})
        st.controller.mode = "FULL"  # backtest only: FULL-AUTO without the 5-session ramp (no real orders)
        seen: set[date] = set()
        rejects: dict[str, int] = {}
        # Speed: replay every alert inside the app's own event loop (one thread hop for the whole run instead of
        # one per alert). Same routes, same code path; only the transport differs from TestClient.
        import httpx

        async def replay() -> None:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as ac:
                for p in payloads:
                    now = datetime.fromtimestamp(p["bar_time_ms"] / 1000 + 1, tz=UTC)
                    clock.set(now)
                    sess = session_date(now)
                    if sess not in seen:
                        seen.add(sess)
                        if len(seen) > 1:  # EOD MLL update for the session that just ended
                            await st.controller.eod_all()
                        with st.sessionmaker() as s:
                            bias = (
                                cfg.recorded_bias.get(sess.isoformat(), "NO_TRADE")
                                if cfg.bias == "recorded"
                                else cfg.bias
                            )
                            s.add(
                                BiasDecision(
                                    session_date=sess,
                                    proxy=inst.bias_proxy,
                                    raw_rating="BACKTEST",
                                    mapped=bias,
                                    version="bt",
                                )
                            )
                            s.commit()
                        r = await ac.post("/api/auth/login", json={"username": "bt", "password": secret})
                        ac.headers["x-csrf-token"] = r.json()["csrf"]
                        await ac.post("/api/attestation", json={"confirm": True})
                    resp = await ac.post(
                        "/api/webhook/tradingview",
                        content=json.dumps({**p, "secret": secret}),
                        headers={"content-type": "text/plain"},
                    )
                    if resp.status_code != 200:
                        body = resp.json()
                        k = f"{p['event']}:{resp.status_code}:{str(body.get('detail', body.get('code', '')))[:40]}"
                        rejects[k] = rejects.get(k, 0) + 1

        assert c.portal is not None  # set while the TestClient context is open
        c.portal.call(replay)
        with st.sessionmaker() as s:
            trades = [
                {
                    "opened_at": t.opened_at.isoformat(),
                    "closed_at": t.closed_at.isoformat() if t.closed_at else None,
                    "direction": t.direction,
                    "qty": t.qty,
                    "pnl": str(t.pnl_usd) if t.pnl_usd is not None else None,
                    "net_r": str(t.net_r) if t.net_r is not None else None,
                    "risk": str(t.risk_usd),
                    "exit_reason": t.exit_reason,
                    "profile": t.profile,
                    "mode": t.risk_profile_kind,
                }
                for t in s.query(Trade).order_by(Trade.id)
            ]
            sig: dict[str, int] = {}
            skips: dict[str, int] = {}
            for x in s.query(Signal):
                sig[x.status] = sig.get(x.status, 0) + 1
                if x.skip_reason:
                    skips[x.skip_reason] = skips.get(x.skip_reason, 0) + 1
            a = s.get(Account, aid)
            mll = str(a.mll) if a and a.mll is not None else None
        r = c.post("/api/auth/login", json={"username": "bt", "password": secret})
        c.headers["x-csrf-token"] = r.json()["csrf"]
        bal = c.get("/api/positions").json()["accounts"][0].get("balance", "0")
    tmp.cleanup()
    return BacktestResult(trades, sig, skips, len(seen), assumptions, bal, mll, rejects)
