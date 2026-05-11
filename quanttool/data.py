from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class Bar:
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


REQUIRED_COLUMNS = {"date", "open", "high", "low", "close", "volume"}


def load_csv(path: str | Path) -> list[Bar]:
    data_path = Path(path)
    if not data_path.exists():
        raise FileNotFoundError(f"CSV file not found: {data_path}")

    with data_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError("CSV file has no header row.")

        missing = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"CSV file is missing required columns: {missing_text}")

        bars = [
            Bar(
                date=date.fromisoformat(row["date"]),
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
            )
            for row in reader
        ]

    if len(bars) < 2:
        raise ValueError("CSV file needs at least two rows for a backtest.")

    return sorted(bars, key=lambda bar: bar.date)
