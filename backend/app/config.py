"""Rule profile loader (§1.7, §23).

- Every YAML float is parsed as Decimal (exact). Money/prices never touch binary floats.
- Lines marked `# VERIFY` are reported as dotted key paths so the UI can show gold badges.
- Typed Pydantic models make the config the single, validated source of rule numbers.
"""

from __future__ import annotations

import re
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------- YAML → Decimal loader ----------


class _DecimalLoader(yaml.SafeLoader):
    pass


def _decimal_float(loader: yaml.SafeLoader, node: yaml.ScalarNode) -> Decimal:
    return Decimal(str(loader.construct_scalar(node)).replace("_", ""))


_DecimalLoader.add_constructor("tag:yaml.org,2002:float", _decimal_float)


def load_yaml_decimal(text: str) -> dict[str, Any]:
    data = yaml.load(text, Loader=_DecimalLoader)  # noqa: S506 - SafeLoader subclass
    if not isinstance(data, dict):
        raise ValueError("rules YAML must be a mapping")
    return data


PRESETS_PATH = Path(__file__).resolve().parents[2] / "config" / "strategy_presets.yaml"


@lru_cache(maxsize=1)
def load_presets() -> dict[str, dict[str, Any]]:
    """D82: the NOISE strategy presets (config/strategy_presets.yaml), keyed by preset id."""
    data = load_yaml_decimal(PRESETS_PATH.read_text(encoding="utf-8"))
    presets = data.get("presets")
    if not isinstance(presets, dict) or not presets:
        raise ValueError("strategy_presets.yaml needs a non-empty `presets` mapping")
    return presets


_KEY_RE = re.compile(r"^(\s*)([A-Za-z0-9_]+)\s*:(.*)$")


def find_verify_paths(text: str) -> list[str]:
    """Dotted paths of keys whose line carries a `# VERIFY` marker (applies to all children)."""
    stack: list[tuple[int, str]] = []
    out: list[str] = []
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        m = _KEY_RE.match(raw)
        if not m:
            continue
        indent, key = len(m.group(1)), m.group(2)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        stack.append((indent, key))
        if "# VERIFY" in raw:
            out.append(".".join(k for _, k in stack))
    return out


# ---------- typed models ----------

D = Decimal
DrawdownType = Literal["eod", "intraday"]


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Purchase(_M):
    drawdown_type: DrawdownType
    dll_enabled: bool
    consistency_pct: D | None


class MaxContracts(_M):
    minis: int
    micros: int


class EvalRules(_M):
    profit_target: D
    consistency_max_day_pct: D | None  # None = no eval consistency rule (LucidPro)
    min_profitable_days: int
    max_loss_limit: D
    drawdown_type: DrawdownType
    daily_loss_limit: D | None  # None = no DLL
    lock_trigger: D
    lock_level: D
    news_allowed_by_firm: bool
    news_breach_min_before: int
    news_breach_min_after: int


class PayoutRules(_M):
    split: D
    buffer: D
    min_request: D
    min_cycle_profit: D
    max_first: D | None = None  # cap on payout #1
    max_next: D | None = None  # cap on payouts #2+
    max_pct_of_profit: D | None = None  # LucidFlex: 50% of cycle profit
    min_profitable_days: int = 0  # LucidFlex: 5 days ≥ min_day_profit per cycle
    min_day_profit: D = D(0)
    max_payouts: int | None = None
    lock_mll_on_payout: bool = False  # LucidFlex: MLL moves to the locked level once a payout is requested


class ScaleTier(_M):
    profit_from: D
    micros: int


class FundedRules(_M):
    max_loss_limit: D
    drawdown_type: DrawdownType
    lock_trigger: D
    lock_level: D
    daily_loss_limit: D | None
    consistency_max_day_pct: D | None
    news_breach_min_before: int
    news_breach_min_after: int
    max_daily_profit_live_trigger: D | None
    news_allowed_by_firm: bool = False
    scaling: list[ScaleTier] | None = None  # LucidFlex funded: max micros by cycle profit
    payouts_to_live: int | None = None
    payouts_live_review: int | None = None
    payout: PayoutRules


class LiveRules(_M):
    starting_balance: D
    max_loss_limit: D
    drawdown_type: DrawdownType
    lock_trigger: D
    lock_level: D
    sim_payout_cap_on_move: D


class SessionRules(_M):
    flat_by: str
    reopen: str


class Behavior(_M):
    min_hold_seconds: D = Field(ge=D("6.5"), le=D(60))  # user: 7.5 s
    firm_microscalp_hold_seconds: int
    rapid_trade_warn_pct: D
    firm_microscalp_pct: D
    no_hedging: bool
    hedge_lock_scope: str
    max_funded_per_household: int
    max_total_accounts: int
    max_open_positions_per_account: int
    inactivity_alert_days: int
    firm_inactivity_delete_days: int


