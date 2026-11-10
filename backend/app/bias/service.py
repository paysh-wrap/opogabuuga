"""Daily bias (§15): run TauricResearch/TradingAgents once per session on each enabled instrument's proxy ETF.

- Scheduled at `schedule.bias` (02:40 ET, D34), Mon–Fri. Latest row per (session, proxy) wins (today_bias).
- Failure / timeout / unknown rating → stored as NO_TRADE + alert (that instrument does not trade today).
- A failed proxy may be retried ("Run now"); a successful one is not re-run the same session.
- Live-only: always the CURRENT session date (never re-run history).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.bias import vibe_trading as vt
from app.bias.tradingagents_adapter import TradingAgentsAdapter, map_rating
from app.models import ApiCredential, BiasDecision

OK = ("LONG_ONLY", "SHORT_ONLY", "NEUTRAL")


def proxies(rules: Any) -> list[str]:
    duo = set(rules.strategy.ai_duo_cfg.markets) if rules.strategy.ai_duo else set()  # D83: AI Duo markets
    return sorted({i.bias_proxy for k, i in rules.instruments.items() if i.enabled or k in duo})


def _done(s: Session, sess: date, proxy: str) -> bool:
    row = s.execute(
        select(BiasDecision)
        .where(BiasDecision.session_date == sess, BiasDecision.proxy == proxy)
        .order_by(BiasDecision.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    return row is not None and row.mapped in OK


MARKET_OF = {"GLD": "Micro Gold futures (MGC)", "QQQ": "Micro Nasdaq-100 futures (MNQ)"}


async def run_bias(
    s: Session,
    ta: TradingAgentsAdapter,
    vault: Any,
    rules: Any,
    clock: Any,
    sess: date,
    notify: Any,
    vt_root: Any = None,
    context: dict[str, Any] | None = None,
) -> dict[str, str]:
    """TradingAgents (backbone) per proxy, then the D53 blend with Vibe-Trading (optional, can only unblock)."""
    cred = s.execute(select(ApiCredential).where(ApiCredential.provider == "tradingagents")).scalar_one_or_none()
    vcred = s.execute(select(ApiCredential).where(ApiCredential.provider == "vibetrading")).scalar_one_or_none()
    out: dict[str, str] = {}
    for proxy in proxies(rules):
        if _done(s, sess, proxy):
            continue
        raw, reasoning, version = "NOT_CONFIGURED", "TradingAgents LLM key not set (Connections page)", ""
        if cred is not None:
            try:
                env = TradingAgentsAdapter.env_for(vault.open(cred.ciphertext), None)
                res = await ta.run(proxy, sess, env)
            except (ValueError, KeyError) as e:
                raw, reasoning = "ERROR", f"credentials: {type(e).__name__}"
            else:
                d = res.data
                raw = str(d.get("rating") or "") if res.ok else "ERROR"
                reasoning = str(d.get("decision") or d.get("error") or "")[:20000]
                version = str(d.get("version") or "")
        mapped, alert = map_rating(raw, rules.bias.rating_map)
        note, label = "", raw
        if vcred is not None and vt_root is not None and not alert:  # D53: second opinion, can only unblock
            from pathlib import Path

            try:
                venv = vt.env_for(vault.open(vcred.ciphertext))
            except (ValueError, KeyError) as e:
                outlook, status = None, f"credentials: {type(e).__name__}"
            else:
                sym = next(
                    (
                        k
                        for k, i in rules.instruments.items()
                        if (i.enabled or (rules.strategy.ai_duo and k in rules.strategy.ai_duo_cfg.markets))
                        and i.bias_proxy == proxy
                    ),
                    proxy,
                )
                outlook, status = await vt.run(
                    vt.executable(Path(vt_root)),
                    venv,
                    vt.prompt(proxy, MARKET_OF.get(proxy, sym), sess.isoformat(), (context or {}).get(sym)),
                    Path(vt_root) / "data" / "vibe-trading",
                )
            mapped, note = vt.blend(mapped, outlook)  # type: ignore[assignment]
            if outlook is not None:
                label = f"{raw}·VT {outlook.direction} {outlook.confidence}"
                note += f" — VT: {outlook.reason}"
            else:
                note += f" ({status})"
                notify(
                    "warn",
                    f"Vibe-Trading gave no call for {proxy}",
                    f"{status} — today's ledger call is TradingAgents only",
                )
        s.add(
            BiasDecision(
                session_date=sess,
                proxy=proxy,
                raw_rating=label[:32],
                mapped=mapped,
                reasoning=(reasoning + ("\n\n[Blend] " + note if note else ""))[:20000],
                version=version,
            )
        )
        audit.record(
            s, clock, "bias", "bias.decided", proxy, {"raw": label[:32], "mapped": mapped, "blend": note[:200]}
        )
        if alert:
            notify("error", f"Bias {proxy}: NO TRADE today", f"{raw}: {reasoning[:200]}")
        out[proxy] = mapped
    s.commit()
    return out


def openbb_context(state: Any) -> dict[str, Any]:
    """D53: OpenBB daily data (already fetched for the Markets panel) → per-market context for Vibe-Trading:
    last close, day change %, 20-day average and which side of it price is. Empty when OpenBB isn't running."""
    feed = getattr(state, "openbb", None)
    out: dict[str, Any] = {}
    for sym, d in ((getattr(feed, "data", None) or {}) if feed is not None else {}).items():
        series = d.get("series") if isinstance(d, dict) else None
        if not series:
            continue
        sma20 = sum(series[-20:]) / len(series[-20:])
        out[sym] = {
            "last": d.get("last"),
            "change_pct": d.get("change_pct"),
            "sma20": round(sma20, 2),
            "vs_sma20": "above" if series[-1] > sma20 else "below",
            "closes_10d": series[-10:],
        }
    return out


RETRY_EVERY_MIN = 30
RETRY_UNTIL = "09:25"  # no point retrying once the morning window is about to open


def retry_due(now: datetime, last_try: str | None, any_missing: bool) -> bool:
    """D78: a proxy that failed this morning (ERROR / NO_TRADE) is retried every 30 min until 09:25 ET."""
    from app.clock import to_et

    if not any_missing:
        return False
    local = to_et(now)
    h, m = (int(x) for x in RETRY_UNTIL.split(":"))
    if local.weekday() >= 5 or (local.hour, local.minute) >= (h, m):
        return False
    if last_try is None:
        return True
    return now - datetime.fromisoformat(last_try) >= timedelta(minutes=RETRY_EVERY_MIN)


def missing_proxies(s: Session, rules: Any, sess: date) -> list[str]:
    return [p for p in proxies(rules) if not _done(s, sess, p)]


def due(now: datetime, at: str, last: str | None, sess: date) -> bool:
    from app.clock import to_et

    local = to_et(now)
    h, m = (int(x) for x in at.split(":"))
    return local.weekday() < 5 and (local.hour, local.minute) >= (h, m) and last != sess.isoformat()
