"""Sentiment agent — herding/contrarian based on simulated market sentiment."""

from typing import List, Dict
from collections import deque
import random
from .base_agent import BaseAgent
from ..market.order import Order, OrderSide, OrderType


class SentimentAgent(BaseAgent):
    """
    Simulates crowd-driven trading behaviour.
    In 'herding' mode (default 70%), follows the recent price trend.
    In 'contrarian' mode (30%), trades against it.
    Sentiment regime flips randomly with a small probability each step.
    """

    def __init__(
        self,
        agent_id: str,
        initial_capital: float = 500_000.0,
        lookback: int = 20,
        position_limit: int = 1000,
        order_size: int = 80,
        herding_probability: float = 0.70,
        regime_switch_prob: float = 0.02,
        action_probability: float = 0.15,
    ) -> None:
        super().__init__(agent_id, "Sentiment", initial_capital, latency_seconds=0.05)
        self.lookback = lookback
        self.position_limit = position_limit
        self.order_size = order_size
        self.herding_probability = herding_probability
        self.regime_switch_prob = regime_switch_prob
        self.action_probability = action_probability
        self._price_history: deque = deque(maxlen=lookback + 5)

        # Start in herding or contrarian mode randomly
        self._is_herding: bool = random.random() < herding_probability

    def decide_action(self, market_state: Dict) -> List[Order]:
        price = market_state.get("mid_price") or market_state.get("current_price", 100.0)
        self._price_history.append(price)
        orders: List[Order] = []

        if len(self._price_history) < self.lookback:
            return orders

        # ── Regime switching ────────────────────────────────────────────
        if random.random() < self.regime_switch_prob:
            self._is_herding = not self._is_herding

        # ── Only act with some probability (not every step) ─────────────
        if random.random() > self.action_probability:
            return orders

        # ── Determine recent trend ──────────────────────────────────────
        prices = list(self._price_history)
        recent_return = (prices[-1] - prices[-self.lookback]) / prices[-self.lookback]

        # Dead zone: no signal if trend is negligible
        if abs(recent_return) < 0.0005:
            return orders

        trend_is_up = recent_return > 0

        # ── Decide trade direction ──────────────────────────────────────
        if self._is_herding:
            # Follow the trend
            want_buy = trend_is_up
        else:
            # Go against the trend
            want_buy = not trend_is_up

        # ── Place order if within limits ────────────────────────────────
        if want_buy and self.position < self.position_limit:
            qty = min(self.order_size, self.position_limit - self.position)
            if qty > 0:
                orders.append(
                    Order(
                        agent_id=self.agent_id,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        price=price,
                        quantity=qty,
                    )
                )

        elif not want_buy and self.position > -self.position_limit:
            qty = min(self.order_size, self.position_limit + self.position)
            if qty > 0:
                orders.append(
                    Order(
                        agent_id=self.agent_id,
                        side=OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        price=price,
                        quantity=qty,
                    )
                )

        return orders

    def reset(self) -> None:
        super().reset()
        self._price_history.clear()
        self._is_herding = random.random() < self.herding_probability
