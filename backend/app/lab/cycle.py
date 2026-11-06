"""§17.3 weekly Lab cycle + §17 apply step (I/O). Uses ONLY recorded live/paper bars and the SAME backtest engine.

cycle:  recorded sessions → walk-forward split (older TRAIN / newer TEST) → champion vs one-step neighbours of the
        §17.2 tunables → best TRAIN candidate that keeps win rate + trade count → must also win out-of-sample →
        Proposal (pending). Never applies anything itself.
apply:  at the 18:00 reset, APPROVED proposals become a new versioned "lab" settings layer (validated like every
        settings change; one-click rollback). Max one applied change per self_improvement.cooldown_days."""

from __future__ import annotations

import asyncio
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import audit
from app.clock import Clock, session_date
from app.indicators.bars import Bar
from app.lab.challenger import Candidate, Perf, best_on_train, explain, passes_oos, perf
from app.lab.tunables import current_values, neighbours, validate_diff
from app.models import Proposal, RiskProfile

TRAIN_SHARE = D("0.75")
MIN_SESSIONS = 20


def _sess(b: Bar) -> Any:
    return session_date(datetime.fromtimestamp(b.open_ms / 1000, tz=UTC))


def split_sessions(bars: list[Bar]) -> tuple[list[Bar], list[Bar]]:
    """Older TRAIN_SHARE of the sessions → train, the newest rest → test (never shuffled: no peeking ahead)."""
    days = sorted({_sess(b) for b in bars})
    if len(days) < 2:
        return list(bars), []
    cut = days[int(len(days) * TRAIN_SHARE)]
    return [b for b in bars if _sess(b) < cut], [b for b in bars if _sess(b) >= cut]


def _plain(v: Any) -> Any:
    if isinstance(v, D):
        return int(v) if v == v.to_integral_value() and "." not in str(v) else float(v)
    if isinstance(v, dict):
        return {k: _plain(x) for k, x in v.items()}
    if isinstance(v, list | tuple):
        return [_plain(x) for x in v]
    return v


def write_rules(raw: dict[str, Any], diff: dict[str, D], folder: Path, name: str) -> Path:
    import copy

    r = copy.deepcopy(raw)
    for k, v in diff.items():
        cur = r
        *head, last = k.split(".")
        for h in head:
            cur = cur[h]
        cur[last] = v
    p = folder / f"{name}.yaml"
    p.write_text(yaml.safe_dump(_plain(r), sort_keys=False), encoding="utf-8")
    return p


Runner = Callable[[list[Bar], str, Path], list[dict[str, Any]]]


def evaluate(
    raw: dict[str, Any],
    cfg: Any,
    symbol: str,
    bars: list[Bar],
    run: Runner,
    folder: Path,
) -> tuple[Perf, Perf, Candidate | None, list[str], int]:
    """Returns (champion train, champion test, winner or None, reasons, candidates tried)."""
    train, test = split_sessions(bars)
    si = cfg.self_improvement
    champ_path = write_rules(raw, {}, folder, "champion")
    champ_tr, champ_te = perf(run(train, symbol, champ_path)), perf(run(test, symbol, champ_path))
    tried: list[Candidate] = []
    for i, d in enumerate(neighbours(current_values(cfg), si.max_param_step_pct)):
        p = write_rules(raw, d, folder, f"c{i}")
        tried.append(Candidate(d, perf(run(train, symbol, p))))
    best = best_on_train(champ_tr, tried)
    if best is None:
        return (
            champ_tr,
            champ_te,
            None,
            ["no change beat the champion on older sessions without lowering win rate"],
            len(tried),
        )
    p = write_rules(raw, best.diff, folder, "best")
    best = Candidate(best.diff, best.train, perf(run(test, symbol, p)))
    ok, why = passes_oos(champ_te, best, si.min_improvement_r, si.min_oos_trades)
    return champ_tr, champ_te, best if ok else None, why, len(tried)


def _last_applied(s: Session) -> datetime | None:
    row = s.execute(
        select(RiskProfile).where(RiskProfile.kind == "lab").order_by(RiskProfile.version.desc()).limit(1)
    ).scalar_one_or_none()
    return row.created_at if row is not None else None


