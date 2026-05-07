// ── SENTINEL Market Types ──────────────────────────────────────────────────

export interface OrderLevel {
  price: number;
  size: number;
}

export interface OrderBook {
  bids: OrderLevel[];
  asks: OrderLevel[];
}

export interface LiquidityPrediction {
  probability: number;
  health_score: number;
  warning_level: "safe" | "caution" | "warning" | "critical";
  features: Record<string, number>;
  timestamp: number;
}

export interface LargeOrderDetection {
  pattern: "iceberg" | "twap";
  side: "buy" | "sell";
  estimated_size: number;
  confidence: number;
  completion_pct?: number;
  executed_so_far?: number;
  avg_interval?: number;
  avg_order_size?: number;
  detected_orders?: number;
  impact?: {
    expected_impact_pct: number;
    expected_impact_dollars: number;
    size_vs_depth_ratio: number;
    market_conditions: string;
  };
}

export interface AgentMetric {
  total_pnl: number;
  realized_pnl: number;
  unrealized_pnl: number;
  sharpe_ratio: number;
  agent_type: string;
  position: number;
  num_trades: number;
}

export interface MarketUpdate {
  type: "market_update";
  timestamp: number;
  price: number;
  spread: number;
  depth: number;
  order_book: OrderBook;
  liquidity_prediction: LiquidityPrediction;
  large_order_detection: LargeOrderDetection | null;
  agent_metrics: Record<string, AgentMetric>;
  step: number;
  volatility: number;
  mode: "SANDBOX" | "LIVE_SHADOW";
}

export interface Alert {
  id: string;
  message: string;
  level: "caution" | "warning" | "critical";
  timestamp: number;
  dismissed: boolean;
}
