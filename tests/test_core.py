from pathlib import Path
import unittest

from quanttool.backtest import Backtester
from quanttool.data import load_csv
from quanttool.indicators import simple_moving_average
from quanttool.risk import RiskConfig
from quanttool.strategies import MovingAverageCrossStrategy


ROOT = Path(__file__).resolve().parents[1]


class CoreTests(unittest.TestCase):
    def test_simple_moving_average(self) -> None:
        self.assertEqual(
            simple_moving_average([1, 2, 3, 4], 3),
            [None, None, 2.0, 3.0],
        )

    def test_load_csv(self) -> None:
        bars = load_csv(ROOT / "examples" / "sample_aapl.csv")
        self.assertGreater(len(bars), 2)
        self.assertLess(bars[0].date, bars[-1].date)

    def test_backtest_runs_and_records_trades(self) -> None:
        bars = load_csv(ROOT / "examples" / "sample_aapl.csv")
        strategy = MovingAverageCrossStrategy(fast_window=5, slow_window=20)
        result = Backtester(strategy, risk=RiskConfig(position_pct=0.95)).run(bars)

        self.assertGreater(result.ending_equity, 0)
        self.assertGreaterEqual(len(result.equity_curve), len(bars))
        self.assertGreaterEqual(len(result.trades), 1)


if __name__ == "__main__":
    unittest.main()