class ContractCfg(_M):
    """Real futures contract for orders (app/contracts.py). override pins one, e.g. "MGCG7" (exchange holidays)."""

    months: str
    roll: Literal["fnd", "expiry"]
    roll_days: int = Field(ge=0, le=20)
    override: str | None = None


class Instrument(_M):
    tick: D
    tick_value: D
    fee_rt: D
    enabled: bool
    group: str
    super_group: str
    bias_proxy: str
    exchange: Literal["CME", "CBOT", "COMEX", "NYMEX"]
    tv_symbol: str
    contract: ContractCfg | None = None  # orders go to the real contract (MGCZ6), not the continuous MGC1!
    stop_buffer_ticks: int | None = None
    min_stop_ticks: int | None = None
    slippage_ticks: int | None = None
    windows: list[tuple[str, str]] | None = None  # per-market entry windows (ET); falls back to internal.windows
    intraday_windows: list[tuple[str, str]] | None = None  # D37 H1: normal Intraday mode only (not low risk/1:1/scalp)
    news_after_min: int | None = None  # no entries until N min after a high-impact release (falls back to firm rule)
    trend_filters: bool = True  # D52: False → this market ignores filters.trend (MNQ takes every setup)


class TradePlanCfg(_M):
    rr_min: D
    rr_max: D
    stop_buffer_ticks: int
    min_stop_ticks: int
    slippage_ticks: int
    one_entry_per_model: bool


class Cooldown(_M):
    streak: int
    sessions: int
    in_scalp: bool = True  # D38 (user): false = the model-fail cooldown does not pause Scalp mode


class TrendFilter(_M):
    """D44: trade only on the side of these trend indicators (all OFF by default; switch on after research)."""

    vwap: bool = False  # session VWAP (resets 18:00 ET)
    ema200_5m: bool = False  # EMA 200 on 5-minute bars
    utbot_5m: bool = False  # UT Bot (key 1, ATR 10) on 5-minute bars
    squeeze_5m_15m: bool = False  # D45: Squeeze Momentum [LazyBear] rising in the trade direction on 5m AND 15m


class Filters(_M):
    c1_min_range_atr: D
    htf_atr_period: int
    model_fail_cooldown: Cooldown
    # D35: G4 (MSO trend/osc agrees) and G5 (CHoCH/BoS after the sweep) as hard gates (true) or score-only (false).
    # Both still earn/lose score points either way.
    require_mso_agree: bool = True
    require_structure_break: bool = True
    # D35: in limit_cisd entry mode, T1 already touched is not a skip (the limit only fills on a full retrace to CISD)
    t1_through_ok_with_limit: bool = False
    # D36 blend: a setup WITHOUT a CHoCH/BoS after the sweep may trade, but its target is capped at this R
    # (closer target → higher hit rate). None = no cap. Setups with a structure break keep the normal R:R window.
    no_break_rr_cap: D | None = None
    trend: TrendFilter = TrendFilter()


class NoiseCfg(_M):
    """D55 (user-approved 2026-11-09): noise-area intraday momentum (Zarattini, Aziz & Barbon 2024) on MNQ RTH.
    Verified on Databento 2019–2026 (docs/results/2026-11-09_session9_strategy_research.md): hourly checks + 1%
    emergency stop → held-out 2024–2026 440 trades, 45.0% win, PF 1.33. Changing these values is NOT verified."""

    symbol: str = "MNQ"
    lookback_days: int = 14  # σ_t = mean |close_t / open − 1| at minute t over the previous N RTH sessions
    min_history_days: int = 10  # fewer stored sessions (warm-up from TradingView heartbeats) → no signal
    min_bars_per_day: int = 300  # an RTH session with fewer 1-minute bars is left out of σ (gaps in the feed)
    check_minutes: int = 60  # decisions on the bar closing at 10:00, 11:00, … (first_check + k·check_minutes)
    first_check: str = "10:00"
    last_check: str = "15:30"  # last time a NEW entry may be decided (hourly → 15:00 is the last check)
    flat_at: str = "16:00"  # every NOISE position is closed on the 16:00 bar
    emergency_stop_pct: D = D("0.01")  # broker-side safety stop, 1% of price (0.3–0.5% cut winners — research)
    take_profit_pct: D = D("0.10")  # broker-side far target (safety only; the trailing rule exits)
    # D58 (user 2026-11-09): fixed-dollar emergency stop per contract (replaces emergency_stop_pct when set). 5-year
    # study (docs/results/session10 §10–12): $250 ties 1% on PF (1.36 vs 1.35), no losing year, worst trade −$250.
    emergency_stop_usd: D | None = D("250")
    max_entries_per_day: int = 3
    contracts: int = 1  # fixed size (user: Pro 25K at 1 micro); still subject to every pre-trade risk check
    roll_gap_pct: D = D("0.015")  # |RTH open / prior RTH close − 1| above this → contract roll or shock: no trades
    # D82 (preset C, D75-P1): once a trade is trigger pts in profit the stop moves to entry + lock pts (ratchet); a
    # locked-stop exit ends NOISE for the day. None = no lock. Both set together (management/profit_lock.py).
    profit_lock_trigger_pts: D | None = None
    profit_lock_pts: D | None = None

    @model_validator(mode="after")
    def _lock_valid(self) -> NoiseCfg:
        if (self.profit_lock_trigger_pts is None) != (self.profit_lock_pts is None):
            raise ValueError("noise profit lock: profit_lock_trigger_pts and profit_lock_pts go together")
        locked = self.profit_lock_trigger_pts is not None and self.profit_lock_pts is not None
        if locked and not (D(0) <= (self.profit_lock_pts or D(0)) < (self.profit_lock_trigger_pts or D(0))):
            raise ValueError("noise profit lock: 0 ≤ profit_lock_pts < profit_lock_trigger_pts")
        return self


