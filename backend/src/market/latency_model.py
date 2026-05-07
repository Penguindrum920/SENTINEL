"""Latency model for agent-exchange communication.

Inspired by ABIDES (Agent-Based Interactive Discrete Event Simulation)
cubic latency model from J.P. Morgan AI Research.

Supports three modes:
  - 'zero'          : No latency (instant execution)
  - 'deterministic'  : Fixed min_latency per agent type
  - 'cubic'          : Realistic jitter: min_latency + (a / x^3) * (min_latency / unit)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

import numpy as np


class LatencyMode(str, Enum):
    ZERO = "zero"
    DETERMINISTIC = "deterministic"
    CUBIC = "cubic"


# Default latency tiers in seconds, grouped by agent archetype.
# These approximate real-world co-location and retail latency differences.
AGENT_LATENCY_TIERS: Dict[str, float] = {
    # Ultra-low latency (co-located)
    "HFT": 0.000_001,        # 1 μs
    "RL_MM": 0.000_010,      # 10 μs

    # Low latency (direct market access)
    "MarketMaker": 0.000_100,    # 100 μs
    "Spoofing": 0.000_100,

    # Medium latency (institutional)
    "Institutional": 0.001,      # 1 ms
    "Informed": 0.001,
    "Momentum": 0.001,
    "MeanReversion": 0.001,
    "LiquidityTrader": 0.001,
    "Sentiment": 0.002,

    # High latency (retail)
    "Retail": 0.010,             # 10 ms
    "Noise": 0.005,              # 5 ms
}


@dataclass
class LatencyConfig:
    """Configuration for a latency model instance."""

    mode: LatencyMode = LatencyMode.DETERMINISTIC

    # --- Cubic model parameters ---
    # Shape of the cubic jitter curve (higher = more extreme tail)
    jitter: float = 0.5
    # Minimum draw value for cubic noise (clips the tail)
    jitter_clip: float = 0.1
    # Fraction of min_latency used as the jitter unit
    jitter_unit: float = 10.0

    # Custom per-agent-type overrides (seconds). Falls back to AGENT_LATENCY_TIERS.
    custom_tiers: Dict[str, float] = field(default_factory=dict)


class LatencyModel:
    """Simulates realistic communication latency between agents and the exchange.

    Usage:
        model = LatencyModel(LatencyConfig(mode=LatencyMode.CUBIC))
        delay = model.get_latency("HFT")        # → ~1μs + cubic jitter
        delay = model.get_latency("Retail")      # → ~10ms + cubic jitter
    """

    def __init__(
        self,
        config: Optional[LatencyConfig] = None,
        rng: Optional[np.random.RandomState] = None,
    ) -> None:
        self.config = config or LatencyConfig()
        self.rng = rng or np.random.RandomState()
        # Merge defaults with any custom overrides
        self._tiers = {**AGENT_LATENCY_TIERS, **(self.config.custom_tiers or {})}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_latency(self, agent_type: str) -> float:
        """Return the simulated one-way latency in **seconds** for *agent_type*."""

        if self.config.mode == LatencyMode.ZERO:
            return 0.0

        min_lat = self._tiers.get(agent_type, 0.005)  # default 5 ms

        if self.config.mode == LatencyMode.DETERMINISTIC:
            return min_lat

        # Cubic model: jitter drawn from (clip, 1]
        clip = self.config.jitter_clip
        a = self.config.jitter
        unit = self.config.jitter_unit

        x = self.rng.uniform(low=clip, high=1.0)
        if x <= 0:
            x = 1e-9  # safety

        jitter_amount = (a / (x ** 3)) * (min_lat / unit)
        return min_lat + jitter_amount

    def get_computation_delay(self, agent_type: str) -> float:
        """Return post-action computation delay in seconds.

        This models the "thinking time" after an agent acts, during which
        it cannot receive new messages — a key ABIDES concept.
        """
        base_delays = {
            "HFT": 0.000_001,
            "RL_MM": 0.000_010,
            "MarketMaker": 0.000_050,
            "Spoofing": 0.000_050,
            "Institutional": 0.000_500,
            "Informed": 0.000_500,
            "Momentum": 0.000_500,
            "MeanReversion": 0.000_500,
            "LiquidityTrader": 0.000_500,
            "Sentiment": 0.001,
            "Retail": 0.005,
            "Noise": 0.002,
        }
        return base_delays.get(agent_type, 0.001)

    def describe(self) -> dict:
        """Return a JSON-serializable description of the model configuration."""
        return {
            "mode": self.config.mode.value,
            "jitter": self.config.jitter,
            "jitter_clip": self.config.jitter_clip,
            "jitter_unit": self.config.jitter_unit,
            "tiers": {k: f"{v*1e6:.1f}μs" for k, v in self._tiers.items()},
        }
