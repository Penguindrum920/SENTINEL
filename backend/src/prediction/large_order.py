"""Large order detector — identifies Iceberg and TWAP institutional orders."""

from typing import Dict, List, Optional
from collections import deque
import numpy as np
from ..utils.logger import get_logger

logger = get_logger("large_order")


class LargeOrderDetector:
    """
    Detects hidden institutional large orders by analysing
    order flow patterns:
    - Iceberg: consistent sizes at regular intervals
    - TWAP: equally-spaced executions over time
    """

    def __init__(
        self,
        min_order_size: int = 10_000,
        history_length: int = 300,
    ) -> None:
        self.min_order_size = min_order_size
        self.history_length = history_length
        self._order_history: deque = deque(maxlen=history_length)
        self._last_positions: Dict[str, int] = {}
        self._last_timestamp: float = -1.0

    def reset(self) -> None:
        """Clear detector state between simulation runs."""
        self._order_history.clear()
        self._last_positions.clear()
        self._last_timestamp = -1.0

    def record_order(self, order_data: Dict) -> None:
        """Record an order for pattern analysis."""
        self._order_history.append(order_data)

    def record_orders_from_state(self, market_state: Dict) -> None:
        """Record changes in institutional inventory as executed slices."""
        agents = market_state.get("agents", {})
        current_time = market_state.get("current_time", 0.0)

        if current_time < self._last_timestamp:
            self.reset()

        self._last_timestamp = current_time
        active_agents = set()

        for agent_id, info in agents.items():
            if info.get("type") != "Institutional":
                continue

            active_agents.add(agent_id)
            position = int(info.get("position", 0))
            previous_position = self._last_positions.get(agent_id, 0)
            delta = position - previous_position

            if delta != 0:
                self._order_history.append({
                    "agent_id": agent_id,
                    "side": "buy" if delta > 0 else "sell",
                    "size": abs(delta),
                    "timestamp": current_time,
                })

            self._last_positions[agent_id] = position

        stale_agents = set(self._last_positions) - active_agents
        for agent_id in stale_agents:
            self._last_positions.pop(agent_id, None)

    def detect(self, market_state: Dict) -> Optional[Dict]:
        """
        Run all detection algorithms and return the highest-confidence result.
        """
        self.record_orders_from_state(market_state)

        if len(self._order_history) < 5:
            return None

        iceberg = self.detect_iceberg()
        twap = self.detect_twap()

        results = [r for r in [iceberg, twap] if r is not None]
        if not results:
            return None

        # Return highest confidence detection
        best = max(results, key=lambda r: r["confidence"])

        # Add impact prediction
        total_depth = market_state.get("total_depth", 1000)
        volatility = market_state.get("volatility", 0.02)
        impact = self.predict_impact(
            best["estimated_size"], total_depth, volatility,
            market_state.get("current_price", 100.0),
        )
        best["impact"] = impact

        return best

    def detect_iceberg(self) -> Optional[Dict]:
        """
        Detect iceberg orders: consistent sizes at regular intervals.
        Flag if size_std / size_mean < 0.1 AND time_diff_std < 10.
        """
        if len(self._order_history) < 5:
            return None

        orders = list(self._order_history)

        for side in ["buy", "sell"]:
            side_orders = [o for o in orders if o.get("side") == side]
            if len(side_orders) < 5:
                continue

            sizes = np.array([o["size"] for o in side_orders[-20:]])
            times = np.array([o["timestamp"] for o in side_orders[-20:]])

            if len(sizes) < 3:
                continue

            size_mean = np.mean(sizes)
            size_std = np.std(sizes)

            if size_mean == 0:
                continue

            # Check for consistent sizes
            size_cv = size_std / size_mean

            # Check for consistent timing
            if len(times) >= 2:
                time_diffs = np.diff(times)
                time_diff_std = np.std(time_diffs) if len(time_diffs) > 1 else float("inf")
            else:
                time_diff_std = float("inf")

            if size_cv < 0.1 and time_diff_std < 10:
                estimated_size = int(size_mean * len(side_orders) * 2)
                if estimated_size < self.min_order_size:
                    continue
                return {
                    "pattern": "iceberg",
                    "side": side,
                    "estimated_size": estimated_size,
                    "confidence": 0.85,
                    "detected_orders": len(side_orders),
                    "avg_order_size": float(size_mean),
                }

        return None

    def detect_twap(self) -> Optional[Dict]:
        """
        Detect TWAP execution: regular time intervals between orders.
        Flag if time_diff_std / time_diff_mean < 0.2.
        """
        if len(self._order_history) < 5:
            return None

        orders = list(self._order_history)

        for side in ["buy", "sell"]:
            side_orders = [o for o in orders if o.get("side") == side]
            if len(side_orders) < 5:
                continue

            times = np.array([o["timestamp"] for o in side_orders[-20:]])
            sizes = np.array([o["size"] for o in side_orders[-20:]])

            if len(times) < 3:
                continue

            time_diffs = np.diff(times)
            if len(time_diffs) < 2:
                continue

            time_diff_mean = np.mean(time_diffs)
            time_diff_std = np.std(time_diffs)

            if time_diff_mean == 0:
                continue

            time_cv = time_diff_std / time_diff_mean

            if time_cv < 0.2:
                executed = int(np.sum(sizes))
                estimated_size = executed * 3  # assume 1/3 complete
                if estimated_size < self.min_order_size:
                    continue
                return {
                    "pattern": "twap",
                    "side": side,
                    "estimated_size": estimated_size,
                    "confidence": 0.78,
                    "completion_pct": 33,
                    "executed_so_far": executed,
                    "avg_interval": float(time_diff_mean),
                }

        return None

    def predict_impact(
        self,
        estimated_size: int,
        total_depth: int,
        volatility: float,
        current_price: float,
    ) -> Dict:
        """
        Predict the expected price impact of a large order.
        """
        if total_depth == 0:
            total_depth = 1  # avoid division by zero

        size_ratio = estimated_size / total_depth
        base_impact = size_ratio * 0.01
        vol_multiplier = volatility / 0.02 if volatility > 0 else 1.0
        expected_impact_pct = base_impact * vol_multiplier
        expected_impact_dollars = expected_impact_pct * current_price

        # Market conditions assessment
        if expected_impact_pct > 0.02:
            conditions = "severe"
        elif expected_impact_pct > 0.01:
            conditions = "significant"
        elif expected_impact_pct > 0.005:
            conditions = "moderate"
        else:
            conditions = "minimal"

        return {
            "expected_impact_pct": round(expected_impact_pct * 100, 4),
            "expected_impact_dollars": round(expected_impact_dollars, 4),
            "size_vs_depth_ratio": round(size_ratio, 4),
            "market_conditions": conditions,
        }