class OpenDriveCfg(_M):
    """D55 (user button, 2026-11-09): opening-drive pullback on MNQ — NOT verified (flat in-sample, PF 1.29 held-out)
    → PAPER accounts only. R:R ≈ 0.95 (below the 1.5 pillar) by the user's explicit choice."""

    symbol: str = "MNQ"
    drive_min_range_frac: D = D("0.35")  # |close(09:59 bar) − RTH open| ≥ this × 14-day average RTH range
    range_days: int = 14
    min_range_days: int = 10
    entry_retrace: D = D("0.382")  # limit at the 38.2% retrace of open → drive extreme
    stop_retrace: D = D("0.786")
    target_frac: D = D("1.0")  # 1.0 = back to the drive extreme
    signal_time: str = "10:00"
    entry_expires: str = "12:30"
    time_stop: str = "13:00"
    contracts: int = 1
    paper_only: bool = True


class AiBiasCfg(_M):
    """D56 (user button, 2026-11-09): trade ONLY the daily TradingAgents + Vibe-Trading call on MNQ — NOT verified.
    The LLM tools cannot be back-tested (spec §15); the hindsight ceiling is in docs/results/session10. Enters at the
    09:30 bar close only when BOTH tools agree strongly on a side; holds to 16:00 with a broker stop. Paper only."""

    symbol: str = "MNQ"
    entry_time: str = "09:31"  # decided on the close of the first RTH minute bar (≈ the 09:30 open)
    stop_pct: D = D("0.005")  # 0.5% of price (≈ $276 per micro): 1% was break-even even with perfect calls
    take_profit_pct: D = D("0.10")  # far safety target; the 16:00 flat exits
    flat_at: str = "16:00"
    contracts: int = 1
    paper_only: bool = True


class PmFadeCfg(_M):
    """D58 (user 2026-11-09): afternoon VWAP-band fade on MNQ, ONLY when NOISE has not traded today; paper first.
    Rules (docs/results/session10/five_year/stops_250.py, 5y with NOISE: pass 66% / bust 32%): on each 1-minute close
    from 13:01 to 15:29 ET, sd = population std of (close − VWAP) over today's RTH bars so far; close > VWAP + band·sd →
    SHORT, close < VWAP − band·sd → LONG, at market; target = VWAP at the signal; fixed $ stop; flat 15:55; 1 per day;
    skip when the target is < min_target_ticks away. Research fills at the next bar open (≈ the signal close)."""

    symbol: str = "MNQ"
    first_signal: str = "13:01"  # close time of the first bar that may signal (bar opening 13:00)
    last_signal: str = "15:29"
    band_sd: D = D("2.0")
    stop_usd: D = D("250")
    min_target_ticks: int = 4
    flat_at: str = "15:55"
    contracts: int = 1
    paper_only: bool = True


