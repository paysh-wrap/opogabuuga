"""TradingView webhook payload (§5.4). Prices are Decimal; times are epoch ms of the bar CLOSE."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

EventName = Literal[
    "HEARTBEAT",
    "C1_SWEPT",
    "CISD",
    "MODEL_CONFIRMED",
    "T1_HIT",
    "T2_HIT",
    "MODEL_FAILED",
    "C3_CLOSED",
    "MSO_CHOCH",
    "MSO_BOS",
    "MSO_DIV",
]
FRACTAL_EVENTS = {"C1_SWEPT", "CISD", "MODEL_CONFIRMED", "T1_HIT", "T2_HIT", "MODEL_FAILED", "C3_CLOSED"}
MSO_EVENTS = {"MSO_CHOCH", "MSO_BOS", "MSO_DIV"}


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Ohlcv(_M):
    o: Decimal
    h: Decimal
    l: Decimal  # noqa: E741
    c: Decimal
    v: Decimal = Decimal(0)


class FractalFields(_M):
    c1_high: Decimal
    c1_low: Decimal
    c1_time_ms: int
    htf_atr14: Decimal | None = None
    t1: Decimal
    t2: Decimal
    invalid: Decimal
    sweep_extreme: Decimal
    sweep_time_ms: int
    cisd_level: Decimal | None = None
    cisd_before_c2_close: bool = False
    t1_preticked: bool = False
    c3_close_time_ms: int | None = None


class MsoFields(_M):
    trend: Literal["BULL", "BEAR", "NONE"]
    osc: Decimal | None = Field(default=None, ge=0, le=100)
    div: Literal["BULL", "BEAR"] | None = None
    htf_trend: Literal["BULL", "BEAR", "NONE"] | None = None
    confirm_time_ms: int


class WebhookPayload(_M):
    v: Literal[1]
    secret: SecretStr
    id: str = Field(min_length=1, max_length=160)
    symbol: str = Field(min_length=1, max_length=32)
    profile: Literal["TIGHT", "STD"]
    tf: str = Field(min_length=1, max_length=8)
    bar_time_ms: int = Field(gt=1_500_000_000_000, lt=4_000_000_000_000)
    event: EventName
    direction: Literal["LONG", "SHORT", "NONE"]
    price: Ohlcv | None = None
    fractal: FractalFields | None = None
    mso: MsoFields | None = None
