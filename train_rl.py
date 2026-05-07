"""Main RL training script for the Sentinel Market Maker."""

import os
import sys
import gymnasium as gym
import numpy as np

# Append backend to path so we can import modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from stable_baselines3.common.env_util import DummyVecEnv

from backend.src.market.simulator import MarketSimulator
from backend.src.market.rl_env import MarketMakerEnv
from backend.src.agents.noise import NoiseAgent
from backend.src.agents.hft_agent import HFTAgent
from backend.src.agents.retail import RetailAgent
from backend.src.agents.informed import InformedAgent
from backend.src.agents.liquidity_trader import LiquidityTraderAgent
from backend.src.agents.rl_agent import RLAgent

class MetricsLoggerCallback(BaseCallback):
    """
    Custom callback for logging structured market-making metrics
    to TensorBoard over the course of training.
    """
    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.pnls = []
        self.inventories = []
        self.drawdowns = []
        self.rewards = []
        self.fill_rates = []

    def _on_step(self) -> bool:
        # Extract info dict returned sequentially by our environment
        infos = self.locals.get("infos", [])
        for info in infos:
            if info:
                self.pnls.append(info.get("pnl", 0))
                self.inventories.append(abs(info.get("inventory", 0)))
                self.drawdowns.append(info.get("drawdown", 0))
                self.fill_rates.append(info.get("fill_rate", 0))
            rewards = self.locals.get("rewards")
            if rewards is not None:
                self.rewards.append(float(rewards[0]))
                
                # Check for end of episode
                if self.locals.get("dones")[0]:
                    final_pnl = self.pnls[-1]
                    mean_inv = np.mean(self.inventories)
                    max_dd = np.max(self.drawdowns)
                    cum_reward = float(np.sum(self.rewards)) if self.rewards else 0.0
                    avg_fill_rate = float(np.mean(self.fill_rates)) if self.fill_rates else 0.0

                    pnl_series = np.array(self.pnls, dtype=float)
                    returns = np.diff(pnl_series) if len(pnl_series) > 1 else np.array([0.0])
                    sharpe_like = float((returns.mean() / (returns.std() + 1e-8)) * np.sqrt(252))
                    drawdown_series = np.maximum.accumulate(pnl_series) - pnl_series if len(pnl_series) > 0 else np.array([0.0])
                    max_drawdown = float(drawdown_series.max())

                    # Approximate spread capture efficiency proxy: pnl per unit abs inventory
                    spread_capture_eff = float(final_pnl / (np.mean(self.inventories) + 1e-6)) if self.inventories else 0.0

                    self.logger.record("market_maker/final_pnl", final_pnl)
                    self.logger.record("market_maker/mean_abs_inventory", mean_inv)
                    self.logger.record("market_maker/max_drawdown", max_dd)
                    self.logger.record("market_maker/cumulative_reward", cum_reward)
                    self.logger.record("market_maker/avg_fill_rate", avg_fill_rate)
                    self.logger.record("market_maker/sharpe_like", sharpe_like)
                    self.logger.record("market_maker/drawdown", max_drawdown)
                    self.logger.record("market_maker/spread_capture_eff", spread_capture_eff)
                    
                    self.pnls.clear()
                    self.inventories.clear()
                    self.drawdowns.clear()
                    self.rewards.clear()
                    self.fill_rates.clear()
        return True

def create_env():
    # 1. Initialize heterogeneous market population + RL participant
    agents = [
        RLAgent("RL_MM", initial_capital=100000.0),
        HFTAgent("HFT_1", position_limit=600),
        InformedAgent("INF_1", signal_probability=0.02, signal_accuracy=0.62),
        LiquidityTraderAgent("LIQ_1", start_probability=0.03),
        RetailAgent("RET_1"),
        NoiseAgent("Noise_1", order_rate=0.35),
        NoiseAgent("Noise_2", order_rate=0.45),
    ]
    
    # 2. Build the Simulator logic
    sim = MarketSimulator(agents=agents, initial_price=100.0, duration_seconds=1000)
    
    # 3. Create the Gym Environment matching wrapper
    env = MarketMakerEnv(simulator=sim, rl_agent_id="RL_MM")
    return env

def train():
    print("Setting up the Reinforcement Learning Market-Maker Environment...")
    
    # Needs to be wrapped in DummyVecEnv for SB3 compatibility
    env = DummyVecEnv([create_env])

    print("Initializing PPO Agent...")
    # PPO is robust and easy to tune, standard choice for continuous action spaces.
    model = PPO(
        "MlpPolicy", 
        env, 
        verbose=1, 
        learning_rate=3e-4, 
        n_steps=1000, 
        batch_size=64, 
        tensorboard_log="./tensorboard_logs/"
    )
    
    callback = MetricsLoggerCallback()
    
    # Let's train for 10,000 steps roughly (10 episodes since duration is 1000)
    TOTAL_TIMESTEPS = 10_000
    
    print(f"Starting Training for {TOTAL_TIMESTEPS} timesteps...")
    model.learn(total_timesteps=TOTAL_TIMESTEPS, callback=callback)
    
    print("Training Complete. Saving model...")
    os.makedirs("./models", exist_ok=True)
    model.save("./models/ppo_market_maker")
    
    print("Model saved to `./models/ppo_market_maker.zip`")
    
if __name__ == "__main__":
    train()