class SizeTierCfg(_M):
    """D63: one row of the automatic size table (account size → micros, drawdown brake)."""

    account_size: D
    mll: D
    contracts: int
    brake_below: D | None = None
    brake_contracts: int | None = None
    grow_per: D | None = None  # D66 (eval tables): +1 micro per grow_per $ of cushion beyond the first
    max_contracts: int | None = None
    day_lock_pct: D | None = None  # D66 (eval tables): stop for the day once today's profit ≥ x × remaining target
    stop_usd: D | None = None  # D70 (eval tables): emergency stop per micro for this row (default: the strategy's stop)
    taper_below_remaining: D | None = None  # D69 (eval tables): fraction of the target still to earn
    taper_contracts: int | None = None  # D69: micros once less than that fraction of the target remains

    @model_validator(mode="after")
    def _valid(self) -> SizeTierCfg:
        if self.stop_usd is not None and self.stop_usd <= 0:
            raise ValueError("size_table: stop_usd > 0")
        if self.grow_per is not None and (
            self.grow_per <= 0 or not self.max_contracts or self.max_contracts < self.contracts
        ):
            raise ValueError("size_table: grow_per > 0 needs max_contracts ≥ contracts")
        if self.day_lock_pct is not None and not (D(0) < self.day_lock_pct <= D(1)):
            raise ValueError("size_table: 0 < day_lock_pct ≤ 1")
        if (self.taper_below_remaining is None) != (self.taper_contracts is None):
            raise ValueError("size_table: taper_below_remaining and taper_contracts go together")
        bad_taper = (
            self.taper_below_remaining is not None
            and self.taper_contracts is not None
            and (not (D(0) < self.taper_below_remaining < D(1)) or not (1 <= self.taper_contracts < self.contracts))
        )
        if bad_taper:
            raise ValueError("size_table: 0 < taper_below_remaining < 1 and 1 ≤ taper_contracts < contracts")
        if self.account_size <= 0 or self.mll <= 0 or self.contracts < 1:
            raise ValueError("size_table: account_size, mll > 0 and contracts ≥ 1")
        if (self.brake_below is None) != (self.brake_contracts is None):
            raise ValueError("size_table: brake_below and brake_contracts go together")
        bad_brake = (
            self.brake_below is not None
            and self.brake_contracts is not None
            and (not (D(0) < self.brake_below < D(1)) or not (1 <= self.brake_contracts < self.contracts))
        )
        if bad_brake:
            raise ValueError("size_table: 0 < brake_below < 1 and 1 ≤ brake_contracts < contracts")
        return self


class StructureFilterCfg(_M):
    """D76: order-block (OB) + SMT (MNQ vs MES) FILTER for NOISE / PM_FADE. Default OFF: nothing blocks;
    with shadow_log the verdict (what it WOULD have blocked, and the OB anchor stop) is stored on the signal.
    A filter can only block.
    Study (docs/results/session12): no variant improved both win rate and profit held-out -> keep enabled=false."""

    enabled: bool = False  # true = a blocked entry becomes a SKIP (OB_BLOCK / SMT_BLOCK)
    shadow_log: bool = True
    ob_filter: bool = True
    ob_tf_min: int = 1
    ob_body_atr: D = D("1.5")
    ob_swing_bars: int = 10
    ob_dist_pts: D = D("25")
    smt_filter: bool = False  # needs MES 1-minute bars in the feed; skipped when absent
    smt_lookback: int = 20
    smt_valid_bars: int = 15
    # D77: Big Beluga MSO divergence gate (G6 style): block an entry when an OPPOSING MSO divergence printed in the last
    # mso_div_minutes. Measured (docs/results/session13): noise-level (5 trades blocked) -> OFF.
    mso_div_filter: bool = False
    mso_tf_min: int = 5
    mso_div_minutes: int = 30
    anchor_buffer_pts: D = D("2")  # shadow only: where an OB-anchored stop would sit (never applied live)


class LunqStructureCfg(_M):
    """D76 LunqFX: optional OB + SMT (MNQ vs MES) filter on a LunqFX PASS. Default OFF (shadow-logged only).
    Not a pillar change: G1-G8 run unchanged; this can only turn a PASS into a SKIP (OB_BLOCK / SMT_BLOCK).
    anchor_stop: move the stop to just beyond a same-side order block ONLY when tighter (never widens risk) and the
    rebuilt R:R stays inside trade_plan rr_min..rr_max; else the original plan is kept.
    Study docs/results/session12/LUNQFX.md decides whether to switch on."""

    enabled: bool = False
    anchor_stop: bool = False
    shadow_log: bool = True
    filter: StructureFilterCfg = StructureFilterCfg()


