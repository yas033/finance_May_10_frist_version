from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt

from quanttool.broker import ExecutionConfig, Fill, PaperBroker
from quanttool.data import Bar
from quanttool.risk import PositionRiskState, RiskConfig
from quanttool.strategies import Signal, Strategy


@dataclass(frozen=True)
class Trade:
    date: str
    side: str
    quantity: int
    price: float
    fee: float
    reason: str


@dataclass
class BacktestResult:
    starting_cash: float
    ending_equity: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe: float
    win_rate: float
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[tuple[str, float]] = field(default_factory=list)


class Backtester:
    def __init__(
        self,
        strategy: Strategy,
        starting_cash: float = 100_000,
        risk: RiskConfig | None = None,
        execution: ExecutionConfig | None = None,
    ) -> None:
        if starting_cash <= 0:
            raise ValueError("starting_cash must be positive")

        self.strategy = strategy
        self.starting_cash = starting_cash
        self.risk = risk or RiskConfig()
        self.broker = PaperBroker(execution or ExecutionConfig())

    def run(self, bars: list[Bar]) -> BacktestResult:
        signals = {signal.date_index: signal for signal in self.strategy.generate(bars)}
        cash = self.starting_cash
        shares = 0
        risk_state = PositionRiskState()
        trades: list[Trade] = []
        equity_curve: list[tuple[str, float]] = []
        closed_trade_returns: list[float] = []

        for index, bar in enumerate(bars):
            if shares > 0 and risk_state.should_stop_out(bar.low, self.risk):
                stop_price = risk_state.entry_price * (1 - self.risk.stop_loss_pct)  # type: ignore[operator]
                fill = self.broker.sell(shares, stop_price)
                if fill is not None:
                    cash, shares = self._apply_sell(cash, shares, fill)
                    trades.append(_trade(bar, fill, "stop loss"))
                    closed_trade_returns.append(_trade_return(risk_state.entry_price, fill.price))
                    risk_state.entry_price = None

            signal = signals.get(index)
            if signal is not None:
                if signal.action == "buy" and shares == 0:
                    fill = self.broker.buy(cash * self.risk.position_pct, bar.close)
                    if fill is not None:
                        cash, shares = self._apply_buy(cash, shares, fill)
                        trades.append(_trade(bar, fill, signal.reason))
                        risk_state.entry_price = fill.price
                elif signal.action == "sell" and shares > 0:
                    fill = self.broker.sell(shares, bar.close)
                    if fill is not None:
                        cash, shares = self._apply_sell(cash, shares, fill)
                        trades.append(_trade(bar, fill, signal.reason))
                        closed_trade_returns.append(_trade_return(risk_state.entry_price, fill.price))
                        risk_state.entry_price = None

            equity_curve.append((bar.date.isoformat(), cash + shares * bar.close))

        if shares > 0:
            last_bar = bars[-1]
            fill = self.broker.sell(shares, last_bar.close)
            if fill is not None:
                cash, shares = self._apply_sell(cash, shares, fill)
                trades.append(_trade(last_bar, fill, "final liquidation"))
                closed_trade_returns.append(_trade_return(risk_state.entry_price, fill.price))
                equity_curve[-1] = (last_bar.date.isoformat(), cash)

        return _build_result(self.starting_cash, equity_curve, trades, closed_trade_returns)

    @staticmethod
    def _apply_buy(cash: float, shares: int, fill: Fill) -> tuple[float, int]:
        cash -= fill.quantity * fill.price + fill.fee
        shares += fill.quantity
        return cash, shares

    @staticmethod
    def _apply_sell(cash: float, shares: int, fill: Fill) -> tuple[float, int]:
        cash += fill.quantity * fill.price - fill.fee
        shares -= fill.quantity
        return cash, shares


def _trade(bar: Bar, fill: Fill, reason: str) -> Trade:
    return Trade(
        date=bar.date.isoformat(),
        side=fill.side,
        quantity=fill.quantity,
        price=fill.price,
        fee=fill.fee,
        reason=reason,
    )


def _trade_return(entry_price: float | None, exit_price: float) -> float:
    if entry_price is None:
        return 0.0
    return exit_price / entry_price - 1


def _build_result(
    starting_cash: float,
    equity_curve: list[tuple[str, float]],
    trades: list[Trade],
    closed_trade_returns: list[float],
) -> BacktestResult:
    ending_equity = equity_curve[-1][1]
    total_return = ending_equity / starting_cash - 1
    annualized_return = _annualized_return(total_return, len(equity_curve))
    returns = _daily_returns(equity_curve)

    return BacktestResult(
        starting_cash=starting_cash,
        ending_equity=ending_equity,
        total_return=total_return,
        annualized_return=annualized_return,
        max_drawdown=_max_drawdown(equity_curve),
        sharpe=_sharpe(returns),
        win_rate=_win_rate(closed_trade_returns),
        trades=trades,
        equity_curve=equity_curve,
    )


def _daily_returns(equity_curve: list[tuple[str, float]]) -> list[float]:
    returns = []
    for previous, current in zip(equity_curve, equity_curve[1:]):
        if previous[1] > 0:
            returns.append(current[1] / previous[1] - 1)
    return returns


def _annualized_return(total_return: float, trading_days: int) -> float:
    if trading_days <= 0:
        return 0.0
    return (1 + total_return) ** (252 / trading_days) - 1


def _max_drawdown(equity_curve: list[tuple[str, float]]) -> float:
    peak = equity_curve[0][1]
    max_dd = 0.0
    for _, equity in equity_curve:
        peak = max(peak, equity)
        if peak > 0:
            max_dd = min(max_dd, equity / peak - 1)
    return max_dd


def _sharpe(returns: list[float]) -> float:
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    variance = sum((value - mean) ** 2 for value in returns) / (len(returns) - 1)
    if variance == 0:
        return 0.0
    return mean / sqrt(variance) * sqrt(252)


def _win_rate(trade_returns: list[float]) -> float:
    if not trade_returns:
        return 0.0
    wins = sum(1 for value in trade_returns if value > 0)
    return wins / len(trade_returns)
