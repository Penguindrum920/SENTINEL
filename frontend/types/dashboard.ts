export type ProjectStage = 'Research Prototype' | 'System Integration' | 'Training and Evaluation';

export interface SimulationMetrics {
  midPrice: number;
  bestBid: number;
  bestAsk: number;
  spread: number;
  orderBookImbalance: number;
  inventory: number;
  realizedPnl: number;
  unrealizedPnl: number;
  cumulativeReward: number;
}

export interface TimeSeriesPoint {
  time: string;
  value: number;
}

export interface PriceSpreadPoint {
  time: string;
  price: number;
  spread: number;
}

export interface TradeFlowPoint {
  time: string;
  buyVolume: number;
  sellVolume: number;
}

export interface DepthHeatLevel {
  level: number;
  bidDepth: number;
  askDepth: number;
}

export interface RecentOrder {
  id: string;
  agent: 'Market Maker' | 'Noise Agent' | 'RL Agent';
  side: 'BUY' | 'SELL';
  price: number;
  quantity: number;
  status: 'Submitted' | 'Filled' | 'Cancelled' | 'Partial Fill';
}

export interface ExecutionSummary {
  submitted: number;
  fills: number;
  cancelled: number;
  matchRate: number;
}

export interface AgentActivity {
  marketMakerAction: string;
  noiseAgentAction: string;
  rlAgentStatus: string;
  recentOrders: RecentOrder[];
  executionSummary: ExecutionSummary;
}

export type MilestoneStatus = 'completed' | 'in-progress' | 'pending';

export interface Milestone {
  phase: string;
  title: string;
  status: MilestoneStatus;
  detail: string;
}

export interface KernelEvent {
  id: string;
  time: string;
  type:
    | 'Kernel'
    | 'Order Submission'
    | 'Order Match'
    | 'Fill'
    | 'Cancellation'
    | 'Latency';
  message: string;
  severity: 'info' | 'warning' | 'critical';
}

export interface ProjectOverview {
  name: string;
  summary: string;
  currentStage: ProjectStage;
  completed: string[];
  inProgress: string[];
}

export interface SimulationDashboardData {
  projectOverview: ProjectOverview;
  metrics: SimulationMetrics;
  priceSeries: PriceSpreadPoint[];
  spreadSeries: TimeSeriesPoint[];
  inventorySeries: TimeSeriesPoint[];
  rewardSeries: TimeSeriesPoint[];
  depthHeatmap: DepthHeatLevel[];
  tradeFlow: TradeFlowPoint[];
  agentActivity: AgentActivity;
  milestones: Milestone[];
  events: KernelEvent[];
  connected: boolean;
}
