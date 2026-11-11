"""Pre-flight (§13): at schedule.preflight (02:50 ET, D34) and whenever automation is enabled. Fail → OFF + banner.

D99: only MANDATORY checks can fail it; OPTIONAL ones (bias) are warnings.
Clock drift blocks only when KNOWN."""

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
    webhook_secret_set: bool = True  # D99 mandatory: without it every TradingView alert is rejected
    clock_detail: str = ""
    clock_uncertainty_s: float | None = None


@dataclass
class PreflightResult:
    ok: bool
    checks: list[dict[str, object]] = field(default_factory=list)

    @property
    def failures(self) -> list[str]:
        """Only MANDATORY checks can fail a pre-flight."""
        return [str(c["check"]) for c in self.checks if not c["ok"] and not c.get("optional")]

    @property
    def warnings(self) -> list[str]:
        """OPTIONAL checks that are not met (D99): shown with a notice, never block."""
        return [str(c["check"]) for c in self.checks if not c["ok"] and c.get("optional")]


# D99: OPTIONAL checks. A missing item here must never block automation (user-binding). Everything else is MANDATORY.
OPTIONAL_CHECKS = frozenset({"bias"})


def run(x: PreflightInput) -> PreflightResult:
    drift_known = x.clock_drift_s is not None
    checks = [
        ("broker", x.broker_ok, ""),
        ("token", x.token_hours_left is None or x.token_hours_left > 2, f"{x.token_hours_left} h left"),
        ("heartbeat_fresh", x.feeds_fresh, ""),
        ("webhook_secret", x.webhook_secret_set, "no webhook secret = no alert can be accepted"),
        ("calendar", x.calendar_loaded, "no calendar = no trading"),
        (
            "bias",
            x.bias_loaded,
            "optional: no TradingAgents bias today — bias-dependent strategies (AI) skip with BIAS_NO_TRADE, "
            "the others (NOISE, Order Flow) proceed",
        ),
        ("verify_confirmed", not x.live or x.unconfirmed_verify == 0, f"{x.unconfirmed_verify} VERIFY values open"),
        ("reconciled", x.reconciled, "broker positions match ours"),
        ("no_orphan_orders", x.orphan_orders == 0, f"{x.orphan_orders} orphan orders"),
        ("attestation", x.attested_today, "external positions attested this session"),
        # D99: mandatory, but only a KNOWN drift >= 2 s blocks; unmeasurable = "unknown" (shown, never assumed OK)
        (
            "clock_drift",
            not drift_known or abs(x.clock_drift_s) - (x.clock_uncertainty_s or 0.0) < 2,  # type: ignore[arg-type]
            x.clock_detail or (f"{x.clock_drift_s} s" if drift_known else "unknown — not measurable"),
        ),
        ("rules_valid", x.rules_error is None, x.rules_error or ""),
    ]
    res = PreflightResult(ok=all(ok for n, ok, _ in checks if n not in OPTIONAL_CHECKS))
    res.checks = [
        {
            "check": n,
            "ok": ok,
            "detail": d,
            **({"optional": True} if n in OPTIONAL_CHECKS else {}),
            **({"unknown": True} if n == "clock_drift" and not drift_known else {}),
        }
        for n, ok, d in checks
    ]
    return res


def allowed_mode(requested: str, stage_sessions: list[int], semi_sessions: int, conservative: bool) -> str:
    """FULL-AUTO only after the first N sessions of each stage on every armed account, and never in
    conservative mode (no position read-back). Otherwise the most it can be is SEMI."""
    if requested != "FULL":
        return requested
    if conservative or any(n < semi_sessions for n in stage_sessions):
        return "SEMI"
    return "FULL"