async def run_cycle(app: Any, s: Session, now: datetime, days: int = 90) -> list[dict[str, Any]]:
    """One Lab cycle per enabled market. Returns a report row per market (also stored as proposals when found)."""
    from app.backtest.nightly import recorded_bars
    from app.backtest.runner import BacktestConfig, run_backtest
    from app.risk.settings_store import latest, latest_firm, merged_raw

    st = app.state
    cfg = st.rules.rules
    si = cfg.self_improvement
    if not si.enabled:
        return [{"status": "disabled"}]
    if s.execute(select(Proposal).where(Proposal.status.in_(("shadow", "pending", "approved")))).first() is not None:
        return [
            {
                "status": "waiting",
                "why": "a challenger is still in shadow, waiting for your decision or the 18:00 apply",
            }
        ]
    last = _last_applied(s)
    if last is not None and now - (last if last.tzinfo else last.replace(tzinfo=UTC)) < timedelta(
        days=si.cooldown_days
    ):
        return [
            {"status": "cooldown", "why": f"last change applied {last.date()}; max one per {si.cooldown_days} days"}
        ]
    firm, std, lab = latest_firm(s), latest(s, "standard"), latest(s, "lab")
    raw = merged_raw(
        st.rules.base,
        firm.body_overrides() if firm else {},
        {**(lab.settings if lab else {}), **(std.settings if std else {})},
    )
    out: list[dict[str, Any]] = []
    for sym, inst in cfg.instruments.items():
        if not inst.enabled:
            continue
        bars = recorded_bars(s, sym, now - timedelta(days=days))
        n_days = len({_sess(b) for b in bars})
        if n_days < MIN_SESSIONS:
            out.append({"symbol": sym, "status": "not_enough_data", "sessions": n_days, "need": MIN_SESSIONS})
            continue

        def run(b: list[Bar], symbol: str, path: Path) -> list[dict[str, Any]]:
            bc = BacktestConfig(
                symbol=symbol, bias="recorded", one_to_one=cfg.one_to_one_mode.enabled, scalp=cfg.scalp_mode.enabled
            )
            return run_backtest(b, bc, path).trades if b else []

        with tempfile.TemporaryDirectory() as tmp:
            ctr, cte, win, why, tried = await asyncio.to_thread(evaluate, raw, cfg, sym, bars, run, Path(tmp))
        row: dict[str, Any] = {"symbol": sym, "sessions": n_days, "candidates": tried, "why": why}
        if win is None:
            row["status"] = "champion_kept"
        else:
            m = {
                "symbol": sym,
                "train": vars_perf(ctr, win.train),
                "test": vars_perf(cte, win.test),
                "oos_champion_e": str(round(cte.e, 4)),
                "shadow": {"since": now.isoformat(), "sessions": 0},
            }
            diff = {k: str(v) for k, v in win.diff.items()}
            version = (s.execute(select(func.max(Proposal.challenger_version))).scalar() or 0) + 1
            prop = Proposal(
                challenger_version=version, diff=diff, metrics=m, explanation=explain(win.diff, ctr, win, cte)
            )
            s.add(prop)
            audit.record(s, st.clock, "lab", "lab.challenger", sym, {"diff": diff})
            s.commit()
            row |= {"status": "proposal", "proposal_id": prop.id, "diff": diff}
            st.controller.notify("info", "Lab found a challenger (now shadow-testing)", prop.explanation[:200])
        out.append(row)
    return out


def vars_perf(champ: Perf, c: Perf | None) -> dict[str, Any]:
    def j(p: Perf | None) -> dict[str, Any] | None:
        return (
            None
            if p is None
            else {"trades": p.trades, "win_rate": str(round(p.win_rate, 4)), "e_r": str(round(p.e, 4))}
        )

    return {"champion": j(champ), "challenger": j(c)}