class StrategyCfg(_M):
    """D55: which strategies may trade (buttons on the Strategy page). Disabled strategies still run in SHADOW where
    they have a shadow path (LunqFX). Defaults keep legacy plan files on the original LunqFX engine."""

    lunqfx: bool = True
    # D82: Strategy preset (config/strategy_presets.yaml) — overlays noise_cfg stop/profit lock, noise, pm_fade and the
    # size tables before validation. None = "custom" (the plan file's own values).
    preset: str | None = None
    noise: bool = False
    open_drive: bool = False
    ai_bias: bool = False
    pm_fade: bool = False
    # D57: NOISE / AI_BIAS scale their emergency stop down as the account draws down instead of pausing at the pause
    # floor: worst case ≤ this fraction of the room (DLL left / distance to MLL − kill distance); None = old pause.
    drawdown_shrink: D | None = D("0.6")
    drawdown_min_stop_pct: D = D("0.002")  # a stop tighter than 0.2% of price is noise → skip DRAWDOWN_TOO_DEEP
    noise_cfg: NoiseCfg = NoiseCfg()
    open_drive_cfg: OpenDriveCfg = OpenDriveCfg()
    ai_bias_cfg: AiBiasCfg = AiBiasCfg()
    pm_fade_cfg: PmFadeCfg = PmFadeCfg()
    structure_filters: StructureFilterCfg = StructureFilterCfg()
    lunqfx_structure: LunqStructureCfg = LunqStructureCfg()
    # D63: automatic size for NOISE / PM_FADE by each account's own size (empty = noise_cfg / pm_fade_cfg.contracts)
    size_table: list[SizeTierCfg] = []
    # D74 (user 2026-11-10): AI-bias SIZING (study docs/results/session11/ai_bias_sizing_study.md, version B): when the
    # daily AI call agrees with the trade side +1 micro (never above the tier's base size + 1), disagrees −1 (min 1).
    # Only accounts of size ≥ ai_sizing_min_account (100K/150K) and only once the live ledger is proven:
    # ≥ min_calls scored calls with observed hit rate ≥ ai_sizing_min_accuracy. Never blocks.
    # DLL / D57 / worst-case checks still apply.
    ai_sizing: bool = True
    # D77: accuracy the AI record must PROVE (Wilson lower bound) before the AI call may BLOCK a NOISE entry.
    # Shipped default
    # 0.70 (D55); the user may choose 0.60/0.65 after reading docs/results/session13/README.md. Allowed 0.55-0.95.
    ai_gate_min_accuracy: D = Field(default=D("0.70"), ge=D("0.55"), le=D("0.95"))
    ai_sizing_min_account: D = D("100000")
    ai_sizing_min_accuracy: D = D("0.60")
    ai_sizing_min_calls: int = 60
    # D64: Strategy-page button "High risk" switches NOISE / PM_FADE sizing to size_table_high (same brake system)
    high_risk: bool = False
    size_table_high: list[SizeTierCfg] = []

    # D66: Evaluation Mode (EVAL stage only, non-negotiable 10) sizes NOISE / PM_FADE from this table when present
    size_table_eval: list[SizeTierCfg] = []
    size_table_eval_high: list[SizeTierCfg] = []  # D69: Evaluation Mode when the High-risk button is on

    @model_validator(mode="before")
    @classmethod
    def _apply_preset(cls, data: Any) -> Any:
        if not isinstance(data, dict) or not data.get("preset"):
            return data
        presets = load_presets()
        key = str(data["preset"])
        if key not in presets:
            raise ValueError(f"unknown strategy preset {key!r} (known: {', '.join(sorted(presets))})")
        out = dict(data)
        for k, v in presets[key]["overlay"].items():
            out[k] = {**(out.get(k) or {}), **v} if isinstance(v, dict) else v
        return out

    def active_eval_table(self) -> list[SizeTierCfg]:
        return self.size_table_eval_high if self.high_risk and self.size_table_eval_high else self.size_table_eval

    def active_size_table(self) -> list[SizeTierCfg]:
        return self.size_table_high if self.high_risk and self.size_table_high else self.size_table


class ScoreCfg(_M):
    weights: dict[str, D]
    min_score: D
    neutral_min_score: D
    exclude_unknown: bool = False  # D35: unknown items (neutral bias, unproven T2 rate) leave the maximum
    osc_strength_min: D
    tp_rate_min: D
    tp_rate_min_samples: int
    div_lookback_bars: int
    session_open_c1_weight: D
    session_open_times: list[str]
    smt_weight: D


class EntryCfg(_M):
    mode: Literal["market", "limit_cisd"]
    limit_timeout_bars: int
    max_wait_bars: int


class ProfileTF(_M):
    ltf: str
    htf: str


class Profiles(_M):
    TIGHT: ProfileTF
    STD: ProfileTF
    std_min_risk_base: D
    # D35: which profiles may trade. ["STD"] = intraday 5m→1H only (user: intraday over scalping).
    enabled: list[Literal["TIGHT", "STD"]] = Field(default_factory=lambda: ["TIGHT", "STD"], min_length=1)  # type: ignore[arg-type]


class GuardCfg(_M):
    mode: Literal["auto", "on", "off"]
    partial_fraction_of_tp: D
    partial_qty: Literal["ceil_half"]
    runner_trail_r: D
    min_contracts_on: int
    min_contracts_off: int
    early_exits_until_r: D


