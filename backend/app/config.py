"""Rule profile loader (§1.7, §23).

- Every YAML float is parsed as Decimal (exact). Money/prices never touch binary floats.
- Lines marked `# VERIFY` are reported as dotted key paths so the UI can show gold badges.
- Typed Pydantic models make the config the single, validated source of rule numbers.
"""

from __future__ import annotations

import re
from datetime import datetime
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


class PayoutConsistencyCfg(_M):
    """D89: Lucid's payout-eligibility consistency rule (LucidPro funded). Limit = `pct`, or `legacy_pct` for accounts
    purchased/reset on or before `legacy_cutoff`. A payout may only be requested while largest day ≤ limit × profit."""

    pct: D = Field(gt=0, le=100)
    legacy_pct: D = Field(gt=0, le=100)
    legacy_cutoff: datetime

    @model_validator(mode="after")
    def _check(self) -> PayoutConsistencyCfg:
        if self.legacy_cutoff.tzinfo is None:
            raise ValueError("legacy_cutoff needs a time zone offset, e.g. 2025-11-28T15:00:00-05:00")
        if self.legacy_pct > self.pct:
            raise ValueError("legacy_pct can't be looser than pct")
        return self


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
    payout_consistency: PayoutConsistencyCfg | None = None  # D89 (LucidPro only; None = no such rule)
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


PATH_ZONES = ("INSIDE", "L1", "AVR-", "AVR", "AVR+", "MAX")  # D101: Asia range + daily ATR(20) zones, in order


class ArModelCfg(_M):
    """D101 (D100: the AR Model is the MAIN Order Flow source, docs/results/session18/order_flow/AR_MODEL_RULES.md):
    ENVIRONMENT → LOCATION → PATH → CONFIRMATION gates on every ORDER_FLOW alert (engine/order_flow.check_ar).
    UNVERIFIED (no tick-data test) — these only ever REMOVE trades; the validators refuse anything looser than the
    teacher's rules (fib zone inside 0.5–0.886, compression never allowed, path block at MAX or tighter)."""

    required: bool = True  # an alert WITHOUT the AR fields (pre-D101 indicator) → OF_NO_CONFIRM
    # ENVIRONMENT + CONFIRMATION are always on. LOCATION and PATH are separate switches: the session-18 AR study
    # (docs/results/session18/ar_model/RESULTS.md, ESTIMATED delta) found they did not help on bar data; real delta
    # may change that. ON by default = the teacher's full model (they only ever remove trades).
    location_filter: bool = True
    path_filter: bool = True
    allowed_envs: list[Literal["EXPANSION", "ROTATION"]] = ["EXPANSION", "ROTATION"]  # COMPRESSION: never (type)
    fib_min: D = D("0.705")  # retracement depth of the swing range (bias side) — focus zone 0.705–0.886
    fib_max: D = D("0.886")  # a close beyond 0.886 invalidates the reversal idea
    value_side: Literal["OUTSIDE_VALUE", "NOT_OPPOSITE"] = "OUTSIDE_VALUE"  # LONG below VAL / SHORT above VAH
    path_block_zone: Literal["L1", "AVR-", "AVR", "AVR+", "MAX"] = "MAX"  # at/beyond this zone WITH the move → skip
    confirm_max_age_min: int = Field(default=3, ge=1, le=15)  # entry candle at most this many minutes after confirm
    require_real_delta: bool = False  # True → delta_source "est" alerts are skipped (OF_DELTA_ESTIMATED)
    trail_candle_min: Literal[5, 15] = 5  # trail behind the last closed 5m (or 15m) candle — ratchet only
    be_after_r: D = D("1.0")  # break-even once follow-through reaches this many R

    @model_validator(mode="after")
    def _check(self) -> ArModelCfg:
        if not self.allowed_envs or len(set(self.allowed_envs)) != len(self.allowed_envs):
            raise ValueError("order_flow.ar: allowed_envs needs EXPANSION and/or ROTATION, no duplicates")
        if not (D("0.5") <= self.fib_min < self.fib_max <= D("0.886")):
            raise ValueError("order_flow.ar: 0.5 ≤ fib_min < fib_max ≤ 0.886 (AR Model location zone)")
        if not (D("0.25") <= self.be_after_r <= D("3")):
            raise ValueError("order_flow.ar: be_after_r within 0.25–3 R")
        return self


