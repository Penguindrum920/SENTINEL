'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useMarketStore } from '@/store/market-store';
import { MarketUpdate } from '@/types/market';
import { getWsBaseUrl } from '@/lib/runtime-config';

const MAX_RETRIES = 5;

export function useMarketWebSocket() {
  const wsRef = useRef<WebSocket | null>(null);
  const retriesRef = useRef(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const flushTimerRef = useRef<NodeJS.Timeout | null>(null);
  const latestUpdateRef = useRef<MarketUpdate | null>(null);

  const setMarketData = useMarketStore((s) => s.setMarketData);
  const setConnected = useMarketStore((s) => s.setConnected);

  const flushLatestUpdate = useCallback(() => {
    flushTimerRef.current = null;
    if (latestUpdateRef.current) {
      setMarketData(latestUpdateRef.current);
      latestUpdateRef.current = null;
    }
  }, [setMarketData]);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(`${getWsBaseUrl()}/ws`);
      wsRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
        retriesRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data: MarketUpdate = JSON.parse(event.data);
          if (data.type === 'market_update') {
            latestUpdateRef.current = data;
            if (!flushTimerRef.current) {
              flushTimerRef.current = setTimeout(flushLatestUpdate, 250);
            }
          }
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;

        // Exponential backoff reconnect
        if (retriesRef.current < MAX_RETRIES) {
          const delay = Math.min(1000 * Math.pow(2, retriesRef.current), 16000);
          retriesRef.current++;
          timerRef.current = setTimeout(connect, delay);
        }
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      setConnected(false);
    }
  }, [flushLatestUpdate, setConnected]);

  const disconnect = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (flushTimerRef.current) clearTimeout(flushTimerRef.current);
    flushTimerRef.current = null;
    latestUpdateRef.current = null;
    if (wsRef.current) wsRef.current.close();
    wsRef.current = null;
    setConnected(false);
  }, [setConnected]);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { connect, disconnect };
}