class InternalCfg(_M):
    risk_pct_by_score: dict[int, D]
    risk_pct_floor: D
    risk_pct_middle: D
    risk_pct_ceiling: D
    risk_pct_absolute_bounds: tuple[D, D]
    max_risk_usd: D | None
    warmup_trades: int
    day_lockin_r: D
    dd_floor_pct: D
    streak_floor_losses: int
    streak_release_wins: int
    pause_below_risk_base: D
    dll_safety_margin: D
    max_trades_per_day: int
    low_risk_max_trades_per_day: int = 7  # D36: Lower-risk mode doubles max trades, capped here
    max_consecutive_losses_per_day: int
    internal_max_micros: int
    kill_switch_mll_distance: D
    adverse_half_enabled: bool = True  # user rule: half off near the stop when every confirmation is against
    adverse_half_at: D = Field(default=D("0.90"), ge=D("0.85"), le=D("0.95"))
    cushion_target_balance: D
    cap_guard_total_above_buffer: D
    consistency_day_stop_buffer_pct: D
    consistency_on_funded: bool
    funded_consistency_pct: D
    funded_consistency_reference_min: D
    auto_flatten: str
    hard_flat: str
    windows: list[tuple[str, str]]
    no_entry_before_news_min: int
    news_flatten_before_min: int


class GateCfg(_M):
    min_trades: int
    min_e_net_r: D
    min_pf: D
    max_violations: int


class OneToOneFilters(_M):
    target_within_t1: bool
    t1_rate_min: D
    t1_rate_min_samples: int
    min_score: D
    require_choch: bool
    require_bias_and_htf: bool
    atr_pct_band: tuple[D, D]
    atr_pct_min_samples: int
    news_after_min: int


class ScalpMode(_M):
    """User button: quick trades on the same confluence + 1:1 win-rate filters, smaller target, time limit."""

    enabled: bool = False
    target_r: D = Field(default=D("0.5"), ge=D("0.3"), le=D("1.0"))
    max_hold_s: int = Field(default=60, ge=25, le=300)
    runner_r: D = Field(default=D("2.0"), ge=D("1.0"), le=D("3.0"))  # where the second half aims (never past 3R)
    trail_r: D = Field(default=D("0.5"), ge=D("0.25"), le=D("1.0"))  # runner trails this far behind the best price


class OneToOneMode(_M):
    enabled: bool
    rr: D
    partial_at_fraction_of_tp: D
    partial_qty_fraction: D
    max_consecutive_losses_per_day: int
    max_trades_per_day: int
    extended_max_trades_per_day: int
    extend_after_win_streak: int
    breakeven_after_partial: bool
    single_contract_lock_r: D
    single_contract_lock_bounds: tuple[D, D]
    stages: list[Literal["EVAL", "FUNDED", "LIVE"]]
    gate: GateCfg
    filters: OneToOneFilters


class TargetSessions(_M):
    target: int
    max: int


class EvalModeCfg(_M):
    default_on: bool
    applies_to_stages: list[Literal["EVAL"]]
    confirm_phrase: str
    risk_pct_by_score: dict[int, D]
    risk_pct_floor: D
    risk_pct_middle: D
    risk_pct_ceiling: D
    max_risk_usd: D
    warmup_trades: int
    target_sessions: TargetSessions
    auto_off_on_stage_change: bool
    pace_escalation: Literal[False]  # never raise risk to catch up (§11C)
    one_to_one: bool = False  # D23: 1:1 plans on EVAL accounts while Evaluation Mode is on


class BiasCfg(_M):
    provider: str
    pinned_version: str
    pinned_commit: str
    repo_url: str
    proxy: dict[str, str]
    timeout_min: int
    rating_map: dict[str, Literal["LONG_ONLY", "SHORT_ONLY", "NEUTRAL"]]
    unknown: Literal["NO_TRADE"]
    backtest_source: Literal["recorded_only"]


class SmtCfg(_M):
    enabled: bool
    pair: list[str]


class MsoCfg(_M):
    pivot_left: int = Field(ge=1, le=50)
    pivot_right: int = Field(ge=1, le=50)
    mom_length: int = Field(ge=1, le=200)
    smooth_length: int = Field(ge=1, le=200)
    div_pivot_left: int = Field(ge=1, le=50)
    div_pivot_right: int = Field(ge=1, le=50)


class IndicatorsCfg(_M):
    require_c2_close_inside_c1: Literal[True]  # pillar
    mso: MsoCfg


class WebhookCfg(_M):
    heartbeat_max_age_s: int = Field(ge=1, le=300)
    event_max_age_s: int = Field(ge=1, le=600)
    max_future_skew_s: int = Field(ge=0, le=60)
    rate_limit_per_min: int = Field(ge=10)
    max_body_bytes: int = Field(ge=1024, le=1_048_576)
    stale_after_bar_multiple: int = Field(ge=1, le=10)


