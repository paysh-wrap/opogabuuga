"""Every outside service Paytience uses, with where to log in / get a key (D3).

Links are informational. The app never logs into these sites for you (§1.1, §1.3).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

FieldKind = Literal["secret", "text", "select"]
Category = Literal["signals", "ai_bias", "broker", "data", "notifications", "network", "firm", "updates"]


@dataclass(frozen=True)
class Link:
    label: str
    url: str


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    kind: FieldKind = "secret"
    required: bool = True
    placeholder: str = ""
    options: tuple[str, ...] = ()
    help: str = ""


@dataclass(frozen=True)
class Provider:
    id: str
    name: str
    category: Category
    purpose: str
    links: tuple[Link, ...]
    fields: tuple[FieldSpec, ...] = ()
    required: bool = False  # needed before trading
    testable: bool = True  # False → "Saved" (never "Connected") because a test would place orders
    steps: tuple[str, ...] = field(default_factory=tuple)
    note: str = ""


# LLM providers supported by TauricResearch/TradingAgents v0.7.x (tradingagents/llm_clients/api_key_env.py)
LLM_PROVIDERS: dict[str, dict[str, str]] = {  # order = UI order; Claude (anthropic) is the default power source
    "anthropic": {
        "env": "ANTHROPIC_API_KEY",
        "keys_url": "https://console.anthropic.com/settings/keys",
        "models_url": "https://api.anthropic.com/v1/models",
        "auth": "anthropic",
    },
    "kimi": {  # Moonshot AI (TradingAgents: MOONSHOT_API_KEY, base https://api.moonshot.ai/v1)
        "env": "MOONSHOT_API_KEY",
        "keys_url": "https://platform.kimi.ai/",
        "models_url": "https://api.moonshot.ai/v1/models",
        "auth": "bearer",
    },
    "qwen": {  # Alibaba Model Studio / DashScope intl (TradingAgents: DASHSCOPE_API_KEY)
        "env": "DASHSCOPE_API_KEY",
        "keys_url": "https://www.alibabacloud.com/help/en/model-studio/get-api-key",
        "models_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1/models",
        "auth": "bearer",
    },
    "openai": {
        "env": "OPENAI_API_KEY",
        "keys_url": "https://platform.openai.com/api-keys",
        "models_url": "https://api.openai.com/v1/models",
        "auth": "bearer",
    },
    "google": {
        "env": "GOOGLE_API_KEY",
        "keys_url": "https://aistudio.google.com/app/apikey",
        "models_url": "https://generativelanguage.googleapis.com/v1beta/models",
        "auth": "google",
    },
    "deepseek": {
        "env": "DEEPSEEK_API_KEY",
        "keys_url": "https://platform.deepseek.com/api_keys",
        "models_url": "https://api.deepseek.com/models",
        "auth": "bearer",
    },
    "xai": {
        "env": "XAI_API_KEY",
        "keys_url": "https://console.x.ai/",
        "models_url": "https://api.x.ai/v1/models",
        "auth": "bearer",
    },
    "groq": {
        "env": "GROQ_API_KEY",
        "keys_url": "https://console.groq.com/keys",
        "models_url": "https://api.groq.com/openai/v1/models",
        "auth": "bearer",
    },
    "mistral": {
        "env": "MISTRAL_API_KEY",
        "keys_url": "https://console.mistral.ai/api-keys",
        "models_url": "https://api.mistral.ai/v1/models",
        "auth": "bearer",
    },
}

# Best models per provider (from TradingAgents v0.7.1's own model catalog) — used when the model fields are blank.
BEST_MODELS: dict[str, dict[str, str]] = {
    "anthropic": {"deep": "claude-opus-5-5", "quick": "claude-sonnet-5"},
    "kimi": {"deep": "kimi-k3", "quick": "kimi-k2.6"},
    "qwen": {"deep": "qwen3.8-max", "quick": "qwen3.8-flash"},
}

LLM_NAMES = {"anthropic": "Claude (Anthropic) — default", "kimi": "Kimi (Moonshot)", "qwen": "Qwen (Alibaba)"}

LUNQFX_NAME = "ICT Fractal Model, HTF Candles, CISD & C2 Targets [LunqFX]"
BIGBELUGA_NAME = "Market Structure Oscillator [BigBeluga]"
TA_REPO = "https://github.com/TauricResearch/TradingAgents"


def _tv_search(name: str) -> str:
    from urllib.parse import quote

    return f"https://www.tradingview.com/scripts/search/{quote(name)}/"


PROVIDERS: tuple[Provider, ...] = (
    Provider(
        id="tradingview",
        name="TradingView (webhook alerts)",
        category="signals",
        required=True,
        testable=False,
        purpose="Runs the Paytience Bridge + your two indicators and sends alerts to this app on every closed bar.",
        links=(
            Link("Log in", "https://www.tradingview.com/accounts/signin/"),
            Link("Plans (webhooks need a paid plan)", "https://www.tradingview.com/pricing/"),
            Link("Webhook help", "https://www.tradingview.com/support/solutions/43000529348-about-webhooks/"),
            Link("2FA settings", "https://www.tradingview.com/settings/#account-settings"),
        ),
        steps=(
            "Use a paid plan with webhooks and turn on 2FA.",
            "Add both indicators and Paytience_Bridge to an MGC chart (MGC1!, Micro Gold — MNQ is off, D42).",
            "Create an alert → 'Any alert() function call' → Webhook URL below.",
            "This card turns gold when the first heartbeat arrives (Phase 2).",
        ),
    ),
    Provider(
        id="tradingagents",
        name="TradingAgents — TauricResearch/TradingAgents",
        category="ai_bias",
        required=True,
        purpose="Daily AI bias (Buy/Overweight/Hold/Underweight/Sell → LONG_ONLY/NEUTRAL/SHORT_ONLY). "
        "Installed from GitHub at the pinned tag in its own isolated environment.",
        links=(
            Link("GitHub repository", TA_REPO),
            Link("Releases", f"{TA_REPO}/releases"),
            *(Link(f"{LLM_NAMES.get(k, k)} key", v["keys_url"]) for k, v in LLM_PROVIDERS.items()),
        ),
        fields=(
            FieldSpec("llm_provider", "LLM provider", "select", options=tuple(LLM_PROVIDERS)),
            FieldSpec("api_key", "LLM API key", "secret", placeholder="paste key"),
            FieldSpec(
                "quick_think_llm",
                "Quick model",
                "text",
                required=False,
                help="Blank = best model: Claude Sonnet 5 · Kimi K2.6 · Qwen 3.8 Flash. Cheaper model = lower cost.",
            ),
            FieldSpec(
                "deep_think_llm",
                "Deep model",
                "text",
                required=False,
                help="Blank = best model: Claude Opus 5.5 · Kimi K3 · Qwen 3.8 Max.",
            ),
        ),
        steps=(
            "Pick an LLM provider and get its API key from the matching link below (log in there).",
            "Paste it here and press Save & Test: we validate the key and the installed package.",
            "Until connected, bias = NO_TRADE (spec §15) and no trades are taken.",
        ),
    ),
    Provider(
        id="alpha_vantage",
        name="Alpha Vantage (optional, TradingAgents data)",
        category="ai_bias",
        purpose="Optional extra market/news data for TradingAgents (default vendor yfinance needs no key).",
        links=(Link("Get free key", "https://www.alphavantage.co/support/#api-key"),),
        fields=(FieldSpec("api_key", "API key"),),
    ),
    Provider(
        id="fred",
        name="FRED (optional, TradingAgents macro data)",
        category="ai_bias",
        purpose="Free St. Louis Fed macro data used by TradingAgents' news analyst.",
        links=(Link("Get free key", "https://fred.stlouisfed.org/docs/api/api_key.html"),),
        fields=(FieldSpec("api_key", "API key"),),
    ),
    Provider(
        id="tradovate",
        name="Tradovate (broker for Lucid accounts)",
        category="broker",
        testable=False,
        purpose="Places bracket orders and reads positions/fills. Prop accounts may not get API access — "
        "ask Lucid support (Phase 0 B1). Tested in Phase 5.",
        links=(
            Link("Trader login", "https://trader.tradovate.com/welcome"),
            Link("API docs", "https://api.tradovate.com/"),
        ),
        fields=(FieldSpec("cid", "Client ID (cid)", "text"), FieldSpec("sec", "Client secret")),
        note="Your Tradovate password is never stored; it is asked once and discarded (§1.2).",
    ),
    Provider(
        id="crosstrade",
        name="CrossTrade (Tradovate orders + positions)",
        category="broker",
        purpose="Places bracket orders on your Lucid Tradovate accounts and reads positions/P&L back, so the "
        "kill switch can see live P&L. Needs CrossTrade Pro + your Tradovate account linked in CrossTrade.",
        links=(
            Link("Sign up / log in", "https://crosstrade.io/"),
            Link("API docs", "https://crosstrade.io/docs/api/tradovate/overview"),
        ),
        fields=(FieldSpec("token", "Secret key (My Account → Security → Reveal)"),),
        note="Needed for automated orders on any Lucid account. It reads positions back, which the live-readiness gate requires.",  # noqa: E501
        steps=(
            "Subscribe to CrossTrade Pro (the REST API needs Pro).",
            "Link your Lucid Tradovate login inside CrossTrade.",
            "Paste the secret key here → Save & Test (read-only check, places no order).",
        ),
    ),
    Provider(
        id="lucid",
        name="Lucid Trading (dashboard link only)",
        category="firm",
        testable=False,
        purpose="Lucid has no API. Log in on their site to buy accounts, check your drawdown type and request "
        "payouts (the Payouts page tells you how much). Rules the app follows: docs/LUCID_RULES.md.",
        links=(
            Link("Lucid website / log in", "https://lucidtrading.com/"),
            Link("Help center (rules, payouts, live)", "https://support.lucidtrading.com/"),
        ),
        steps=(
            "Log in on Lucid's site → note each account's Tradovate account number.",
            "Add it on the Automation page (Tradovate account #) and pick EOD or Intraday to match Lucid.",
            "Fridays: request the payout amount shown on the Payouts page, then mark it here.",
        ),
        note="The app never logs into Lucid or automates their website (§1.3).",
    ),
    Provider(
        id="databento",
        name="Databento (historical futures data)",
        category="data",
        purpose="1-minute MNQ/MES/MYM/MGC history for backtests and the Strategy Lab (self-learning).",
        links=(Link("Sign up", "https://databento.com/signup"), Link("API keys", "https://databento.com/portal/keys")),
        fields=(FieldSpec("api_key", "API key", placeholder="db-..."),),
    ),
    Provider(
        id="fincept",
        name="Fincept (fundamental research — optional)",
        category="data",
        testable=False,
        purpose="Extra fundamental context for gold and Nasdaq (macro, rates, news). INFORMATION ONLY: never changes "
        "the TradingAgents bias, the gates or sizing. Fincept Terminal itself is a separate desktop app (AGPL-3.0, "
        "personal use).",
        links=(
            Link("Sign up (free tier)", "https://fincept.in"),
            Link("Data API docs", "https://docs.fincept.in"),
            Link("Desktop terminal", "https://github.com/Fincept-Corporation/FinceptTerminal/releases"),
        ),
        fields=(FieldSpec("api_key", "Fincept Data API key", required=False),),
        note="Panel wiring waits until the API endpoints are verified (no guessing on data sources).",
    ),
    Provider(
        id="vibetrading",
        name="Vibe-Trading — HKUDS/Vibe-Trading (AI second opinion)",
        category="ai_bias",
        required=False,
        purpose="Second AI opinion on the daily bias (D53). Each morning after TradingAgents it reads OpenBB market "
        "data and gives LONG / SHORT / NEUTRAL with a confidence. It can only UNBLOCK: if TradingAgents allows one "
        "side and Vibe-Trading strongly disagrees, both sides are allowed and the intraday rules decide. "
        "It never places, sizes or blocks trades by itself. Installed in its own environment (.venv-vt).",
        links=(
            Link("GitHub repository", "https://github.com/HKUDS/Vibe-Trading"),
            Link("Claude (Anthropic) key", "https://console.anthropic.com/settings/keys"),
            Link("Qwen (Alibaba DashScope) key", "https://www.alibabacloud.com/help/en/model-studio/get-api-key"),
            Link("OpenRouter key", "https://openrouter.ai/keys"),
        ),
        fields=(
            FieldSpec("llm_provider", "LLM provider", "select", options=("anthropic", "qwen", "openrouter", "openai")),
            FieldSpec("api_key", "LLM API key", "secret", placeholder="paste key"),
            FieldSpec(
                "model",
                "Model (optional)",
                "text",
                required=False,
                placeholder="default: claude-sonnet-5-5 / qwen-plus-latest",
            ),
        ),
    ),
    Provider(
        id="openbb",
        name="OpenBB (market data — keys optional)",
        category="data",
        testable=False,
        fields=(  # all optional: the free Yahoo feed works without any key
            FieldSpec(
                "pat",
                "OpenBB Hub personal access token",
                "secret",
                required=False,
                placeholder="optional",
                help="my.openbb.co → Settings → Personal Access Token",
            ),
            FieldSpec("fmp_api_key", "Financial Modeling Prep key", "secret", required=False, placeholder="optional"),
            FieldSpec("polygon_api_key", "Polygon key", "secret", required=False, placeholder="optional"),
        ),
        purpose="Free daily MGC/MNQ data (Yahoo Finance via OpenBB) — live on the Dashboard 'Markets · OpenBB' panel "
        "(runs in its own uvx process, refreshed every 5 min). Information only; signals still come from TradingView "
        "webhooks and bias from TradingAgents.",
        links=(
            Link("OpenBB", "https://github.com/OpenBB-finance/OpenBB"),
            Link("OpenBB Hub (token)", "https://my.openbb.co/app/platform/pat"),
            Link(
                "OpenBB MCP server",
                "https://github.com/OpenBB-finance/OpenBB/tree/develop/openbb_platform/extensions/mcp_server",
            ),
        ),
    ),
    Provider(
        id="forexfactory",
        name="ForexFactory (economic calendar — no key needed)",
        category="data",
        testable=False,
        purpose="High-impact USD news → blackouts and funded flat windows. Fetched automatically every 4 h "
        "(free weekly feed). No calendar data = no trading (§15). Status: Today page.",
        links=(Link("Calendar", "https://www.forexfactory.com/calendar"),),
    ),
    Provider(
        id="discord",
        name="Discord (notifications)",
        category="notifications",
        purpose="Alerts for approvals, fills, risk events and payouts.",
        links=(
            Link(
                "How to create a webhook", "https://support.discord.com/hc/en-us/articles/228383668-Intro-to-Webhooks"
            ),
        ),
        fields=(FieldSpec("webhook_url", "Webhook URL", placeholder="https://discord.com/api/webhooks/..."),),
    ),
    Provider(
        id="ngrok",
        name="ngrok (permanent webhook URL)",
        category="network",
        purpose="Free static domain so the TradingView webhook URL never changes. Paytience downloads and starts "
        "ngrok by itself — no command prompt. If ngrok is not set up or fails, a temporary Cloudflare link is used "
        "(with a warning) and the URL changes on every restart.",
        links=(
            Link("1. Sign up (free)", "https://dashboard.ngrok.com/signup"),
            Link("2. Claim your free static domain", "https://dashboard.ngrok.com/domains"),
            Link("3. Copy your authtoken", "https://dashboard.ngrok.com/get-started/your-authtoken"),
        ),
        fields=(
            FieldSpec("authtoken", "ngrok authtoken"),
            FieldSpec("domain", "Static domain", "text", placeholder="your-name.ngrok-free.app"),
        ),
        steps=(
            "Sign up at ngrok.com (free).",
            "Dashboard → Domains → claim your free static domain (looks like your-name.ngrok-free.app).",
            "Dashboard → Your Authtoken → copy it.",
            "Paste both here, Save & test. Paytience starts ngrok automatically from then on.",
        ),
        note="Permanent — set the webhook URL once in TradingView. The authtoken is encrypted and never shown again.",
    ),
    Provider(
        id="github_updates",
        name="GitHub (app updates)",
        category="updates",
        purpose="Optional (D88): lets the Windows desktop app check for and install new versions of Paytience. "
        "Use a READ-ONLY fine-grained token. The app works without it.",
        links=(Link("Create a fine-grained token", "https://github.com/settings/personal-access-tokens/new"),),
        fields=(FieldSpec("token", "GitHub fine-grained token", placeholder="github_pat_…"),),
        steps=(
            "GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new.",
            "Repository access: Only select repositories → paysh-wrap/opogabuuga.",
            "Permissions → Repository → Contents: Read-only (nothing else).",
            "Generate, copy, paste here and Save & test.",
        ),
        note="Encrypted, write-only, never shown again. Updates install only when you click Install now.",
    ),
    Provider(
        id="tunnel",
        name="Public HTTPS URL (Cloudflare Tunnel)",
        category="network",
        purpose="TradingView can only reach this app over HTTPS on port 443. A VPN alone does not provide this.",
        links=(
            Link("Cloudflare dashboard", "https://dash.cloudflare.com/"),
            Link(
                "Tunnel guide",
                "https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/",
            ),
        ),
        fields=(FieldSpec("public_url", "Public URL", "text", placeholder="https://paytience.example.com"),),
    ),
)

INDICATORS: tuple[dict[str, str], ...] = (
    {
        "id": "lunqfx",
        "name": LUNQFX_NAME,
        "author": "LunqFX",
        "role": "WHERE / WHAT — direction, stop anchor, T2 target",
        "link": _tv_search("ICT Fractal Model HTF Candles CISD C2 Targets LunqFX"),
        "setting": "Require C2 to close back inside C1 = ON",
    },
    {
        "id": "bigbeluga_mso",
        "name": BIGBELUGA_NAME,
        "author": "BigBeluga",
        "role": "WHEN / WHETHER — structure turn, trend side, divergence veto",
        "link": _tv_search("Market Structure Oscillator BigBeluga"),
        "setting": "Default settings",
    },
)


def get_provider(pid: str) -> Provider:
    for p in PROVIDERS:
        if p.id == pid:
            return p
    raise KeyError(pid)
