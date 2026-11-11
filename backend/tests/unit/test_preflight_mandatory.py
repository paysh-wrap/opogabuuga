"""D99: pre-flight blocks ONLY on mandatory items. Every optional item missing must not block; every mandatory
item missing must."""

import pytest

from app.automation.preflight import OPTIONAL_CHECKS, PreflightInput, run


def _ok(**over):
    base = dict(
        broker_ok=True, token_hours_left=None, feeds_fresh=True, calendar_loaded=True, bias_loaded=True, live=False,
        unconfirmed_verify=0, reconciled=True, orphan_orders=0, attested_today=True, clock_drift_s=0.1,
        rules_error=None, conservative_mode=False,
    )  # fmt: skip
    return PreflightInput(**{**base, **over})


def test_all_good_passes_with_no_warnings():
    r = run(_ok())
    assert r.ok and r.failures == [] and r.warnings == []


def test_optional_checks_are_only_the_daily_bias():
    assert {"bias"} == OPTIONAL_CHECKS


def test_missing_bias_never_blocks_but_is_reported():
    r = run(_ok(bias_loaded=False))
    assert r.ok and r.failures == [] and r.warnings == ["bias"]
    row = next(c for c in r.checks if c["check"] == "bias")
    assert row["optional"] is True and "proceed" in str(row["detail"])


@pytest.mark.parametrize(
    "field,value,failing",
    [
        ("broker_ok", False, "broker"),
        ("feeds_fresh", False, "heartbeat_fresh"),
        ("webhook_secret_set", False, "webhook_secret"),
        ("calendar_loaded", False, "calendar"),
        ("attested_today", False, "attestation"),
        ("clock_drift_s", 5.0, "clock_drift"),
        ("clock_drift_s", -9.0, "clock_drift"),
        ("reconciled", False, "reconciled"),
        ("orphan_orders", 1, "no_orphan_orders"),
        ("rules_error", "bad yaml", "rules_valid"),
        ("token_hours_left", 1.0, "token"),
    ],
)
def test_each_mandatory_item_missing_blocks(field, value, failing):
    r = run(_ok(**{field: value}))
    assert not r.ok and failing in r.failures


def test_verify_values_block_live_only():
    assert run(_ok(unconfirmed_verify=3, live=False)).ok
    assert "verify_confirmed" in run(_ok(unconfirmed_verify=3, live=True)).failures


def test_clock_unknown_does_not_block_and_is_flagged_unknown():
    r = run(_ok(clock_drift_s=None))
    assert r.ok
    row = next(c for c in r.checks if c["check"] == "clock_drift")
    assert row["unknown"] is True and "unknown" in str(row["detail"])


def test_clock_uncertainty_blocks_only_when_certain():
    assert run(_ok(clock_drift_s=2.4, clock_uncertainty_s=0.6)).ok  # may still be < 2 s
    assert not run(_ok(clock_drift_s=3.0, clock_uncertainty_s=0.5)).ok
    row = next(c for c in run(_ok(clock_drift_s=0.3)).checks if c["check"] == "clock_drift")
    assert "unknown" not in row


def test_nothing_about_optional_connections_is_a_check():
    names = {c["check"] for c in run(_ok()).checks}
    for opt in ("discord", "ai_key", "tradingagents", "trading_r1", "databento", "openbb", "github", "vibe"):
        assert not any(opt in n for n in names)
