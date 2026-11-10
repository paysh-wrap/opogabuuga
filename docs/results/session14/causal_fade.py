"""Session 14: shared shim that makes the session 10/11 account engines use the LIVE (causal) PM-fade rule.
Rule (strategy_service.run_pm_fade): fade at minute k is allowed only if NO NOISE signal fired at a check <= k.
A NOISE signal whose entry bar falls while the fade is open is dropped (one position per account).
Switch: env FADE_RULE=causal (default) | hindsight (old: fade only on days NOISE took no trade -> reproduces the old reports)."""
import os

CAUSAL = os.environ.get("FADE_RULE", "causal") != "hindsight"
CHECKS = list(range(29, 360, 60))
PTS_NOMINAL, END = 124.0, 386


def first_sig(D):
    """first NOISE signal check minute of the day (flat at the start of the day, so the first non-zero side is a signal); 10**9 if none."""
    v = getattr(D, "_fs", None)
    if v is None:
        v = 10 ** 9
        if getattr(D, "noise_ok", False):
            for k in CHECKS:
                if D.side.get(k, 0) != 0:
                    v = k
                    break
        D._fs = v
    return v


def fade_x(D):
    """exit bar of the fade with the nominal 124-pt stop (target VWAP, stop, or 15:56)."""
    v = getattr(D, "_fx", None)
    if v is None:
        k, s, e, tgt = D.fade
        stop = e - s * PTS_NOMINAL
        v = END - 1
        for j in range(k + 1, END):
            if (s > 0 and D.l[j] <= stop) or (s < 0 and D.h[j] >= stop) or (s > 0 and D.h[j] >= tgt) or (s < 0 and D.l[j] <= tgt):
                v = j
                break
        D._fx = v
    return v


def fade_allowed(D, taken):
    """replaces the old `taken == 0` fade condition."""
    if D.fade is None:
        return False
    if not CAUSAL:
        return taken == 0
    return first_sig(D) > D.fade[0]


def noise_blocked(D, k):
    """NOISE signal at check k is dropped because a (causally allowed) fade is open at its entry bar k+1."""
    if not CAUSAL or D.fade is None:
        return False
    fk = D.fade[0]
    return first_sig(D) > fk and fk < k + 1 <= fade_x(D)
