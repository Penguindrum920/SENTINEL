"""Visualization helpers for market simulation."""

import matplotlib.pyplot as plt
import pandas as pd
import os

def render_market_charts(df: pd.DataFrame, output_dir: str = "."):
    """Renders charts requested in Phase 1: Price, Spread, Imbalance, PnL/Inventory."""
    if df.empty:
        return
        
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Price Chart
    plt.figure(figsize=(10, 6))
    plt.plot(df['step'], df['best_bid'], label='Best Bid', color='green', alpha=0.7)
    plt.plot(df['step'], df['best_ask'], label='Best Ask', color='red', alpha=0.7)
    plt.plot(df['step'], df['mid_price'], label='Mid Price', color='blue')
    plt.title('Prices over Time')
    plt.xlabel('Simulation Step')
    plt.ylabel('Price')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'price_chart.png'))
    plt.close()
    
    # 2. Spread Chart
    plt.figure(figsize=(10, 4))
    plt.plot(df['step'], df['spread'], color='orange', alpha=0.8)
    if 'rolling_spread_10' in df.columns:
        plt.plot(df['step'], df['rolling_spread_10'], color='darkred', label='10-step MA')
    plt.title('Bid-Ask Spread')
    plt.xlabel('Simulation Step')
    plt.ylabel('Spread')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'spread_chart.png'))
    plt.close()
    
    # 3. Order Book Imbalance
    if 'book_imbalance' in df.columns:
        plt.figure(figsize=(10, 4))
        plt.plot(df['step'], df['book_imbalance'], color='purple')
        plt.axhline(0, color='black', linestyle='--')
        plt.title('Order Book Imbalance (Bids - Asks) / Total')
        plt.xlabel('Simulation Step')
        plt.ylabel('Imbalance [-1(Ask) to 1(Bid)]')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.savefig(os.path.join(output_dir, 'imbalance_chart.png'))
        plt.close()
        
def plot_agent_performance(agent_df: pd.DataFrame, agent_id: str, output_dir: str = "."):
    if agent_df.empty:
        return
        
    plt.figure(figsize=(10, 4))
    plt.plot(agent_df['step'], agent_df['position'], color='teal')
    plt.title(f'Agent Inventory over Time: {agent_id}')
    plt.xlabel('Simulation Step')
    plt.ylabel('Position (Shares)')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f'{agent_id}_inventory_chart.png'))
    plt.close()
