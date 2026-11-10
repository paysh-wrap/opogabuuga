"""Live credential checks. Read-only calls only — a test must never place an order or send a message."""

from __future__ import annotations

import os
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
    url = spec["models_url"]
    if provider == "qwen" and os.environ.get(
        "PAYTIENCE_QWEN_BASE_URL"
    ):  # workspace keys (sk-ws-…) only work on their own endpoint
        url = os.environ["PAYTIENCE_QWEN_BASE_URL"].rstrip("/") + "/models"
    r = await http.get(url, headers=headers)
    return _status_msg(r, f"{provider} key accepted")


async def _alpha_vantage(v: dict[str, str], http: httpx.AsyncClient) -> TestResult:
    r = await http.get(
        "https://www.alphavantage.co/query",
        params={"function": "GLOBAL_QUOTE", "symbol": "QQQ", "apikey": v["api_key"]},
    )
    if r.status_code != 200:
        return TestResult(False, f"HTTP {r.status_code}")
    body = r.json()
    if body.get("Global Quote"):  # Alpha Vantage answers this call for ANY key, so a typo cannot be detected here
        return TestResult(True, "Data request works (Alpha Vantage does not verify keys — double-check it)")
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
    if r.status_code == 400 and "auth" in r.text:  # Databento: bad key → 400 auth_* (key = username, no password)
        return TestResult(False, "Key rejected (use the db-… API key)")
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


async def _ngrok(v: dict[str, str], http: httpx.AsyncClient) -> TestResult:
    """D79: proves token + domain by starting the agent once (or reuses the running one). Secrets never returned."""
    from app import tunnel
    from app.settings import get_settings

    domain = tunnel.clean_domain(v["domain"])
    m = tunnel.ACTIVE
    if m is not None and m.state.mode == "ngrok" and m.state.domain == domain:
        return TestResult(True, f"ngrok is running · permanent URL https://{domain}")
    if m is not None:
        m._kill()  # frees the domain if the manager is retrying; it restarts on poke below
    try:
        ok, msg = await tunnel.verify_ngrok(get_settings().tools_dir, v["authtoken"], domain)
    except Exception as e:
        return TestResult(False, f"Could not run ngrok: {type(e).__name__}")
    finally:
        if m is not None:
            m.poke()
    return TestResult(ok, msg)


async def _crosstrade(v: dict[str, str], http: httpx.AsyncClient) -> TestResult:
    r = await http.get("https://app.crosstrade.io/v1/api/tv/status", headers={"Authorization": f"Bearer {v['token']}"})
    if r.status_code == 200:
        return TestResult(True, "Key accepted · Tradovate link OK")
    err = (r.json() or {}).get("error", "") if r.content else ""
    return TestResult(False, f"HTTP {r.status_code} {err}".strip())


async def _vibetrading(v: dict[str, str], http: httpx.AsyncClient) -> TestResult:
    """D53: Vibe-Trading must be installed (.venv-vt) and its LLM key must work."""
    from app.bias.vibe_trading import executable
    from app.settings import get_settings

    if not executable(get_settings().vt_root).exists():
        return TestResult(False, "Vibe-Trading not installed — run start.py (or make vibetrading) once")
    p = v.get("llm_provider", "anthropic")
    if p in ("anthropic", "qwen"):
        return await test_llm_key(p, v["api_key"], http)
    url = {"openrouter": "https://openrouter.ai/api/v1/key", "openai": "https://api.openai.com/v1/models"}[p]
    r = await http.get(url, headers={"Authorization": f"Bearer {v['api_key']}"})
    return _status_msg(r, f"{p} key accepted")


TESTERS: dict[str, Tester] = {
    "vibetrading": _vibetrading,
    "crosstrade": _crosstrade,
    "alpha_vantage": _alpha_vantage,
    "fred": _fred,
    "databento": _databento,
    "discord": _discord,
    "telegram": _telegram,
    "tunnel": _tunnel,
    "ngrok": _ngrok,
}
