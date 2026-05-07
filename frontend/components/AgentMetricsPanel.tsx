'use client';

import React, { useState } from 'react';
import { useMarketStore } from '@/store/market-store';

const AGENT_COLORS: Record<string, string> = {
  MarketMaker: '#00ff41',
  HFT: '#00bfff',
  Institutional: '#ffb800',
  Retail: '#ff6600',
  Informed: '#bf00ff',
  Noise: '#666666',
};

function finiteNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

export default function AgentMetricsPanel() {
  const [expanded, setExpanded] = useState(true);
  const marketData = useMarketStore((s) => s.marketData);
  const agents = marketData?.agent_metrics ?? {};

  const agentList = Object.entries(agents).sort((a, b) => {
    // Sort by agent type, then by PnL
    const typeComp = a[1].agent_type.localeCompare(b[1].agent_type);
    if (typeComp !== 0) return typeComp;
    return finiteNumber(b[1].total_pnl) - finiteNumber(a[1].total_pnl);
  });

  const totalPnl = agentList.reduce((sum, [, metrics]) => sum + finiteNumber(metrics.total_pnl), 0);
  const totalAbsPosition = agentList.reduce(
    (sum, [, metrics]) => sum + Math.abs(finiteNumber(metrics.position)),
    0,
  );
  const totalTrades = agentList.reduce((sum, [, metrics]) => sum + finiteNumber(metrics.num_trades), 0);

  return (
    <div className="terminal-panel">
      <div
        className="panel-header cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="panel-tag">AGENTS</span>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-gray-500">
            {agentList.length} ACTIVE
          </span>
          <span className="text-xs text-gray-600">
            {expanded ? '▼' : '▶'}
          </span>
        </div>
      </div>

      {expanded && (
        <div className="overflow-auto max-h-80">
          {/* Table header */}
          <div className="grid grid-cols-12 gap-1 px-2 py-1 text-xs font-mono text-gray-600 border-b border-gray-800 sticky top-0 bg-black">
            <div className="col-span-3">AGENT</div>
            <div className="col-span-2">TYPE</div>
            <div className="col-span-2 text-right">PNL</div>
            <div className="col-span-2 text-right">SHARPE</div>
            <div className="col-span-2 text-right">POSITION</div>
            <div className="col-span-1 text-right">TRD</div>
          </div>

          {/* Agent rows */}
          {agentList.map(([id, metrics]) => {
            const color = AGENT_COLORS[metrics.agent_type] || '#888';
            const totalPnl = finiteNumber(metrics.total_pnl);
            const sharpeRatio = finiteNumber(metrics.sharpe_ratio);
            const position = finiteNumber(metrics.position);
            const numTrades = finiteNumber(metrics.num_trades);
            const pnlColor = totalPnl >= 0 ? '#00ff41' : '#ff0040';

            return (
              <div
                key={id}
                className="grid grid-cols-12 gap-1 px-2 py-0.5 text-xs font-mono border-b border-gray-900 hover:bg-gray-900/50"
              >
                <div className="col-span-3 text-gray-300 truncate">{id}</div>
                <div className="col-span-2" style={{ color }}>
                  {metrics.agent_type.substring(0, 6).toUpperCase()}
                </div>
                <div className="col-span-2 text-right" style={{ color: pnlColor }}>
                  {totalPnl >= 0 ? '+' : ''}
                  {totalPnl.toFixed(0)}
                </div>
                <div className="col-span-2 text-right text-gray-300">
                  {sharpeRatio.toFixed(2)}
                </div>
                <div className="col-span-2 text-right text-gray-400">
                  {position.toLocaleString()}
                </div>
                <div className="col-span-1 text-right text-gray-500">
                  {numTrades}
                </div>
              </div>
            );
          })}

          {/* Summary row */}
          {agentList.length > 0 && (
            <div className="grid grid-cols-12 gap-1 px-2 py-1 text-xs font-mono border-t border-gray-700 bg-gray-900/30">
              <div className="col-span-3 text-gray-500">TOTAL</div>
              <div className="col-span-2 text-gray-500">{agentList.length}</div>
              <div className="col-span-2 text-right" style={{
                color: totalPnl >= 0 ? '#00ff41' : '#ff0040'
              }}>
                {totalPnl.toFixed(0)}
              </div>
              <div className="col-span-2 text-right text-gray-500">—</div>
              <div className="col-span-2 text-right text-gray-500">
                {totalAbsPosition.toLocaleString()}
              </div>
              <div className="col-span-1 text-right text-gray-500">
                {totalTrades}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
