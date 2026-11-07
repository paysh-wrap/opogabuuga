"""Adapter for TauricResearch/TradingAgents (pinned, never modified) — §15.

The package lives in its own virtualenv (PAYTIENCE_TA_PYTHON). We talk to it through
`ta_runner.py` over stdin/stdout JSON, so its dependencies can never affect trading and a
hang is bounded by a hard timeout.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import signal
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal

from app.connections.registry import BEST_MODELS, LLM_PROVIDERS

Mapped = Literal["LONG_ONLY", "SHORT_ONLY", "NEUTRAL", "NO_TRADE"]
RUNNER = Path(__file__).with_name("ta_runner.py")


def map_rating(raw: str | None, rating_map: dict[str, str]) -> tuple[Mapped, bool]:
    """Five-tier map (§15). Returns (mapped, alert). Unknown text, REVIEW or failure → NO_TRADE + alert."""
    key = (raw or "").strip().upper()
    mapped = rating_map.get(key)
    if mapped in ("LONG_ONLY", "SHORT_ONLY", "NEUTRAL"):
        return mapped, False  # type: ignore[return-value]
    return "NO_TRADE", True


@dataclass(frozen=True)
class RunnerResult:
    ok: bool
    data: dict[str, Any]


class TradingAgentsAdapter:
    def __init__(self, python_bin: str, pinned_version: str, timeout_s: float) -> None:
        self.python_bin = python_bin
        self.pinned_version = pinned_version
        self.timeout_s = timeout_s

    def installed(self) -> bool:
        return Path(self.python_bin).exists()

    async def _call(
        self, req: dict[str, Any], env_extra: dict[str, str] | None = None, timeout_s: float | None = None
    ) -> RunnerResult:
        if not self.installed():
            return RunnerResult(False, {"error": f"TradingAgents environment not found at {self.python_bin}"})
        env = {k: v for k, v in os.environ.items() if not k.endswith("_API_KEY")}
        env.update(env_extra or {})
        proc = await asyncio.create_subprocess_exec(
            self.python_bin,
            "-I",
            str(RUNNER),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            start_new_session=True,  # own process group, so a timeout kills every child it started
        )
        try:
            out, _err = await asyncio.wait_for(
                proc.communicate(json.dumps(req).encode()), timeout=timeout_s or self.timeout_s
            )
        except TimeoutError:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            with contextlib.suppress(Exception):
                await asyncio.wait_for(proc.communicate(), timeout=5)  # drain + close the pipes after kill
            return RunnerResult(False, {"error": "timeout"})
        try:
            data = json.loads(out.decode() or "{}")
        except json.JSONDecodeError:
            return RunnerResult(False, {"error": "runner returned invalid JSON"})
        return RunnerResult(bool(data.get("ok")), data)

    async def version(self) -> RunnerResult:
        return await self._call({"cmd": "version"}, timeout_s=60)

    async def catalog(self) -> RunnerResult:
        return await self._call({"cmd": "catalog"}, timeout_s=60)

    @staticmethod
    def env_for(creds: dict[str, str], catalog: dict[str, dict[str, list[str]]] | None) -> dict[str, str]:
        provider = creds["llm_provider"]
        spec = LLM_PROVIDERS[provider]
        quick = creds.get("quick_think_llm") or ""
        deep = creds.get("deep_think_llm") or ""
        opts = (catalog or {}).get(provider, {})
        best = BEST_MODELS.get(provider, {})
        quick = quick or best.get("quick") or (opts.get("quick") or [""])[0]
        deep = deep or best.get("deep") or (opts.get("deep") or [""])[0]
        env = {spec["env"]: creds["api_key"], "TRADINGAGENTS_LLM_PROVIDER": provider}
        if provider == "qwen" and os.environ.get("PAYTIENCE_QWEN_BASE_URL"):
            env["DASHSCOPE_BASE_URL"] = os.environ["PAYTIENCE_QWEN_BASE_URL"]
        if quick:
            env["TRADINGAGENTS_QUICK_THINK_LLM"] = quick
        if deep:
            env["TRADINGAGENTS_DEEP_THINK_LLM"] = deep
        return env

    async def run(self, ticker: str, today: date, env: dict[str, str]) -> RunnerResult:
        """Live-only: callers pass the CURRENT session date. Never re-run for past dates (§15)."""
        return await self._call({"cmd": "run", "ticker": ticker, "date": today.isoformat()}, env)
