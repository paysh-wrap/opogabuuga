"""Vibe-Trading (HKUDS/Vibe-Trading, MIT) — second AI opinion on the daily bias (D53).

Runs ONLY as a subprocess from its own virtualenv `.venv-vt` (never imported into the API process), like
TradingAgents. Each morning, after TradingAgents has rated a proxy (GLD for MGC, QQQ for MNQ), Vibe-Trading is asked
for the same session's directional outlook with OpenBB market context; it answers with one strict line
`VT_OUTLOOK {"direction": "LONG|SHORT|NEUTRAL", "confidence": 0-100, "reason": "..."}`.

Blend (pure, `blend`): TradingAgents stays the backbone — no TradingAgents rating = NO_TRADE. Vibe-Trading can only
UNBLOCK: when TradingAgents limits the day to one side and Vibe-Trading strongly disagrees (opposite direction,
confidence ≥ VETO_CONFIDENCE), the day becomes NEUTRAL (both sides; the intraday rules decide). It never blocks a
side on its own and never places, sizes or exits a trade. Missing / failed / unparsable → TradingAgents alone.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import signal
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PIN = "0.1.19"  # vibe-trading-ai on PyPI (github.com/HKUDS/Vibe-Trading)
VETO_CONFIDENCE = 60
TIMEOUT_S = 600
# provider id → (LANGCHAIN_PROVIDER, env var for the key, default model, extra env)
PROVIDERS: dict[str, tuple[str, str, str, dict[str, str]]] = {
    "anthropic": ("anthropic", "ANTHROPIC_API_KEY", "claude-sonnet-5-5", {"LANGCHAIN_TEMPERATURE": "1"}),
    "qwen": (
        "dashscope",
        "DASHSCOPE_API_KEY",
        "qwen-plus-latest",
        {"DASHSCOPE_BASE_URL": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"},
    ),
    "openrouter": (
        "openrouter",
        "OPENROUTER_API_KEY",
        "deepseek/deepseek-v4-pro",
        {"OPENROUTER_BASE_URL": "https://openrouter.ai/api/v1"},
    ),
    "openai": ("openai", "OPENAI_API_KEY", "gpt-5.5-instant", {"OPENAI_BASE_URL": "https://api.openai.com/v1"}),
}
_LINE = re.compile(r"VT_OUTLOOK\s*(\{.*?\})", re.S)


@dataclass(frozen=True)
class Outlook:
    direction: str  # LONG | SHORT | NEUTRAL
    confidence: int
    reason: str


def env_for(creds: dict[str, str]) -> dict[str, str]:
    """Connections-page values → subprocess environment (the key is never written to disk)."""
    pid = creds.get("llm_provider", "anthropic")
    if pid not in PROVIDERS:
        raise ValueError(f"unknown provider {pid}")
    lc, key_env, model, extra = PROVIDERS[pid]
    if not creds.get("api_key"):
        raise ValueError("api_key missing")
    if pid == "qwen" and os.environ.get("PAYTIENCE_QWEN_BASE_URL"):
        extra = {**extra, "DASHSCOPE_BASE_URL": os.environ["PAYTIENCE_QWEN_BASE_URL"]}
    return {
        "LANGCHAIN_PROVIDER": lc,
        "LANGCHAIN_MODEL_NAME": creds.get("model") or model,
        key_env: creds["api_key"],
        **extra,
    }


def prompt(proxy: str, market: str, session: str, context: dict[str, Any] | None, backfill: bool = False) -> str:
    ctx = json.dumps(context or {}, default=str)[:1500]
    asof = (
        f" HISTORICAL BACKFILL: act as if it is the morning of {session} before the open. Use ONLY information "
        f"published on or before {session}; ignore anything later."
        if backfill
        else ""
    )
    return asof + (
        f"You are a futures day-trading risk desk. Session date {session} (US/Eastern). Market: {market} "
        f"(directional proxy ETF {proxy}). Recent daily data from OpenBB (may be empty): {ctx}. "
        "Using current news, macro calendar and price action, give ONE intraday directional outlook for today's "
        "session. Do not run backtests. Finish your answer with exactly one line, nothing after it:\n"
        'VT_OUTLOOK {"direction": "LONG" or "SHORT" or "NEUTRAL", "confidence": integer 0-100, '
        '"reason": "max 25 words"}'
    )


def parse(stdout: str) -> Outlook | None:
    """Last VT_OUTLOOK line in the CLI output → Outlook; anything malformed → None (= ignored)."""
    found = _LINE.findall(stdout or "")
    if not found:
        return None
    try:
        d = json.loads(found[-1])
        direction = str(d.get("direction", "")).upper()
        conf = int(d.get("confidence", 0))
    except (ValueError, TypeError, AttributeError):
        return None
    if direction not in ("LONG", "SHORT", "NEUTRAL") or not 0 <= conf <= 100:
        return None
    return Outlook(direction, conf, str(d.get("reason", ""))[:300])


def blend(ta_mapped: str, vt: Outlook | None) -> tuple[str, str]:
    """(TradingAgents mapped bias, Vibe-Trading outlook) → (final mapped bias, short note). PURE."""
    if ta_mapped not in ("LONG_ONLY", "SHORT_ONLY", "NEUTRAL"):
        return ta_mapped, "TradingAgents unavailable → no trade (backbone)"
    if vt is None:
        return ta_mapped, "Vibe-Trading not available → TradingAgents alone"
    side = {"LONG_ONLY": "LONG", "SHORT_ONLY": "SHORT"}.get(ta_mapped)
    if side and vt.direction not in (side, "NEUTRAL") and vt.confidence >= VETO_CONFIDENCE:
        return "NEUTRAL", f"Vibe-Trading disagrees ({vt.direction} {vt.confidence}) → both sides allowed"
    return ta_mapped, f"Vibe-Trading {vt.direction} {vt.confidence} — TradingAgents decides"


def executable(root: Path) -> Path:
    return root / ".venv-vt" / ("Scripts/vibe-trading.exe" if os.name == "nt" else "bin/vibe-trading")


async def run(
    exe: Path, env: dict[str, str], text: str, home: Path, timeout_s: int = TIMEOUT_S
) -> tuple[Outlook | None, str]:
    """One research run. Returns (outlook or None, short status). Never raises; kills the whole process group."""
    if not exe.exists():
        return None, "not installed"
    home.mkdir(parents=True, exist_ok=True)
    full_env = {**os.environ, **env, "HOME": str(home), "USERPROFILE": str(home), "PYTHONIOENCODING": "utf-8"}
    try:
        p = await asyncio.create_subprocess_exec(
            str(exe),
            "run",
            "-p",
            text,
            "--no-rich",
            "--max-iter",
            "12",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=full_env,
            start_new_session=os.name != "nt",
        )
    except OSError as e:
        return None, f"start failed: {type(e).__name__}"
    try:
        out, _ = await asyncio.wait_for(p.communicate(), timeout_s)
    except TimeoutError:
        try:
            if os.name != "nt":
                os.killpg(p.pid, signal.SIGKILL)
            else:
                p.kill()
        except ProcessLookupError:
            pass
        return None, "timeout"
    text_out = out.decode("utf-8", "replace")
    o = parse(text_out)
    if o is None:
        m = re.search(r"Reason:\s*(.+)", text_out)
        return None, ("no outlook: " + (m.group(1)[:120] if m else f"exit {p.returncode}"))
    return o, "ok"
