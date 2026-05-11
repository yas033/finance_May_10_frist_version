from __future__ import annotations

import argparse

from quanttool.backtest import Backtester, BacktestResult
from quanttool.broker import ExecutionConfig
from quanttool.data import load_csv
from quanttool.risk import RiskConfig
from quanttool.strategies import MovingAverageCrossStrategy


def main() -> None:
    parser = argparse.ArgumentParser(prog="quanttool")
    subparsers = parser.add_subparsers(dest="command", required=True)

    backtest = subparsers.add_parser("backtest", help="Run a moving-average backtest from CSV data.")
    backtest.add_argument("--data", required=True, help="Path to CSV data.")
    backtest.add_argument("--cash", type=float, default=100_000, help="Starting cash.")
    backtest.add_argument("--fast", type=int, default=10, help="Fast SMA window.")
    backtest.add_argument("--slow", type=int, default=30, help="Slow SMA window.")
    backtest.add_argument("--position-pct", type=float, default=0.95, help="Max cash allocation per entry.")
    backtest.add_argument("--stop-loss-pct", type=float, default=0.08, help="Stop loss percentage.")
    backtest.add_argument("--fee-bps", type=float, default=1.0, help="Commission in basis points.")
    backtest.add_argument("--slippage-bps", type=float, default=2.0, help="Slippage in basis points.")
    backtest.add_argument("--show-trades", action="store_true", help="Print executed trades.")

    args = parser.parse_args()
    if args.command == "backtest":
        result = run_backtest(args)
        print_result(result, show_trades=args.show_trades)


def run_backtest(args: argparse.Namespace) -> BacktestResult:
    bars = load_csv(args.data)
    strategy = MovingAverageCrossStrategy(fast_window=args.fast, slow_window=args.slow)
    risk = RiskConfig(position_pct=args.position_pct, stop_loss_pct=args.stop_loss_pct)
    execution = ExecutionConfig(fee_bps=args.fee_bps, slippage_bps=args.slippage_bps)
    return Backtester(strategy, args.cash, risk, execution).run(bars)


def print_result(result: BacktestResult, show_trades: bool = False) -> None:
    print("Backtest result")
    print(f"Starting cash:     ${result.starting_cash:,.2f}")
    print(f"Ending equity:     ${result.ending_equity:,.2f}")
    print(f"Total return:      {result.total_return:.2%}")
    print(f"Annualized return: {result.annualized_return:.2%}")
    print(f"Max drawdown:      {result.max_drawdown:.2%}")
    print(f"Sharpe ratio:      {result.sharpe:.2f}")
    print(f"Win rate:          {result.win_rate:.2%}")
    print(f"Trades:            {len(result.trades)}")

    if show_trades:
        print()
        print("Trades")
        for trade in result.trades:
            print(
                f"{trade.date} {trade.side.upper():4} "
                f"{trade.quantity:5d} @ {trade.price:8.2f} "
                f"fee={trade.fee:7.2f} reason={trade.reason}"
            )


if __name__ == "__main__":
    main()
