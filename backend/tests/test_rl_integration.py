import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from backend.src.agents.rl_agent import RLAgent
from backend.src.market.simulator import MarketSimulator


def test_rl_agent_routes_quotes_through_simulator_lifecycle():
    rl_agent = RLAgent("RL_MM", initial_capital=100000.0)
    simulator = MarketSimulator(agents=[rl_agent], initial_price=100.0, duration_seconds=10)
    simulator.reset(seed=7)

    rl_agent.set_action([-1.0, 0.0, -1.0])
    simulator.step()
    first_order_ids = set(rl_agent.active_orders.keys())
    book_order_ids = {order.order_id for order in simulator.order_book.bids + simulator.order_book.asks}

    assert simulator.step_count == 1
    assert len(first_order_ids) == 2
    assert first_order_ids.issubset(book_order_ids)
    assert rl_agent.consume_last_cancel_count() == 0

    rl_agent.set_action([1.0, 0.0, 1.0])
    simulator.step()
    second_order_ids = set(rl_agent.active_orders.keys())
    book_order_ids = {order.order_id for order in simulator.order_book.bids + simulator.order_book.asks}

    assert simulator.step_count == 2
    assert len(second_order_ids) == 2
    assert first_order_ids.isdisjoint(second_order_ids)
    assert first_order_ids.isdisjoint(book_order_ids)
    assert second_order_ids.issubset(book_order_ids)
    assert rl_agent.consume_last_cancel_count() == 2
