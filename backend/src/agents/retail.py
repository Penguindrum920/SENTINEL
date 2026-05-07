"""Retail agent — trades on moving average crossover with stop-loss/take-profit."""

from typing import List, Dict
from collections import deque
from .base_agent import BaseAgent
from ..market.order import Order, OrderSide, OrderType


class RetailAgent(BaseAgent):
    """
    Uses 20/50 moving average crossover for entry signals.
    Manages risk with stop-loss and take-profit thresholds.
    """

    def __init__(
        self,
        agent_id: str,
        initial_capital: float = 50_000.0,
        stop_loss: float = 0.02,
        take_profit: float = 0.05,
        order_size: int = 50,
    ) -> None:
        super().__init__(agent_id, "Retail", initial_capital, latency_seconds=0.1)
        self.wakeup_interval = 2.0
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.order_size = order_size
        self._price_history: deque = deque(maxlen=60)
        self._entry_price: float = 0.0

    def decide_action(self, market_state: Dict) -> List[Order]:
        price = market_state.get("mid_price") or market_state.get("current_price", 100.0)
        self._price_history.append(price)
        orders: List[Order] = []

        if len(self._price_history) < 50:
            return orders

        prices = list(self._price_history)

        # Moving averages
        ma20 = sum(prices[-20:]) / 20
        ma50 = sum(prices[-50:]) / 50

        # Check stop-loss / take-profit on existing position
        if self.position != 0 and self._entry_price > 0:
            pnl_pct = (price - self._entry_price) / self._entry_price
            if self.position < 0:
                pnl_pct = -pnl_pct

            if pnl_pct <= -self.stop_loss or pnl_pct >= self.take_profit:
                # Close position
                side = OrderSide.SELL if self.position > 0 else OrderSide.BUY
                orders.append(
                    Order(
                        agent_id=self.agent_id,
                        side=side,
                        order_type=OrderType.MARKET,
                        price=price,
                        quantity=abs(self.position),
                    )
                )
                self._entry_price = 0.0
                return orders

        # MA crossover signals (only if no position)
        if self.position == 0:
            prev_ma20 = sum(prices[-21:-1]) / 20
            prev_ma50 = sum(prices[-51:-1]) / 50

            # Bullish crossover
            if prev_ma20 <= prev_ma50 and ma20 > ma50:
                orders.append(
                    Order(
                        agent_id=self.agent_id,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        price=price,
                        quantity=self.order_size,
                    )
                )
                self._entry_price = price

            # Bearish crossover
            elif prev_ma20 >= prev_ma50 and ma20 < ma50:
                orders.append(
                    Order(
                        agent_id=self.agent_id,
                        side=OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        price=price,
                        quantity=self.order_size,
                    )
                )
                self._entry_price = price

        return orders

    def reset(self) -> None:
        super().reset()
        self._price_history.clear()
        self._entry_price = 0.0
