"""Per-model state machine (§6): IDLE → SWEEP → CONFIRMED → ARMED → ENTERED → MANAGING → RESOLVED(...) → IDLE."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

State = Literal["IDLE", "SWEEP", "CONFIRMED", "ARMED", "ENTERED", "MANAGING", "RESOLVED"]
Resolution = Literal["TP", "STOP", "BE", "TRAIL", "TIME", "STRUCT", "MODEL_FAILED", "EXPIRED", "CANCELLED"]

ALLOWED: dict[str, set[str]] = {
    "IDLE": {"SWEEP", "CONFIRMED"},
    "SWEEP": {"CONFIRMED", "RESOLVED"},
    "CONFIRMED": {"ARMED", "RESOLVED"},
    "ARMED": {"ENTERED", "RESOLVED"},
    "ENTERED": {"MANAGING", "RESOLVED"},
    "MANAGING": {"RESOLVED"},
    "RESOLVED": {"IDLE"},
}


class IllegalTransition(Exception):
    pass


@dataclass
class ModelMachine:
    model_key: str
    state: State = "IDLE"
    resolution: Resolution | None = None
    log: list[tuple[int, str, str, str]] = field(default_factory=list)  # (time_ms, from, to, note)

    def to(self, new: State, at_ms: int, note: str = "", resolution: Resolution | None = None) -> None:
        if new not in ALLOWED[self.state]:
            raise IllegalTransition(f"{self.model_key}: {self.state} → {new}")
        if new == "RESOLVED":
            if resolution is None:
                raise IllegalTransition("RESOLVED needs a resolution")
            self.resolution = resolution
        self.log.append((at_ms, self.state, new, note or (resolution or "")))
        self.state = new

    @property
    def ever_entered(self) -> bool:
        return any(to == "ENTERED" for _, _, to, _ in self.log)
