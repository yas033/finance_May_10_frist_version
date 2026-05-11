from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskConfig:
    position_pct: float = 0.95
    stop_loss_pct: float | None = 0.08

    def __post_init__(self) -> None:
        if not 0 < self.position_pct <= 1:
            raise ValueError("position_pct must be in (0, 1]")
        if self.stop_loss_pct is not None and not 0 < self.stop_loss_pct < 1:
            raise ValueError("stop_loss_pct must be in (0, 1)")


@dataclass
class PositionRiskState:
    entry_price: float | None = None

    def should_stop_out(self, low_price: float, config: RiskConfig) -> bool:
        if self.entry_price is None or config.stop_loss_pct is None:
            return False
        stop_price = self.entry_price * (1 - config.stop_loss_pct)
        return low_price <= stop_price
