'use client';

import React, { useEffect } from 'react';
import { useMarketStore } from '@/store/market-store';

export default function AlertBanner() {
  const alerts = useMarketStore((s) => s.alerts);
  const dismissAlert = useMarketStore((s) => s.dismissAlert);

  const activeAlerts = alerts.filter((a) => !a.dismissed);
  const latestAlert = activeAlerts[activeAlerts.length - 1];

  // Auto-dismiss caution alerts after 10s
  useEffect(() => {
    const cautions = activeAlerts.filter((a) => a.level === 'caution');
    const timers = cautions.map((a) =>
      setTimeout(() => dismissAlert(a.id), 10000)
    );
    return () => timers.forEach(clearTimeout);
  }, [activeAlerts, dismissAlert]);

  if (!latestAlert) return null;

  const colorMap: Record<string, { bg: string; border: string; text: string }> = {
    caution: { bg: 'rgba(255, 184, 0, 0.08)', border: '#ffb800', text: '#ffb800' },
    warning: { bg: 'rgba(255, 102, 0, 0.08)', border: '#ff6600', text: '#ff6600' },
    critical: { bg: 'rgba(255, 0, 64, 0.1)', border: '#ff0040', text: '#ff0040' },
  };

  const style = colorMap[latestAlert.level] || colorMap.warning;

  return (
    <div
      className="w-full px-4 py-2 flex items-center justify-between font-mono text-xs animate-slideDown"
      style={{
        backgroundColor: style.bg,
        borderBottom: `1px solid ${style.border}`,
      }}
    >
      <div className="flex items-center gap-2">
        <span className="blink" style={{ color: style.text }}>●</span>
        <span style={{ color: style.text }} className="font-bold">
          [{latestAlert.level.toUpperCase()}]
        </span>
        <span className="text-gray-300">{latestAlert.message}</span>
      </div>
      <button
        onClick={() => dismissAlert(latestAlert.id)}
        className="text-gray-500 hover:text-gray-300 px-2"
      >
        ✕
      </button>
    </div>
  );
}
