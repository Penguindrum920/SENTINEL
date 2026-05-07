import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backend.src.agents.rl_agent import RLAgent
from backend.src.market.rl_policy import RLPolicyController
from backend.src.market.simulator import MarketSimulator


class StubPolicyModel:
    def __init__(self) -> None:
        self.last_observation = None

    def predict(self, observation, deterministic=True):
        self.last_observation = observation
        return np.array([0.0, 0.0, 0.0], dtype=np.float32), None


class NaNPolicyModel:
    def predict(self, observation, deterministic=True):
        return np.array([np.nan, np.nan, np.nan], dtype=np.float32), None


def test_rl_policy_controller_queues_model_action_for_rl_agent():
    rl_agent = RLAgent("RL_MM", initial_capital=100000.0)
    simulator = MarketSimulator(agents=[rl_agent], initial_price=100.0, duration_seconds=10)
    simulator.reset(seed=11)

    stub_model = StubPolicyModel()
    controller = RLPolicyController(policy_model=stub_model, rl_agent_id="RL_MM")

    action = controller.prepare_step(simulator)
    simulator.step()

    assert action == (0.0, 0.0, 0.0)
    assert stub_model.last_observation.shape == (13,)
    assert len(rl_agent.active_orders) == 2


def test_rl_policy_controller_sanitizes_non_finite_actions():
    rl_agent = RLAgent("RL_MM", initial_capital=100000.0)
    simulator = MarketSimulator(agents=[rl_agent], initial_price=100.0, duration_seconds=10)
    simulator.reset(seed=12)

    controller = RLPolicyController(policy_model=NaNPolicyModel(), rl_agent_id="RL_MM")
    action = controller.prepare_step(simulator)
    simulator.step()

    assert action == (0.0, 0.0, 0.0)
    assert len(rl_agent.active_orders) == 2
