from __future__ import annotations

from dataclasses import dataclass

from quanttool.data import Bar
from quanttool.indicators import simple_moving_average


@dataclass(frozen=True)
class Signal:
    date_index: int
    action: str
    reason: str


class Strategy:
    name = "base"

    def generate(self, bars: list[Bar]) -> list[Signal]:
        raise NotImplementedError


@dataclass
class MovingAverageCrossStrategy(Strategy):
    fast_window: int = 10
    slow_window: int = 30
    name: str = "moving_average_cross"

    def generate(self, bars: list[Bar]) -> list[Signal]:
        if self.fast_window >= self.slow_window:
            raise ValueError("fast_window must be smaller than slow_window")

        closes = [bar.close for bar in bars]
        fast = simple_moving_average(closes, self.fast_window)
        slow = simple_moving_average(closes, self.slow_window)

        signals: list[Signal] = []
        for index in range(1, len(bars)):
            if fast[index - 1] is None or slow[index - 1] is None:
                continue
            if fast[index] is None or slow[index] is None:
                continue

            crossed_up = fast[index - 1] <= slow[index - 1] and fast[index] > slow[index]
            crossed_down = fast[index - 1] >= slow[index - 1] and fast[index] < slow[index]

            if crossed_up:
                signals.append(Signal(index, "buy", "fast SMA crossed above slow SMA"))
            elif crossed_down:
                signals.append(Signal(index, "sell", "fast SMA crossed below slow SMA"))

        return signals
