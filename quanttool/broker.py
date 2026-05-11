from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutionConfig:
    fee_bps: float = 1.0
    slippage_bps: float = 2.0

    @property
    def fee_rate(self) -> float:
        return self.fee_bps / 10_000

    @property
    def slippage_rate(self) -> float:
        return self.slippage_bps / 10_000


@dataclass(frozen=True)
class Fill:
    side: str
    quantity: int
    price: float
    fee: float


class PaperBroker:
    def __init__(self, config: ExecutionConfig) -> None:
        self.config = config

    def buy(self, cash: float, reference_price: float) -> Fill | None:
        price = reference_price * (1 + self.config.slippage_rate)
        quantity = int(cash / (price * (1 + self.config.fee_rate)))
        if quantity <= 0:
            return None
        fee = quantity * price * self.config.fee_rate
        return Fill("buy", quantity, price, fee)

    def sell(self, quantity: int, reference_price: float) -> Fill | None:
        if quantity <= 0:
            return None
        price = reference_price * (1 - self.config.slippage_rate)
        fee = quantity * price * self.config.fee_rate
        return Fill("sell", quantity, price, fee)