class ReliabilityCfg(_M):
    """Restart / lost-signal / feed-loss protection (session 14). Thresholds are rules config, never hardcoded."""

    feed_guard_enabled: bool = True  # position open + no 1-minute bar: warn, then flatten (FEED_LOST)
    feed_warn_min: int = Field(default=3, ge=1, le=30)  # no bar for this long → error alert + new entries blocked
    feed_flatten_min: int = Field(default=6, ge=2, le=60)  # no bar for this long → flatten (protective, no hold)
    reprocess_window_min: int = Field(default=5, ge=1, le=30)  # unprocessed heartbeats this recent are replayed
    missed_check_alert_s: int = Field(default=90, ge=30, le=600)  # NOISE check minute without a stored bar

    @model_validator(mode="after")
    def _order(self) -> ReliabilityCfg:
        if self.feed_flatten_min <= self.feed_warn_min:
            raise ValueError("reliability: feed_flatten_min must be greater than feed_warn_min")
        return self


class ScheduleCfg(_M):
    reconcile_reset: str
    eod_update: str = "16:50"
    calendar: str
    bias: str
    preflight: str
    sync: list[str]
    sync_every_min: int
    report: str
    payouts: str
    nightly_backtest: str
    lab_cycle: str


class AutoResume(_M):
    paper: bool
    live: bool


class AutomationCfg(_M):
    default_mode: Literal["OFF", "SEMI", "FULL"]
    accounts_to_trade: int = Field(ge=1, le=5)
    selection_mode: Literal["priority", "manual"]
    semi_auto_sessions_per_stage: int
    auto_arm_new_accounts: bool
    require_external_attestation: bool
    auto_resume_after_recovery: AutoResume


class PayoutsCfg(_M):
    frequency: Literal["weekly", "on_demand", "every_n_sessions"]
    check_time: str
    sweep_above: D
    skim_mode: Literal["half", "off"]
    block_trading_while_pending: bool
    # D65 (user 2026-11-09, Lucid Pro: no payout window, request any day once eligible): "max_eligible" plans the
    # largest allowed payout (balance − buffer, capped) when the cycle profit ≥ min_cycle_profit and the largest day ≤
    # the funded consistency %; "every_n_sessions" checks once per session at session_check_time, at least
    # min_sessions_between sessions after the last payout. min_pct_of_cap: wait until the payout is ≥ this × the cap
    # (study: 0.5 = most take-home on 100K / 150K Regular); null = request as soon as eligible.
    mode: Literal["sweep_skim", "max_eligible"] = "sweep_skim"
    min_sessions_between: int = Field(2, ge=1, le=20)
    session_check_time: str = "17:05"
    min_pct_of_cap: D | None = Field(None, gt=0, le=1)


class PurchaseGate(_M):
    min_trades: int
    min_e_net_r: D
    min_pf: D
    max_violations: int
    demo_days: int
    semi_auto_sessions: int


class PlanCfg(_M):
    annual_target_net: D
    annual_floor_net: D
    tools_annual: D
    eval_cost_per_account: D
    trades_per_year_assumed: int
    r_avg_assumed: D


class SelfImprovement(_M):
    enabled: bool
    auto_promote_paper: bool
    cooldown_days: int
    min_oos_trades: int
    min_improvement_r: D
    max_param_step_pct: D
    shadow_min_sessions: int = 10  # §17.3: challenger runs in SHADOW ≥10 sessions / 20 trades before you can approve
    shadow_min_trades: int = 20
    shadow_max_sessions: int = 30  # still short of trades after this → shadow fails (no endless waiting)
    rollback_window_trades: int = 30  # §17.4: live rolling-30 E below the champion's OOS bound → auto-rollback


