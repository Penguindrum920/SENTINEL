"""Market Maker agent — provides liquidity via bid/ask quotes with inventory skew."""

from typing import List, Dict
from .base_agent import BaseAgent
from ..market.order import Order, OrderSide, OrderType


class MarketMakerAgent(BaseAgent):
    """
    Continuously quotes bid and ask around mid-price.
    Skews quotes proportionally to inventory to manage risk.
    Halves quote size at 50% max inventory, stops quoting at 90%.
    Flattens position near market close.
    """

    def __init__(
        self,
        agent_id: str,
        initial_capital: float = 1_000_000.0,
        base_spread: float = 0.001,
        quote_size: int = 100,
        max_inventory: int = 5000,
    ) -> None:
        super().__init__(agent_id, "MarketMaker", initial_capital, latency_seconds=0.001)
        self.base_spread = base_spread
        self.quote_size = quote_size
        self.max_inventory = max_inventory

    def decide_action(self, market_state: Dict) -> List[Order]:
        mid = market_state.get("mid_price") or market_state.get("current_price", 100.0)
        time_to_close = market_state.get("time_to_close", float("inf"))
        orders: List[Order] = []

        # Flatten near close
        if time_to_close < 600 and self.position != 0:
            side = OrderSide.SELL if self.position > 0 else OrderSide.BUY
            orders.append(
                Order(
                    agent_id=self.agent_id,
                    side=side,
                    order_type=OrderType.MARKET,
                    price=mid,
                    quantity=abs(self.position),
                )
            )
            return orders

        # Inventory ratio determines quoting behaviour
        inv_ratio = abs(self.position) / self.max_inventory if self.max_inventory else 0

        # Stop quoting at 90% capacity
        if inv_ratio >= 0.9:
            return orders

        # Determine quote size
        size = self.quote_size
        if inv_ratio > 0.5:
            size = self.quote_size // 2

        # Inventory skew: shift quotes away from the side we're overweight on
        skew = (self.position / self.max_inventory) * self.base_spread * mid
        half_spread = (self.base_spread * mid) / 2

        bid_price = round(mid - half_spread - skew, 2)
        ask_price = round(mid + half_spread - skew, 2)

        orders.append(
            Order(
                agent_id=self.agent_id,
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=bid_price,
                quantity=size,
            )
        )
        orders.append(
            Order(
                agent_id=self.agent_id,
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                price=ask_price,
                quantity=size,
            )
        )
        return orders

    def consume_cancellations(self) -> List[str]:
        return self.cancel_all_active_orders()