def apply_approved(s: Session, base: Any, clock: Clock) -> list[int]:
    """18:00: approved proposals → new versioned 'lab' settings layer. Re-validates bounds and the whole rule set."""
    from app.risk.settings_store import SettingsError, build, latest, latest_firm, merged_raw

    applied: list[int] = []
    for prop in s.execute(select(Proposal).where(Proposal.status == "approved").order_by(Proposal.id)).scalars():
        firm, std, lab = latest_firm(s), latest(s, "standard"), latest(s, "lab")
        cur_settings = dict(lab.settings) if lab else {}
        cfg_now, _ = build(
            merged_raw(base, firm.body_overrides() if firm else {}, {**cur_settings, **(std.settings if std else {})})
        )
        errs = validate_diff(prop.diff, current_values(cfg_now), cfg_now.self_improvement.max_param_step_pct)
        merged = {**cur_settings, **prop.diff}
        try:
            build(merged_raw(base, firm.body_overrides() if firm else {}, {**merged, **(std.settings if std else {})}))
        except SettingsError as e:
            errs += e.errors
        if errs:
            prop.status = "invalid"
            audit.record(s, clock, "lab", "lab.apply_rejected", str(prop.id), {"errors": errs})
            continue
        version = (s.execute(select(func.max(RiskProfile.version)).where(RiskProfile.kind == "lab")).scalar() or 0) + 1
        if lab:
            lab.active = False
        s.add(
            RiskProfile(
                kind="lab",
                version=version,
                settings=merged,
                author="lab",
                note=f"proposal {prop.id}",
                diff={k: {"to": v} for k, v in prop.diff.items()},
                active=True,
            )
        )
        prop.status = "applied"
        audit.record(s, clock, "lab", "lab.applied", str(prop.id), {"diff": prop.diff, "version": version})
        s.flush()
        applied.append(prop.id)
    s.commit()
    return applied


def rollback_lab(s: Session, clock: Clock, author: str) -> int:
    """Turn off the newest lab layer; the previous one (if any) becomes active. Returns that version (0 = none)."""
    rows = list(
        s.execute(select(RiskProfile).where(RiskProfile.kind == "lab").order_by(RiskProfile.version.desc())).scalars()
    )
    cur = next((r for r in rows if r.active), None)
    if cur is None:
        return 0
    cur.active = False
    prev = next((r for r in rows if r.version < cur.version), None)
    if prev is not None:
        prev.active = True
    audit.record(s, clock, author, "lab.rollback", f"v{cur.version}", {"now": prev.version if prev else 0})
    s.commit()
    return prev.version if prev else 0


def _effective_raw(s: Session, base: Any) -> dict[str, Any]:
    from app.risk.settings_store import latest, latest_firm, merged_raw

    firm, std, lab = latest_firm(s), latest(s, "standard"), latest(s, "lab")
    mine = {**(lab.settings if lab else {}), **(std.settings if std else {})}
    return merged_raw(base, firm.body_overrides() if firm else {}, mine)


def shadow_verdict(champ: Perf, chal: Perf, sessions: int, si: Any) -> str:
    """PURE. 'wait' until enough new sessions + trades; then 'pass' only if the challenger still keeps the win rate
    and trade count and is at least as good as the champion; 'fail' otherwise or when shadow ran too long."""
    if sessions < si.shadow_min_sessions or chal.trades < si.shadow_min_trades:
        return "fail" if sessions >= si.shadow_max_sessions else "wait"
    ok = chal.win_rate >= champ.win_rate and chal.trades >= champ.trades * D("0.9") and chal.e >= champ.e
    return "pass" if ok else "fail"


