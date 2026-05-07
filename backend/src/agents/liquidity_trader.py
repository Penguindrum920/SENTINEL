"""Liquidity trader agent — executes exogenous buy/sell pressure via sliced orders."""

from typing import List, Dict
import random
from .base_agent import BaseAgent
from ..market.order import Order, OrderSide, OrderType


class LiquidityTraderAgent(BaseAgent):
    """
    Represents a non-strategic liquidity demander/supplier.

    Behavior:
    - Starts a parent order intermittently (buy or sell exogenous need).
    - Splits parent order into smaller child slices over time.
    - Uses a mix of market and near-touch limit orders.
    """

    def __init__(
        self,
        agent_id: str,
        initial_capital: float = 2_000_000.0,
        wakeup_interval: float = 1.5,
        start_probability: float = 0.02,
        min_parent_qty: int = 2_000,
        max_parent_qty: int = 10_000,
        min_child_qty: int = 50,
        max_child_qty: int = 300,
    ) -> None:
        super().__init__(agent_id, "LiquidityTrader", initial_capital, latency_seconds=0.02)
        self.wakeup_interval = wakeup_interval
        self.start_probability = start_probability
        self.min_parent_qty = min_parent_qty
        self.max_parent_qty = max_parent_qty
        self.min_child_qty = min_child_qty
        self.max_child_qty = max_child_qty

        self._active_side: OrderSide | None = None
        self._remaining_parent_qty: int = 0

    def decide_action(self, market_state: Dict) -> List[Order]:
        orders: List[Order] = []
        mid = market_state.get("mid_price") or market_state.get("current_price", 100.0)

        if self._remaining_parent_qty <= 0:
            if random.random() < self.start_probability:
                self._active_side = random.choice([OrderSide.BUY, OrderSide.SELL])
                self._remaining_parent_qty = random.randint(self.min_parent_qty, self.max_parent_qty)
            return orders

        child_qty = min(
            self._remaining_parent_qty,
            random.randint(self.min_child_qty, self.max_child_qty),
        )
        self._remaining_parent_qty -= child_qty

        # More aggressive when spread is tight, otherwise lean to passive near-touch limits.
        spread = market_state.get("spread", 0.05)
        use_market = random.random() < (0.55 if spread <= 0.08 else 0.35)

        if use_market:
            orders.append(
                Order(
                    agent_id=self.agent_id,
                    side=self._active_side,
                    order_type=OrderType.MARKET,
                    price=mid,
                    quantity=child_qty,
                )
            )
        else:
            tick = 0.01
            px = mid - tick if self._active_side == OrderSide.BUY else mid + tick
            orders.append(
                Order(
                    agent_id=self.agent_id,
                    side=self._active_side,
                    order_type=OrderType.LIMIT,
                    price=round(px, 2),
                    quantity=child_qty,
                )
            )

        return orders

    def reset(self) -> None:
        super().reset()
        self._active_side = None
        self._remaining_parent_qty = 0

    def consume_cancellations(self) -> List[str]:
        return self.cancel_all_active_orders()
