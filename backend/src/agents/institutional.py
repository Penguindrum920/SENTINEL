"""Institutional agent — executes large orders via TWAP over a time window."""

from typing import List, Dict
from .base_agent import BaseAgent
from ..market.order import Order, OrderSide, OrderType
import random


class InstitutionalAgent(BaseAgent):
    """
    Executes a large order using TWAP (Time-Weighted Average Price) slicing.
    Splits the target quantity into intervals over the execution window.
    """

    def __init__(
        self,
        agent_id: str,
        initial_capital: float = 100_000_000.0,
        target_quantity: int = 50_000,
        execution_window: int = 3600,
        slice_interval: int = 60,
        max_slice_size: int = 1000,
    ) -> None:
        super().__init__(agent_id, "Institutional", initial_capital, latency_seconds=0.01)
        self.target_quantity = target_quantity
        self.execution_window = execution_window
        self.slice_interval = slice_interval
        self.max_slice_size = max_slice_size
        self.executed_quantity: int = 0
        self.side: OrderSide = random.choice([OrderSide.BUY, OrderSide.SELL])
        self._last_slice_time: float = 0.0
        self._started: bool = False

    def decide_action(self, market_state: Dict) -> List[Order]:
        current_time = market_state.get("current_time", 0.0)
        price = market_state.get("mid_price") or market_state.get("current_price", 100.0)
        orders: List[Order] = []

        # Already done
        if self.executed_quantity >= self.target_quantity:
            return orders

        # Start execution at a random point in the session
        if not self._started:
            if random.random() < 0.01:  # ~1% chance per step to start
                self._started = True
                self._last_slice_time = current_time
            return orders

        # TWAP: slice at regular intervals
        elapsed_since_slice = current_time - self._last_slice_time
        if elapsed_since_slice >= self.slice_interval:
            remaining = self.target_quantity - self.executed_quantity
            num_remaining_slices = max(
                1,
                int((self.execution_window - (current_time - self._last_slice_time))
                    / self.slice_interval),
            )
            slice_size = min(
                remaining,
                self.max_slice_size,
                remaining // num_remaining_slices + 1,
            )
            if slice_size > 0:
                orders.append(
                    Order(
                        agent_id=self.agent_id,
                        side=self.side,
                        order_type=OrderType.LIMIT,
                        price=round(
                            price * (1.001 if self.side == OrderSide.BUY else 0.999), 2
                        ),
                        quantity=slice_size,
                    )
                )
                self._last_slice_time = current_time

        return orders

    def update_position(self, trade) -> None:
        super().update_position(trade)
        self.executed_quantity = abs(self.position)

    def reset(self) -> None:
        super().reset()
        self.executed_quantity = 0
        self.side = random.choice([OrderSide.BUY, OrderSide.SELL])
        self._last_slice_time = 0.0
        self._started = False

    def consume_cancellations(self) -> List[str]:
        return self.cancel_all_active_orders()
