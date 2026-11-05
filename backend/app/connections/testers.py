"""Live credential checks. Read-only calls only — a test must never place an order or send a message."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx

from app.connections.registry import LLM_PROVIDERS


@dataclass(frozen=True)
class TestResult:
    ok: bool
    detail: str


Tester = Callable[[dict[str, str], httpx.AsyncClient], Awaitable[TestResult]]


def _status_msg(r: httpx.Response, ok_text: str) -> TestResult:
    if r.status_code == 200:
        return TestResult(True, ok_text)
    if r.status_code in (401, 403):
        return TestResult(False, f"Key rejected (HTTP {r.status_code})")
    return TestResult(False, f"Unexpected response HTTP {r.status_code}")


async def test_llm_key(provider: str, key: str, http: httpx.AsyncClient) -> TestResult:
    spec = LLM_PROVIDERS.get(provider)
    if spec is None:
        return TestResult(False, f"Unsupported provider {provider!r}")
    headers: dict[str, str]
    if spec["auth"] == "anthropic":
        headers = {"x-api-key": key, "anthropic-version": "2023-06-01"}
    elif spec["auth"] == "google":
        headers = {"x-goog-api-key": key}
    else:
        headers = {"Authorization": f"Bearer {key}"}
    r = await http.get(spec["models_url"], headers=headers)
    return _status_msg(r, f"{provider} key accepted")


async def _alpha_vantage(v: dict[str, str], http: httpx.AsyncClient) -> TestResult:
    r = await http.get(
        "https://www.alphavantage.co/query",
        params={"function": "GLOBAL_QUOTE", "symbol": "QQQ", "apikey": v["api_key"]},
    )
    if r.status_code != 200:
        return TestResult(False, f"HTTP {r.status_code}")
    body = r.json()
    if body.get("Global Quote"):
        return TestResult(True, "Key accepted (QQQ quote received)")
    msg = body.get("Error Message") or body.get("Information") or body.get("Note") or "No data returned"
    return TestResult(False, str(msg)[:200])


async def _fred(v: dict[str, str], http: httpx.AsyncClient) -> TestResult:
    r = await http.get(
        "https://api.stlouisfed.org/fred/series",
        params={"series_id": "GDP", "api_key": v["api_key"], "file_type": "json"},
    )
    return _status_msg(r, "Key accepted") if r.status_code != 400 else TestResult(False, "Key rejected")


async def _databento(v: dict[str, str], http: httpx.AsyncClient) -> TestResult:
    r = await http.get("https://hist.databento.com/v0/metadata.list_datasets", auth=(v["api_key"], ""))
    if r.status_code == 200 and "GLBX.MDP3" in r.text:
        return TestResult(True, "Key accepted (CME Globex GLBX.MDP3 available)")
    return _status_msg(r, "Key accepted")


async def _discord(v: dict[str, str], http: httpx.AsyncClient) -> TestResult:
    url = v["webhook_url"]
    if not url.startswith(("https://discord.com/api/webhooks/", "https://discordapp.com/api/webhooks/")):
        return TestResult(False, "Not a Discord webhook URL")
    r = await http.get(url)  # GET returns webhook info and sends nothing
    return _status_msg(r, "Webhook valid") if r.status_code != 404 else TestResult(False, "Webhook not found")


async def _telegram(v: dict[str, str], http: httpx.AsyncClient) -> TestResult:
    r = await http.get(f"https://api.telegram.org/bot{v['bot_token']}/getMe")
    if r.status_code == 200 and r.json().get("ok"):
        return TestResult(True, f"Bot @{r.json()['result'].get('username', '?')} reachable")
    return TestResult(False, f"Bot token rejected (HTTP {r.status_code})")


async def _tunnel(v: dict[str, str], http: httpx.AsyncClient) -> TestResult:
    base = v["public_url"].rstrip("/")
    if not base.startswith("https://"):
        return TestResult(False, "Must start with https:// (TradingView only posts to 443/80)")
    r = await http.get(f"{base}/api/health")
    if r.status_code == 200 and r.json().get("app") == "paytience":
        return TestResult(True, "Reachable from the internet — this is your webhook base URL")
    return TestResult(False, f"Not reachable or not Paytience (HTTP {r.status_code})")


async def _crosstrade(v: dict[str, str], http: httpx.AsyncClient) -> TestResult:
    r = await http.get("https://app.crosstrade.io/v1/api/tv/status", headers={"Authorization": f"Bearer {v['token']}"})
    if r.status_code == 200:
        return TestResult(True, "Key accepted · Tradovate link OK")
    err = (r.json() or {}).get("error", "") if r.content else ""
    return TestResult(False, f"HTTP {r.status_code} {err}".strip())


TESTERS: dict[str, Tester] = {
    "crosstrade": _crosstrade,
    "alpha_vantage": _alpha_vantage,
    "fred": _fred,
    "databento": _databento,
    "discord": _discord,
    "telegram": _telegram,
    "tunnel": _tunnel,
}
