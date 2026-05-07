'use client';

import React from 'react';
import { useMarketStore } from '@/store/market-store';

export default function LargeOrderDetector() {
  const marketData = useMarketStore((s) => s.marketData);
  const detection = marketData?.large_order_detection;

  if (!detection || !detection.pattern) {
    return (
      <div className="terminal-panel">
        <div className="panel-header">
          <span className="panel-tag">LARGE ORDERS</span>
          <span className="text-xs text-gray-600">● SCANNING</span>
        </div>
        <div className="flex items-center justify-center h-32">
          <div className="text-center">
            <div className="text-gray-600 text-sm font-mono">NO LARGE ORDERS DETECTED</div>
            <div className="text-gray-700 text-xs font-mono mt-1">Monitoring order flow...</div>
          </div>
        </div>
      </div>
    );
  }

  const sideColor = detection.side === 'buy' ? '#00ff41' : '#ff0040';
  const patternLabel = detection.pattern.toUpperCase();

  return (
    <div className="terminal-panel">
      <div className="panel-header">
        <span className="panel-tag">LARGE ORDERS</span>
        <span className="text-xs blink" style={{ color: sideColor }}>
          ● DETECTED
        </span>
      </div>

      <div className="p-3 space-y-3">
        {/* Pattern & Side badges */}
        <div className="flex gap-2 items-center">
          <span
            className="px-2 py-0.5 text-xs font-mono font-bold border"
            style={{ borderColor: '#ffb800', color: '#ffb800' }}
          >
            {patternLabel}
          </span>
          <span
            className="px-2 py-0.5 text-xs font-mono font-bold border"
            style={{ borderColor: sideColor, color: sideColor }}
          >
            {detection.side.toUpperCase()}
          </span>
        </div>

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-2">
          <div className="stat-cell">
            <span className="stat-label">EST. SIZE</span>
            <span className="stat-value text-white">
              {detection.estimated_size.toLocaleString()}
            </span>
          </div>
          <div className="stat-cell">
            <span className="stat-label">CONFIDENCE</span>
            <span className="stat-value" style={{ color: '#ffb800' }}>
              {(detection.confidence * 100).toFixed(0)}%
            </span>
          </div>
        </div>

        {/* Confidence bar */}
        <div className="w-full">
          <div className="h-1 bg-gray-800 w-full">
            <div
              className="h-1 transition-all duration-500"
              style={{
                width: `${detection.confidence * 100}%`,
                backgroundColor: '#ffb800',
                boxShadow: '0 0 8px rgba(255, 184, 0, 0.5)',
              }}
            />
          </div>
        </div>

        {/* Impact prediction */}
        {detection.impact && (
          <div className="border-t border-gray-800 pt-2">
            <div className="text-xs text-gray-600 font-mono mb-1">IMPACT PREDICTION</div>
            <div className="grid grid-cols-2 gap-2">
              <div className="stat-cell">
                <span className="stat-label">IMPACT %</span>
                <span className="stat-value text-red-400">
                  {detection.impact.expected_impact_pct.toFixed(4)}%
                </span>
              </div>
              <div className="stat-cell">
                <span className="stat-label">IMPACT $</span>
                <span className="stat-value text-red-400">
                  ${detection.impact.expected_impact_dollars.toFixed(2)}
                </span>
              </div>
            </div>
            <div className="text-xs font-mono mt-1">
              <span className="text-gray-500">CONDITIONS: </span>
              <span className={
                detection.impact.market_conditions === 'severe' ? 'text-red-400' :
                detection.impact.market_conditions === 'significant' ? 'text-orange-400' :
                'text-yellow-400'
              }>
                {detection.impact.market_conditions.toUpperCase()}
              </span>
            </div>
          </div>
        )}

        {/* TWAP-specific info */}
        {detection.completion_pct !== undefined && (
          <div className="text-xs font-mono text-gray-500">
            COMPLETION: {detection.completion_pct}% | EXECUTED: {detection.executed_so_far?.toLocaleString()}
          </div>
        )}
      </div>
    </div>
  );
}
