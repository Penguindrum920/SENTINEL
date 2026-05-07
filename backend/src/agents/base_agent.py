"""Abstract base agent for the SENTINEL market simulator."""

from abc import ABC, abstractmethod
from typing import List, Dict
import math
from ..market.order import Order
from ..market.trade import Trade


class BaseAgent(ABC):
    """
    Abstract base class for all trading agents.

    Every agent has capital, a position, and tracks its own PnL.
    Subclasses must implement decide_action() to produce orders
    based on the current market state.
    """

    def __init__(
        self,
        agent_id: str,
        agent_type: str,
        initial_capital: float = 100_000.0,
        latency_seconds: float = 0.0,
    ) -> None:
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.cash = initial_capital
        self.latency_seconds = latency_seconds

        # Position tracking
        self.position: int = 0  # net shares held (positive=long, negative=short)
        self.avg_entry_price: float = 0.0
        self.realized_pnl: float = 0.0
        self.num_trades: int = 0
        self._trade_returns: List[float] = []
        self.active_orders: Dict[str, Order] = {}

    @abstractmethod
    def decide_action(self, market_state: Dict) -> List[Order]:
        """
        Given the current market state, return a list of orders to submit.
        Must be implemented by every agent subclass.
        """
        ...

    def consume_cancellations(self) -> List[str]:
        """Return any outstanding order IDs the simulator should cancel."""
        return []

    def cancel_all_active_orders(self) -> List[str]:
        """Cancel and clear any currently tracked resting orders."""
        order_ids = list(self.active_orders.keys())
        self.active_orders.clear()
        return order_ids

    def update_position(self, trade: Trade) -> None:
        """Update position and PnL after a trade fills."""
        if trade.buyer_agent_id == self.agent_id:
            self._apply_fill(trade.quantity, trade.price, is_buy=True)
        elif trade.seller_agent_id == self.agent_id:
            self._apply_fill(trade.quantity, trade.price, is_buy=False)
        self.num_trades += 1

    def _apply_fill(self, quantity: int, price: float, is_buy: bool) -> None:
        """Apply a fill to the position, tracking average entry and realized PnL."""
        if not math.isfinite(price):
            return

        direction = 1 if is_buy else -1
        new_qty = direction * quantity
        cash_delta = price * quantity

        if is_buy:
            self.cash -= cash_delta
        else:
            self.cash += cash_delta

        if (self.position >= 0 and is_buy) or (self.position <= 0 and not is_buy):
            # Adding to position: update average entry
            total_cost = self.avg_entry_price * abs(self.position) + price * quantity
            self.position += new_qty
            if self.position != 0:
                self.avg_entry_price = total_cost / abs(self.position)
        else:
            # Reducing or flipping position: realize PnL
            close_qty = min(quantity, abs(self.position))
            if is_buy:
                pnl = (self.avg_entry_price - price) * close_qty  # closing short
            else:
                pnl = (price - self.avg_entry_price) * close_qty  # closing long
            self.realized_pnl += pnl
            self._trade_returns.append(pnl)
            self.position += new_qty

            # If flipped, the remainder is a new position at the trade price
            if abs(new_qty) > close_qty:
                self.avg_entry_price = price

    def reset(self) -> None:
        """Reset mutable state for a fresh simulation episode."""
        self.capital = self.initial_capital
        self.cash = self.initial_capital
        self.position = 0
        self.avg_entry_price = 0.0
        self.realized_pnl = 0.0
        self.num_trades = 0
        self._trade_returns.clear()
        self.active_orders.clear()

    def get_unrealized_pnl(self, current_price: float) -> float:
        """Mark-to-market unrealized PnL."""
        if self.position == 0:
            return 0.0
        if not math.isfinite(current_price) or not math.isfinite(self.avg_entry_price):
            return 0.0
        return (current_price - self.avg_entry_price) * self.position

    def get_metrics(self, current_price: float = 0.0) -> Dict:
        """Return agent performance metrics."""
        realized = self.realized_pnl if math.isfinite(self.realized_pnl) else 0.0
        unrealized = self.get_unrealized_pnl(current_price)
        if not math.isfinite(unrealized):
            unrealized = 0.0
        total_pnl = realized + unrealized
        if not math.isfinite(total_pnl):
            total_pnl = 0.0
        return_pct = (total_pnl / self.initial_capital) * 100 if self.initial_capital else 0.0
        sharpe = self._compute_sharpe()
        if not math.isfinite(return_pct):
            return_pct = 0.0
        if not math.isfinite(sharpe):
            sharpe = 0.0

        return {
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "position": self.position,
            "total_pnl": round(total_pnl, 2),
            "realized_pnl": round(realized, 2),
            "unrealized_pnl": round(unrealized, 2),
            "return_pct": round(return_pct, 4),
            "sharpe_ratio": round(sharpe, 4),
            "num_trades": self.num_trades,
        }

    def _compute_sharpe(self) -> float:
        """Compute Sharpe ratio from trade returns."""
        returns = [value for value in self._trade_returns if math.isfinite(value)]
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        std = math.sqrt(variance) if variance > 0 else 0.0
        if std == 0:
            return 0.0
        return (mean / std) * math.sqrt(252)  # annualized

    def __repr__(self) -> str:
        return f"{self.agent_type}({self.agent_id}, pos={self.position}, pnl={self.realized_pnl:.2f})"
