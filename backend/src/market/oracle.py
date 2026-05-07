"""Mean-reverting fundamental value oracle.

Inspired by ABIDES SparseMeanRevertingOracle. Generates a hidden "true price"
that the simulated market price should loosely track. Informed agents can observe
this value (with noise) and trade on the information gap.

The oracle follows an Ornstein–Uhlenbeck process:
    dP = κ(r̄ - P)dt + σ dW
where:
    r̄   = long-run mean price
    κ    = mean-reversion speed (higher = faster pull to mean)
    σ    = volatility of the fundamental process
    dW   = Wiener process increment
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np


@dataclass
class OracleConfig:
    """Parameters for the mean-reverting oracle."""

    r_bar: float = 100.0        # Long-run equilibrium price
    kappa: float = 0.05         # Mean-reversion speed (0 = random walk, 1 = instant revert)
    sigma_s: float = 0.02       # Fundamental volatility per time step
    observation_noise: float = 0.005  # Noise added when agents observe the oracle
    enabled: bool = True        # Whether the oracle is active
    replay_path: List[float] = field(default_factory=list)  # Real price series for replay mode


class MeanRevertingOracle:
    """Generates a fundamental value time series that agents can use for informed trading.

    Usage:
        oracle = MeanRevertingOracle(OracleConfig(r_bar=100, kappa=0.05, sigma_s=0.02))
        oracle.reset(seed=42)

        for t in range(3600):
            oracle.advance(dt=1.0)
            true_price = oracle.current_value
            noisy_obs  = oracle.observe()  # what an informed agent would see
    """

    def __init__(
        self,
        config: Optional[OracleConfig] = None,
        rng: Optional[np.random.RandomState] = None,
    ) -> None:
        self.config = config or OracleConfig()
        self.rng = rng or np.random.RandomState()

        self._current_value: float = self.config.r_bar
        self._history: List[float] = [self._current_value]
        self._time: float = 0.0
        self._replay_index: int = 0  # cursor into replay_path

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def current_value(self) -> float:
        """The current 'true' fundamental price (hidden from most agents)."""
        return self._current_value

    @property
    def history(self) -> List[float]:
        """Full history of fundamental values."""
        return list(self._history)

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self, seed: Optional[int] = None) -> None:
        """Reset the oracle to its initial state."""
        if seed is not None:
            self.rng = np.random.RandomState(seed)
        self._current_value = self.config.r_bar
        self._history = [self._current_value]
        self._time = 0.0
        self._replay_index = 0

    def advance(self, dt: float = 1.0) -> float:
        """Advance the oracle by *dt* seconds and return the new fundamental value.

        In replay mode (replay_path is set), steps through the real price series.
        Otherwise uses the Euler-Maruyama OU discretization:
            P_{t+1} = P_t + κ(r̄ - P_t)dt + σ√dt · Z,   Z ~ N(0,1)
        """
        if not self.config.enabled:
            return self._current_value

        # ── Replay mode: follow real price series ──────────────────────────
        if self.config.replay_path:
            path = self.config.replay_path
            if self._replay_index < len(path):
                self._current_value = float(path[self._replay_index])
                self._replay_index += 1
            else:
                # Path exhausted — switch to OU continuation
                kappa = self.config.kappa
                r_bar = self._current_value  # anchor to last real price
                sigma = self.config.sigma_s
                drift = kappa * (r_bar - self._current_value) * dt
                diffusion = sigma * np.sqrt(dt) * self.rng.randn()
                self._current_value = max(0.01, self._current_value + drift + diffusion)

            self._history.append(self._current_value)
            self._time += dt
            return self._current_value

        # ── Synthetic OU mode ──────────────────────────────────────────────
        kappa = self.config.kappa
        r_bar = self.config.r_bar
        sigma = self.config.sigma_s

        drift = kappa * (r_bar - self._current_value) * dt
        diffusion = sigma * np.sqrt(dt) * self.rng.randn()
        self._current_value += drift + diffusion
        self._current_value = max(self._current_value, 0.01)

        self._history.append(self._current_value)
        self._time += dt
        return self._current_value

    def observe(self, sigma_n: Optional[float] = None) -> float:
        """Return the current fundamental value with observation noise.

        This is what an informed agent "sees" — close to the truth but noisy.
        """
        noise_level = sigma_n if sigma_n is not None else self.config.observation_noise
        noise = noise_level * self.rng.randn()
        return self._current_value + noise

    def get_mispricing(self, market_price: float) -> float:
        """Return the gap between the oracle value and the current market price.

        Positive = market is overpriced relative to fundamental.
        Negative = market is underpriced.
        """
        return market_price - self._current_value

    def get_mispricing_pct(self, market_price: float) -> float:
        """Mispricing as a percentage of fundamental value."""
        if self._current_value == 0:
            return 0.0
        return (market_price - self._current_value) / self._current_value * 100

    def describe(self) -> dict:
        """JSON-serializable description."""
        return {
            "enabled": self.config.enabled,
            "r_bar": self.config.r_bar,
            "kappa": self.config.kappa,
            "sigma_s": self.config.sigma_s,
            "observation_noise": self.config.observation_noise,
            "current_value": round(self._current_value, 4),
            "history_length": len(self._history),
        }

    def get_recent_history(self, n: int = 240) -> List[float]:
        """Return the last *n* values for charting."""
        return self._history[-n:]
