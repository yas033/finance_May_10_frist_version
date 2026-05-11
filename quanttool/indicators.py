from __future__ import annotations


def simple_moving_average(values: list[float], window: int) -> list[float | None]:
    if window <= 0:
        raise ValueError("window must be positive")

    averages: list[float | None] = []
    rolling_sum = 0.0
    for index, value in enumerate(values):
        rolling_sum += value
        if index >= window:
            rolling_sum -= values[index - window]

        if index + 1 < window:
            averages.append(None)
        else:
            averages.append(rolling_sum / window)
    return averages
