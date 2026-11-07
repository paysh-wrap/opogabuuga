"""OpenBB market panel (display only — never used for signals, sizing or orders).

OpenBB runs in its own `uvx` environment as a subprocess (like TradingAgents in .venv-ta), never imported into the
API process. Daily closes for the MGC/MNQ continuous futures (Yahoo via OpenBB), cached; failures are reported, not
hidden (§1.8), and never block trading.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import time
from dataclasses import dataclass, field
from typing import Any

SYMBOLS = {"MGC": "MGC=F", "MNQ": "MNQ=F"}
TTL_S = 300
TIMEOUT_S = 240
UVX_ARGS = ["--from", "openbb", "--with", "openbb-yfinance", "--with", "openbb-equity", "python", "-I", "-c"]
SCRIPT = """
import json, datetime
import os
from openbb import obb
# optional keys from the Connections page (passed in the environment, never on the command line)
if os.environ.get("PB_OPENBB_PAT"):
    try:
        obb.account.login(pat=os.environ["PB_OPENBB_PAT"], remember_me=False)
    except Exception:
        pass
for _k in ("fmp_api_key", "polygon_api_key"):
    if os.environ.get("PB_" + _k.upper()):
        setattr(obb.user.credentials, _k, os.environ["PB_" + _k.upper()])
start = (datetime.date.today() - datetime.timedelta(days=45)).isoformat()
out = {}
for k, s in %s.items():
    try:
        rows = obb.equity.price.historical(s, provider="yfinance", interval="1d", start_date=start).to_dict("records")
        out[k] = [[str(r.get("date"))[:10], float(r["close"])] for r in rows if r.get("close") is not None]
    except Exception as e:
        out[k] = {"error": type(e).__name__}
print("OBB" + json.dumps(out))
"""


def summarize(raw: dict[str, Any]) -> dict[str, Any]:
    """Pure: {sym: [[date, close], ...]} → last, change, change %, series (last 30 closes)."""
    out: dict[str, Any] = {}
    for k, rows in raw.items():
        if not isinstance(rows, list) or not rows:
            out[k] = {"error": rows.get("error", "NO_DATA") if isinstance(rows, dict) else "NO_DATA"}
            continue
        last, prev = rows[-1][1], (rows[-2][1] if len(rows) > 1 else rows[-1][1])
        out[k] = {
            "date": rows[-1][0],
            "last": round(last, 2),
            "change": round(last - prev, 2),
            "change_pct": round((last - prev) / prev * 100, 2) if prev else 0.0,
            "series": [round(c, 2) for _, c in rows[-30:]],
        }
    return out


def parse_output(stdout: str) -> dict[str, Any]:
    line = next((x for x in stdout.splitlines() if x.startswith("OBB")), None)
    if line is None:
        raise ValueError("no OpenBB output")
    data = json.loads(line[3:])
    if not isinstance(data, dict):
        raise ValueError("bad OpenBB output")
    return data


@dataclass
class OpenBBFeed:
    uvx: str | None = field(default_factory=lambda: shutil.which("uvx"))
    data: dict[str, Any] | None = None
    error: str | None = None
    fetched_at: float = 0.0
    _task: asyncio.Task[None] | None = None
    creds: dict[str, str] = field(default_factory=dict)  # optional keys from the Connections page

    def snapshot(self) -> dict[str, Any]:
        if self.uvx is None:
            status = "NOT_INSTALLED"
        elif self.data is None:
            status = "ERROR" if self.error else "LOADING"
        else:
            status = "OK" if not self.error else "STALE"
        if self.uvx is not None and time.time() - self.fetched_at > TTL_S and (self._task is None or self._task.done()):
            self._task = asyncio.get_running_loop().create_task(self.refresh())
        return {
            "status": status,
            "error": self.error,
            "age_s": int(time.time() - self.fetched_at) if self.data else None,
            "source": "OpenBB · Yahoo Finance (continuous front-month, daily)",
            "symbols": self.data or {},
        }

    async def refresh(self) -> None:
        assert self.uvx is not None
        self.fetched_at = time.time()
        try:
            p = await asyncio.create_subprocess_exec(
                self.uvx,
                *UVX_ARGS,
                SCRIPT % repr(SYMBOLS),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env={
                    **os.environ,
                    **{f"PB_{('OPENBB_PAT' if k == 'pat' else k.upper())}": v for k, v in self.creds.items() if v},
                },
            )
            out, _ = await asyncio.wait_for(p.communicate(), TIMEOUT_S)
            self.data, self.error = summarize(parse_output(out.decode())), None
        except (TimeoutError, ValueError, OSError) as e:
            self.error = f"{type(e).__name__}: {e}"[:200]