class CasperCfg(_M):
    """D108 (user 2026-11-11 "implement 1st transcript knowledge too"): Casper / Jesse Rogers 4h order-flow course
    (docs/results/session18/order_flow/TEACHER_RULES_4H.md) as REFINEMENTS of the AR Model (D100: never override it).
    Each rule is its own switch (engine/order_flow.check_casper, codes OF_CASPER_<RULE>). UNVERIFIED. ON by default
    only where it simply tightens an AR definition; new filters default OFF. Validators refuse anything looser."""

    # "price confirms order flow": the entry candle closes away from the trapped side (LONG upper part, SHORT lower)
    price_confirms: bool = True
    close_pos_min: D = D("0.5")  # close location in the entry candle range on the trade side (0.5 = favourable half)
    # aggression = a REAL stack: a STACKED_IMBALANCE alert needs ≥ min_stacked diagonal imbalances in a row
    stacked_definition: bool = True
    min_stacked: int = Field(default=3, ge=3, le=6)
    # CVD confirmation: the other side gets a return — CVD over the last bars moves in the trade direction
    cvd_confirm: bool = False
    # CONDITION: RTH open vs the PRIOR RTH value area (above = bullish lean, below = bearish); no trade against it
    condition: bool = False
    inside_value_ok: bool = True  # open inside prior value = no lean → both sides allowed
    # no-trade: levels bunched (prior RTH value area narrower than min_va_width_atr × daily ATR(20)) = flat day
    bunched: bool = False
    min_va_width_atr: D = D("0.25")
    # stop never ON a round number: push it round_buffer_ticks beyond a nearby round level (plan re-checked)
    round_stop: bool = False
    round_buffer_ticks: int = Field(default=2, ge=1, le=3)
    round_step: dict[Literal["MNQ", "MGC"], D] = {"MNQ": D("50"), "MGC": D("5")}

    @model_validator(mode="after")
    def _check(self) -> CasperCfg:
        if not (D("0.5") <= self.close_pos_min <= D("0.9")):
            raise ValueError("order_flow.casper: 0.5 ≤ close_pos_min ≤ 0.9")
        if not (D("0.05") <= self.min_va_width_atr <= D("1")):
            raise ValueError("order_flow.casper: min_va_width_atr within 0.05–1 daily ATR")
        if any(v <= 0 for v in self.round_step.values()):
            raise ValueError("order_flow.casper: round_step must be > 0")
        return self


class OrderFlowCfg(_M):
    """D95 (user button, 2026-11-11): order-flow signals from pine/Paytience_OrderFlow.pine (ORDER_FLOW webhook
    alerts) — UNVERIFIED (no order-flow backtest: no tick data); D102: not forced paper-only (contracts stay 1).
    D101: rebuilt around the AR Model (`ar`)."""

    # D96 (user 2026-11-11, override of D55 for Order Flow ONLY): the markets Order Flow may trade. MGC here is a
    # per-strategy switch — the global instruments.MGC.enabled stays false, so every other strategy keeps MGC off.
    instruments: list[Literal["MNQ", "MGC"]] = ["MNQ"]
    buffer_ticks: int = Field(default=1, ge=1, le=20)  # stop this many ticks beyond the defended level
    rr: D = D("2.0")  # target = 2R
    rr_min: D = D("1.5")  # firm floor (D49): config refuses lower
    min_risk_ticks: int = Field(default=8, ge=1)
    max_risk_ticks: int = Field(default=120, ge=1)
    max_per_day: int = Field(default=3, ge=1, le=10)
    contracts: int = 1
    paper_only: bool = False  # D102 (user 2026-11-11): no strategy is forced paper-only; live gates unchanged
    flat_at: str = "16:00"  # D96: an open order-flow position is flattened at this ET time (before the global flat)
    ar: ArModelCfg = ArModelCfg()  # D101: AR Model layers
    casper: CasperCfg = CasperCfg()  # D108: Casper 4h course refinements (each a switch)

    @model_validator(mode="after")
    def _check(self) -> OrderFlowCfg:
        if not self.instruments or len(set(self.instruments)) != len(self.instruments):
            raise ValueError("order_flow: instruments needs MNQ and/or MGC, no duplicates")
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", self.flat_at):
            raise ValueError("order_flow: flat_at is HH:MM")
        if self.rr_min < D("1.5") or self.rr < self.rr_min:
            raise ValueError("order_flow: rr_min ≥ 1.5 and rr ≥ rr_min")
        if self.min_risk_ticks > self.max_risk_ticks:
            raise ValueError("order_flow: min_risk_ticks ≤ max_risk_ticks")
        if self.contracts != 1:  # D102: paper_only is a user choice now; the fixed 1 micro stays (D95)
            raise ValueError("order_flow: UNVERIFIED — contracts must stay 1 (D95)")
        return self


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
    paper_only: bool = False  # D102 (user 2026-11-11): no strategy is forced paper-only; live gates unchanged


