"""D106 (user 2026-11-11: "Remove all unnecessary gates and have each strategy have different gates"): read-only
per-strategy gates view for the Strategy page.

Each kept strategy lists ONLY the checks its own code in signals/strategy_service.py (+ engine/noise.py,
engine/order_flow.py, engine/pm_fade.py, engine/ai_duo.py, engine/ta_mgc.py) performs, in the
order the code performs them, with every number read from the live config (nothing hardcoded). The firm/safety
checks that apply to every strategy (news, DLL/MLL, consistency, hedge lock, kill switch, 1 position, flat times,
pre-flight) are listed once as the shared "Lucid rules (always on)" block — they are not removable and this module
never changes them; it only DESCRIBES the gates and reads each strategy's latest signal (or, for Order Flow, its
latest audited skip) to show pass / fail / not reached.

`describe` and `evaluate` are pure (no I/O); the route does the two reads."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, current_user, get_db
from app.models import AuditLog, Signal
from app.risk.split_risk import split_active

router = APIRouter(prefix="/api")

LUCID = "LUCID"  # pseudo gate: the point where a strategy hands over to the shared Lucid rules (window/news/hedge)
WINDOW_CODES = ("INSTRUMENT_DISABLED", "OUTSIDE_WINDOW")
PLAN_CODES = (
    "OF_UNKNOWN_SIGNAL",
    "OF_BAD_PRICE",
    "OF_LEVEL_WRONG_SIDE",
    "STOP_INVALID",
    "STOP_TOO_TIGHT",
    "STOP_TOO_WIDE",
    "RR_BELOW_MIN",
)
# model_key tag of each strategy's signals: "{symbol}-{TAG}-{day}…" (strategy_service._today_signals)
TAGS = {"noise": "NOISE", "pm_fade": "FADE", "ai_bias": "AI", "ai_duo": "DUO", "order_flow": "OF"}
SPLIT_SIDES = {"NOISE": "SIDE_NOISE", "DUO": "SIDE_DUO"}  # D92 split card: one row per side


def _g(id_: str, name: str, text: str, codes: tuple[str, ...] = (), kind: str = "entry") -> dict[str, Any]:
    return {"id": id_, "name": name, "text": text, "codes": list(codes), "kind": kind}


def _win(r: Any, symbol: str) -> dict[str, Any]:
    inst = r.instrument(symbol)
    w = ", ".join(f"{a}–{b}" for a, b in (inst.windows or r.internal.windows))
    return _g("WINDOW", "Trading window", f"{symbol} enabled, bar inside {w} ET.", WINDOW_CODES)


def _lucid_step() -> dict[str, Any]:
    return _g(LUCID, "Lucid rules", "Calendar loaded, news blackout, hedge lock — see “Lucid rules (always on)”.")


def _struct(r: Any) -> list[dict[str, Any]]:
    """D76 OB/SMT filter: only listed while switched on (default OFF — tested, no gain)."""
    sf = r.strategy.structure_filters
    if not sf.enabled:
        return []
    codes = ("OB_BLOCK", "SMT_BLOCK")  # D120: MSO_DIV_BLOCK removed with the MSO indicator
    return [_g("STRUCTURE", "Order-block / SMT filter (D76)", "Blocks an entry when structure is against it.", codes)]


def describe(r: Any) -> list[dict[str, Any]]:
    """PURE: every kept strategy with its own gates (evaluation order) + exit rules, from the live config `r`."""
    st = r.strategy
    nc, pf, ab, du, of = (
        st.noise_cfg,
        st.pm_fade_cfg,
        st.ai_bias_cfg,
        st.ai_duo_cfg,
        st.order_flow_cfg,
    )
    stop = f"${nc.emergency_stop_usd}" if nc.emergency_stop_usd is not None else f"{nc.emergency_stop_pct:%}"
    noise = [
        _g(
            "CHECK_TIME",
            "Decision bar",
            f"Bar closing {nc.first_check}, then every {nc.check_minutes} min; last new entry {nc.last_check} ET.",
        ),
        _g(
            "WARMUP",
            "Warm-up + roll guard",
            f"≥ {nc.min_history_days} stored sessions (lookback {nc.lookback_days}), prior close known, "
            f"|open / prior close − 1| ≤ {nc.roll_gap_pct:%}.",
        ),
        _g("BREAKOUT", "Noise-band breakout", "Close above the upper noise band → LONG, below the lower → SHORT."),
        _g("MAX_ENTRIES", "Entries per day", f"At most {nc.max_entries_per_day}; a locked-stop exit ends the day."),
        _win(r, nc.symbol),
        _lucid_step(),
        *_struct(r),
        _g(
            "AI_PROVEN",
            "AI block (advisory until proven)",
            f"Blocks only when both AIs agree strongly against the side AND the record proves "
            f"≥ {float(st.ai_gate_min_accuracy):.0%}.",
            ("BIAS_PROVEN_AGAINST",),
        ),
        _g("VWAP_TRAIL", "VWAP / band trail", "Long exits below max(upper band, VWAP); short above min.", (), "exit"),
        _g("STOP", "Emergency stop", f"Broker stop {stop} per contract.", (), "exit"),
        _g("FLAT", "Flat", f"Closed on the {nc.flat_at} ET bar.", (), "exit"),
    ]
    fade = [
        _g("FADE_TIME", "Fade window", f"Bar closes {pf.first_signal}–{pf.last_signal} ET, one signal per day."),
        _g("NOISE_IDLE", "NOISE did not trade", "Only on a day without a NOISE PASS signal."),
        _g("BAND", "VWAP band", f"Close beyond VWAP ± {pf.band_sd} σ → fade back to VWAP."),
        _g(
            "TARGET",
            "Target distance",
            f"VWAP target ≥ {pf.min_target_ticks} ticks away (else the day ends).",
            ("TARGET_TOO_CLOSE",),
        ),
        _win(r, pf.symbol),
        _lucid_step(),
        *_struct(r),
        _g("STOP", "Stop", f"Fixed ${pf.stop_usd} stop; target VWAP.", (), "exit"),
        _g("FLAT", "Flat", f"Closed on the {pf.flat_at} ET bar.", (), "exit"),
    ]
    ai = [
        _g("ENTRY_TIME", "Decision bar", f"Bar closing {ab.entry_time} ET, one per day."),
        _g("AI_CALL", "AI call today", "A TradingAgents + Vibe-Trading call is stored for today."),
        _g("AI_AGREE", "Both AIs agree strongly", "No trade when they disagree or are not strong."),
        _win(r, ab.symbol),
        _lucid_step(),
        _g("STOP", "Stop", f"{ab.stop_pct:%} stop.", (), "exit"),
        _g("FLAT", "Flat", f"Closed on the {ab.flat_at} ET bar.", (), "exit"),
    ]
    wins = ", ".join(f"{m} {a}–{b}" for m, (a, b) in sorted(du.windows.items()) if m in du.markets)
    excl = ", ".join(f"{a}–{b}" for a, b in du.excluded)
    duo = [
        _g("DUO_TIME", "Entry window", f"{wins} ET; bars touching {excl or 'nothing'} never trigger; once a day."),
        _g(
            "AI_AGREE",
            "Both AIs agree",
            f"Same side, TradingAgents strong, Vibe-Trading confidence ≥ {du.vt_min_conf}.",
            ("AI_MISSING", "AI_TA_MISSING", "AI_VT_MISSING", "AI_NEUTRAL", "AI_DISAGREE", "AI_NOT_STRONG"),
        ),
        _g(
            "RESEARCH",
            "MGC research setup",
            f"MGC: TradingAgents setup valid (confidence ≥ {st.ta_mgc_cfg.min_confidence}), not expired, "
            "price inside the entry zone.",
            (
                "RESEARCH_FAILED",
                "RESEARCH_NO_TRADE",
                "SETUP_MALFORMED",
                "SETUP_ZONE_INVALID",
                "SETUP_LEVELS_INVALID",
                "SETUP_CONF_LOW",
                "SETUP_EXPIRED",
                "SETUP_INVALIDATED",
                "TARGET_REACHED",
                "NO_ENTRY_IN_ZONE",
            ),
        ),
        _g(
            "PULLBACK",
            "VWAP pullback",
            f"A {du.bar_minutes}-min bar tags VWAP and closes back on the AI side.",
            ("NO_PULLBACK", "FEED_GAP"),
        ),
        _g(
            "PLAN",
            "Stop + R:R",
            f"Structure stop (capped at the NOISE stop), target {du.rr_target}R, ≥ {du.rr_min}R.",
            ("STOP_INVALID", "STOP_TOO_TIGHT", "STOP_TOO_WIDE", "RR_BELOW_MIN"),
        ),
        _g("WINDOW", "Market enabled", f"Market in AI Duo markets ({', '.join(du.markets)}).", WINDOW_CODES),
        _lucid_step(),
        _g("MANAGE", "Management", f"BE at {du.be_r}R, trail from {du.trail_start_r}R.", (), "exit"),
        _g("FLAT", "Flat", f"Closed on the {du.flat_at} ET bar.", (), "exit"),
    ]
    a = of.ar
    am = of.amt  # D110 AMT+ button: CONTEXT → LOCATION before the AR layers
    amt = (
        [
            _g(
                "AMT_CONTEXT",
                "AMT+ · Context",
                "Trade only with the acceptance vs the prior RTH value area (above = longs, below = shorts); balance: "
                + ("VA-edge trades only." if am.balance_mode == "edges" else "no trade."),
                ("OF_AMT_NO_CONTEXT", "OF_AMT_COUNTER_CONTEXT", "OF_AMT_BALANCE"),
            ),
            *(
                [
                    _g(
                        "AMT_LOCATION",
                        "AMT+ · Key level",
                        f"Signal at a key level ({', '.join(am.levels)}).",
                        ("OF_AMT_NO_LEVEL",),
                    )
                ]
                if am.level_filter
                else []
            ),
        ]
        if am.enabled
        else []
    )
    z = of.zone_atr  # D111 ATR-zone type (iceberg PROXY)
    zone = (
        [
            _g(
                "ZONE_EVENT",
                "Zone · Event (iceberg PROXY)",
                f"Footprint absorption / large-volume zone ≥ min size; modes {', '.join(z.modes)}.",
                (
                    "OF_ZONE_NOT_ENTRY",
                    "OF_ZONE_MODE_OFF",
                    "OF_ZONE_NO_EVENT",
                    "OF_ZONE_EVENT_SMALL",
                    "OF_ZONE_EXCLUSIVE",
                ),
            ),
            _g(
                "ZONE_TIME",
                "Zone · Time filters",
                f"Dead zone {z.dead_zone[0]}–{z.dead_zone[1]} ET needs rel. volume ≥ {z.dead_zone_min_rvol}; "
                f"no new trades in the last {z.last_minutes} min of RTH.",
                ("OF_ZONE_DEAD_ZONE", "OF_ZONE_LAST_MINUTES"),
            ),
            _g(
                "ZONE_SETUP",
                "Zone · ATR setup",
                f"POSITION {z.entry_atr_pct}×ATR out of the zone; REVERSION at 1/2/3 ATR with price-change confirm, "
                "no fade on a TICK program day.",
                (
                    "OF_ZONE_NOT_PROVEN",
                    "OF_ZONE_REV_LEVEL",
                    "OF_ZONE_NO_PRICE_CHANGE",
                    "OF_ZONE_PROGRAM_DAY",
                    "OF_ZONE_NOT_A_PLUS",
                ),
            ),
        ]
        if z.enabled
        else []
    )
    flow = [
        *amt,
        *zone,
        _g(
            "ENVIRONMENT",
            "AR · Environment",
            f"Allowed: {', '.join(a.allowed_envs)}; compression never.",
            ("OF_COMPRESSION", "OF_ENVIRONMENT"),
        ),
        *(
            [
                _g(
                    "LOCATION",
                    "AR · Location",
                    f"Fib {a.fib_min}–{a.fib_max}, value side {a.value_side}.",
                    ("OF_LOCATION",),
                )
            ]
            if a.location_filter
            else []
        ),
        *(
            [
                _g(
                    "PATH",
                    "AR · Path",
                    f"Path known; no trade with the move at/beyond {a.path_block_zone}.",
                    ("OF_PATH_UNKNOWN", "OF_PATH_EXHAUSTED"),
                )
            ]
            if a.path_filter
            else []
        ),
        _g(
            "CONFIRMATION",
            "AR · Confirmation",
            f"Confirmation candle ≤ {a.confirm_max_age_min} min before entry"
            + ("; real delta only." if a.require_real_delta else "."),
            ("OF_NO_CONFIRM", "OF_DELTA_ESTIMATED"),
        ),
        _g(
            "PLAN",
            "Stop + R:R plan",
            f"Stop beyond the absorption zone + {of.buffer_ticks} tick(s), {of.min_risk_ticks}–{of.max_risk_ticks} "
            f"ticks, target {of.rr}R, ≥ {of.rr_min}R"
            + (
                f"; AMT+ target = next key level when {of.rr_min}–{am.target_max_rr}R."
                if am.enabled and am.target_to_level
                else "."
            ),
            PLAN_CODES,
        ),
        _g("WINDOW", "Trading window", f"Market in Order Flow markets ({', '.join(of.instruments)}).", WINDOW_CODES),
        _g("ONE_POSITION", "One order-flow position", "One open order-flow position at a time.", ("OF_POSITION_OPEN",)),
        _g("DAILY_CAP", "Daily cap", f"At most {of.max_per_day} per day.", ("OF_DAILY_CAP",)),
        _lucid_step(),
        _g("FLAT", "Flat", f"Closed from {of.flat_at} ET.", (), "exit"),
    ]
    return [
        {"key": "noise", "name": "NOISE", "on": st.noise, "symbols": [nc.symbol], "gates": noise},
        {"key": "pm_fade", "name": "Afternoon fade", "on": st.pm_fade, "symbols": [pf.symbol], "gates": fade},
        {"key": "ai_bias", "name": "AI only", "on": st.ai_bias, "symbols": [ab.symbol], "gates": ai},
        {"key": "ai_duo", "name": "AI Duo", "on": st.ai_duo, "symbols": list(du.markets), "gates": duo},
        {
            "key": "order_flow",
            "name": "Order Flow",
            "on": st.order_flow,
            "symbols": list(of.instruments),
            "gates": flow,
        },
        {
            "key": "noise_ai_split",
            "name": "NOISE + AI Duo — 50/50 risk split",
            "on": split_active(st.noise_ai_split, st.noise, st.ai_duo),
            "symbols": sorted({nc.symbol, *du.markets}),
            "gates": split_gates(noise, duo, st.noise_ai_split_share),
        },
    ]


def _codes(gates: list[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(c for g in gates if g["id"] != LUCID for c in g["codes"])


def split_gates(noise: list[dict[str, Any]], duo: list[dict[str, Any]], share: Any) -> list[dict[str, Any]]:
    """D92: the split button runs BOTH sides unchanged; it only adds the half-size / half-DLL budget (tighten-only)."""
    pct = f"{float(share):.0%}"
    return [
        _g("SIDE_NOISE", "NOISE side", "Every NOISE gate (see the NOISE card), at half size.", _codes(noise)),
        _g("SIDE_DUO", "AI Duo side", "Every AI Duo gate (see the AI Duo card), at half size.", _codes(duo)),
        _g(
            "SPLIT",
            "50/50 risk budget",
            f"Each side trades {pct} of its size (round down, min 1 micro) and may use {pct} of the DLL.",
            ("SPLIT_BUDGET_EXCEEDED",),
        ),
        _lucid_step(),
    ]


def _kill_mode(r: Any) -> str:
    """D137: which equity the kill switch watches (My Settings strategy.eod_closed_balance)."""
    if r.strategy.eod_closed_balance:
        return "EOD accounts: closed balance only (open loss ignored), intraday accounts: balance + open P&L"
    return "watching balance + open P&L"


def lucid_rules(r: Any) -> list[dict[str, Any]]:
    """PURE: the shared firm/safety checks every strategy passes (not removable, never edited here)."""
    i, ev, fu, b = r.internal, r.eval, r.funded, r.behavior
    kill_mode = _kill_mode(r)

    def usd(x: Any) -> str:
        return "none in this plan" if x is None else f"${x}"  # D116: null in the plan yaml = no DLL (Pro eval / Flex)

    # D116: the plan stores 40 (= 40 %), never a fraction — the old `:%` format printed "4000%"
    cons = (  # B8: a plan without the rule said "Eval largest day ≤ none of the target"
        "No consistency rule in this plan's evaluation."
        if ev.consistency_max_day_pct is None
        else f"Eval largest day ≤ {ev.consistency_max_day_pct.normalize():f}% of the target; size cut to fit."
    )
    return [
        _g(
            "NEWS",
            "News + calendar",
            f"No entry {i.no_entry_before_news_min} min before high-impact news, flatten {i.news_flatten_before_min} "
            "min before; no calendar = no trading.",
            ("NEWS_BLACKOUT", "CALENDAR_MISSING"),
        ),
        _g(
            "DLL_MLL",
            "Daily loss + max loss",
            f"DLL eval {usd(ev.daily_loss_limit)} / funded {usd(fu.daily_loss_limit)}; max loss eval "
            f"{usd(ev.max_loss_limit)} / funded {usd(fu.max_loss_limit)}.",
        ),
        _g("CONSISTENCY", "Consistency", cons),
        _g("HEDGE", "Hedge lock", f"Never both sides ({b.hedge_lock_scope}).", ("HEDGE_LOCK",)),
        _g("KILL", "Kill switch", f"Freeze within ${i.kill_switch_mll_distance} of the max loss; {kill_mode}; never auto-resumes."),
        _g("ONE_POSITION", "Positions", f"Max {b.max_open_positions_per_account} open position per account."),
        _g("FLAT_TIMES", "Flat times", f"Auto flatten {i.auto_flatten}, hard flat {i.hard_flat} ET."),
        _g("PREFLIGHT", "Pre-flight", f"Pre-flight at {r.schedule.preflight} ET must pass before arming."),
    ]


def evaluate(gates: list[dict[str, Any]], last: dict[str, Any] | None) -> dict[str, Any]:
    """PURE: gate statuses from the latest decision `last` = {status PASS|SKIP, code, at, direction} or None.
    PASS → every entry gate PASS. SKIP with a strategy code → earlier gates PASS, that gate FAIL, later NOT_REACHED.
    Any other code (window/news/hedge/risk) → the strategy's own setup gates before the Lucid step PASS and the
    Lucid step FAIL (`lucid_code` names it). Exit rules carry status None."""
    entry = [g for g in gates if g["kind"] == "entry"]
    out = [{**g, "status": None} for g in gates]
    if last is None:
        return {"gates": out, "last": None, "lucid_code": None}
    code = last.get("code")
    if last.get("status") == "PASS" or not code:
        fail = len(entry)
    else:
        own = [n for n, g in enumerate(entry) if code in g["codes"]]
        fail = own[0] if own else next(n for n, g in enumerate(entry) if g["id"] == LUCID)
    ids = {g["id"]: n for n, g in enumerate(entry)}
    for g in out:
        if g["kind"] != "entry":
            continue
        n = ids[g["id"]]
        g["status"] = "PASS" if n < fail else "FAIL" if n == fail else "NOT_REACHED"
    lucid = code if fail < len(entry) and entry[fail]["id"] == LUCID else None
    return {"gates": out, "last": last, "lucid_code": lucid}


def _iso(d: datetime | None) -> str | None:
    if d is None:
        return None
    return (d if d.tzinfo else d.replace(tzinfo=UTC)).astimezone(UTC).isoformat()


def _latest_signal(db: Session, tag: str) -> dict[str, Any] | None:
    sig = db.execute(
        select(Signal).where(Signal.model_key.like(f"%-{tag}-%")).order_by(Signal.id.desc()).limit(1)
    ).scalar_one_or_none()
    if sig is None:
        return None
    return {
        "status": sig.status,
        "code": sig.skip_reason,
        "at": _iso(sig.bar_time),
        "symbol": sig.symbol,
        "direction": sig.direction,
        "source": "signal",
    }


def _latest_of_skip(db: Session) -> dict[str, Any] | None:
    row = db.execute(
        select(AuditLog).where(AuditLog.action == "order_flow.skip").order_by(AuditLog.id.desc()).limit(1)
    ).scalar_one_or_none()
    if row is None:
        return None
    p = row.payload or {}
    return {
        "status": "SKIP",
        "code": p.get("code"),
        "at": _iso(row.at),
        "symbol": row.entity.split("-", 1)[0],
        "direction": p.get("direction"),
        "source": "audit",
    }


@router.get("/strategy-gates")
def strategy_gates(request: Request, _: Principal = Depends(current_user), db: Session = Depends(get_db)) -> Any:
    """D106: each kept strategy's own gates with live pass/fail from its latest decision + the shared Lucid rules."""
    r = request.app.state.rules.rules
    rows = []
    for s in describe(r):
        if s["key"] == "noise_ai_split":  # D92: the later of the two sides' decisions; the other side shows no data
            sides = [(t, x) for t in SPLIT_SIDES if (x := _latest_signal(db, t)) is not None]
            tag, last = max(sides, key=lambda p: p[1]["at"] or "") if sides else (None, None)
            ev = evaluate(s["gates"], last)
            for g in ev["gates"]:
                if g["id"] in SPLIT_SIDES.values() and tag is not None and g["id"] != SPLIT_SIDES[tag]:
                    g["status"] = None
            rows.append({**{k: v for k, v in s.items() if k != "gates"}, **ev})
            continue
        last = _latest_signal(db, TAGS[s["key"]])
        if s["key"] == "order_flow":  # an AR/plan skip makes no signal row — it is audited instead
            skip = _latest_of_skip(db)
            if skip is not None and (last is None or (skip["at"] or "") > (last["at"] or "")):
                last = skip
        rows.append({**{k: v for k, v in s.items() if k != "gates"}, **evaluate(s["gates"], last)})
    return {"strategies": rows, "lucid_rules": lucid_rules(r)}
