"""Metrics calculation for market and agent performance."""

import pandas as pd
import numpy as np

def calculate_market_metrics(state_history: list) -> pd.DataFrame:
    """Converts the raw state history dictionaries into a DataFrame and calculates summary metrics."""
    if not state_history:
        return pd.DataFrame()
        
    df = pd.DataFrame(state_history)
    
    # Calculate rolling spread
    if 'spread' in df.columns:
        df['rolling_spread_10'] = df['spread'].rolling(10).mean()
        
    # Calculate log returns of the mid price
    if 'mid_price' in df.columns:
        df['log_return'] = np.log(df['mid_price'] / df['mid_price'].shift(1))
        df['rolling_volatility'] = df['log_return'].rolling(20).std() * np.sqrt(252 * 390)
        
    # Calculate book imbalance
    if 'bid_depth' in df.columns and 'ask_depth' in df.columns:
        df['book_imbalance'] = (df['bid_depth'] - df['ask_depth']) / (df['bid_depth'] + df['ask_depth']).replace(0, 1)

    return df

def extract_agent_pnl(state_history: list, agent_id: str) -> pd.DataFrame:
    """Extracts the timeseries PnL and inventory for a specific agent."""
    records = []
    for state in state_history:
        step = state.get('step', 0)
        agents = state.get('agents', {})
        agent_data = agents.get(agent_id, {})
        
        position = agent_data.get('position', 0)
        # Using inventory_ratio roughly mapped back or directly extract if pos is there
        records.append({
            'step': step,
            'position': position,
            'inventory_ratio': agent_data.get('inventory_ratio', 0.0)
        })
    return pd.DataFrame(records)
