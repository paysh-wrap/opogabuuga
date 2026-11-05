"""Rule profile loader (§1.7, §23).

- Every YAML float is parsed as Decimal (exact). Money/prices never touch binary floats.
- Lines marked `# VERIFY` are reported as dotted key paths so the UI can show gold badges.
- Typed Pydantic models make the config the single, validated source of rule numbers.
"""

from __future__ import annotations

import re
from decimal import Decimal
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
    min_hold_seconds: int
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
    stop_buffer_ticks: int | None = None
    min_stop_ticks: int | None = None
    slippage_ticks: int | None = None
    windows: list[tuple[str, str]] | None = None  # per-market entry windows (ET); falls back to internal.windows
    news_after_min: int | None = None  # no entries until N min after a high-impact release (falls back to firm rule)


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


class Filters(_M):
    c1_min_range_atr: D
    htf_atr_period: int
    model_fail_cooldown: Cooldown


class ScoreCfg(_M):
    weights: dict[str, D]
    min_score: D
    neutral_min_score: D
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
    frequency: Literal["weekly", "on_demand"]
    check_time: str
    sweep_above: D
    skim_mode: Literal["half", "off"]
    block_trading_while_pending: bool


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
        if not (D(1) <= tp.rr_min <= tp.rr_max):
            raise ValueError("trade_plan: need 1 <= rr_min <= rr_max")
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
        if not (1 <= o.max_trades_per_day <= o.extended_max_trades_per_day <= 5):
            raise ValueError("one_to_one_mode: max trades <= extended max trades <= 5")
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
