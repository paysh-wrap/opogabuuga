"""ORM tables (§19). Money/prices use DecimalType; times are aware UTC."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base, DecimalType, UTCDateTime


def _utcnow() -> datetime:
    return datetime.now(UTC)


class _Row:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow)


# ---------- auth ----------
class User(_Row, Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))  # Argon2 hash only
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuthSession(_Row, Base):
    __tablename__ = "auth_sessions"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    csrf_token: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)


# ---------- accounts / profiles ----------
class Account(_Row, Base):
    __tablename__ = "accounts"
    broker_account_id: Mapped[str] = mapped_column(String(64), unique=True)
    label: Mapped[str] = mapped_column(String(64), default="")
    stage: Mapped[str] = mapped_column(String(8))  # EVAL | FUNDED | LIVE
    drawdown_type: Mapped[str] = mapped_column(String(10))  # eod | intraday
    dll_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    consistency_pct: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    eval_mode: Mapped[str] = mapped_column(String(8), default="inherit")  # inherit | on | off
    armed: Mapped[bool] = mapped_column(Boolean, default=False)
    selected: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    mode_override: Mapped[str | None] = mapped_column(String(8), nullable=True)
    mll: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    mll_peak: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    mll_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    paused_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_trade_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    closed_by_firm: Mapped[bool] = mapped_column(Boolean, default=False)
    is_sim: Mapped[bool] = mapped_column(Boolean, default=True, server_default="1")
    starting_balance: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    stage_started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class AccountStageHistory(_Row, Base):
    __tablename__ = "account_stage_history"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    from_stage: Mapped[str | None] = mapped_column(String(8), nullable=True)
    to_stage: Mapped[str] = mapped_column(String(8))
    reason: Mapped[str] = mapped_column(Text, default="")


class RuleProfile(_Row, Base):
    __tablename__ = "rule_profiles"
    version: Mapped[int] = mapped_column(Integer, unique=True)
    body: Mapped[str] = mapped_column(Text)  # JSON object of firm-rule overrides (dotted key → value)
    verified_paths: Mapped[list[str]] = mapped_column(JSON, default=list)
    author: Mapped[str] = mapped_column(String(64))
    note: Mapped[str] = mapped_column(Text)

    def body_overrides(self) -> dict[str, Any]:
        import json

        data = json.loads(self.body or "{}")
        return data if isinstance(data, dict) else {}

    @staticmethod
    def encode_overrides(d: dict[str, Any]) -> str:
        import json

        return json.dumps(d, sort_keys=True)


class RiskProfile(_Row, Base):
    __tablename__ = "risk_profiles"
    __table_args__ = (UniqueConstraint("kind", "version"),)
    kind: Mapped[str] = mapped_column(String(12))  # standard | evaluation | lab (§17 approved tunables)
    version: Mapped[int] = mapped_column(Integer)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON)
    author: Mapped[str] = mapped_column(String(64))
    note: Mapped[str] = mapped_column(Text, default="")
    diff: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, default=False)


class StrategyConfig(_Row, Base):
    __tablename__ = "strategy_configs"
    version: Mapped[int] = mapped_column(Integer, unique=True)
    role: Mapped[str] = mapped_column(String(12))  # champion | challenger | retired
    params: Mapped[dict[str, Any]] = mapped_column(JSON)
    oos_metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


# ---------- signals / trading ----------
class Signal(_Row, Base):
    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint("model_key", name="uq_signals_model_key"),
    )  # one signal per fractal model (§6 one entry per model)
    status: Mapped[str] = mapped_column(String(8), default="WAIT", server_default="WAIT")  # WAIT|PASS|SKIP|EXPIRED
    updated_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    entry_bar_time: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    symbol: Mapped[str] = mapped_column(String(16))
    profile: Mapped[str] = mapped_column(String(8))
    direction: Mapped[str] = mapped_column(String(6))
    model_key: Mapped[str] = mapped_column(String(96), index=True)
    bar_time: Mapped[datetime] = mapped_column(UTCDateTime)
    score: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    c1_range_atr: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    skip_reason: Mapped[str | None] = mapped_column(String(48), nullable=True, index=True)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    strategy_version: Mapped[int | None] = mapped_column(Integer, nullable=True)


class SignalGate(_Row, Base):
    __tablename__ = "signal_gates"
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"))
    gate: Mapped[str] = mapped_column(String(4))
    passed: Mapped[bool] = mapped_column(Boolean)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class TradePlanRow(_Row, Base):
    __tablename__ = "trade_plans"
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"))
    mode: Mapped[str] = mapped_column(String(12), default="STANDARD", server_default="STANDARD")
    lock_price: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    direction: Mapped[str] = mapped_column(String(6))
    entry: Mapped[Decimal] = mapped_column(DecimalType)
    stop: Mapped[Decimal] = mapped_column(DecimalType)
    take_profit: Mapped[Decimal] = mapped_column(DecimalType)
    risk_pts: Mapped[Decimal] = mapped_column(DecimalType)
    rr: Mapped[Decimal] = mapped_column(DecimalType)
    partial_price: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    breakeven_price: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)


class Order(_Row, Base):
    __tablename__ = "orders"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"), nullable=True)
    broker_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    kind: Mapped[str] = mapped_column(String(16))  # entry | stop | tp
    side: Mapped[str] = mapped_column(String(4))
    qty: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    status: Mapped[str] = mapped_column(String(16))
    source: Mapped[str] = mapped_column(String(8), default="AUTO")  # AUTO | SEMI | MANUAL


class Fill(_Row, Base):
    __tablename__ = "fills"
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    qty: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(DecimalType)
    filled_at: Mapped[datetime] = mapped_column(UTCDateTime)


class Trade(_Row, Base):
    __tablename__ = "trades"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("signals.id"), nullable=True)
    symbol: Mapped[str] = mapped_column(String(16))
    direction: Mapped[str] = mapped_column(String(6))
    qty: Mapped[int] = mapped_column(Integer)
    entry: Mapped[Decimal] = mapped_column(DecimalType)
    exit: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    risk_usd: Mapped[Decimal] = mapped_column(DecimalType)
    pnl_usd: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    gross_r: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    net_r: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    guard_on: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_profile_kind: Mapped[str] = mapped_column(String(12), default="standard")
    resolution: Mapped[str | None] = mapped_column(String(16), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(UTCDateTime)
    closed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    mode: Mapped[str] = mapped_column(String(8), default="PAPER")  # PAPER | LIVE | BACKTEST
    trade_ref: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    profile: Mapped[str | None] = mapped_column(String(8), nullable=True)
    legs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    exit_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)


class DailyAccountStats(_Row, Base):
    __tablename__ = "daily_account_stats"
    __table_args__ = (UniqueConstraint("account_id", "session_date"),)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    session_date: Mapped[date] = mapped_column(Date)
    day_profit: Mapped[Decimal] = mapped_column(DecimalType, default=Decimal(0))
    day_net_r: Mapped[Decimal] = mapped_column(DecimalType, default=Decimal(0))
    consistency_ratio: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    trades: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    eod_balance: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)
    stopped_reason: Mapped[str | None] = mapped_column(String(48), nullable=True)
    consecutive_losses: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    win_streak: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    peak_pnl: Mapped[Decimal] = mapped_column(DecimalType, default=Decimal(0), server_default="0")


class Cooldown(_Row, Base):
    __tablename__ = "cooldowns"
    __table_args__ = (UniqueConstraint("symbol", "profile", name="uq_cooldowns_symbol_profile"),)
    symbol: Mapped[str] = mapped_column(String(16))
    profile: Mapped[str] = mapped_column(String(8))
    streak: Mapped[int] = mapped_column(Integer, default=0)
    until_session: Mapped[date | None] = mapped_column(Date, nullable=True)


class BiasDecision(_Row, Base):
    __tablename__ = "bias_decisions"
    session_date: Mapped[date] = mapped_column(Date)
    proxy: Mapped[str] = mapped_column(String(8))
    raw_rating: Mapped[str] = mapped_column(String(32))
    mapped: Mapped[str] = mapped_column(String(12))
    reasoning: Mapped[str] = mapped_column(Text, default="")
    version: Mapped[str] = mapped_column(String(32))
    cost_usd: Mapped[Decimal | None] = mapped_column(DecimalType, nullable=True)


class Attestation(_Row, Base):
    __tablename__ = "attestations"
    session_date: Mapped[date] = mapped_column(Date)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    text: Mapped[str] = mapped_column(Text)


class Payout(_Row, Base):
    __tablename__ = "payouts"
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    week: Mapped[str] = mapped_column(String(10))  # ISO week, e.g. 2026-W45
    kind: Mapped[str] = mapped_column(String(6))  # sweep | skim
    amount: Mapped[Decimal] = mapped_column(DecimalType)
    balance_before: Mapped[Decimal] = mapped_column(DecimalType)
    status: Mapped[str] = mapped_column(String(10), default="ready")  # ready|submitted|processed
    submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


# ---------- market data / backtest / lab ----------
class Bar(Base):
    __tablename__ = "bars"
    __table_args__ = (UniqueConstraint("symbol", "tf", "close_time"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16))
    tf: Mapped[str] = mapped_column(String(4))
    close_time: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    o: Mapped[Decimal] = mapped_column(DecimalType)
    h: Mapped[Decimal] = mapped_column(DecimalType)
    l: Mapped[Decimal] = mapped_column(DecimalType)  # noqa: E741
    c: Mapped[Decimal] = mapped_column(DecimalType)
    v: Mapped[Decimal] = mapped_column(DecimalType)
    source: Mapped[str] = mapped_column(String(16))


class Event(_Row, Base):
    __tablename__ = "events"
    __table_args__ = (Index("ix_events_symbol_profile_event", "symbol", "profile", "event"),)
    event_id: Mapped[str] = mapped_column(String(160), unique=True)  # webhook idempotency
    symbol: Mapped[str] = mapped_column(String(16))
    profile: Mapped[str] = mapped_column(String(8))
    event: Mapped[str] = mapped_column(String(20))
    direction: Mapped[str] = mapped_column(String(6), default="NONE", server_default="NONE")
    bar_time: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)


class BacktestRun(_Row, Base):
    __tablename__ = "backtest_runs"
    kind: Mapped[str] = mapped_column(String(12))  # NIGHTLY|ON_DEMAND|WHAT_IF|SHADOW|PARITY
    status: Mapped[str] = mapped_column(String(12), default="queued")
    cache_key: Mapped[str] = mapped_column(String(128), index=True)
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class BacktestTrade(_Row, Base):
    __tablename__ = "backtest_trades"
    run_id: Mapped[int] = mapped_column(ForeignKey("backtest_runs.id"))
    data: Mapped[dict[str, Any]] = mapped_column(JSON)


class OptimizerRun(_Row, Base):
    __tablename__ = "optimizer_runs"
    status: Mapped[str] = mapped_column(String(12))
    params: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Proposal(_Row, Base):
    __tablename__ = "proposals"
    challenger_version: Mapped[int] = mapped_column(Integer)
    diff: Mapped[dict[str, Any]] = mapped_column(JSON)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON)
    explanation: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(12), default="pending")


# ---------- connections (D3) ----------
class ApiCredential(_Row, Base):
    """Encrypted, write-only provider credentials. Plaintext never leaves the backend."""

    __tablename__ = "api_credentials"
    provider: Mapped[str] = mapped_column(String(32), unique=True)
    ciphertext: Mapped[str] = mapped_column(Text)  # Fernet token of JSON {field: value}
    hints: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)  # field -> "••••1234"
    status: Mapped[str] = mapped_column(String(12), default="saved")  # saved|connected|failed
    status_detail: Mapped[str] = mapped_column(Text, default="")
    tested_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow)


class IndicatorSource(Base):
    """Pine source + license pasted by the user (§1.6). Never fetched from TradingView."""

    __tablename__ = "indicator_sources"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    source: Mapped[str] = mapped_column(Text)
    license: Mapped[str] = mapped_column(String(64))
    personal_use_only: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow)


class AppSetting(Base):
    """Small key → JSON store for runtime state (automation mode, approvals config...)."""

    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[Any] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=_utcnow)


# ---------- audit / notifications ----------
class AuditLog(Base):
    """Append-only (DB triggers block UPDATE/DELETE) + SHA-256 hash chain."""

    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(UTCDateTime)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64), index=True)
    entity: Mapped[str] = mapped_column(String(64), default="")
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)


class Notification(_Row, Base):
    __tablename__ = "notifications"
    level: Mapped[str] = mapped_column(String(8))  # info | warn | error
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(Text, default="")
    channels: Mapped[list[str]] = mapped_column(JSON, default=list)
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)
    kind: Mapped[str] = mapped_column(String(32), default="general", server_default="general")
    read_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True, index=True)
