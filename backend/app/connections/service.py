"""Connections: save (encrypted), test, status. Plaintext secrets never leave this module."""

from __future__ import annotations

import re
import time
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import audit
from app.bias.tradingagents_adapter import TradingAgentsAdapter
from app.clock import Clock
from app.connections.registry import INDICATORS, LLM_PROVIDERS, PROVIDERS, Provider, get_provider
from app.connections.testers import TESTERS, TestResult, test_llm_key
from app.crypto import Vault, hint
from app.models import ApiCredential, Event, IndicatorSource

_latest_tag_cache: dict[str, tuple[float, str]] = {}


def validate_values(p: Provider, values: dict[str, str]) -> dict[str, str]:
    allowed = {f.name: f for f in p.fields}
    unknown = set(values) - set(allowed)
    if unknown:
        raise ValueError(f"unknown fields: {sorted(unknown)}")
    clean: dict[str, str] = {}
    for name, f in allowed.items():
        v = (values.get(name) or "").strip()
        if f.required and not v:
            raise ValueError(f"{f.label} is required")
        if len(v) > 2048:
            raise ValueError(f"{f.label} too long")
        if f.kind == "select" and v and v not in f.options:
            raise ValueError(f"{f.label}: choose one of {', '.join(f.options)}")
        if v:
            clean[name] = v
    if p.id == "ngrok" and "domain" in clean:
        from app.tunnel import clean_domain

        clean["domain"] = clean_domain(clean["domain"])
    return clean


def _hints(p: Provider, values: dict[str, str]) -> dict[str, str]:
    return {
        f.name: (hint(values[f.name]) if f.kind == "secret" else values[f.name]) for f in p.fields if f.name in values
    }


async def latest_ta_tag(http: httpx.AsyncClient) -> str | None:
    cached = _latest_tag_cache.get("ta")
    if cached and time.monotonic() - cached[0] < 3600:
        return cached[1]
    try:
        r = await http.get("https://api.github.com/repos/TauricResearch/TradingAgents/tags", params={"per_page": 1})
        if r.status_code == 200 and r.json():
            tag = str(r.json()[0]["name"])
            _latest_tag_cache["ta"] = (time.monotonic(), tag)
            return tag
    except httpx.HTTPError:
        return None
    return None


async def run_test(
    p: Provider, values: dict[str, str], http: httpx.AsyncClient, ta: TradingAgentsAdapter
) -> TestResult:
    try:
        if p.id == "tradingagents":
            ver = await ta.version()
            if not ver.ok:
                return TestResult(False, f"TradingAgents not runnable: {ver.data.get('error')}")
            installed = str(ver.data.get("version"))
            if installed != ta.pinned_version:
                return TestResult(False, f"Installed {installed} ≠ pinned {ta.pinned_version}")
            key = await test_llm_key(values["llm_provider"], values["api_key"], http)
            if not key.ok:
                return key
            return TestResult(True, f"TradingAgents {installed} installed · {key.detail}")
        tester = TESTERS.get(p.id)
        if tester is None:
            return TestResult(True, "Saved")
        return await tester(values, http)
    except httpx.HTTPError as e:
        return TestResult(False, f"Network error: {type(e).__name__}")
    except (KeyError, ValueError) as e:
        return TestResult(False, f"Invalid input: {e}")


def _heartbeat_status(s: Session, clock: Clock) -> tuple[str, str]:
    from app.indicators.bars import tf_minutes
    from app.monitor.feed import feed_status

    pairs = s.execute(select(Event.symbol, Event.profile).where(Event.event == "HEARTBEAT").distinct()).all()
    rows = []
    for sym, prof in pairs:
        ev = s.execute(
            select(Event)
            .where(Event.event == "HEARTBEAT", Event.symbol == sym, Event.profile == prof)
            .order_by(Event.bar_time.desc())
            .limit(1)
        ).scalar_one()
        rows.append((sym, prof, ev.bar_time, ev.payload))
    if not rows:
        return "waiting", "Waiting for the first TradingView heartbeat"
    now = clock.now()
    parts, statuses = [], []
    for sym, prof, last, payload in rows:
        tf = str((payload or {}).get("tf", "1"))
        st = feed_status(int(last.timestamp() * 1000), tf_minutes(tf), now, 2)
        statuses.append(st)
        parts.append(f"{sym} {prof}: {st.lower()} ({int((now - last).total_seconds())} s ago)")
    detail = " · ".join(parts)
    if "FRESH" in statuses:
        return "connected", "Receiving alerts · " + detail
    if "STALE" in statuses:
        return "failed", "Feed stale — check your TradingView alert · " + detail
    return "waiting", "Market closed · " + detail


def provider_view(
    p: Provider, row: ApiCredential | None, s: Session, clock: Clock, extra: dict[str, Any] | None = None
) -> dict[str, Any]:
    if p.id == "tradingview":
        status, detail = _heartbeat_status(s, clock)
    elif not p.fields:
        status, detail = "link", ""  # the note is shown separately; avoid duplicating it
    elif row is None:
        status, detail = "not_set", "Not configured"
    else:
        status, detail = row.status, row.status_detail
    links = [{"label": lk.label, "url": lk.url} for lk in p.links]
    if p.id == "tradingagents" and row is not None:
        prov = row.hints.get("llm_provider")
        if prov in LLM_PROVIDERS:
            links.append({"label": f"Get {prov} API key", "url": LLM_PROVIDERS[prov]["keys_url"]})
    return {
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "purpose": p.purpose,
        "required": p.required,
        "testable": p.testable,
        "steps": list(p.steps),
        "note": p.note,
        "links": links,
        "fields": [
            {
                "name": f.name,
                "label": f.label,
                "kind": f.kind,
                "required": f.required,
                "placeholder": f.placeholder,
                "options": list(f.options),
                "help": f.help,
            }
            for f in p.fields
        ],
        "status": status,
        "detail": detail,
        "hints": row.hints if row else {},
        "tested_at": row.tested_at.isoformat() if row and row.tested_at else None,
        **(extra or {}),
    }


