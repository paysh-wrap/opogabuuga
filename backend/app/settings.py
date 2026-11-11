"""Process settings from environment (.env). Rule numbers never live here (see config.py)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PAYTIENCE_", env_file=(REPO_ROOT / ".env", ".env"), extra="ignore")

    env: str = "dev"
    allow_live: bool = False  # §1.5 — LIVE also needs UI toggle + typed phrase + checklist
    database_url: str = f"sqlite:///{REPO_ROOT / 'data' / 'paytience.db'}"
    redis_url: str = "redis://localhost:6379/0"
    rules_path: Path = REPO_ROOT / "config" / "rules" / "lucid_flex_25k.yaml"  # default plan; switch on Risk page
    master_key: SecretStr = Field(default=SecretStr(""), description="Fernet key for stored API keys")
    webhook_secret: SecretStr = SecretStr("")
    bind_host: str = "127.0.0.1"
    cookie_secure: bool = False  # True behind HTTPS
    session_hours: int = 12
    admin_user: str = ""
    admin_password: SecretStr = SecretStr("")  # only used once by `make create-admin`; never stored
    http_timeout_s: float = 10.0
    scheduler_enabled: bool = True  # in-process jobs (payouts, calendar); tests turn it off
    watchdog_interval_s: float = 5.0  # wall-clock flat-time / news / MLL watchdog (needs scheduler_enabled)
    ta_python: str = str(  # isolated TradingAgents venv (Windows keeps Python in Scripts\python.exe)
        REPO_ROOT / ".venv-ta" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    vt_root: Path = (
        REPO_ROOT  # D53: Vibe-Trading CLI lives in <vt_root>/.venv-vt (isolated); runtime in data/vibe-trading
    )
    tr1_root: Path = REPO_ROOT  # D94: Trading-R1 in <tr1_root>/.venv-tr1, TR1_HOME <tr1_root>/data/tr1
    web_dist: Path = REPO_ROOT / "frontend" / "dist"
    tools_dir: Path = REPO_ROOT / "data" / "tools"  # D79: ngrok / cloudflared binaries (own folder)
    tunnel_autostart: bool = False  # desktop app sets true: run ngrok (or the Cloudflare fallback) at start


@lru_cache
def get_settings() -> Settings:
    return Settings()
