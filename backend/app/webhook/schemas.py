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
    "ORDER_FLOW",
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


class OrderFlowFields(_M):
    """D95: one order-flow signal from pine/Paytience_OrderFlow.pine. stop/target are informational — the engine
    rebuilds them (engine/order_flow.py)."""

    kind: Literal["ABSORPTION", "DELTA_DIVERGENCE", "STACKED_IMBALANCE", "SWEEP", "POC_MAGNET"]
    entry: Decimal = Field(gt=0)
    defended: Decimal = Field(gt=0)
    stop: Decimal | None = None
    target: Decimal | None = None
    delta: Decimal | None = None
    cum_delta: Decimal | None = None
    poc: Decimal | None = None
    # D101 AR Model layers (optional: older indicator versions omit them → the engine skips OF_NO_CONFIRM)
    env: Literal["EXPANSION", "ROTATION", "COMPRESSION"] | None = None
    location_zone: str | None = Field(default=None, max_length=24)  # label only (F0705 … / BEYOND_0886)
    fib: Decimal | None = Field(default=None, ge=0, le=5)
    value_side: Literal["BELOW_VAL", "IN_VALUE", "ABOVE_VAH"] | None = None
    path_zone: Literal["INSIDE", "L1", "AVR-", "AVR", "AVR+", "MAX"] | None = None
    path_side: Literal["ABOVE", "BELOW", "INSIDE"] | None = None
    delta_source: Literal["real", "est"] | None = None
    confirm_time: int | None = Field(default=None, gt=1_500_000_000_000, lt=4_000_000_000_000)
    absorption_low: Decimal | None = Field(default=None, gt=0)
    absorption_high: Decimal | None = Field(default=None, gt=0)
    stacked: int | None = Field(default=None, ge=0, le=100)
    # D108 Casper refinements (optional; an active rule without its field skips OF_CASPER_<RULE>)
    close_pos: Decimal | None = Field(default=None, ge=0, le=1)
    cvd_slope: Decimal | None = None
    open_vs_value: Literal["BELOW_VAL", "IN_VALUE", "ABOVE_VAH"] | None = None
    prior_va_width_atr: Decimal | None = Field(default=None, ge=0, le=100)
    # D110 AMT+ (optional; with the AMT+ button on, a missing context / level skips OF_AMT_NO_CONTEXT / OF_AMT_NO_LEVEL)
    prev_rth_vah: Decimal | None = Field(default=None, gt=0)
    prev_rth_val: Decimal | None = Field(default=None, gt=0)
    prev_rth_poc: Decimal | None = Field(default=None, gt=0)
    eth_vwap: Decimal | None = Field(default=None, gt=0)
    context: Literal["ACCEPT_ABOVE", "ACCEPT_BELOW", "BALANCE"] | None = None
    ctx_session: Literal["ASIA", "LONDON", "RTH"] | None = None
    key_level_type: (
        Literal["ETH_VWAP", "PRIOR_VAH", "PRIOR_VAL", "PRIOR_POC", "LVN", "DELTA_OUTLIER", "PRIOR_HIGH", "PRIOR_LOW"]
        | None
    ) = None
    target_level: Decimal | None = Field(default=None, gt=0)


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
    order_flow: OrderFlowFields | None = None
