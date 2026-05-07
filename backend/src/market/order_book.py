"""Order book with price-time priority matching engine."""

from typing import List, Optional, Dict
from .order import Order, OrderSide, OrderType, OrderStatus
from .trade import Trade
from ..utils.logger import get_logger

logger = get_logger("order_book")


class OrderBook:
    """
    Limit order book with price-time priority matching.

    Bids are sorted descending by price (best bid first).
    Asks are sorted ascending by price (best ask first).
    Within the same price level, earlier orders have priority.
    """

    def __init__(self) -> None:
        self.bids: List[Order] = []
        self.asks: List[Order] = []
        self.trades: List[Trade] = []
        self._trade_count: int = 0

    def add_order(self, order: Order) -> List[Trade]:
        """Add an order to the book. Returns list of trades if matched."""
        if order.order_type == OrderType.MARKET:
            return self._match_market_order(order)
        else:
            return self._match_limit_order(order)

    def _match_market_order(self, order: Order) -> List[Trade]:
        """Match a market order against the opposite side."""
        trades: List[Trade] = []
        book = self.asks if order.side == OrderSide.BUY else self.bids

        while order.remaining_quantity > 0 and book:
            best = book[0]
            fill_qty = min(order.remaining_quantity, best.remaining_quantity)
            if order.side == OrderSide.BUY:
                trade = self._create_trade(order, best, best.price, fill_qty)
            else:
                trade = self._create_trade(best, order, best.price, fill_qty)
            trades.append(trade)

            if best.is_filled:
                book.pop(0)

        if order.remaining_quantity > 0:
            order.status = OrderStatus.CANCELLED  # unfilled market order remainder

        return trades

    def _match_limit_order(self, order: Order) -> List[Trade]:
        """Match a limit order, then rest any unfilled quantity on the book."""
        trades: List[Trade] = []

        if order.side == OrderSide.BUY:
            # Match against asks where ask price <= order price
            while (
                order.remaining_quantity > 0
                and self.asks
                and self.asks[0].price <= order.price
            ):
                best_ask = self.asks[0]
                fill_qty = min(order.remaining_quantity, best_ask.remaining_quantity)
                trade = self._create_trade(order, best_ask, best_ask.price, fill_qty)
                trades.append(trade)
                if best_ask.is_filled:
                    self.asks.pop(0)

            # Rest unfilled quantity on the bid side
            if order.remaining_quantity > 0:
                self._insert_bid(order)

        else:  # SELL
            # Match against bids where bid price >= order price
            while (
                order.remaining_quantity > 0
                and self.bids
                and self.bids[0].price >= order.price
            ):
                best_bid = self.bids[0]
                fill_qty = min(order.remaining_quantity, best_bid.remaining_quantity)
                trade = self._create_trade(best_bid, order, best_bid.price, fill_qty)
                trades.append(trade)
                if best_bid.is_filled:
                    self.bids.pop(0)

            # Rest unfilled quantity on the ask side
            if order.remaining_quantity > 0:
                self._insert_ask(order)

        return trades

    def _create_trade(
        self, buy_order: Order, sell_order: Order, price: float, quantity: int
    ) -> Trade:
        """Create a trade and fill both orders."""
        buy_order.fill(quantity)
        sell_order.fill(quantity)
        self._trade_count += 1

        trade = Trade(
            buyer_order_id=buy_order.order_id,
            seller_order_id=sell_order.order_id,
            buyer_agent_id=buy_order.agent_id,
            seller_agent_id=sell_order.agent_id,
            price=price,
            quantity=quantity,
        )
        self.trades.append(trade)
        return trade

    def _insert_bid(self, order: Order) -> None:
        """Insert a bid order in descending price order (price-time priority)."""
        for i, existing in enumerate(self.bids):
            if order.price > existing.price:
                self.bids.insert(i, order)
                return
        self.bids.append(order)

    def _insert_ask(self, order: Order) -> None:
        """Insert an ask order in ascending price order (price-time priority)."""
        for i, existing in enumerate(self.asks):
            if order.price < existing.price:
                self.asks.insert(i, order)
                return
        self.asks.append(order)

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order by ID. Returns True if found and cancelled."""
        for book in [self.bids, self.asks]:
            for i, order in enumerate(book):
                if order.order_id == order_id:
                    order.status = OrderStatus.CANCELLED
                    book.pop(i)
                    return True
        return False

    @property
    def best_bid(self) -> Optional[float]:
        return self.bids[0].price if self.bids else None

    @property
    def best_ask(self) -> Optional[float]:
        return self.asks[0].price if self.asks else None

    @property
    def mid_price(self) -> Optional[float]:
        if self.best_bid is not None and self.best_ask is not None:
            return (self.best_bid + self.best_ask) / 2
        return None

    @property
    def spread(self) -> Optional[float]:
        if self.best_bid is not None and self.best_ask is not None:
            return self.best_ask - self.best_bid
        return None

    def get_depth(self, levels: int = 5) -> Dict[str, list]:
        """Get order book depth for the top N price levels."""
        bid_levels = self._aggregate_levels(self.bids, levels)
        ask_levels = self._aggregate_levels(self.asks, levels)
        return {"bids": bid_levels, "asks": ask_levels}

    def get_total_depth(self, levels: int = 5) -> int:
        """Total quantity across top N levels on both sides."""
        depth = self.get_depth(levels)
        bid_total = sum(level["size"] for level in depth["bids"])
        ask_total = sum(level["size"] for level in depth["asks"])
        return bid_total + ask_total

    def _aggregate_levels(
        self, orders: List[Order], levels: int
    ) -> List[Dict[str, float]]:
        """Aggregate orders into price levels."""
        level_map: Dict[float, int] = {}
        for order in orders:
            price = round(order.price, 2)
            level_map[price] = level_map.get(price, 0) + order.remaining_quantity
            if len(level_map) >= levels:
                break

        return [
            {"price": price, "size": size} for price, size in level_map.items()
        ]

    def __repr__(self) -> str:
        return (
            f"OrderBook(bids={len(self.bids)}, asks={len(self.asks)}, "
            f"trades={self._trade_count}, spread={self.spread})"
        )
