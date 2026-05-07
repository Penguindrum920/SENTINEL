'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import type {
  AgentActivity,
  KernelEvent,
  Milestone,
  ProjectOverview,
  TradeFlowPoint,
} from '@/types/dashboard';
import AlertBanner from '@/components/AlertBanner';
import PriceChart from '@/components/PriceChart';
import LiquidityGauge from '@/components/LiquidityGauge';
import LargeOrderDetector from '@/components/LargeOrderDetector';
import OrderBookHeatmap from '@/components/OrderBookHeatmap';
import AgentMetricsPanel from '@/components/AgentMetricsPanel';
import { useMarketWebSocket } from '@/lib/websocket';
import { useSimulationDashboardData } from '@/lib/mock-simulation';
import { api } from '@/lib/api-client';
import { useMarketStore } from '@/store/market-store';

type MetricTone = 'positive' | 'negative' | 'warning' | 'accent' | 'neutral';

function finiteNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function sumFinite<T>(items: T[], selector: (item: T) => unknown): number {
  return items.reduce((sum, item) => sum + finiteNumber(selector(item), 0), 0);
}

function formatClock(value: number): string {
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const seconds = Math.floor(value % 60);
  return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds
    .toString()
    .padStart(2, '0')}`;
}

function formatSigned(value: number, digits = 2): string {
  if (!Number.isFinite(value)) {
    return '—';
  }
  return `${value >= 0 ? '+' : '-'}${Math.abs(value).toFixed(digits)}`;
}

function toneClass(tone: MetricTone): string {
  if (tone === 'positive') return 'text-[#00ff41]';
  if (tone === 'negative') return 'text-[#ff0040]';
  if (tone === 'warning') return 'text-[#ffb800]';
  if (tone === 'accent') return 'text-[#00bfff]';
  return 'text-gray-200';
}

function milestoneClass(status: Milestone['status']): string {
  if (status === 'completed') return 'border-[#00ff41] text-[#00ff41]';
  if (status === 'in-progress') return 'border-[#ffb800] text-[#ffb800]';
  return 'border-gray-700 text-gray-500';
}

function eventClass(severity: KernelEvent['severity']): string {
  if (severity === 'critical') return 'border-l-[#ff0040]';
  if (severity === 'warning') return 'border-l-[#ffb800]';
  return 'border-l-[#00bfff]';
}

function feedStateLabel(connected: boolean, simulationRunning: boolean, activeLabel: string): string {
  if (!connected) return 'BACKEND OFFLINE';
  if (!simulationRunning) return 'SIM PAUSED';
  return activeLabel;
}

function TerminalOverviewPanel({ overview }: { overview: ProjectOverview }) {
  return (
    <div className="terminal-panel h-full">
      <div className="panel-header">
        <span className="panel-tag">SYSTEM BRIEF</span>
        <span className="border border-[#00bfff] px-2 py-0.5 text-[10px] font-bold tracking-[0.14em] text-[#00bfff]">
          {overview.currentStage.toUpperCase()}
        </span>
      </div>

      <div className="space-y-4 p-3">
        <div>
          <div className="text-[10px] tracking-[0.16em] text-gray-500">MISSION</div>
          <div className="mt-1 text-sm leading-6 text-gray-200">{overview.summary}</div>
        </div>

        <div className="grid gap-3 lg:grid-cols-2">
          <div className="border border-gray-900 bg-black/30 p-3">
            <div className="text-[10px] tracking-[0.16em] text-[#00ff41]">ONLINE MODULES</div>
            <div className="mt-2 space-y-2 text-xs text-gray-300">
              {overview.completed.map((item) => (
                <div key={item} className="flex items-start gap-2">
                  <span className="mt-0.5 text-[#00ff41]">+</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="border border-gray-900 bg-black/30 p-3">
            <div className="text-[10px] tracking-[0.16em] text-[#ffb800]">ACTIVE WORKSTREAMS</div>
            <div className="mt-2 space-y-2 text-xs text-gray-300">
              {overview.inProgress.map((item) => (
                <div key={item} className="flex items-start gap-2">
                  <span className="mt-0.5 text-[#ffb800]">&gt;</span>
                  <span>{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function TerminalMilestonesPanel({ milestones }: { milestones: Milestone[] }) {
  return (
    <div className="terminal-panel h-full">
      <div className="panel-header">
        <span className="panel-tag">PROGRAM TRACKER</span>
        <span className="text-[10px] tracking-[0.16em] text-gray-500">{milestones.length} PHASES</span>
      </div>

      <div className="space-y-2 p-3">
        {milestones.map((milestone) => (
          <div key={milestone.phase} className="border border-gray-900 bg-black/30 p-3">
            <div className="flex items-center justify-between gap-3">
              <div className="text-xs text-gray-100">
                {milestone.phase} / {milestone.title}
              </div>
              <span
                className={`border px-2 py-0.5 text-[10px] font-bold tracking-[0.14em] ${milestoneClass(
                  milestone.status,
                )}`}
              >
                {milestone.status.toUpperCase()}
              </span>
            </div>
            <div className="mt-2 text-xs leading-5 text-gray-400">{milestone.detail}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function TerminalEventPanel({
  events,
  connected,
  simulationRunning,
}: {
  events: KernelEvent[];
  connected: boolean;
  simulationRunning: boolean;
}) {
  const statusLabel = feedStateLabel(connected, simulationRunning, 'LIVE FEED');
  const emptyLabel = !connected ? 'BACKEND OFFLINE' : 'EVENT STREAM IDLE';

  return (
    <div className="terminal-panel h-full">
      <div className="panel-header">
        <span className="panel-tag">KERNEL EVENT TAPE</span>
        <span className="text-[10px] tracking-[0.16em] text-gray-500">{statusLabel}</span>
      </div>

      <div className="max-h-[340px] space-y-2 overflow-auto p-3">
        {events.length === 0 ? (
          <div className="border border-dashed border-gray-800 px-3 py-6 text-center text-xs tracking-[0.14em] text-gray-600">
            {emptyLabel}
          </div>
        ) : (
          events.map((event) => (
            <div
              key={event.id}
              className={`border border-gray-900 border-l-2 bg-black/30 p-3 ${eventClass(event.severity)}`}
            >
              <div className="flex items-center justify-between gap-3 text-[10px] tracking-[0.14em]">
                <span className="text-gray-500">{event.type.toUpperCase()}</span>
                <span className="text-gray-600">{event.time}</span>
              </div>
              <div className="mt-1 text-xs text-gray-200">{event.message}</div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function TerminalTradeFlowPanel({
  data,
  connected,
  simulationRunning,
}: {
  data: TradeFlowPoint[];
  connected: boolean;
  simulationRunning: boolean;
}) {
  const rows = data.slice(-8).reverse();
  const peakVolume = Math.max(
    1,
    ...rows.flatMap((row) => [row.buyVolume, row.sellVolume]),
  );
  const statusLabel = feedStateLabel(connected, simulationRunning, 'BUY VS SELL');
  const emptyLabel = !connected ? 'BACKEND OFFLINE' : 'FLOW BUFFER IDLE';

  return (
    <div className="terminal-panel h-full">
      <div className="panel-header">
        <span className="panel-tag">FLOW LADDER</span>
        <span className="text-[10px] tracking-[0.16em] text-gray-500">{statusLabel}</span>
      </div>

      <div className="space-y-2 p-3">
        {rows.length === 0 ? (
          <div className="border border-dashed border-gray-800 px-3 py-6 text-center text-xs tracking-[0.14em] text-gray-600">
            {emptyLabel}
          </div>
        ) : (
          rows.map((row) => (
            <div key={row.time} className="space-y-1 border border-gray-900 bg-black/30 p-2">
              <div className="flex items-center justify-between text-[10px] tracking-[0.14em] text-gray-500">
                <span>{row.time}</span>
                <span>
                  B {row.buyVolume} / S {row.sellVolume}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="h-2 bg-gray-950">
                  <div
                    className="h-full bg-[#00ff41]"
                    style={{ width: `${(row.buyVolume / peakVolume) * 100}%` }}
                  />
                </div>
                <div className="h-2 bg-gray-950">
                  <div
                    className="ml-auto h-full bg-[#ff0040]"
                    style={{ width: `${(row.sellVolume / peakVolume) * 100}%` }}
                  />
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function TerminalActivityPanel({
  activity,
  connected,
  simulationRunning,
}: {
  activity: AgentActivity;
  connected: boolean;
  simulationRunning: boolean;
}) {
  const statusLabel = feedStateLabel(connected, simulationRunning, 'AGENT TRACE');

  return (
    <div className="terminal-panel h-full">
      <div className="panel-header">
        <span className="panel-tag">EXECUTION MONITOR</span>
        <span className="text-[10px] tracking-[0.16em] text-gray-500">{statusLabel}</span>
      </div>

      <div className="grid gap-3 p-3 xl:grid-cols-[0.95fr_1.1fr]">
        <div className="space-y-3">
          <div className="border border-gray-900 bg-black/30 p-3">
            <div className="text-[10px] tracking-[0.16em] text-gray-500">MARKET MAKER</div>
            <div className="mt-1 text-xs text-gray-200">{activity.marketMakerAction}</div>
          </div>
          <div className="border border-gray-900 bg-black/30 p-3">
            <div className="text-[10px] tracking-[0.16em] text-gray-500">NOISE AGENT</div>
            <div className="mt-1 text-xs text-gray-200">{activity.noiseAgentAction}</div>
          </div>
          <div className="border border-gray-900 bg-black/30 p-3">
            <div className="text-[10px] tracking-[0.16em] text-gray-500">RL POLICY</div>
            <div className="mt-1 text-xs text-gray-200">{activity.rlAgentStatus}</div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="border border-gray-900 bg-black/30 p-3">
              <div className="text-[10px] tracking-[0.16em] text-gray-500">SUBMITTED</div>
              <div className="mt-1 text-lg font-bold text-[#00bfff]">
                {activity.executionSummary.submitted}
              </div>
            </div>
            <div className="border border-gray-900 bg-black/30 p-3">
              <div className="text-[10px] tracking-[0.16em] text-gray-500">MATCH RATE</div>
              <div className="mt-1 text-lg font-bold text-[#00ff41]">
                {activity.executionSummary.matchRate}%
              </div>
            </div>
            <div className="border border-gray-900 bg-black/30 p-3">
              <div className="text-[10px] tracking-[0.16em] text-gray-500">FILLS</div>
              <div className="mt-1 text-lg font-bold text-[#00ff41]">
                {activity.executionSummary.fills}
              </div>
            </div>
            <div className="border border-gray-900 bg-black/30 p-3">
              <div className="text-[10px] tracking-[0.16em] text-gray-500">CANCELS</div>
              <div className="mt-1 text-lg font-bold text-[#ffb800]">
                {activity.executionSummary.cancelled}
              </div>
            </div>
          </div>
        </div>

        <div className="border border-gray-900 bg-black/30">
          <div className="grid grid-cols-12 gap-2 border-b border-gray-900 px-3 py-2 text-[10px] tracking-[0.14em] text-gray-500">
            <div className="col-span-2">ID</div>
            <div className="col-span-3">AGENT</div>
            <div className="col-span-1 text-center">SD</div>
            <div className="col-span-2 text-right">PX</div>
            <div className="col-span-2 text-right">QTY</div>
            <div className="col-span-2 text-right">STATUS</div>
          </div>
          <div className="max-h-[260px] overflow-auto">
            {activity.recentOrders.length === 0 ? (
              <div className="px-3 py-6 text-center text-xs tracking-[0.14em] text-gray-600">
                {!connected ? 'BACKEND OFFLINE' : 'NO ACTIVE AGENT TRACE'}
              </div>
            ) : (
              activity.recentOrders.map((order) => (
                <div
                  key={order.id}
                  className="grid grid-cols-12 gap-2 border-b border-gray-950 px-3 py-2 text-xs text-gray-300"
                >
                  <div className="col-span-2 text-gray-500">{order.id}</div>
                  <div className="col-span-3 truncate">{order.agent}</div>
                  <div
                    className={`col-span-1 text-center ${
                      order.side === 'BUY' ? 'text-[#00ff41]' : 'text-[#ff0040]'
                    }`}
                  >
                    {order.side === 'BUY' ? 'B' : 'S'}
                  </div>
                  <div className="col-span-2 text-right">{order.price.toFixed(3)}</div>
                  <div className="col-span-2 text-right">{order.quantity}</div>
                  <div
                    className={`col-span-2 text-right ${
                      order.status === 'Filled'
                        ? 'text-[#00ff41]'
                        : order.status === 'Cancelled'
                          ? 'text-[#ff0040]'
                          : order.status === 'Partial Fill'
                            ? 'text-[#ffb800]'
                            : 'text-[#00bfff]'
                    }`}
                  >
                    {order.status.toUpperCase()}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  useMarketWebSocket();

  const dashboard = useSimulationDashboardData();
  const marketData = useMarketStore((state) => state.marketData);
  const connected = useMarketStore((state) => state.connected);
  const simulationRunning = useMarketStore((state) => state.simulationRunning);
  const resetSimulationData = useMarketStore((state) => state.resetSimulationData);
  const setSimulationRunning = useMarketStore((state) => state.setSimulationRunning);
  const simulationMode = useMarketStore((state) => state.simulationMode);
  const setSimulationMode = useMarketStore((state) => state.setSimulationMode);

  const [currentTime, setCurrentTime] = useState('');

  useEffect(() => {
    let cancelled = false;

    const syncHealth = async () => {
      try {
        const health = await api.health();
        if (cancelled) {
          return;
        }
        setSimulationRunning(health.simulation_active);
        setSimulationMode(health.mode);
        if (!health.simulation_active) {
          resetSimulationData();
        }
      } catch {
        // Ignore health sync failures and let websocket state drive the shell.
      }
    };

    void syncHealth();

    return () => {
      cancelled = true;
    };
  }, [resetSimulationData, setSimulationMode, setSimulationRunning]);

  useEffect(() => {
    setCurrentTime(new Date().toLocaleTimeString());
    const timer = setInterval(() => setCurrentTime(new Date().toLocaleTimeString()), 1000);
    return () => clearInterval(timer);
  }, []);

  const handleStartStop = async () => {
    try {
      if (simulationRunning) {
        await api.stopSimulation();
        resetSimulationData();
        setSimulationRunning(false);
      } else {
        resetSimulationData();
        await api.startSimulation();
        setSimulationRunning(true);
      }
    } catch (error) {
      console.error('Simulation control error:', error);
    }
  };

  const handleModeToggle = async () => {
    const nextMode = simulationMode === 'SANDBOX' ? 'LIVE_SHADOW' : 'SANDBOX';
    try {
      await api.setSimulationMode(nextMode);
      setSimulationMode(nextMode);
    } catch (error) {
      console.error('Failed to change mode:', error);
    }
  };

  const bids = marketData?.order_book?.bids ?? [];
  const asks = marketData?.order_book?.asks ?? [];
  const bidDepth = bids.reduce((sum, level) => sum + level.size, 0);
  const askDepth = asks.reduce((sum, level) => sum + level.size, 0);
  const depth = marketData?.depth ?? (bidDepth + askDepth > 0 ? bidDepth + askDepth : null);
  const midPrice = marketData?.price ?? null;
  const spread =
    bids[0]?.price != null && asks[0]?.price != null
      ? Math.max(0, asks[0].price - bids[0].price)
      : marketData?.spread ?? null;
  const derivedBid = midPrice != null && spread != null ? midPrice - spread / 2 : null;
  const derivedAsk = midPrice != null && spread != null ? midPrice + spread / 2 : null;
  const bestBid = bids[0]?.price ?? derivedBid;
  const bestAsk = asks[0]?.price ?? derivedAsk;
  const imbalance =
    bidDepth + askDepth > 0
      ? (bidDepth - askDepth) / (bidDepth + askDepth)
      : null;
  const liveAgentMetrics = Object.values(marketData?.agent_metrics ?? {});
  const inventory = sumFinite(liveAgentMetrics, (agent) => agent.position);
  const realizedPnl = sumFinite(liveAgentMetrics, (agent) => agent.realized_pnl);
  const unrealizedPnl = sumFinite(liveAgentMetrics, (agent) => agent.unrealized_pnl);
  const totalPnl = realizedPnl + unrealizedPnl;
  const hasMarketSnapshot = marketData !== null;
  const midLabel = hasMarketSnapshot && midPrice != null ? `$${midPrice.toFixed(2)}` : '--';
  const depthLabel = hasMarketSnapshot && depth != null ? depth.toLocaleString() : '—';

  const metricCells = useMemo(
    () => [
      {
        label: 'BID/ASK',
        value:
          bestBid != null && bestAsk != null
            ? `${bestBid.toFixed(2)} / ${bestAsk.toFixed(2)}`
            : '—',
        tone: 'neutral' as const,
      },
      {
        label: 'SPREAD',
        value: spread != null ? spread.toFixed(4) : '—',
        tone:
          spread == null
            ? ('neutral' as const)
            : spread > 0.1
              ? ('warning' as const)
              : ('accent' as const),
      },
      {
        label: 'IMBALANCE',
        value: imbalance != null ? formatSigned(imbalance, 3) : '—',
        tone:
          imbalance == null
            ? ('neutral' as const)
            : imbalance >= 0
              ? ('positive' as const)
              : ('negative' as const),
      },
      {
        label: 'DEPTH',
        value: depthLabel,
        tone: 'neutral' as const,
      },
      {
        label: 'INVENTORY',
        value: hasMarketSnapshot ? inventory.toLocaleString() : '—',
        tone:
          !hasMarketSnapshot
            ? ('neutral' as const)
            : inventory >= 0
              ? ('accent' as const)
              : ('warning' as const),
      },
      {
        label: 'REALIZED PNL',
        value: hasMarketSnapshot ? formatSigned(realizedPnl) : '—',
        tone:
          !hasMarketSnapshot
            ? ('neutral' as const)
            : realizedPnl >= 0
              ? ('positive' as const)
              : ('negative' as const),
      },
      {
        label: 'UNREALIZED PNL',
        value: hasMarketSnapshot ? formatSigned(unrealizedPnl) : '—',
        tone:
          !hasMarketSnapshot
            ? ('neutral' as const)
            : unrealizedPnl >= 0
              ? ('positive' as const)
              : ('negative' as const),
      },
      {
        label: 'TOTAL PNL',
        value: hasMarketSnapshot ? formatSigned(totalPnl) : '—',
        tone:
          !hasMarketSnapshot
            ? ('neutral' as const)
            : totalPnl >= 0
              ? ('positive' as const)
              : ('negative' as const),
      },
    ],
    [
      bestAsk,
      bestBid,
      depthLabel,
      hasMarketSnapshot,
      inventory,
      imbalance,
      realizedPnl,
      spread,
      totalPnl,
      unrealizedPnl,
    ],
  );

  return (
    <div className="min-h-screen bg-black font-mono text-white">
      <AlertBanner />

      <header className="border-b border-gray-800 bg-black/95 px-4 py-2">
        <div className="flex flex-col gap-2 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <div className="h-2 w-2 rotate-45 bg-amber-400" />
              <span className="text-sm font-bold tracking-[0.28em] text-amber-400">SENTINEL</span>
            </div>
            <span className="hidden text-[11px] tracking-[0.18em] text-gray-600 sm:inline">
              SMART EARLY-WARNING NETWORK FOR TRADING
            </span>
            <span className="border border-gray-800 px-2 py-0.5 text-[10px] tracking-[0.16em] text-cyan-400">
              {dashboard.projectOverview.currentStage.toUpperCase()}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-[11px] tracking-[0.12em] text-gray-500">
            <span>
              SIM TIME:{' '}
              <span className="text-gray-300">
                {marketData ? formatClock(marketData.timestamp) : '--:--:--'}
              </span>
            </span>
            <span>
              MID:{' '}
              <span className="text-gray-200">{midLabel}</span>
            </span>
            <span>
              STEP:{' '}
              <span className="text-gray-300">{marketData?.step?.toLocaleString() ?? '0'}</span>
            </span>
            <span>
              MODELED DEPTH:{' '}
              <span className="text-cyan-400">{depthLabel}</span>
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-1.5 text-xs">
              <span className={connected ? 'blink text-[#00ff41]' : 'text-[#ff0040]'}>●</span>
              <span className="text-gray-500">{connected ? 'CONNECTED' : 'DISCONNECTED'}</span>
            </div>

            <Link
              href="/sandbox"
              className="border border-[#00bfff] bg-[rgba(0,191,255,0.08)] px-3 py-1 text-xs font-bold tracking-[0.12em] text-[#00bfff] transition-colors hover:bg-[rgba(0,191,255,0.18)]"
            >
              SANDBOX →
            </Link>

            <button
              onClick={handleModeToggle}
              className="border px-3 py-1 text-xs font-bold tracking-[0.12em] transition-colors"
              style={{
                borderColor: simulationMode === 'SANDBOX' ? '#00ff41' : '#ffb800',
                color: simulationMode === 'SANDBOX' ? '#00ff41' : '#ffb800',
                backgroundColor:
                  simulationMode === 'SANDBOX'
                    ? 'rgba(0, 255, 65, 0.08)'
                    : 'rgba(255, 184, 0, 0.08)',
              }}
            >
              {simulationMode === 'SANDBOX' ? 'MODE: SANDBOX' : 'MODE: LIVE SHADOW'}
            </button>

            <button
              onClick={handleStartStop}
              className="border px-3 py-1 text-xs font-bold tracking-[0.12em] transition-colors"
              style={{
                borderColor: simulationRunning ? '#ff0040' : '#00ff41',
                color: simulationRunning ? '#ff0040' : '#00ff41',
                backgroundColor: simulationRunning
                  ? 'rgba(255, 0, 64, 0.08)'
                  : 'rgba(0, 255, 65, 0.08)',
              }}
            >
              {simulationRunning ? 'STOP SIM' : 'START SIM'}
            </button>
          </div>
        </div>
      </header>

      <section className="grid grid-cols-2 gap-px border-b border-gray-900 bg-gray-900 sm:grid-cols-4 xl:grid-cols-8">
        {metricCells.map((metric) => (
          <div key={metric.label} className="bg-black/95 px-3 py-2">
            <div className="text-[10px] tracking-[0.16em] text-gray-500">{metric.label}</div>
            <div className={`mt-1 text-sm font-semibold ${toneClass(metric.tone)}`}>{metric.value}</div>
          </div>
        ))}
      </section>

      <main className="grid min-h-[calc(100vh-116px)] grid-cols-12 gap-2 p-2 pb-12">
        <div className="col-span-12 xl:col-span-8">
          <PriceChart />
        </div>
        <div className="col-span-12 md:col-span-6 xl:col-span-2">
          <LiquidityGauge />
        </div>
        <div className="col-span-12 md:col-span-6 xl:col-span-2">
          <LargeOrderDetector />
        </div>

        <div className="col-span-12 lg:col-span-4">
          <TerminalOverviewPanel overview={dashboard.projectOverview} />
        </div>
        <div className="col-span-12 lg:col-span-4">
          <TerminalMilestonesPanel milestones={dashboard.milestones} />
        </div>
        <div className="col-span-12 lg:col-span-4">
          <TerminalEventPanel
            events={dashboard.events}
            connected={connected}
            simulationRunning={simulationRunning}
          />
        </div>

        <div className="col-span-12 lg:col-span-4">
          <OrderBookHeatmap />
        </div>
        <div className="col-span-12 lg:col-span-8">
          <AgentMetricsPanel />
        </div>

        <div className="col-span-12 lg:col-span-4">
          <TerminalTradeFlowPanel
            data={dashboard.tradeFlow}
            connected={connected}
            simulationRunning={simulationRunning}
          />
        </div>
        <div className="col-span-12 lg:col-span-8">
          <TerminalActivityPanel
            activity={dashboard.agentActivity}
            connected={connected}
            simulationRunning={simulationRunning}
          />
        </div>
      </main>

      <footer className="fixed bottom-0 left-0 right-0 z-50 flex justify-between border-t border-gray-800 bg-black px-4 py-1 text-xs text-gray-600">
        <span>SENTINEL v2.0 TERMINAL</span>
        <span>
          {marketData
            ? `$${marketData.price.toFixed(2)} | SPR ${marketData.spread.toFixed(4)} | DEPTH ${marketData.depth.toLocaleString()} | VOL ${marketData.volatility.toFixed(4)}`
            : simulationRunning
              ? 'SYNCING LIVE FEED...'
              : `SIM IDLE | STAGE ${dashboard.projectOverview.currentStage.toUpperCase()}`}
        </span>
        <span>{currentTime}</span>
      </footer>
    </div>
  );
}
