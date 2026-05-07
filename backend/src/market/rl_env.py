"""Gymnasium environment for training Reinforcement Learning agents in the limit order book."""

import numpy as np
import gymnasium as gym
from gymnasium import spaces
from typing import Dict, Tuple
from .simulator import MarketSimulator
from .rl_features import extract_market_maker_observation
from ..agents.rl_agent import RLAgent

class MarketMakerEnv(gym.Env):
    """
    RL Environment where the agent acts as a Market Maker.
    Actions: Continuous[spread, skew, size]
      - spread (-1 to 1): Distance between quotes.
      - skew (-1 to 1): Inventory bias (offsets quotes).
      - size (-1 to 1): Quantity of shares to offer.
    Observations: Vector of 13 normalized market and agent variables.
    """
    
    def __init__(self, simulator: MarketSimulator, rl_agent_id: str = "RL_MM"):
        super(MarketMakerEnv, self).__init__()
        self.simulator = simulator
        self.rl_agent_id = rl_agent_id
        
        # Action space: [spread, skew, size] between -1 and 1
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(3,), dtype=np.float32)
        
        # Observations: [best_bid, best_ask, spread, mid, imbalance, recent_px_chg,
        # signed_vol, inventory, realized_pnl, unrealized_pnl, vol, fill_rate, time]
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(13,), dtype=np.float32)
        
        # Tracking states for reward shaping
        self.last_pnl = 0.0
        self.last_position = 0
        self.max_drawdown = 0.0
        self.peak_pnl = 0.0
        
    def reset(self, seed=None, options=None) -> Tuple[np.ndarray, Dict]:
        super().reset(seed=seed)
        
        initial_state = self.simulator.reset(seed=seed)
        self.last_pnl = 0.0
        self.last_position = 0
        self.max_drawdown = 0.0
        self.peak_pnl = 0.0
        
        return self._extract_obs(initial_state), {}

    def _get_rl_agent(self) -> RLAgent:
        agent = self.simulator.get_agent(self.rl_agent_id)
        if not isinstance(agent, RLAgent):
            raise RuntimeError(f"Simulator does not contain RLAgent('{self.rl_agent_id}')")
        return agent
        
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        rl_agent = self._get_rl_agent()
        actual_spread, actual_skew, actual_qty = rl_agent.decode_action(action)

        state = self.simulator.get_market_state()
        mid = state['mid_price']

        rl_agent.set_action(action)
        next_state = self.simulator.step()
        num_cancels = rl_agent.consume_last_cancel_count()
        
        # Compute Rewards
        current_pnl = self._get_agent_pnl()
        position = self._get_agent_inventory()
        
        pnl_diff = current_pnl - self.last_pnl
        self.last_pnl = current_pnl
        
        # Track drawdown
        self.peak_pnl = max(self.peak_pnl, current_pnl)
        drawdown = self.peak_pnl - current_pnl
        self.max_drawdown = max(self.max_drawdown, drawdown)
        
        # Shaping penalties
        inventory_penalty = 0.005 * (position ** 2) 
        cancel_penalty = 0.01 * num_cancels
        drawdown_penalty = 0.01 * drawdown
        
        # Add carry penalty so lingering inventory over time is discouraged.
        inventory_carry_penalty = 0.0005 * abs(position)

        # Spooner-like inventory-aware asymmetric reward.
        reward = pnl_diff - inventory_penalty - inventory_carry_penalty - cancel_penalty - drawdown_penalty
        
        self.last_position = position
        
        obs = self._extract_obs(next_state)
        done = next_state['time_to_close'] <= 0
        truncated = False 
        
        # Pass info dict for evaluation callbacks
        info = {
            "pnl": current_pnl,
            "inventory": position,
            "mid_price": mid,
            "drawdown": drawdown,
            "cancel_penalty": cancel_penalty,
            "inventory_penalty": inventory_penalty,
            "inventory_carry_penalty": inventory_carry_penalty,
            "quoted_spread": actual_spread,
            "quoted_skew": actual_skew,
            "quoted_size": actual_qty,
            "fill_rate": next_state.get("fill_rate", 0.0),
            "spread": next_state.get("spread", 0.0),
        }
        
        return obs, reward, done, truncated, info

    def _extract_obs(self, state: Dict) -> np.ndarray:
        return extract_market_maker_observation(self.simulator, self.rl_agent_id)

    def _get_agent_pnl(self) -> float:
        agent = self.simulator.get_agent(self.rl_agent_id)
        if agent is not None:
            mid = self.simulator.get_market_state()['mid_price']
            return agent.realized_pnl + agent.get_unrealized_pnl(mid)
        return 0.0
        
    def _get_agent_inventory(self) -> int:
        agent = self.simulator.get_agent(self.rl_agent_id)
        if agent is not None:
            return agent.position
        return 0
