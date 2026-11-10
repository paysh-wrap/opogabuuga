"""D84 TradingAgents MGC research job: gold-driver research → structured setup, then Vibe-Trading's opinion on MGC.

Reuses the EXISTING TradingAgents and Vibe-Trading connections (API Keys page store, ta_runner / .venv-ta and .venv-vt
subprocesses) — no new key. No key = "AI key not connected" and nothing runs (no crash, no row). Each report + decision
is stored in the bias ledger as a BiasDecision with proxy `GLD.RS` (like backfill `QQQ.BF`: never counted toward the
live accuracy proof). `reasoning` holds JSON {"setup", "vt", "report", "error"}.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.bias import vibe_trading as vt
from app.bias.tradingagents_adapter import TradingAgentsAdapter
from app.models import ApiCredential, BiasDecision

RETRY_EVERY_MIN = 30
NOT_CONNECTED = "AI key not connected"


def research_proxy(cfg_proxy: str) -> str:
    return f"{cfg_proxy}.RS"  # BiasDecision.proxy is 8 chars: GLD.RS


def connected(s: Session) -> bool:
    return s.execute(select(ApiCredential.id).where(ApiCredential.provider == "tradingagents")).first() is not None


def latest(s: Session, cfg_proxy: str, sess: date) -> BiasDecision | None:
    return s.execute(
        select(BiasDecision)
        .where(BiasDecision.proxy == research_proxy(cfg_proxy), BiasDecision.session_date == sess)
        .order_by(BiasDecision.id.desc())
        .limit(1)
    ).scalar_one_or_none()


def payload(row: BiasDecision | None) -> dict[str, Any] | None:
    if row is None:
        return None
    try:
        d = json.loads(row.reasoning)
    except ValueError:
        return {"error": "stored research unreadable"}
    return d if isinstance(d, dict) else {"error": "stored research unreadable"}


def research_due(now_et: datetime, at: str, last_try: str | None, done: bool, until: str) -> bool:
    """Weekdays from `at` (02:45 ET); once a day. A failed run (no row yet) retries every 30 min until `until`."""
    h, m = (int(x) for x in at.split(":"))
    uh, um = (int(x) for x in until.split(":"))
    if (
        done
        or now_et.weekday() >= 5
        or (now_et.hour, now_et.minute) < (h, m)
        or (now_et.hour, now_et.minute) >= (uh, um)
    ):
        return False
    if last_try is None:
        return True
    return now_et - datetime.fromisoformat(last_try) >= timedelta(minutes=RETRY_EVERY_MIN)


async def run_research(
    s: Session,
    ta: TradingAgentsAdapter,
    vault: Any,
    rules: Any,
    clock: Any,
    sess: date,
    notify: Any,
    vt_root: Any = None,
    context: dict[str, Any] | None = None,
    calendar: list[str] | None = None,
) -> str:
    """One research run: 'NOT_CONNECTED' | 'ERROR' | 'STORED'. A missing key or a runner failure never raises."""
    cfg = rules.strategy.ta_mgc_cfg
    cred = s.execute(select(ApiCredential).where(ApiCredential.provider == "tradingagents")).scalar_one_or_none()
    if cred is None:
        return "NOT_CONNECTED"
    vcred = s.execute(select(ApiCredential).where(ApiCredential.provider == "vibetrading")).scalar_one_or_none()
    err, setup, report, version = "", None, "", ""
    try:
        env = TradingAgentsAdapter.env_for(vault.open(cred.ciphertext), None)
        res = await ta.research(cfg.proxy, sess, env, "MGC", {**(context or {}), "calendar": calendar or []})
    except (ValueError, KeyError) as e:
        res, err = None, f"credentials: {type(e).__name__}"
    if res is not None:
        if res.ok:
            setup, report, version = (
                res.data.get("setup"),
                str(res.data.get("report", "")),
                str(res.data.get("version", "")),
            )
        else:
            err = str(res.data.get("error", "research failed"))[:300]
    outlook: dict[str, Any] | None = None
    vt_note = ""
    if (
        err == "" and vcred is not None and vt_root is not None
    ):  # Vibe-Trading's own opinion on MGC (same rule as AI Duo)
        try:
            venv = vt.env_for(vault.open(vcred.ciphertext))
        except (ValueError, KeyError) as e:
            vt_note = f"credentials: {type(e).__name__}"
        else:
            from pathlib import Path

            o, status = await vt.run(
                vt.executable(Path(vt_root)),
                venv,
                vt.prompt(cfg.proxy, "Micro Gold futures (MGC)", sess.isoformat(), (context or {}).get("openbb")),
                Path(vt_root) / "data" / "vibe-trading",
            )
            if o is not None:
                outlook = {"direction": o.direction, "confidence": o.confidence, "reason": o.reason}
            else:
                vt_note = str(status)[:200]
    elif err == "" and vcred is None:
        vt_note = "Vibe-Trading not connected"
    side = str((setup or {}).get("side", "")).upper() if isinstance(setup, dict) else ""
    conf = (setup or {}).get("confidence") if isinstance(setup, dict) else None
    label = f"{side or 'ERR'} {conf if isinstance(conf, int) else '-'}"
    if outlook is not None:
        label += f"·VT {outlook['direction']} {outlook['confidence']}"
    s.add(
        BiasDecision(
            session_date=sess,
            proxy=research_proxy(cfg.proxy),
            raw_rating=label[:32],
            mapped="NEUTRAL" if not err else "NO_TRADE",
            reasoning=json.dumps(
                {"setup": setup, "vt": outlook, "vt_note": vt_note, "error": err, "report": report[:15000]}
            )[:20000],
            version=version,
        )
    )
    audit.record(s, clock, "bias", "ta_mgc.research", research_proxy(cfg.proxy), {"label": label, "error": err[:200]})
    if err:
        notify("warn", "TradingAgents MGC research failed", err[:200])
    s.commit()
    return "ERROR" if err else "STORED"
