"""Mean Reversion agent — Bollinger Band + RSI contrarian strategy."""

from typing import List, Dict
from collections import deque
import math
from .base_agent import BaseAgent
from ..market.order import Order, OrderSide, OrderType


class MeanReversionAgent(BaseAgent):
    """
    Buys when price touches the lower Bollinger Band with RSI < 30.
    Sells when price touches the upper Bollinger Band with RSI > 70.
    Exits when price returns to the moving average.
    """

    def __init__(
        self,
        agent_id: str,
        initial_capital: float = 3_000_000.0,
        lookback: int = 30,
        num_std: float = 2.0,
        rsi_period: int = 14,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        position_limit: int = 2000,
        order_size: int = 150,
    ) -> None:
        super().__init__(agent_id, "MeanReversion", initial_capital, latency_seconds=0.002)
        self.lookback = lookback
        self.num_std = num_std
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.position_limit = position_limit
        self.order_size = order_size
        self._price_history: deque = deque(maxlen=max(lookback, rsi_period + 1) + 10)

    def _compute_rsi(self, prices: List[float]) -> float:
        """Compute RSI from a price series."""
        if len(prices) < self.rsi_period + 1:
            return 50.0  # neutral default

        changes = [prices[i] - prices[i - 1] for i in range(-self.rsi_period, 0)]
        gains = [c for c in changes if c > 0]
        losses = [-c for c in changes if c < 0]

        avg_gain = sum(gains) / self.rsi_period if gains else 0.0
        avg_loss = sum(losses) / self.rsi_period if losses else 0.0

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def decide_action(self, market_state: Dict) -> List[Order]:
        price = market_state.get("mid_price") or market_state.get("current_price", 100.0)
        self._price_history.append(price)
        orders: List[Order] = []

        if len(self._price_history) < self.lookback:
            return orders

        prices = list(self._price_history)

        # Bollinger Bands
        window = prices[-self.lookback:]
        sma = sum(window) / len(window)
        variance = sum((p - sma) ** 2 for p in window) / len(window)
        std = math.sqrt(variance) if variance > 0 else 0.0

        upper_band = sma + self.num_std * std
        lower_band = sma - self.num_std * std

        # RSI
        rsi = self._compute_rsi(prices)

        # ── Manage existing position: exit at mean ──────────────────────
        if self.position > 0:
            # Long position: exit when price returns to SMA
            if price >= sma:
                orders.append(
                    Order(
                        agent_id=self.agent_id,
                        side=OrderSide.SELL,
                        order_type=OrderType.MARKET,
                        price=price,
                        quantity=abs(self.position),
                    )
                )
                return orders

        elif self.position < 0:
            # Short position: exit when price returns to SMA
            if price <= sma:
                orders.append(
                    Order(
                        agent_id=self.agent_id,
                        side=OrderSide.BUY,
                        order_type=OrderType.MARKET,
                        price=price,
                        quantity=abs(self.position),
                    )
                )
                return orders

        # ── Entry signals (only if flat) ────────────────────────────────
        if self.position == 0 and std > 0:
            # Buy at lower band with oversold RSI
            if price <= lower_band and rsi < self.rsi_oversold:
                qty = min(self.order_size, self.position_limit)
                orders.append(
                    Order(
                        agent_id=self.agent_id,
                        side=OrderSide.BUY,
                        order_type=OrderType.LIMIT,
                        price=round(price + 0.01, 2),
                        quantity=qty,
                    )
                )

            # Sell at upper band with overbought RSI
            elif price >= upper_band and rsi > self.rsi_overbought:
                qty = min(self.order_size, self.position_limit)
                orders.append(
                    Order(
                        agent_id=self.agent_id,
                        side=OrderSide.SELL,
                        order_type=OrderType.LIMIT,
                        price=round(price - 0.01, 2),
                        quantity=qty,
                    )
                )

        return orders

    def reset(self) -> None:
        super().reset()
        self._price_history.clear()

    def consume_cancellations(self) -> List[str]:
        return self.cancel_all_active_orders()