async def shadow_check(app: Any, s: Session, now: datetime, run: Runner | None = None) -> list[dict[str, Any]]:
    """Nightly: replay every SHADOW challenger and the champion on the sessions recorded since it was found."""
    from app.backtest.nightly import recorded_bars
    from app.backtest.runner import BacktestConfig, run_backtest

    st = app.state
    cfg = st.rules.rules
    si = cfg.self_improvement
    out: list[dict[str, Any]] = []
    for prop in list(s.execute(select(Proposal).where(Proposal.status == "shadow")).scalars()):
        sym = prop.metrics.get("symbol")
        since = prop.created_at if prop.created_at.tzinfo else prop.created_at.replace(tzinfo=UTC)
        bars = recorded_bars(s, sym, since) if sym else []
        sessions = len({_sess(b) for b in bars})

        def default_run(b: list[Bar], symbol: str, path: Path) -> list[dict[str, Any]]:
            bc = BacktestConfig(
                symbol=symbol, bias="recorded", one_to_one=cfg.one_to_one_mode.enabled, scalp=cfg.scalp_mode.enabled
            )
            return run_backtest(b, bc, path).trades if b else []

        r = run or default_run
        raw = _effective_raw(s, st.rules.base)
        with tempfile.TemporaryDirectory() as tmp:
            cp = write_rules(raw, {}, Path(tmp), "champ")
            xp = write_rules(raw, {k: D(v) for k, v in prop.diff.items()}, Path(tmp), "chal")
            champ = perf(await asyncio.to_thread(r, bars, sym or "", cp))
            chal = perf(await asyncio.to_thread(r, bars, sym or "", xp))
        verdict = shadow_verdict(champ, chal, sessions, si)
        m = dict(prop.metrics)
        m["shadow"] = {"since": since.isoformat(), "sessions": sessions, **vars_perf(champ, chal), "verdict": verdict}
        prop.metrics = m
        if verdict == "pass":
            auto = si.auto_promote_paper and not st.settings.allow_live
            prop.status = "approved" if auto else "pending"
            audit.record(s, st.clock, "lab", "lab.shadow_passed", str(prop.id), {"auto_approved": auto})
            st.controller.notify(
                "info", "Lab challenger passed shadow", "auto-approved (paper)" if auto else "ready for your approval"
            )
        elif verdict == "fail":
            prop.status = "shadow_failed"
            audit.record(s, st.clock, "lab", "lab.shadow_failed", str(prop.id), m["shadow"])
        s.commit()
        out.append({"proposal": prop.id, "verdict": verdict, "sessions": sessions})
    return out


def rolling_e(s: Session, since: datetime, window: int) -> tuple[int, D | None]:
    """Net-R expectancy of the last `window` closed trades since `since` (live or paper)."""
    from app.models import Trade

    rows = (
        s.execute(
            select(Trade.net_r)
            .where(Trade.closed_at.is_not(None), Trade.closed_at >= since, Trade.net_r.is_not(None))
            .order_by(Trade.closed_at.desc())
            .limit(window)
        )
        .scalars()
        .all()
    )
    vals = [D(str(x)) for x in rows if x is not None]
    return len(vals), (sum(vals, D(0)) / len(vals) if vals else None)


def auto_rollback(app: Any, s: Session, now: datetime) -> dict[str, Any] | None:
    """§17.4 nightly: if the live rolling-N expectancy since the newest Lab change is below the champion's
    out-of-sample result recorded when the change was found, roll it back automatically and tell the user."""
    from app.risk.settings_store import latest

    st = app.state
    si = st.rules.rules.self_improvement
    lab = latest(s, "lab")
    if lab is None or not lab.note.startswith("proposal "):
        return None
    prop = s.get(Proposal, int(lab.note.split()[1]))
    bound = D(prop.metrics.get("oos_champion_e", "0")) if prop else D(0)
    since = lab.created_at if lab.created_at.tzinfo else lab.created_at.replace(tzinfo=UTC)
    n, e = rolling_e(s, since, si.rollback_window_trades)
    if n < si.rollback_window_trades or e is None or e >= bound:
        return {"status": "kept", "trades": n, "e": None if e is None else str(round(e, 4)), "bound": str(bound)}
    v = rollback_lab(s, st.clock, "lab-auto")
    if prop is not None:
        prop.status = "rolled_back"
        s.commit()
    st.rules.refresh(s)
    st.controller.notify("warning", "Lab change rolled back automatically", f"rolling-{n} E {e:.3f}R < {bound}R")
    return {"status": "rolled_back", "trades": n, "e": str(round(e, 4)), "bound": str(bound), "active_version": v}
