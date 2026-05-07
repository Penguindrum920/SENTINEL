"""Testing the Phase 1, 2, and 3 simulator components and making visualizations."""

import os
import sys

# Append backend to path so we can import modules for testing locally
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'src'))

from backend.src.market.simulator import MarketSimulator
from backend.src.agents.noise import NoiseAgent
from backend.src.agents.market_maker import MarketMakerAgent
from backend.src.agents.hft_agent import HFTAgent
from backend.src.agents.informed import InformedAgent
from backend.src.agents.retail import RetailAgent
from backend.src.agents.liquidity_trader import LiquidityTraderAgent
from backend.src.utils.metrics import calculate_market_metrics, extract_agent_pnl
from backend.src.utils.visualization import render_market_charts, plot_agent_performance

def run_simulation():
    print("Initializing Market Simulation...")
    
    # Setup Phase 2 Agents
    agents = [
        MarketMakerAgent("MM_1", initial_capital=100000.0),
        HFTAgent("HFT_1", position_limit=300),
        InformedAgent("INF_1", signal_probability=0.02, signal_accuracy=0.60),
        LiquidityTraderAgent("LIQ_1", start_probability=0.04),
        RetailAgent("RET_1"),
        NoiseAgent("Noise_1", order_rate=0.5),
        NoiseAgent("Noise_2", order_rate=0.5)
    ]
    
    sim = MarketSimulator(agents=agents, initial_price=100.0, duration_seconds=500)
    
    print("Running 500 steps of simulation...")
    results = sim.run()
    
    print("Simulation Complete!")
    print(f"Final Price: {results['final_price']}")
    print(f"Total Trades: {results['total_trades']}")
    
    # Calculate Phase 1/2 Metrics & Visualizations 
    print("Calculating metrics and generating structural charts...")
    historical_state = sim._state_history
    
    # Calculate overarching metrics dataframe
    market_df = calculate_market_metrics(historical_state)
    
    if not market_df.empty:
        os.makedirs("output", exist_ok=True)
        render_market_charts(market_df, "output")
        print("Generated structural charts (Phase 1):")
        print(" -> output/price_chart.png")
        print(" -> output/spread_chart.png")
        print(" -> output/imbalance_chart.png")
        
    # Phase 2 Agent Tracking
    agent_id = "MM_1"
    agent_df = extract_agent_pnl(historical_state, agent_id)
    if not agent_df.empty:
        plot_agent_performance(agent_df, agent_id, output_dir="output")
        print(f"Generated agent performance chart (Phase 2):")
        print(f" -> output/{agent_id}_inventory_chart.png")

if __name__ == "__main__":
    run_simulation()
