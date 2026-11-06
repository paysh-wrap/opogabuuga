"""§17.3 champion/challenger selection (PURE). Walk-forward: candidates are ranked on the older TRAIN sessions and
must then hold up on the newer TEST sessions they never saw. User rule (2026-11-06): a change may never lower the
win rate or the trade count; it must raise expectancy."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal as D
from typing import Any


@dataclass(frozen=True)
class Perf:
    trades: int
    wins: int
    net_r: D  # sum of net R

    @property
    def win_rate(self) -> D:
        return D(self.wins) / self.trades if self.trades else D(0)

    @property
    def e(self) -> D:
        return self.net_r / self.trades if self.trades else D(0)


def perf(trades: list[dict[str, Any]]) -> Perf:
    done = [t for t in trades if t.get("pnl") is not None]
    wins = sum(1 for t in done if D(str(t["pnl"])) > 0)
    net = sum((D(str(t["net_r"])) for t in done if t.get("net_r") is not None), D(0))
    return Perf(len(done), wins, net)


@dataclass(frozen=True)
class Candidate:
    diff: dict[str, D]
    train: Perf
    test: Perf | None = None


def keeps_user_rules(c: Perf, champ: Perf, min_trade_ratio: D) -> bool:
    return c.win_rate >= champ.win_rate and D(c.trades) >= D(champ.trades) * min_trade_ratio


def best_on_train(champ: Perf, cands: list[Candidate], min_trade_ratio: D = D("0.9")) -> Candidate | None:
    ok = [c for c in cands if keeps_user_rules(c.train, champ, min_trade_ratio) and c.train.e > champ.e]
    return max(ok, key=lambda c: (c.train.e, c.train.win_rate), default=None)


def passes_oos(
    champ_test: Perf, c: Candidate, min_improvement_r: D, min_oos_trades: int, min_trade_ratio: D = D("0.9")
) -> tuple[bool, list[str]]:
    """Out-of-sample guard. Returns (ok, reasons it failed)."""
    why: list[str] = []
    t = c.test
    if t is None:
        return False, ["not tested out of sample"]
    if t.trades < min_oos_trades:
        why.append(f"only {t.trades} out-of-sample trades (need {min_oos_trades})")
    if t.e < champ_test.e + min_improvement_r:
        why.append(f"OOS expectancy {t.e:.3f}R not ≥ champion {champ_test.e:.3f}R + {min_improvement_r}R")
    if not keeps_user_rules(t, champ_test, min_trade_ratio):
        why.append("OOS win rate or trade count below the champion")
    return not why, why


def explain(diff: dict[str, D], champ_train: Perf, c: Candidate, champ_test: Perf) -> str:
    k, v = next(iter(diff.items()))
    t = c.test or c.train
    return (
        f"Change {k} to {v}. Older sessions: {c.train.trades} trades, win {c.train.win_rate:.0%}, "
        f"{c.train.e:+.3f}R/trade (champion {champ_train.trades}, {champ_train.win_rate:.0%}, {champ_train.e:+.3f}R). "
        f"Newer unseen sessions: {t.trades} trades, win {t.win_rate:.0%}, {t.e:+.3f}R/trade "
        f"(champion {champ_test.trades}, {champ_test.win_rate:.0%}, {champ_test.e:+.3f}R)."
    )
