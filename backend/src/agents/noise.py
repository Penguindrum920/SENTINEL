"""Noise agent — generates random orders at a configurable rate."""

from typing import List, Dict
import random
from .base_agent import BaseAgent
from ..market.order import Order, OrderSide, OrderType


class NoiseAgent(BaseAgent):
    """
    Submits random orders to provide background liquidity / noise.
    50% market orders, 50% limit orders, random sizes between min/max.
    """

    def __init__(
        self,
        agent_id: str,
        initial_capital: float = 20_000.0,
        order_rate: float = 0.1,
        min_size: int = 10,
        max_size: int = 200,
    ) -> None:
        super().__init__(agent_id, "Noise", initial_capital, latency_seconds=0.05)
        self.wakeup_interval = 1.0
        self.order_rate = order_rate
        self.min_size = min_size
        self.max_size = max_size

    def decide_action(self, market_state: Dict) -> List[Order]:
        price = market_state.get("mid_price") or market_state.get("current_price", 100.0)
        orders: List[Order] = []

        if random.random() > self.order_rate:
            return orders

        side = random.choice([OrderSide.BUY, OrderSide.SELL])
        size = random.randint(self.min_size, self.max_size)

        # 50% market, 50% limit
        if random.random() < 0.5:
            orders.append(
                Order(
                    agent_id=self.agent_id,
                    side=side,
                    order_type=OrderType.MARKET,
                    price=price,
                    quantity=size,
                )
            )
        else:
            # Limit order within 0.5% of mid price
            offset = price * random.uniform(0.001, 0.005)
            limit_price = round(
                price - offset if side == OrderSide.BUY else price + offset, 2
            )
            orders.append(
                Order(
                    agent_id=self.agent_id,
                    side=side,
                    order_type=OrderType.LIMIT,
                    price=limit_price,
                    quantity=size,
                )
            )

        return orders