def list_views(s: Session, clock: Clock, extras: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = {r.provider: r for r in s.execute(select(ApiCredential)).scalars()}
    return [provider_view(p, rows.get(p.id), s, clock, (extras or {}).get(p.id)) for p in PROVIDERS]


async def save_and_test(
    s: Session,
    vault: Vault,
    clock: Clock,
    http: httpx.AsyncClient,
    ta: TradingAgentsAdapter,
    pid: str,
    values: dict[str, str],
    actor: str,
) -> ApiCredential:
    p = get_provider(pid)
    if not p.fields:
        raise ValueError("this connection has nothing to save")
    row = s.execute(select(ApiCredential).where(ApiCredential.provider == pid)).scalar_one_or_none()
    # Blank secret fields keep the stored value (write-only UI never receives it back).
    if row is not None:
        old = vault.open(row.ciphertext)
        values = {
            **{k: v for k, v in old.items() if k in {f.name for f in p.fields}},
            **{k: v for k, v in values.items() if v.strip()},
        }
    clean = validate_values(p, values)
    if p.testable:
        result = await run_test(p, clean, http, ta)
    else:
        why = "not testable without sending an order" if p.category == "broker" else "no live test available"
        result = TestResult(True, f"Saved ({why})")
    status = ("connected" if result.ok else "failed") if p.testable else "saved"
    if row is None:
        row = ApiCredential(provider=pid, ciphertext="", hints={})
        s.add(row)
    row.ciphertext = vault.seal(clean)
    row.hints = _hints(p, clean)
    row.status, row.status_detail = status, result.detail
    row.tested_at = clock.now() if p.testable else None
    row.updated_at = clock.now()
    audit.record(s, clock, actor, "connection.saved", pid, {"status": status, "fields": sorted(clean)})
    s.flush()
    return row


async def retest(
    s: Session, vault: Vault, clock: Clock, http: httpx.AsyncClient, ta: TradingAgentsAdapter, pid: str, actor: str
) -> ApiCredential:
    p = get_provider(pid)
    row = s.execute(select(ApiCredential).where(ApiCredential.provider == pid)).scalar_one_or_none()
    if row is None:
        raise LookupError("not configured")
    if not p.testable:
        return row
    result = await run_test(p, vault.open(row.ciphertext), http, ta)
    row.status, row.status_detail = ("connected" if result.ok else "failed"), result.detail
    row.tested_at = clock.now()
    audit.record(s, clock, actor, "connection.tested", pid, {"status": row.status})
    s.flush()
    return row


def remove(s: Session, clock: Clock, pid: str, actor: str) -> None:
    get_provider(pid)
    row = s.execute(select(ApiCredential).where(ApiCredential.provider == pid)).scalar_one_or_none()
    if row is not None:
        s.delete(row)
        audit.record(s, clock, actor, "connection.removed", pid, {})
        s.flush()


def credentials(s: Session, vault: Vault, pid: str) -> dict[str, str] | None:
    """Decrypted values for internal use (adapters). Never return this from an API route."""
    row = s.execute(select(ApiCredential).where(ApiCredential.provider == pid)).scalar_one_or_none()
    return vault.open(row.ciphertext) if row else None


# ---------- indicators (§1.6) ----------
_LICENSES = (
    (r"Attribution-NonCommercial-ShareAlike|CC BY-NC-SA", "CC BY-NC-SA 4.0", True),
    (r"Attribution-NonCommercial|CC BY-NC", "CC BY-NC 4.0", True),
    (r"Mozilla Public License", "MPL-2.0", False),
    (r"\bMIT License\b", "MIT", False),
    (r"GNU General Public License|\bGPL", "GPL", False),
)


def detect_license(source: str) -> tuple[str, bool]:
    head = source[:4000]
    for pat, name, nc in _LICENSES:
        if re.search(pat, head, re.IGNORECASE):
            return name, nc
    return "Unknown — read it before porting", True


def save_indicator(s: Session, clock: Clock, iid: str, source: str, actor: str) -> IndicatorSource:
    if iid not in {i["id"] for i in INDICATORS}:
        raise KeyError(iid)
    if "//@version" not in source:
        raise ValueError("That doesn't look like Pine Script source (missing //@version)")
    if len(source) > 500_000:
        raise ValueError("source too large")
    lic, nc = detect_license(source)
    row = s.get(IndicatorSource, iid) or IndicatorSource(id=iid, source="", license="")
    row.source, row.license, row.personal_use_only, row.updated_at = source, lic, nc, clock.now()
    s.add(row)
    audit.record(s, clock, actor, "indicator.source_saved", iid, {"license": lic, "chars": len(source)})
    s.flush()
    return row


def indicator_views(s: Session, clock: Clock) -> list[dict[str, Any]]:
    hb_status, hb_detail = _heartbeat_status(s, clock)
    out = []
    for ind in INDICATORS:
        row = s.get(IndicatorSource, ind["id"])
        out.append(
            {
                **ind,
                "source_on_file": row is not None,
                "license": row.license if row else None,
                "personal_use_only": row.personal_use_only if row else None,
                "alerts_status": hb_status,
                "alerts_detail": hb_detail,
            }
        )
    return out
