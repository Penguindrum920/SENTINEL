"""Agent registry/factory for composing market populations."""

from typing import Dict, Any, List

from .market_maker import MarketMakerAgent
from .noise import NoiseAgent
from .hft_agent import HFTAgent
from .informed import InformedAgent
from .retail import RetailAgent
from .liquidity_trader import LiquidityTraderAgent
from .rl_agent import RLAgent


AGENT_REGISTRY = {
    "market_maker": MarketMakerAgent,
    "noise": NoiseAgent,
    "hft": HFTAgent,
    "informed": InformedAgent,
    "retail": RetailAgent,
    "liquidity": LiquidityTraderAgent,
    "rl": RLAgent,
}


def create_agent(agent_type: str, agent_id: str, **kwargs):
    key = agent_type.lower()
    if key not in AGENT_REGISTRY:
        raise ValueError(f"Unknown agent_type='{agent_type}'. Supported={list(AGENT_REGISTRY.keys())}")
    return AGENT_REGISTRY[key](agent_id=agent_id, **kwargs)


def create_population(configs: List[Dict[str, Any]]):
    """Create agents from list of configs.

    Example item:
      {"type": "noise", "agent_id": "N1", "kwargs": {"order_rate": 0.5}}
    """
    agents = []
    for cfg in configs:
        a_type = cfg["type"]
        a_id = cfg["agent_id"]
        kwargs = cfg.get("kwargs", {})
        agents.append(create_agent(a_type, a_id, **kwargs))
    return agents
