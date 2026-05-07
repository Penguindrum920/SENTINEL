"""Trade data structure for the SENTINEL market simulator."""

from dataclasses import dataclass, field
import uuid
import time


@dataclass
class Trade:
    """Represents an executed trade between two orders."""

    buyer_order_id: str
    seller_order_id: str
    buyer_agent_id: str
    seller_agent_id: str
    price: float
    quantity: int
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)

    @property
    def value(self) -> float:
        """Notional value of the trade."""
        return self.price * self.quantity

    def __repr__(self) -> str:
        return (
            f"Trade({self.quantity}@{self.price:.2f} "
            f"buyer={self.buyer_agent_id} seller={self.seller_agent_id})"
        )
