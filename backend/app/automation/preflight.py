"""Pre-flight (§13): run at 06:40 (D2) and whenever automation is enabled. Any failure → OFF + banner."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class PreflightInput:
    broker_ok: bool
    token_hours_left: float | None  # None = adapter has no token (sim)
    feeds_fresh: bool
    calendar_loaded: bool
    bias_loaded: bool
    live: bool
    unconfirmed_verify: int
    reconciled: bool
    orphan_orders: int
    attested_today: bool
    clock_drift_s: float | None
    rules_error: str | None
    conservative_mode: bool


@dataclass
class PreflightResult:
    ok: bool
    checks: list[dict[str, object]] = field(default_factory=list)

    @property
    def failures(self) -> list[str]:
        return [str(c["check"]) for c in self.checks if not c["ok"]]


def run(x: PreflightInput) -> PreflightResult:
    checks = [
        ("broker", x.broker_ok, ""),
        ("token", x.token_hours_left is None or x.token_hours_left > 2, f"{x.token_hours_left} h left"),
        ("heartbeat_fresh", x.feeds_fresh, ""),
        ("calendar", x.calendar_loaded, "no calendar = no trading"),
        ("bias", x.bias_loaded, "TradingAgents bias for today"),
        ("verify_confirmed", not x.live or x.unconfirmed_verify == 0, f"{x.unconfirmed_verify} VERIFY values open"),
        ("reconciled", x.reconciled, "broker positions match ours"),
        ("no_orphan_orders", x.orphan_orders == 0, f"{x.orphan_orders} orphan orders"),
        ("attestation", x.attested_today, "external positions attested this session"),
        ("clock_drift", x.clock_drift_s is not None and abs(x.clock_drift_s) < 2, f"{x.clock_drift_s} s"),
        ("rules_valid", x.rules_error is None, x.rules_error or ""),
    ]
    res = PreflightResult(ok=all(ok for _, ok, _ in checks))
    res.checks = [{"check": n, "ok": ok, "detail": d} for n, ok, d in checks]
    return res


def allowed_mode(requested: str, stage_sessions: list[int], semi_sessions: int, conservative: bool) -> str:
    """FULL-AUTO only after the first N sessions of each stage on every armed account, and never in
    conservative mode (no position read-back). Otherwise the most it can be is SEMI."""
    if requested != "FULL":
        return requested
    if conservative or any(n < semi_sessions for n in stage_sessions):
        return "SEMI"
    return "FULL"
