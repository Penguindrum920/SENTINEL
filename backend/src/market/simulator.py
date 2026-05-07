"""Market simulator — orchestrates agents, order book, and state tracking using a discrete event kernel."""

from typing import Dict, List, Optional
import math
import random
from collections import deque

from .kernel import EventKernel, EventType
from .order_book import OrderBook
from .order import Order, OrderSide, OrderType, OrderStatus
from .trade import Trade
from .oracle import MeanRevertingOracle, OracleConfig
from .latency_model import LatencyModel, LatencyConfig, LatencyMode
from ..agents.base_agent import BaseAgent
from ..utils.logger import get_logger

logger = get_logger("simulator")


class MarketSimulator:
    """
    Multi-agent market microstructure simulator powered by an event kernel.

    Agents wake up asynchronously, generate orders based on the latest market
    snapshot, and those orders arrive at the exchange after each agent's
    structural latency. The simulator tracks both order-book state and the
    richer metrics consumed by the API, predictors, and RL environment.
    """

    def __init__(
        self,
        agents: List[BaseAgent],
        initial_price: float = 100.0,
        duration_seconds: int = 23_400,
        mode: str = "SANDBOX",
        order_ttl_seconds: float = 20.0,
        oracle_config: Optional[OracleConfig] = None,
        latency_config: Optional[LatencyConfig] = None,
        speed_multiplier: float = 1.0,
    ) -> None:
        self.agents = sorted(agents, key=lambda agent: agent.latency_seconds)
        self.order_book = OrderBook()
        self.kernel = EventKernel()
        self.initial_price = initial_price
        self.duration_seconds = duration_seconds
        self.order_ttl_seconds = order_ttl_seconds
        self.speed_multiplier: float = speed_multiplier

        # ABIDES-inspired oracle: hidden fundamental value
        self.oracle = MeanRevertingOracle(
            config=oracle_config or OracleConfig(r_bar=initial_price, enabled=False)
        )
        # ABIDES-inspired latency model: realistic jitter per agent type
        self.latency_model = LatencyModel(
            config=latency_config or LatencyConfig(mode=LatencyMode.DETERMINISTIC)
        )

        self.current_price: float = initial_price
        self.step_count: int = 0
        self.running: bool = False
        self.mode: str = mode

        self._price_history: deque[float] = deque(maxlen=1_000)
        self._state_history: List[Dict] = []
        self._all_trades: List[Trade] = []
        self._recent_volume_history: deque[tuple[float, int]] = deque(maxlen=2_000)

        self.reset()

    @property
    def current_time(self) -> float:
        return self.kernel.current_time

    def reset(self, seed: Optional[int] = None) -> Dict:
        """Reset the simulator for a new episode and return the initial state."""
        if seed is not None:
            random.seed(seed)
            try:
                import numpy as np

                np.random.seed(seed)
            except Exception:
                logger.debug("NumPy unavailable while seeding simulator")

        self.order_book = OrderBook()
        self.kernel.clear()
        self.current_price = self.initial_price
        self.step_count = 0
        self.running = False

        self._price_history.clear()
        self._price_history.append(self.initial_price)
        self._state_history.clear()
        self._all_trades.clear()
        self._recent_volume_history.clear()

        # Reset oracle to initial fundamental value
        self.oracle.reset(seed=seed)

        self._seed_order_book()

        for agent in self.agents:
            agent.reset()

            if getattr(agent, "external_action_controlled", False):
                continue

            first_wake = random.uniform(0.01, 1.0)
            self.kernel.schedule(first_wake, EventType.WAKEUP, self._agent_wakeup, agent)

        return self.get_market_state()

    def _seed_order_book(self) -> None:
        """Place initial resting orders to bootstrap the book."""
        for i in range(10):
            offset = (i + 1) * 0.01
            bid = Order(
                agent_id="SEED",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=round(self.initial_price - offset, 2),
                quantity=500,
            )
            ask = Order(
                agent_id="SEED",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                price=round(self.initial_price + offset, 2),
                quantity=500,
            )
            self.order_book.add_order(bid)
            self.order_book.add_order(ask)

    def _ensure_liquidity_floor(self) -> None:
        """Replenish thin books so the dashboard demo remains two-sided and responsive."""
        total_depth = self.order_book.get_total_depth(levels=10)
        if (
            self.order_book.best_bid is not None
            and self.order_book.best_ask is not None
            and total_depth >= 600
        ):
            return

        anchor = self.order_book.mid_price or self.current_price or self.initial_price
        for i in range(5):
            offset = (i + 1) * 0.02
            quantity = 150
            bid = Order(
                agent_id="SEED",
                side=OrderSide.BUY,
                order_type=OrderType.LIMIT,
                price=round(anchor - offset, 2),
                quantity=quantity,
            )
            ask = Order(
                agent_id="SEED",
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                price=round(anchor + offset, 2),
                quantity=quantity,
            )
            self.order_book.add_order(bid)
            self.order_book.add_order(ask)

    def _process_order(self, order: Order) -> None:
        """Exchange receives and processes an order."""
        if self.mode != "SANDBOX":
            return
        if order.quantity <= 0:
            logger.warning(f"Rejected non-positive order quantity from {order.agent_id}: {order.quantity}")
            return
        if not math.isfinite(order.price):
            logger.warning(f"Rejected non-finite order price from {order.agent_id}: {order.price}")
            return

        trades = self.order_book.add_order(order)
        self._all_trades.extend(trades)

        owner = next((agent for agent in self.agents if agent.agent_id == order.agent_id), None)
        if (
            owner is not None
            and order.order_type == OrderType.LIMIT
            and order.remaining_quantity > 0
        ):
            owner.active_orders[order.order_id] = order
            self.kernel.schedule(
                self.order_ttl_seconds,
                EventType.CANCEL_ARRIVAL,
                self._cancel_order,
                order.order_id,
            )

        signed_qty = order.quantity if order.side == OrderSide.BUY else -order.quantity

        for trade in trades:
            self.current_price = trade.price
            self._price_history.append(self.current_price)
            self._recent_volume_history.append((self.current_time, signed_qty))

            for agent in self.agents:
                if agent.agent_id in (trade.buyer_agent_id, trade.seller_agent_id):
                    self.kernel.schedule(
                        agent.latency_seconds,
                        EventType.MARKET_DATA,
                        agent.update_position,
                        trade,
                    )

        self._prune_inactive_orders()

    def _cancel_order(self, order_id: str) -> bool:
        """Cancel a resting order and clear its agent-side tracking."""
        cancelled = self.order_book.cancel_order(order_id)
        for agent in self.agents:
            agent.active_orders.pop(order_id, None)
        if cancelled:
            logger.debug(f"Cancelled stale order {order_id}")
        return cancelled

    def _prune_inactive_orders(self) -> None:
        """Remove filled or cancelled resting orders from agent-side tracking."""
        for agent in self.agents:
            inactive_ids = [
                order_id
                for order_id, order in agent.active_orders.items()
                if order.is_filled
                or order.status == OrderStatus.CANCELLED
                or order.remaining_quantity <= 0
            ]
            for order_id in inactive_ids:
                agent.active_orders.pop(order_id, None)

    def _request_agent_orders(self, agent: BaseAgent) -> None:
        """Process an agent action cycle through the simulator's normal order path."""
        note_cancel_result = getattr(agent, "note_cancel_result", None)
        for order_id in agent.consume_cancellations():
            cancelled = self._cancel_order(order_id)
            if callable(note_cancel_result):
                note_cancel_result(cancelled)

        state = self.get_market_state()
        orders = agent.decide_action(state)
        for order in orders:
            self.kernel.schedule(
                agent.latency_seconds,
                EventType.ORDER_ARRIVAL,
                self._process_order,
                order,
            )

    def _agent_wakeup(self, agent: BaseAgent) -> None:
        """Trigger an agent to observe the market and submit fresh orders."""
        if not self.running:
            return

        try:
            self._request_agent_orders(agent)
        except Exception as exc:
            logger.error(f"Agent {agent.agent_id} error: {exc}")

        interval = getattr(agent, "wakeup_interval", 1.0)
        jitter = random.uniform(0.9, 1.1)
        self.kernel.schedule(interval * jitter, EventType.WAKEUP, self._agent_wakeup, agent)

    def run(self, steps: Optional[int] = None) -> Dict:
        """Run the simulation synchronously until the requested horizon."""
        self.reset()
        self.running = True
        target_time = float(steps if steps is not None else self.duration_seconds)

        logger.info(f"Starting kernel event loop until T={target_time:.2f}s")
        while self.running and self.current_time < target_time:
            self.step()

        self.running = False
        return self.get_results()

    def step(self) -> Dict:
        """Advance the simulation by one second of simulated time."""
        if not self.running:
            self.running = True

        for agent in self.agents:
            if getattr(agent, "external_action_controlled", False):
                try:
                    self._request_agent_orders(agent)
                except Exception as exc:
                    logger.error(f"Externally controlled agent {agent.agent_id} error: {exc}")

        self.step_count += 1
        target_time = self.current_time + 1.0
        self.kernel.run_until(target_time)

        # Advance the fundamental value oracle
        self.oracle.advance(dt=1.0)

        self._ensure_liquidity_floor()

        if self.order_book.mid_price is not None:
            self.current_price = self.order_book.mid_price

        self._price_history.append(self.current_price)

        state = self.get_market_state()
        self._state_history.append(state)
        return state

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Return the simulator agent with the requested ID, if present."""
        return next((agent for agent in self.agents if agent.agent_id == agent_id), None)

    def get_market_state(self) -> Dict:
        """Return the current market state snapshot."""
        depth_data = self.order_book.get_depth(levels=10)
        total_depth = self.order_book.get_total_depth(levels=10)
        volatility = self._compute_volatility()

        prices = list(self._price_history)
        recent_price_change = 0.0
        if len(prices) >= 5 and prices[-5] > 0:
            recent_price_change = (prices[-1] - prices[-5]) / prices[-5]

        volume_window = 10.0
        recent_signed_volume = sum(
            qty for ts, qty in self._recent_volume_history if (self.current_time - ts) <= volume_window
        )

        bid_sum = sum(level["size"] for level in depth_data["bids"])
        ask_sum = sum(level["size"] for level in depth_data["asks"])
        imbalance = (bid_sum - ask_sum) / max(1, bid_sum + ask_sum)
        fill_rate = len(self._all_trades) / max(1.0, self.current_time)

        state = {
            "current_time": self.current_time,
            "mid_price": self.order_book.mid_price or self.current_price,
            "best_bid": self.order_book.best_bid,
            "best_ask": self.order_book.best_ask,
            "spread": self.order_book.spread or 0.0,
            "bid_depth": bid_sum,
            "ask_depth": ask_sum,
            "bid_levels": depth_data["bids"],
            "ask_levels": depth_data["asks"],
            "order_book_imbalance": imbalance,
            "recent_signed_volume": recent_signed_volume,
            "recent_price_change": recent_price_change,
            "fill_rate": fill_rate,
            "total_depth": total_depth,
            "current_price": self.current_price,
            "time_to_close": max(0.0, self.duration_seconds - self.current_time),
            "volatility": volatility,
            "agents": {
                agent.agent_id: {
                    "type": agent.agent_type,
                    "position": agent.position,
                    "inventory_ratio": self._inventory_ratio(agent),
                }
                for agent in self.agents
            },
            "step": self.step_count,
        }

        # Oracle data (ABIDES-inspired fundamental value)
        if self.oracle.enabled:
            state["oracle"] = {
                "fundamental_value": round(self.oracle.current_value, 4),
                "mispricing": round(self.oracle.get_mispricing(self.current_price), 4),
                "mispricing_pct": round(self.oracle.get_mispricing_pct(self.current_price), 4),
            }

        return state

    def get_results(self) -> Dict:
        """Return final simulation results."""
        agent_metrics = {}
        for agent in self.agents:
            agent_metrics[agent.agent_id] = agent.get_metrics(self.current_price)

        return {
            "final_price": self.current_price,
            "initial_price": self.initial_price,
            "total_trades": len(self._all_trades),
            "total_steps": self.step_count,
            "price_history": list(self._price_history),
            "agent_metrics": agent_metrics,
        }

    def _compute_volatility(self) -> float:
        """Compute annualized volatility from recent log returns."""
        prices = list(self._price_history)
        if len(prices) < 20:
            return 0.0

        window = prices[-20:]
        log_returns = []
        for i in range(1, len(window)):
            if window[i] > 0 and window[i - 1] > 0:
                log_returns.append(math.log(window[i] / window[i - 1]))

        if len(log_returns) < 2:
            return 0.0

        mean_ret = sum(log_returns) / len(log_returns)
        variance = sum((ret - mean_ret) ** 2 for ret in log_returns) / (len(log_returns) - 1)
        std = math.sqrt(variance) if variance > 0 else 0.0

        return std * math.sqrt(252 * 390)

    def _inventory_ratio(self, agent: BaseAgent) -> float:
        limit = (
            getattr(agent, "max_inventory", None)
            or getattr(agent, "max_position", None)
            or getattr(agent, "position_limit", None)
        )
        if not limit:
            return 0.0
        return abs(agent.position) / float(limit)

    def stop(self) -> None:
        """Stop the simulation loop."""
        self.running = False
        logger.info("Simulation stopped")


# ── Sandbox Presets ─────────────────────────────────────────────────────────


def get_sandbox_presets() -> Dict:
    """Return available sandbox configuration presets."""
    return {
        "minimal": {
            "name": "Minimal",
            "description": "10 agents — quick test of core mechanics",
            "icon": "⚡",
            "agents": {"MarketMaker": 1, "HFT": 2, "Noise": 3, "Retail": 2, "Informed": 1, "Sentiment": 1},
            "oracle": False,
            "latency": "deterministic",
        },
        "balanced": {
            "name": "Balanced",
            "description": "40 agents — the default SENTINEL experience",
            "icon": "⚖️",
            "agents": {"MarketMaker": 3, "HFT": 2, "Institutional": 2, "Retail": 10, "Informed": 3, "Noise": 10, "Momentum": 2, "MeanReversion": 2, "Spoofing": 1, "Sentiment": 5},
            "oracle": False,
            "latency": "deterministic",
        },
        "institutional": {
            "name": "Institutional Pressure",
            "description": "80 agents — heavy institutional + momentum flow",
            "icon": "🏦",
            "agents": {"MarketMaker": 5, "HFT": 4, "Institutional": 8, "Retail": 15, "Informed": 5, "Noise": 20, "Momentum": 8, "MeanReversion": 5, "Spoofing": 2, "Sentiment": 8},
            "oracle": True,
            "latency": "cubic",
        },
        "stress_test": {
            "name": "Stress Test",
            "description": "200 agents — ABIDES-scale stress with noise flood",
            "icon": "🔥",
            "agents": {"MarketMaker": 8, "HFT": 10, "Institutional": 5, "Retail": 30, "Informed": 10, "Noise": 100, "Momentum": 12, "MeanReversion": 10, "Spoofing": 3, "Sentiment": 12},
            "oracle": True,
            "latency": "cubic",
        },
    }


def create_sandbox_agents(preset_name: str, custom_config: Optional[Dict] = None) -> List[BaseAgent]:
    """Create an agent population from a sandbox preset or custom config."""
    from ..agents.market_maker import MarketMakerAgent
    from ..agents.hft_agent import HFTAgent
    from ..agents.institutional import InstitutionalAgent
    from ..agents.retail import RetailAgent
    from ..agents.informed import InformedAgent
    from ..agents.noise import NoiseAgent
    from ..agents.momentum import MomentumAgent
    from ..agents.mean_reversion import MeanReversionAgent
    from ..agents.spoofing import SpoofingAgent
    from ..agents.sentiment import SentimentAgent

    agent_classes = {
        "MarketMaker": MarketMakerAgent,
        "HFT": HFTAgent,
        "Institutional": InstitutionalAgent,
        "Retail": RetailAgent,
        "Informed": InformedAgent,
        "Noise": NoiseAgent,
        "Momentum": MomentumAgent,
        "MeanReversion": MeanReversionAgent,
        "Spoofing": SpoofingAgent,
        "Sentiment": SentimentAgent,
    }

    presets = get_sandbox_presets()
    if preset_name == "custom" and custom_config:
        agent_config = custom_config
    elif preset_name in presets:
        agent_config = presets[preset_name]["agents"]
    else:
        agent_config = presets["balanced"]["agents"]

    agents: List[BaseAgent] = []
    for agent_type, count in agent_config.items():
        cls = agent_classes.get(agent_type)
        if cls is None:
            logger.warning(f"Unknown agent type in preset: {agent_type}")
            continue
        for i in range(count):
            agents.append(cls(f"{agent_type.upper()[:4]}_{i}"))

    return agents