class RulesConfig(_M):
    account_size: D
    purchase: Purchase
    max_contracts: MaxContracts
    eval: EvalRules
    funded: FundedRules
    live: LiveRules
    session: SessionRules
    behavior: Behavior
    instruments: dict[str, Instrument]
    correlation_groups: dict[str, list[str]]
    super_groups: dict[str, list[str]]
    trade_plan: TradePlanCfg
    filters: Filters
    strategy: StrategyCfg = StrategyCfg()
    score: ScoreCfg
    entry: EntryCfg
    profiles: Profiles
    drawdown_guard: GuardCfg
    internal: InternalCfg
    one_to_one_mode: OneToOneMode
    scalp_mode: ScalpMode = ScalpMode()
    eval_mode: EvalModeCfg
    bias: BiasCfg
    smt: SmtCfg
    indicators: IndicatorsCfg
    webhook: WebhookCfg
    reliability: ReliabilityCfg = ReliabilityCfg()
    schedule: ScheduleCfg
    automation: AutomationCfg
    payouts: PayoutsCfg
    purchase_gate: PurchaseGate
    plan: PlanCfg
    self_improvement: SelfImprovement

    @model_validator(mode="after")
    def _structural(self) -> RulesConfig:
        # Structural sanity only. Full user-setting validation lives in risk/validation.py (§11).
        tp = self.trade_plan
        # D48/D49 (user, binding): every trade aims at least 1.5R (user 2026-11-06: "1.5-2.5"). D36 had quietly
        # lowered the minimum to 1.0 (84% of its trades then aimed below 1.75R) — a plan below 1.5R never loads.
        if not (D("1.5") <= tp.rr_min <= tp.rr_max):
            raise ValueError("trade_plan: need 1.5 <= rr_min <= rr_max (user rule: R:R 1.5-2.5)")
        for name, c in (("internal", self.internal), ("eval_mode", self.eval_mode)):
            if not (c.risk_pct_floor <= c.risk_pct_middle <= c.risk_pct_ceiling):
                raise ValueError(f"{name}: floor <= middle <= ceiling required")
        lo, hi = self.internal.risk_pct_absolute_bounds
        for v in (self.eval_mode.risk_pct_ceiling, self.internal.risk_pct_ceiling):
            if not (lo <= v <= hi):
                raise ValueError("risk % outside absolute bounds")
        for sym, inst in self.instruments.items():
            if inst.super_group not in self.super_groups:
                raise ValueError(f"instrument {sym}: unknown super_group {inst.super_group}")
            if inst.group not in self.correlation_groups or sym not in self.correlation_groups[inst.group]:
                raise ValueError(f"instrument {sym}: not a member of correlation group {inst.group}")
        o = self.one_to_one_mode
        if o.rr != D(1):
            raise ValueError("one_to_one_mode.rr must be exactly 1")
        if not (D(0) < o.partial_at_fraction_of_tp < D(1) and D(0) < o.partial_qty_fraction < D(1)):
            raise ValueError("one_to_one_mode partial fractions must be between 0 and 1")
        if not (1 <= o.max_trades_per_day <= o.extended_max_trades_per_day <= 7):  # D36: scalp/1:1 up to 7/day
            raise ValueError("one_to_one_mode: max trades <= extended max trades <= 7")
        if not (self.internal.max_consecutive_losses_per_day <= o.max_consecutive_losses_per_day <= 3):
            raise ValueError("one_to_one_mode allows at most 3 consecutive losses per day")
        if o.extend_after_win_streak < 1:
            raise ValueError("extend_after_win_streak must be >= 1")
        lo, hi = o.single_contract_lock_bounds
        if not (D(0) < lo <= o.single_contract_lock_r <= hi < o.partial_at_fraction_of_tp * o.rr):
            raise ValueError("single_contract_lock_r must sit inside its bounds and below the 75% trigger")
        if o.gate.min_e_net_r < self.purchase_gate.min_e_net_r or o.gate.min_trades < self.purchase_gate.min_trades:
            raise ValueError("1:1 gate can't be looser than the purchase gate")
        f = o.filters
        if f.min_score < self.score.min_score:
            raise ValueError("1:1 filters can only be stricter: min_score below the normal minimum")
        if not (D(0) < f.t1_rate_min < D(1)) or not (D(0) <= f.atr_pct_band[0] < f.atr_pct_band[1] <= D(100)):
            raise ValueError("1:1 filters: t1_rate_min in (0,1) and 0 <= ATR band low < high <= 100")
        if f.news_after_min < self.eval.news_breach_min_after:
            raise ValueError("1:1 news buffer can't be shorter than the firm's")
        if not (D(0) < self.internal.funded_consistency_pct <= D(100)):
            raise ValueError("funded_consistency_pct must be in (0, 100]")
        b = self.behavior
        if b.min_hold_seconds <= b.firm_microscalp_hold_seconds:
            raise ValueError("min_hold_seconds must exceed firm_microscalp_hold_seconds")
        if not (D(0) < b.rapid_trade_warn_pct < b.firm_microscalp_pct):
            raise ValueError("rapid_trade_warn_pct must be below firm_microscalp_pct")
        if self.drawdown_guard.runner_trail_r > D(2):
            raise ValueError("runner_trail_r must be <= 2.0R")
        return self

    def instrument(self, symbol: str) -> Instrument:
        try:
            return self.instruments[symbol]
        except KeyError as e:
            raise KeyError(f"unknown instrument {symbol}") from e

    def super_group_of(self, symbol: str) -> str:
        """Super-group for hedge lock; accepts minis too (NQ, ES...) via correlation groups."""
        for group, members in self.correlation_groups.items():
            if symbol in members:
                for sg, groups in self.super_groups.items():
                    if group in groups:
                        return sg
        raise KeyError(f"no super-group for {symbol}")


class LoadedRules(BaseModel):
    model_config = ConfigDict(frozen=True)
    rules: RulesConfig
    verify_paths: list[str]
    source_text: str


def load_rules(path: Path) -> LoadedRules:
    text = path.read_text(encoding="utf-8")
    return LoadedRules(
        rules=RulesConfig.model_validate(load_yaml_decimal(text)),
        verify_paths=find_verify_paths(text),
        source_text=text,
    )
