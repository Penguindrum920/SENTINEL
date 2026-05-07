"""Inference-time controller for the PPO market-making policy."""

from __future__ import annotations

import os
from typing import Any, Optional

import numpy as np

from .rl_features import extract_market_maker_observation
from .simulator import MarketSimulator
from ..agents.rl_agent import RLAgent
from ..utils.logger import get_logger

logger = get_logger("rl_policy")


class RLPolicyController:
    """Loads a trained PPO policy and pushes actions into RLAgent before each step."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        rl_agent_id: str = "RL_MM",
        policy_model: Optional[Any] = None,
    ) -> None:
        self.model_path = os.path.abspath(model_path) if model_path else None
        self.rl_agent_id = rl_agent_id
        self.model = policy_model
        self._external_model = policy_model is not None

        if self.model is None and self.model_path:
            self._load_model()

    @property
    def ready(self) -> bool:
        return self.model is not None

    def _load_model(self) -> None:
        if not self.model_path:
            return
        if not os.path.exists(self.model_path):
            logger.warning(f"RL policy model not found at {self.model_path}")
            return

        try:
            from stable_baselines3 import PPO  # type: ignore
        except Exception as exc:
            logger.warning(f"stable_baselines3 unavailable; RL policy disabled: {exc}")
            return

        try:
            self.model = PPO.load(self.model_path, device="cpu")
            logger.info(f"Loaded RL policy from {self.model_path}")
        except Exception as exc:
            logger.warning(f"Failed to load RL policy model: {exc}")
            self.model = None

    def reload(self) -> bool:
        """Attempt to (re)load the on-disk policy model."""
        if self._external_model:
            return self.ready
        self.model = None
        if self.model_path:
            self._load_model()
        return self.ready

    def prepare_step(self, simulator: MarketSimulator) -> Optional[tuple[float, ...]]:
        """Compute and queue the next action for the RL agent, if available."""
        if self.model is None:
            return None

        agent = simulator.get_agent(self.rl_agent_id)
        if not isinstance(agent, RLAgent):
            return None

        observation = extract_market_maker_observation(simulator, self.rl_agent_id)
        if not np.isfinite(observation).all():
            logger.warning("RL observation contained non-finite values; replacing with zeros")
            observation = np.nan_to_num(observation, nan=0.0, posinf=0.0, neginf=0.0)

        action, _ = self.model.predict(observation, deterministic=True)
        action_array = np.asarray(action, dtype=np.float32)
        if not np.isfinite(action_array).all():
            logger.warning("RL policy returned non-finite action; falling back to neutral quote")
            action_array = np.zeros(3, dtype=np.float32)
        action_array = np.clip(action_array, -1.0, 1.0)
        agent.set_action(action_array)
        return tuple(float(value) for value in action_array)