class AiDuoCfg(_M):
    """D83 (user button 2026-11-10, beside ai_bias): trade only when TradingAgents AND Vibe-Trading pick the same side
    (Vibe-Trading is an opinion only, never trades); enter on the first 5-minute VWAP pullback close in that direction
    inside the entry window (09:36–11:30 ET per market, D86); structure stop capped at the NOISE
    dollar stop; target rr_target R (floor 1.5R); 1 micro. Markets: MNQ and/or MGC (AI Duo only; NOISE stays MNQ).
    NOT back-testable. D102 (user 2026-11-11): no longer forced paper-only; every live gate still applies.
    Design: docs/results/session16/ai_combined_strategy_design.md."""

    markets: list[Literal["MNQ", "MGC"]] = ["MNQ", "MGC"]  # each market decides once a day (own AI proxy: QQQ / GLD)
    # entry window per market, ET (D86, user 2026-11-10: back to the best-tested hours; 03:00 starts lost,
    # see docs/results/session16/ai_duo_window). The window start
    # is also the session-VWAP anchor; the last bar close in the window that may trigger ends it (NO_PULLBACK skip).
    windows: dict[Literal["MNQ", "MGC"], tuple[str, str]] = {"MGC": ("09:36", "11:30"), "MNQ": ("09:36", "11:30")}
    # per-market account (Account.id; max 1 position per account stays): MGC and MNQ may run on different accounts.
    # A market without an entry uses any selected/armed account not assigned to the other market.
    accounts: dict[Literal["MNQ", "MGC"], int | None] = {}
    excluded: list[tuple[str, str]] = [("09:30", "09:35")]  # no bar touching these minutes may trigger (D11)
    bar_minutes: int = 5
    vt_min_conf: int = 60  # Vibe-Trading confidence needed for "strong"
    stop_buffer_ticks: int = 2
    rr_target: D = D("2.0")
    rr_min: D = D("1.5")  # firm floor (CLAUDE.md D49): config refuses lower
    flat_at: str = "16:00"
    contracts: int = 1  # micros per trade on every account except the big (150K) ones below
    paper_only: bool = False  # D102 (user 2026-11-11): no strategy is forced paper-only; live gates unchanged
    # D85 (user 2026-11-10): total risk per trade (stop distance × qty + fees + slippage), all account sizes
    max_risk_usd: D = D("250")
    # D85 (user-approved override of "max 1 open position per account", AI Duo on accounts ≥ big_account_size ONLY):
    # up to max_open_positions positions at once and max_qty micros per trade (a CAP: sizing still comes from the risk
    # engine + max_risk_usd + the aggregate DLL/MLL check). Every other account stays at 1 position / `contracts`.
    big_account_size: D = D("150000")
    max_open_positions: int = 4
    max_qty: int = 4
    brake_below: D = D("0.5")  # cushion brake: 1 micro while (equity − MLL) < brake_below × the account's loss limit
    # D85 trade management (reuses the guard's BE price, the lock rule and the runner trail; ratchet only):
    be_r: D = D("1.0")  # break-even (+ fee cover) once +1R
    trail_start_r: D = D("1.5")
    trail_r: D = D("1.0")
    # profit lock per market, points: (trigger, lock) — once +trigger pts the stop moves to entry +lock pts, or to the
    # AI setup's own lock level when it gave one. User 2026-11-10: MNQ +100 → +50 (NOISE keeps its tested +100 → +10).
    lock_pts: dict[Literal["MNQ", "MGC"], tuple[D, D]] = {"MNQ": (D(100), D(50))}
    # step trail per market, ticks: (step, raise) — for every `step` ticks of open profit the stop is raised by `raise`
    # ticks above the ORIGINAL stop (ratchet only, never through the market). User-set 2026-11-10 (D85 addendum):
    # MGC 60 → 20. A market with a step trail does not use lock_pts; the AI setup's own level still replaces it.
    step_trail: dict[Literal["MNQ", "MGC"], tuple[int, int]] = {"MGC": (60, 20)}

    @model_validator(mode="after")
    def _valid(self) -> AiDuoCfg:
        if self.max_risk_usd <= 0 or self.max_open_positions < 1 or self.max_qty < 1 or self.big_account_size <= 0:
            raise ValueError("ai_duo: max_risk_usd > 0, max_open_positions ≥ 1, max_qty ≥ 1, big_account_size > 0")
        if not (D(0) < self.brake_below <= D(1)):
            raise ValueError("ai_duo: 0 < brake_below ≤ 1")
        if self.be_r <= 0 or any(not (D(0) <= lock < trig) for trig, lock in self.lock_pts.values()):
            raise ValueError("ai_duo: be_r > 0 and each lock_pts needs 0 ≤ lock < trigger")
        if any(m not in self.lock_pts and m not in self.step_trail for m in self.markets):
            raise ValueError("ai_duo: every market needs lock_pts or step_trail")
        if any(not (0 < raise_ticks <= step) for step, raise_ticks in self.step_trail.values()):
            raise ValueError("ai_duo: step_trail needs 0 < raise_ticks ≤ step_ticks")
        if self.trail_start_r <= 0 or self.trail_r <= 0:
            raise ValueError("ai_duo: trail_start_r and trail_r > 0")
        if self.rr_min < D("1.5") or self.rr_target < self.rr_min:
            raise ValueError("ai_duo: rr_min ≥ 1.5 and rr_target ≥ rr_min")
        if self.bar_minutes < 1 or self.contracts < 1 or self.vt_min_conf < 1 or self.stop_buffer_ticks < 0:
            raise ValueError("ai_duo: bar_minutes, contracts, vt_min_conf ≥ 1 and stop_buffer_ticks ≥ 0")
        if not self.markets or len(set(self.markets)) != len(self.markets):
            raise ValueError("ai_duo: markets needs MNQ and/or MGC, no duplicates")
        times = [self.flat_at, *(x for w in self.excluded for x in w), *(x for w in self.windows.values() for x in w)]
        if any(not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", x) for x in times):
            raise ValueError("ai_duo: times are HH:MM")
        if any(a >= b for a, b in self.windows.values()):
            raise ValueError("ai_duo: each window starts before it ends")
        if any(m not in self.windows for m in self.markets):
            raise ValueError("ai_duo: every market needs a window")
        if any(i is not None and i < 1 for i in self.accounts.values()):
            raise ValueError("ai_duo: account ids are positive")
        return self

    def window_for(self, symbol: str) -> tuple[str, str]:
        return self.windows[symbol]  # type: ignore[index]


class TaMgcCfg(_M):
    """D84 (user 2026-11-10; part of the single AI Duo button, MGC): TradingAgents MGC research → one structured gold
    setup per day (side, confidence, entry zone, invalidation, target, valid-until, reasons), taken only when
    Vibe-Trading agrees on the side (the shared AI Duo agreement rule). Entry window / exclusions / paper-only /
    1 micro come from ai_duo_cfg. §7 plan builder: rr floor from trade_plan.rr_min (≥ 1.5R), cap trade_plan.rr_max,
    preferred rr_preferred (setups between the floor and 2R are allowed and tagged). MGC only, while AI Duo is on."""

    proxy: str = "GLD"
    research_at: str = "02:45"  # ET, weekdays, once a day (retried every 30 min until the Duo window ends)
    min_confidence: int = 55  # setup confidence needed (TradingAgents' own number)
    stop_buffer_ticks: int = 4
    rr_preferred: D = D("2.0")

    @model_validator(mode="after")
    def _valid(self) -> TaMgcCfg:
        if self.rr_preferred < D("1.5") or self.stop_buffer_ticks < 0 or not 0 <= self.min_confidence <= 100:
            raise ValueError("ta_mgc: rr_preferred ≥ 1.5, stop_buffer_ticks ≥ 0, min_confidence 0-100")
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", self.research_at):
            raise ValueError("ta_mgc: research_at is HH:MM")
        return self


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
    paper_only: bool = False  # D102 (user 2026-11-11): no strategy is forced paper-only; live gates unchanged


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


# D105 (LunqFX) + D107 (Opening drive): removed strategies - their keys in old plan files / stored settings are ignored
LEGACY_LUNQFX_KEYS = ("lunqfx", "lunqfx_structure", "open_drive", "open_drive_cfg")


class StrategyCfg(_M):
    """D55: which strategies may trade (buttons on the Strategy page). D105: the LunqFX button/keys were removed;
    old plan files / stored settings that still carry them are tolerated and ignored (see _apply_preset)."""

    # D82: Strategy preset (config/strategy_presets.yaml) — overlays noise_cfg stop/profit lock, noise, pm_fade and the
    # size tables before validation. None = "custom" (the plan file's own values).
    preset: str | None = None
    noise: bool = False
    ai_bias: bool = False
    pm_fade: bool = False
    ai_duo: bool = False  # D83: AI Duo button (paper only, default OFF)
    order_flow: bool = False  # D95: Order Flow button (UNVERIFIED, default OFF; D102: not forced paper-only)
    # D92: "NOISE + AI Duo — 50/50 risk split" button (default OFF): with NOISE and AI Duo both on, each side
    # trades half size (rounded down, min 1) and may use half of the daily loss limit (D102: no forced paper-only).
    # Tighten-only.
    noise_ai_split: bool = False
    noise_ai_split_share: D = Field(default=D("0.5"), gt=D(0), le=D("0.5"))
    # D57: NOISE / AI_BIAS scale their emergency stop down as the account draws down instead of pausing at the pause
    # floor: worst case ≤ this fraction of the room (DLL left / distance to MLL − kill distance); None = old pause.
    drawdown_shrink: D | None = D("0.6")
    drawdown_min_stop_pct: D = D("0.002")  # a stop tighter than 0.2% of price is noise → skip DRAWDOWN_TOO_DEEP
    noise_cfg: NoiseCfg = NoiseCfg()
    ai_bias_cfg: AiBiasCfg = AiBiasCfg()
    pm_fade_cfg: PmFadeCfg = PmFadeCfg()
    ai_duo_cfg: AiDuoCfg = AiDuoCfg()
    order_flow_cfg: OrderFlowCfg = OrderFlowCfg()
    ta_mgc_cfg: TaMgcCfg = TaMgcCfg()
    structure_filters: StructureFilterCfg = StructureFilterCfg()
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
        if isinstance(data, dict) and any(k in data for k in LEGACY_LUNQFX_KEYS):
            data = {
                k: v for k, v in data.items() if k not in LEGACY_LUNQFX_KEYS
            }  # D105/D107: removed strategies, ignored
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


class FastLadderStep(_M):
    cushion_frac: D  # step applies while cushion (risk_base) >= cushion_frac x the loss limit (MLL)
    extra: int  # micros added on top of the base size while it applies


class FastLadderCfg(_M):
    enabled: bool = False
    steps: list[FastLadderStep] = []
    max_contracts: int = 1  # hard ceiling for base + ladder + early extras


class FastHarvestCfg(_M):
    enabled: bool = False
    day_stop_pct_of_target: D = D(
        "35"
    )  # stop new entries once today's profit >= x% of the profit target (tighten only)


class FastEarlyCfg(_M):
    enabled: bool = False
    first_trades: int = 0  # applies only to the first N closed trades of the stage ...
    until_profit_frac: D | None = None  # ... and/or only while the eval profit is below this share of the target
    cushion_frac: D = D("0.5")  # ... and only while cushion >= cushion_frac x the loss limit
    risk_pct: D | None = None  # score-tier path: raise the risk % to this (never lowers it)
    extra_contracts: int = 0  # fixed-size path: micros added


class FastQualityCfg(_M):
    enabled: bool = False
    mode: Literal["prev_day", "trailing"] = "prev_day"  # skip a day after a losing day / a losing trailing window
    trailing_days: int = 10


class FastEvalCfg(_M):
    """D87 Fast Evaluation (EVAL stage ONLY, non-negotiable 10; PAPER like everything else). Four independent
    mechanisms, each with its own switch. Never touches kill switch, DLL/MLL, gates, R:R, hedge/news/flat rules."""

    default_on: bool = False
    applies_to_stages: list[Literal["EVAL"]] = ["EVAL"]
    confirm_phrase: str = "ENABLE FAST EVALUATION"
    ladder: FastLadderCfg = FastLadderCfg()
    harvest: FastHarvestCfg = FastHarvestCfg()
    early: FastEarlyCfg = FastEarlyCfg()
    quality_day: FastQualityCfg = FastQualityCfg()
    pace_escalation: Literal[False] = False  # no martingale, no catching up

    @model_validator(mode="after")
    def _valid(self) -> FastEvalCfg:
        if any(st.extra < 1 or st.cushion_frac <= 0 for st in self.ladder.steps):
            raise ValueError("fast_eval.ladder: every step needs extra >= 1 and cushion_frac > 0")
        fr = [st.cushion_frac for st in self.ladder.steps]
        if fr != sorted(fr) or len(set(fr)) != len(fr):
            raise ValueError("fast_eval.ladder: steps must have strictly ascending cushion_frac")
        ex = [st.extra for st in self.ladder.steps]
        if ex != sorted(ex):
            raise ValueError("fast_eval.ladder: extra must not decrease as the cushion grows")
        if self.ladder.max_contracts < 1:
            raise ValueError("fast_eval.ladder.max_contracts >= 1")
        h = self.harvest.day_stop_pct_of_target
        if not (D(0) < h <= D(100)):
            raise ValueError("fast_eval.harvest.day_stop_pct_of_target must be in (0, 100]")
        e = self.early
        if e.first_trades < 0 or e.extra_contracts < 0 or not (D(0) < e.cushion_frac <= D(1)):
            raise ValueError("fast_eval.early: first_trades >= 0, extra_contracts >= 0, 0 < cushion_frac <= 1")
        if e.until_profit_frac is not None and not (D(0) < e.until_profit_frac <= D(1)):
            raise ValueError("fast_eval.early.until_profit_frac must be in (0, 1]")
        if e.enabled and e.first_trades == 0 and e.until_profit_frac is None:
            raise ValueError("fast_eval.early: enabled needs first_trades > 0 or until_profit_frac")
        if e.risk_pct is not None and not (D(0) < e.risk_pct <= D("0.14")):
            raise ValueError("fast_eval.early.risk_pct must be in (0, 0.14] (the Evaluation Mode ceiling)")
        if self.quality_day.trailing_days < 1:
            raise ValueError("fast_eval.quality_day.trailing_days >= 1")
        return self


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
    """D91: BigBeluga MSO. OFF by default: gates G4-G6 and the MSO score components are not evaluated, and LunqFX
    (which needs them) can only run in SHADOW. The parameters stay for the opt-in path and the old regression tests."""

    enabled: bool = False
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
    fast_eval: FastEvalCfg = FastEvalCfg()
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
        missing = [x for x in self.strategy.order_flow_cfg.instruments if x not in self.instruments]
        if missing:  # D96: tick size / value / fees always come from the instrument config, never from code
            raise ValueError(f"strategy.order_flow_cfg.instruments: no instrument config for {missing}")
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
