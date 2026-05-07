"""Momentum agent — trend-following with breakout channels and trailing stop."""

from typing import List, Dict
from collections import deque
from .base_agent import BaseAgent
from ..market.order import Order, OrderSide, OrderType


class MomentumAgent(BaseAgent):
    """
    Tracks an N-bar high/low price channel.
    Enters long on breakout above the channel high, short below channel low.
    Exits on a trailing stop or when price re-enters the channel.
    """

    def __init__(
        self,
        agent_id: str,
        initial_capital: float = 2_000_000.0,
        channel_length: int = 50,
        position_limit: int = 3000,
        trailing_stop_pct: float = 0.015,
        order_size: int = 200,
    ) -> None:
        super().__init__(agent_id, "Momentum", initial_capital, latency_seconds=0.005)
        self.channel_length = channel_length
        self.position_limit = position_limit
        self.trailing_stop_pct = trailing_stop_pct
        self.order_size = order_size
        self._price_history: deque = deque(maxlen=channel_length + 1)
        self._peak_price: float = 0.0  # tracks high-water mark for trailing stop
        self._trough_price: float = float("inf")  # tracks low-water mark for short trailing stop

    def decide_action(self, market_state: Dict) -> List[Order]:
        price = market_state.get("mid_price") or market_state.get("current_price", 100.0)
        self._price_history.append(price)
        orders: List[Order] = []

        if len(self._price_history) < self.channel_length:
            return orders

        prices = list(self._price_history)
        channel_high = max(prices[:-1])  # high of previous N bars
        channel_low = min(prices[:-1])   # low of previous N bars

        # ── Manage existing position ────────────────────────────────────
        if self.position > 0:
            # Update peak for trailing stop
            self._peak_price = max(self._peak_price, price)
            drawdown = (self._peak_price - price) / self._peak_price

            # Exit: trailing stop hit OR price fell back inside channel
            if drawdown >= self.trailing_stop_pct or price < channel_high:
                orders.append(
                    Order(
                        agent_id=self.agent_id,
                        side=OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        price=price,
                        quantity=abs(self.position),
                    )
                )
                self._peak_price = 0.0
                return orders

        elif self.position < 0:
            # Update trough for trailing stop
            self._trough_price = min(self._trough_price, price)
            rally = (price - self._trough_price) / self._trough_price if self._trough_price > 0 else 0

            # Exit: trailing stop hit OR price rose back inside channel
            if rally >= self.trailing_stop_pct or price > channel_low:
                orders.append(
                    Order(
                        agent_id=self.agent_id,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        price=price,
                        quantity=abs(self.position),
                    )
                )
                self._trough_price = float("inf")
                return orders

        # ── Entry signals (only if flat) ────────────────────────────────
        if self.position == 0:
            # Breakout above channel high → go long
            if price > channel_high:
                qty = min(self.order_size, self.position_limit)
                orders.append(
                    Order(
                        agent_id=self.agent_id,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        price=price,
                        quantity=qty,
                    )
                )
                self._peak_price = price

            # Breakout below channel low → go short
            elif price < channel_low:
                qty = min(self.order_size, self.position_limit)
                orders.append(
                    Order(
                        agent_id=self.agent_id,
                        side=OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        price=price,
                        quantity=qty,
                    )
                )
                self._trough_price = price

        return orders

    def reset(self) -> None:
        super().reset()
        self._price_history.clear()
        self._peak_price = 0.0
        self._trough_price = float("inf")
