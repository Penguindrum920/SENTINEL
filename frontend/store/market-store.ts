import { create } from 'zustand';
import { MarketUpdate, Alert } from '@/types/market';

interface MarketStore {
  marketData: MarketUpdate | null;
  priceHistory: { time: number; price: number; spread: number }[];
  connected: boolean;
  alerts: Alert[];
  simulationRunning: boolean;
  simulationMode: 'SANDBOX' | 'LIVE_SHADOW';

  setMarketData: (data: MarketUpdate) => void;
  setConnected: (connected: boolean) => void;
  addAlert: (alert: Alert) => void;
  dismissAlert: (id: string) => void;
  clearAlerts: () => void;
  resetSimulationData: () => void;
  setSimulationRunning: (running: boolean) => void;
  setSimulationMode: (mode: 'SANDBOX' | 'LIVE_SHADOW') => void;
}

const MAX_PRICE_HISTORY = 240;

export const useMarketStore = create<MarketStore>((set) => ({
  marketData: null,
  priceHistory: [],
  connected: false,
  alerts: [],
  simulationRunning: false,
  simulationMode: 'SANDBOX',

  setMarketData: (data: MarketUpdate) =>
    set((state) => {
      const newPoint = {
        time: data.timestamp,
        price: data.price,
        spread: data.spread,
      };
      const history = [...state.priceHistory, newPoint];
      if (history.length > MAX_PRICE_HISTORY) {
        history.shift();
      }

      // Auto-generate alerts from warning levels
      const newAlerts = [...state.alerts];
      const pred = data.liquidity_prediction;
      if (pred && (pred.warning_level === 'warning' || pred.warning_level === 'critical')) {
        const existing = newAlerts.find(
          (a) => !a.dismissed && a.level === pred.warning_level
        );
        if (!existing) {
          newAlerts.push({
            id: `alert-${Date.now()}`,
            message: `Liquidity ${pred.warning_level.toUpperCase()}: Health ${pred.health_score.toFixed(1)}% | Shock probability ${(pred.probability * 100).toFixed(1)}%`,
            level: pred.warning_level as 'warning' | 'critical',
            timestamp: data.timestamp,
            dismissed: false,
          });
        }
      }

      return {
        marketData: data,
        priceHistory: history,
        alerts: newAlerts.slice(-20), // keep max 20 alerts
        simulationMode: data.mode,
      };
    }),

  setConnected: (connected: boolean) => set({ connected }),

  addAlert: (alert: Alert) =>
    set((state) => ({ alerts: [...state.alerts, alert].slice(-20) })),

  dismissAlert: (id: string) =>
    set((state) => ({
      alerts: state.alerts.map((a) =>
        a.id === id ? { ...a, dismissed: true } : a
      ),
    })),

  clearAlerts: () => set({ alerts: [] }),

  resetSimulationData: () =>
    set({
      marketData: null,
      priceHistory: [],
      alerts: [],
      simulationRunning: false,
    }),

  setSimulationRunning: (running: boolean) => set({ simulationRunning: running }),

  setSimulationMode: (mode: 'SANDBOX' | 'LIVE_SHADOW') => set({ simulationMode: mode }),
}));
