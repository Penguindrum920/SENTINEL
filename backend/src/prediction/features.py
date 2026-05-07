"""Feature extraction for liquidity prediction."""

from typing import Dict, List
from ..utils.config import config


class FeatureExtractor:
    """
    Extracts liquidity-related features from the current market state
    for use by the LiquidityShockPredictor.
    """

    def __init__(
        self,
        baseline_spread: float = config.baseline_spread,
        baseline_depth: float = config.baseline_depth,
        baseline_volatility: float = config.baseline_volatility,
    ) -> None:
        self.baseline_spread = baseline_spread
        self.baseline_depth = baseline_depth
        self.baseline_volatility = baseline_volatility

    def extract_liquidity_features(
        self, market_state: Dict, lookback: int = 60
    ) -> Dict[str, float]:
        """
        Extract 6 liquidity features from current market state.

        Returns:
            Dict with keys: spread_ratio, depth_ratio, volatility_ratio,
            mm_inventory_stress, active_mm_count, time_to_close
        """
        mid_price = market_state.get("mid_price", 100.0)
        spread = market_state.get("spread", 0.0)
        total_depth = market_state.get("total_depth", 0)
        volatility = market_state.get("volatility", 0.0)
        time_to_close = market_state.get("time_to_close", 23400.0)
        agents = market_state.get("agents", {})

        # Spread ratio: normalised spread relative to baseline
        current_spread_ratio = (spread / mid_price) if mid_price > 0 else 0.0
        spread_ratio = current_spread_ratio / self.baseline_spread if self.baseline_spread > 0 else 0.0

        # Depth ratio: total depth / baseline
        depth_ratio = total_depth / self.baseline_depth if self.baseline_depth > 0 else 0.0

        # Volatility ratio
        volatility_ratio = volatility / self.baseline_volatility if self.baseline_volatility > 0 else 0.0

        # Market maker inventory stress
        mm_agents = {
            k: v for k, v in agents.items()
            if v.get("type") == "MarketMaker"
        }
        if mm_agents:
            mm_inventory_stress = sum(
                abs(v.get("inventory_ratio", 0.0)) for v in mm_agents.values()
            ) / len(mm_agents)
            # Count active MMs (not near max capacity)
            active_mm_count = sum(
                1 for v in mm_agents.values()
                if abs(v.get("position", 0)) < 4500
            )
        else:
            mm_inventory_stress = 0.0
            active_mm_count = 0

        return {
            "spread_ratio": round(spread_ratio, 6),
            "depth_ratio": round(depth_ratio, 6),
            "volatility_ratio": round(volatility_ratio, 6),
            "mm_inventory_stress": round(mm_inventory_stress, 6),
            "active_mm_count": active_mm_count,
            "time_to_close": time_to_close,
        }
