'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  ScatterChart, Scatter, Cell, ComposedChart, ReferenceLine
} from 'recharts';

/* ─── Types ─────────────────────────────────────────────── */
interface Preset {
  name: string;
  description: string;
  icon: string;
  agents: Record<string, number>;
  oracle: boolean;
  latency: string;
}

interface AgentMetric {
  total_pnl: number;
  realized_pnl: number;
  unrealized_pnl: number;
  sharpe_ratio: number;
  agent_type: string;
  position: number;
  num_trades: number;
}

interface MarketUpdate {
  type: string;
  timestamp: number;
  price: number;
  spread: number;
  depth: number;
  order_book: { bids: any[]; asks: any[] };
  liquidity_prediction: any;
  large_order_detection: any;
  agent_metrics: Record<string, AgentMetric>;
  step: number;
  volatility: number;
  mode: string;
  speed: number;
  oracle?: { fundamental_value: number; mispricing: number; mispricing_pct: number };
}

/* ─── Constants ─────────────────────────────────────────── */
const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
const SPEEDS = [0.5, 1, 2, 5, 10];
const AGENT_COLORS: Record<string, string> = {
  MarketMaker: '#00ff41', HFT: '#00bfff', Institutional: '#a855f7',
  Retail: '#ffb800', Informed: '#ff6b6b', Noise: '#6b7280',
  Momentum: '#f97316', MeanReversion: '#06b6d4', Spoofing: '#ef4444',
  Sentiment: '#ec4899', RL_MM: '#10b981', LiquidityTrader: '#8b5cf6',
};

/* ─── Page ──────────────────────────────────────────────── */
const ALL_AGENT_TYPES = ['MarketMaker','HFT','Institutional','Retail','Informed','Noise','Momentum','MeanReversion','Spoofing','Sentiment'];
const PERIODS = ['1d','5d','1mo','3mo','6mo','1y','2y'];
const INTERVALS = ['1m','5m','15m','1h','1d','1wk'];

export default function SandboxPage() {
  const [presets, setPresets] = useState<Record<string, Preset>>({});
  const [selectedPreset, setSelectedPreset] = useState('balanced');
  const [running, setRunning] = useState(false);
  const [connected, setConnected] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [oracleEnabled, setOracleEnabled] = useState(false);
  const [latencyMode, setLatencyMode] = useState('deterministic');
  const [initialPrice, setInitialPrice] = useState(100);
  const [sidebarTab, setSidebarTab] = useState<'preset'|'custom'|'stock'>('preset');

  // Custom agent builder
  const [customCounts, setCustomCounts] = useState<Record<string,number>>(
    Object.fromEntries(ALL_AGENT_TYPES.map(t => [t, 0]))
  );
  const [useCustomAgents, setUseCustomAgents] = useState(false);

  // Stock replay
  const [stockTicker, setStockTicker] = useState('AAPL');
  const [stockPeriod, setStockPeriod] = useState('3mo');
  const [stockInterval, setStockInterval] = useState('1d');
  const [stockInfo, setStockInfo] = useState<any>(null);
  const [stockLoading, setStockLoading] = useState(false);
  const [stockError, setStockError] = useState('');
  const [replayMode, setReplayMode] = useState(false);

  // Market data
  const [priceHistory, setPriceHistory] = useState<any[]>([]);
  const [latestUpdate, setLatestUpdate] = useState<MarketUpdate | null>(null);
  const [agentMetrics, setAgentMetrics] = useState<Record<string, AgentMetric>>({});
  const wsRef = useRef<WebSocket | null>(null);
  const bufferRef = useRef<MarketUpdate | null>(null);

  // Load presets on mount
  useEffect(() => {
    fetch(`${API}/api/sandbox/presets`).then(r => r.json()).then(setPresets).catch(() => {
      setPresets({
        minimal: { name: 'Minimal', description: '10 agents', icon: '⚡', agents: { MarketMaker: 1, HFT: 2, Noise: 3, Retail: 2, Informed: 1, Sentiment: 1 }, oracle: false, latency: 'deterministic' },
        balanced: { name: 'Balanced', description: '40 agents', icon: '⚖️', agents: { MarketMaker: 3, HFT: 2, Institutional: 2, Retail: 10, Informed: 3, Noise: 10, Momentum: 2, MeanReversion: 2, Spoofing: 1, Sentiment: 5 }, oracle: false, latency: 'deterministic' },
        institutional: { name: 'Institutional', description: '80 agents', icon: '🏦', agents: { MarketMaker: 5, HFT: 4, Institutional: 8, Retail: 15, Informed: 5, Noise: 20, Momentum: 8, MeanReversion: 5, Spoofing: 2, Sentiment: 8 }, oracle: true, latency: 'cubic' },
        stress_test: { name: 'Stress Test', description: '200 agents', icon: '🔥', agents: { MarketMaker: 8, HFT: 10, Institutional: 5, Retail: 30, Informed: 10, Noise: 100, Momentum: 12, MeanReversion: 10, Spoofing: 3, Sentiment: 12 }, oracle: true, latency: 'cubic' },
      });
    });
  }, []);

  // WebSocket connection
  useEffect(() => {
    if (!running) return;
    const ws = new WebSocket(`${WS_URL}/ws`);
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);
    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.type === 'market_update') bufferRef.current = data;
      } catch {}
    };
    // Flush buffer at ~4 Hz
    const flush = setInterval(() => {
      const d = bufferRef.current;
      if (!d) return;
      bufferRef.current = null;
      setLatestUpdate(d);
      setAgentMetrics(d.agent_metrics || {});
      setPriceHistory(prev => {
        const next = [...prev, {
          time: d.step,
          price: d.price,
          spread: d.spread,
          fundamental: d.oracle?.fundamental_value ?? null,
        }];
        return next.length > 300 ? next.slice(-300) : next;
      });
    }, 250);
    return () => { ws.close(); clearInterval(flush); };
  }, [running]);

  // Fetch stock info
  const fetchStock = useCallback(async () => {
    setStockLoading(true); setStockError('');
    try {
      const r = await fetch(`${API}/api/sandbox/stock/fetch`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker: stockTicker, period: stockPeriod, interval: stockInterval }),
      });
      const d = await r.json();
      if (d.error) { setStockError(d.error); setStockInfo(null); }
      else { setStockInfo(d); }
    } catch { setStockError('Network error'); }
    finally { setStockLoading(false); }
  }, [stockTicker, stockPeriod, stockInterval]);

  // Start stock replay
  const startReplay = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/sandbox/stock/replay`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker: stockTicker, period: stockPeriod, interval: stockInterval,
          preset: selectedPreset, latency_mode: latencyMode, speed,
          custom_agents: useCustomAgents ? customCounts : undefined,
        }),
      });
      const d = await r.json();
      if (!d.error) { setPriceHistory([]); setLatestUpdate(null); setReplayMode(true); setRunning(true); }
      else setStockError(d.error);
    } catch { setStockError('Failed to start replay'); }
  }, [stockTicker, stockPeriod, stockInterval, selectedPreset, latencyMode, speed, useCustomAgents, customCounts]);

  // Start sandbox
  const startSandbox = useCallback(async () => {
    const customAgents = useCustomAgents
      ? Object.fromEntries(Object.entries(customCounts).filter(([,v]) => v > 0))
      : undefined;
    try {
      await fetch(`${API}/api/sandbox/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          preset: useCustomAgents ? 'custom' : selectedPreset,
          initial_price: initialPrice,
          oracle_enabled: oracleEnabled,
          latency_mode: latencyMode,
          speed,
          custom_agents: customAgents,
        }),
      });
      setPriceHistory([]);
      setLatestUpdate(null);
      setReplayMode(false);
      setRunning(true);
    } catch (err) { console.error('Failed to start sandbox', err); }
  }, [selectedPreset, initialPrice, oracleEnabled, latencyMode, speed, useCustomAgents, customCounts]);

  // Stop
  const stopSandbox = useCallback(async () => {
    try { await fetch(`${API}/api/simulation/stop`, { method: 'POST' }); } catch {}
    setRunning(false);
    setConnected(false);
  }, []);

  // Speed change
  const changeSpeed = useCallback(async (s: number) => {
    setSpeed(s);
    if (running) {
      try { await fetch(`${API}/api/sandbox/speed`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ speed: s }) }); } catch {}
    }
  }, [running]);

  // Derived data
  const preset = presets[selectedPreset];
  const totalAgents = preset ? Object.values(preset.agents).reduce((a, b) => a + b, 0) : 0;
  const u = latestUpdate;

  // Agent scatter data
  const scatterData = Object.entries(agentMetrics).map(([id, m]) => ({
    id, x: m.position, y: m.total_pnl, type: m.agent_type, trades: m.num_trades,
  }));

  // Agent type aggregates
  const typeAgg: Record<string, { pnl: number; count: number; sharpe: number }> = {};
  Object.values(agentMetrics).forEach(m => {
    if (!typeAgg[m.agent_type]) typeAgg[m.agent_type] = { pnl: 0, count: 0, sharpe: 0 };
    typeAgg[m.agent_type].pnl += m.total_pnl;
    typeAgg[m.agent_type].count += 1;
    typeAgg[m.agent_type].sharpe += m.sharpe_ratio;
  });

  // Depth data
  const depthBids = (u?.order_book?.bids || []).map((b: any) => ({ price: b.price, size: -b.size })).reverse();
  const depthAsks = (u?.order_book?.asks || []).map((a: any) => ({ price: a.price, size: a.size }));
  const depthData = [...depthBids, ...depthAsks];

  return (
    <div className="min-h-screen bg-[#0a0a0f] text-[#e0e0e0] font-mono">
      {/* ─── Header ─── */}
      <header className="border-b border-[#1a1a2e] px-6 py-3 flex items-center justify-between bg-[#0d0d15]/90 backdrop-blur-md sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#00ff41] to-[#00bfff] flex items-center justify-center text-black font-bold text-sm">S</div>
          <div>
            <h1 className="text-lg font-bold bg-gradient-to-r from-[#00ff41] to-[#00bfff] bg-clip-text text-transparent">SENTINEL SANDBOX</h1>
            <p className="text-[10px] text-[#6b7280] -mt-0.5">Interactive Market Simulation Engine</p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <a href="/dashboard" className="text-[#6b7280] hover:text-[#00bfff] transition-colors">← Dashboard</a>
          <span className={`flex items-center gap-1.5 ${connected ? 'text-[#00ff41]' : 'text-[#ff0040]'}`}>
            <span className={`w-2 h-2 rounded-full ${connected ? 'bg-[#00ff41] animate-pulse' : 'bg-[#ff0040]'}`}></span>
            {connected ? 'LIVE' : 'OFFLINE'}
          </span>
          {u && <span className="text-[#00bfff]">Step {u.step}</span>}
          {u && <span className="text-[#ffb800]">${u.price?.toFixed(2)}</span>}
        </div>
      </header>

      <div className="flex h-[calc(100vh-52px)]">
        {/* ─── Left Sidebar: Controls ─── */}
        <aside className="w-80 border-r border-[#1a1a2e] flex-shrink-0 flex flex-col bg-[#0d0d15]/50">
          {/* Tab headers */}
          <div className="flex border-b border-[#1a1a2e]">
            {([['preset','⚙ Preset'],['custom','🎛 Custom'],['stock','📈 Stock']] as const).map(([tab, label]) => (
              <button key={tab} onClick={() => setSidebarTab(tab)}
                className={`flex-1 py-2.5 text-[10px] font-bold tracking-widest uppercase transition-all ${sidebarTab === tab ? 'text-[#00ff41] border-b-2 border-[#00ff41]' : 'text-[#6b7280] hover:text-[#a0a0b0]'}`}>
                {label}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">

            {/* ── TAB: PRESETS ── */}
            {sidebarTab === 'preset' && (<>
              <section>
                <h3 className="text-[10px] uppercase tracking-widest text-[#6b7280] mb-2">Simulation Preset</h3>
                <div className="space-y-2">
                  {Object.entries(presets).map(([key, p]) => (
                    <button key={key} onClick={() => { setSelectedPreset(key); setUseCustomAgents(false); if (p.oracle !== undefined) setOracleEnabled(p.oracle); if (p.latency) setLatencyMode(p.latency); }}
                      className={`w-full text-left p-3 rounded-lg border transition-all duration-200 ${selectedPreset === key && !useCustomAgents ? 'border-[#00ff41]/50 bg-[#00ff41]/5 shadow-[0_0_15px_rgba(0,255,65,0.1)]' : 'border-[#1a1a2e] bg-[#111118] hover:border-[#2a2a3e]'}`}>
                      <div className="flex items-center gap-2">
                        <span className="text-lg">{p.icon}</span>
                        <div>
                          <div className="text-sm font-semibold text-white">{p.name}</div>
                          <div className="text-[10px] text-[#6b7280]">{p.description}</div>
                        </div>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-1">
                        {Object.entries(p.agents).slice(0,5).map(([t,c]) => (
                          <span key={t} className="text-[9px] px-1.5 py-0.5 rounded" style={{ background: (AGENT_COLORS[t]||'#6b7280')+'22', color: AGENT_COLORS[t]||'#6b7280', border: `1px solid ${(AGENT_COLORS[t]||'#6b7280')}44` }}>
                            {t.slice(0,4)} ×{c}
                          </span>
                        ))}
                      </div>
                    </button>
                  ))}
                </div>
              </section>

              <section>
                <h3 className="text-[10px] uppercase tracking-widest text-[#6b7280] mb-2">Parameters</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-[10px] text-[#6b7280]">Initial Price ($)</label>
                    <input type="number" value={initialPrice} onChange={e => setInitialPrice(+e.target.value)} disabled={running}
                      className="w-full mt-1 px-3 py-1.5 rounded bg-[#111118] border border-[#1a1a2e] text-white text-xs focus:border-[#00ff41] outline-none" />
                  </div>
                  <div className="flex items-center justify-between">
                    <label className="text-[10px] text-[#6b7280]">Oracle (OU Fundamental)</label>
                    <button onClick={() => setOracleEnabled(!oracleEnabled)} disabled={running}
                      className={`w-10 h-5 rounded-full transition-all duration-300 relative ${oracleEnabled ? 'bg-[#00ff41]' : 'bg-[#2a2a3e]'}`}>
                      <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all duration-300 ${oracleEnabled ? 'left-5' : 'left-0.5'}`}></span>
                    </button>
                  </div>
                  <div>
                    <label className="text-[10px] text-[#6b7280]">Latency Model</label>
                    <select value={latencyMode} onChange={e => setLatencyMode(e.target.value)} disabled={running}
                      className="w-full mt-1 px-3 py-1.5 rounded bg-[#111118] border border-[#1a1a2e] text-white text-xs focus:border-[#00ff41] outline-none">
                      <option value="zero">Zero (Instant)</option>
                      <option value="deterministic">Deterministic</option>
                      <option value="cubic">Cubic (ABIDES-style)</option>
                    </select>
                  </div>
                </div>
              </section>
            </>)}

            {/* ── TAB: CUSTOM AGENTS ── */}
            {sidebarTab === 'custom' && (<>
              <section>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-[10px] uppercase tracking-widest text-[#6b7280]">Build Your Market</h3>
                  <span className="text-[10px] text-[#00ff41] font-bold">{Object.values(customCounts).reduce((a,b)=>a+b,0)} agents</span>
                </div>
                <div className="space-y-3">
                  {ALL_AGENT_TYPES.map(type => (
                    <div key={type}>
                      <div className="flex items-center justify-between mb-1">
                        <div className="flex items-center gap-2">
                          <span className="w-2 h-2 rounded-full" style={{ background: AGENT_COLORS[type]||'#6b7280' }}></span>
                          <span className="text-[11px] text-[#a0a0b0]">{type}</span>
                        </div>
                        <span className="text-[11px] font-bold text-white w-6 text-right">{customCounts[type]}</span>
                      </div>
                      <input type="range" min={0} max={type === 'Noise' ? 100 : type === 'Retail' ? 50 : 20} value={customCounts[type]}
                        onChange={e => setCustomCounts(prev => ({ ...prev, [type]: +e.target.value }))}
                        disabled={running}
                        className="w-full h-1.5 rounded-full appearance-none cursor-pointer"
                        style={{ accentColor: AGENT_COLORS[type]||'#00ff41' }}
                      />
                    </div>
                  ))}
                </div>
              </section>

              <section>
                <h3 className="text-[10px] uppercase tracking-widest text-[#6b7280] mb-2">Parameters</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-[10px] text-[#6b7280]">Initial Price ($)</label>
                    <input type="number" value={initialPrice} onChange={e => setInitialPrice(+e.target.value)} disabled={running}
                      className="w-full mt-1 px-3 py-1.5 rounded bg-[#111118] border border-[#1a1a2e] text-white text-xs focus:border-[#00ff41] outline-none" />
                  </div>
                  <div>
                    <label className="text-[10px] text-[#6b7280]">Latency Model</label>
                    <select value={latencyMode} onChange={e => setLatencyMode(e.target.value)} disabled={running}
                      className="w-full mt-1 px-3 py-1.5 rounded bg-[#111118] border border-[#1a1a2e] text-white text-xs focus:border-[#00ff41] outline-none">
                      <option value="zero">Zero (Instant)</option>
                      <option value="deterministic">Deterministic</option>
                      <option value="cubic">Cubic (ABIDES-style)</option>
                    </select>
                  </div>
                </div>
              </section>

              <button onClick={() => { setUseCustomAgents(true); startSandbox(); }} disabled={running || Object.values(customCounts).every(v=>v===0)}
                className="w-full py-3 rounded-lg font-bold text-sm uppercase tracking-wider bg-gradient-to-r from-[#a855f7] to-[#00bfff] text-white disabled:opacity-40 hover:shadow-[0_0_20px_rgba(168,85,247,0.3)] transition-all duration-300">
                ▶  Launch Custom Market
              </button>
            </>)}

            {/* ── TAB: STOCK REPLAY ── */}
            {sidebarTab === 'stock' && (<>
              <section>
                <h3 className="text-[10px] uppercase tracking-widest text-[#6b7280] mb-3">Real Stock Replay</h3>
                <p className="text-[10px] text-[#6b7280] mb-3 leading-relaxed">Import real historical OHLCV data. Agents trade against the actual price path — see what might have happened.</p>

                <div className="space-y-3">
                  <div>
                    <label className="text-[10px] text-[#6b7280]">Ticker Symbol</label>
                    <div className="flex gap-2 mt-1">
                      <input value={stockTicker} onChange={e => setStockTicker(e.target.value.toUpperCase())} disabled={running}
                        placeholder="AAPL, TSLA, ^NSEI..."
                        className="flex-1 px-3 py-1.5 rounded bg-[#111118] border border-[#1a1a2e] text-white text-xs focus:border-[#00bfff] outline-none uppercase" />
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <label className="text-[10px] text-[#6b7280]">Period</label>
                      <select value={stockPeriod} onChange={e => setStockPeriod(e.target.value)} disabled={running}
                        className="w-full mt-1 px-2 py-1.5 rounded bg-[#111118] border border-[#1a1a2e] text-white text-xs focus:border-[#00bfff] outline-none">
                        {PERIODS.map(p => <option key={p}>{p}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="text-[10px] text-[#6b7280]">Interval</label>
                      <select value={stockInterval} onChange={e => setStockInterval(e.target.value)} disabled={running}
                        className="w-full mt-1 px-2 py-1.5 rounded bg-[#111118] border border-[#1a1a2e] text-white text-xs focus:border-[#00bfff] outline-none">
                        {INTERVALS.map(i => <option key={i}>{i}</option>)}
                      </select>
                    </div>
                  </div>

                  <button onClick={fetchStock} disabled={stockLoading || running}
                    className="w-full py-2 rounded-lg text-[11px] font-bold border border-[#00bfff]/50 text-[#00bfff] hover:bg-[#00bfff]/10 disabled:opacity-40 transition-all">
                    {stockLoading ? '⏳ Fetching...' : '🔍 Preview Data'}
                  </button>

                  {stockError && <div className="text-[10px] text-[#ff0040] bg-[#ff0040]/10 border border-[#ff0040]/30 rounded p-2">{stockError}</div>}

                  {stockInfo && (
                    <div className="rounded-lg border border-[#1a1a2e] bg-[#111118] p-3 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-bold text-white">{stockInfo.ticker}</span>
                        <span className="text-[10px] text-[#6b7280]">{stockInfo.currency}</span>
                      </div>
                      <div className="text-[10px] text-[#a0a0b0]">{stockInfo.name}</div>
                      <div className="grid grid-cols-2 gap-2 text-[10px]">
                        <div><span className="text-[#6b7280]">Last Close</span><div className="text-[#00ff41] font-bold">${stockInfo.last_close?.toFixed(2)}</div></div>
                        <div><span className="text-[#6b7280]">Bars</span><div className="text-white font-bold">{stockInfo.bars}</div></div>
                        <div><span className="text-[#6b7280]">Realized Vol</span><div className="text-[#ffb800] font-bold">{(stockInfo.realized_vol*100).toFixed(1)}%</div></div>
                        <div><span className="text-[#6b7280]">Period</span><div className="text-white">{stockInfo.period_start} → {stockInfo.period_end?.slice(5)}</div></div>
                      </div>
                      {stockInfo.price_preview?.length > 1 && (
                        <div className="mt-2 h-16">
                          <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={stockInfo.price_preview.map((p: number, i: number) => ({ i, p }))}>
                              <Line type="monotone" dataKey="p" stroke="#00bfff" strokeWidth={1.5} dot={false} />
                            </LineChart>
                          </ResponsiveContainer>
                        </div>
                      )}
                    </div>
                  )}

                  <div>
                    <label className="text-[10px] text-[#6b7280]">Agent Preset for Replay</label>
                    <select value={selectedPreset} onChange={e => setSelectedPreset(e.target.value)} disabled={running}
                      className="w-full mt-1 px-3 py-1.5 rounded bg-[#111118] border border-[#1a1a2e] text-white text-xs focus:border-[#00bfff] outline-none">
                      {Object.entries(presets).map(([k,p]) => <option key={k} value={k}>{p.name} ({Object.values(p.agents).reduce((a,b)=>a+b,0)} agents)</option>)}
                    </select>
                  </div>

                  <button onClick={startReplay} disabled={running || !stockInfo}
                    className="w-full py-3 rounded-lg font-bold text-sm uppercase tracking-wider bg-gradient-to-r from-[#00bfff] to-[#a855f7] text-white disabled:opacity-40 hover:shadow-[0_0_20px_rgba(0,191,255,0.3)] transition-all duration-300">
                    {running && replayMode ? '■ Stop Replay' : '▶  Launch Replay'}
                  </button>
                </div>
              </section>
            </>)}

          </div>

          {/* Shared footer: speed + launch (only for preset/custom tabs) */}
          {sidebarTab !== 'stock' && (
            <div className="p-4 border-t border-[#1a1a2e] space-y-3">
              <div>
                <div className="text-[10px] uppercase tracking-widest text-[#6b7280] mb-2">Simulation Speed</div>
                <div className="flex gap-1">
                  {SPEEDS.map(s => (
                    <button key={s} onClick={() => changeSpeed(s)}
                      className={`flex-1 py-1.5 rounded text-[10px] font-bold transition-all ${speed === s ? 'bg-[#00ff41] text-black shadow-[0_0_10px_rgba(0,255,65,0.3)]' : 'bg-[#111118] text-[#6b7280] hover:bg-[#1a1a2e]'}`}>
                      {s}×
                    </button>
                  ))}
                </div>
              </div>
              {sidebarTab === 'preset' && (
                <button onClick={running ? stopSandbox : startSandbox}
                  className={`w-full py-3 rounded-lg font-bold text-sm uppercase tracking-wider transition-all duration-300 ${running ? 'bg-[#ff0040] text-white hover:bg-[#cc0033] shadow-[0_0_20px_rgba(255,0,64,0.3)]' : 'bg-gradient-to-r from-[#00ff41] to-[#00bfff] text-black hover:shadow-[0_0_20px_rgba(0,255,65,0.3)]'}`}>
                  {running ? '■  Stop Simulation' : '▶  Launch Sandbox'}
                </button>
              )}
            </div>
          )}
          {sidebarTab === 'stock' && running && (
            <div className="p-4 border-t border-[#1a1a2e]">
              <button onClick={stopSandbox} className="w-full py-3 rounded-lg font-bold text-sm uppercase tracking-wider bg-[#ff0040] text-white hover:bg-[#cc0033] shadow-[0_0_20px_rgba(255,0,64,0.3)] transition-all">
                ■  Stop Replay
              </button>
            </div>
          )}
        </aside>


        {/* ─── Main Area ─── */}
        <main className="flex-1 overflow-y-auto p-4 space-y-4">
          {!running && !latestUpdate ? (
            /* Landing state */
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="text-6xl mb-4">🔬</div>
              <h2 className="text-2xl font-bold bg-gradient-to-r from-[#00ff41] to-[#00bfff] bg-clip-text text-transparent mb-2">SENTINEL Sandbox</h2>
              <p className="text-[#6b7280] text-sm max-w-md">Configure your simulation preset, tune parameters, and launch an interactive multi-agent market microstructure sandbox powered by ABIDES-inspired discrete event simulation.</p>
              <div className="mt-6 grid grid-cols-3 gap-4 text-xs">
                {['Real-time Order Book', 'Agent PnL Scatter', 'Oracle Price Overlay'].map(f => (
                  <div key={f} className="px-4 py-3 rounded-lg border border-[#1a1a2e] bg-[#111118]">
                    <span className="text-[#00bfff]">{f}</span>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Live visualization */
            <>
              {/* Metric Strip */}
              <div className="grid grid-cols-6 gap-3">
                {[
                  { label: 'PRICE', value: `$${u?.price?.toFixed(2) || '--'}`, color: '#00ff41' },
                  { label: 'SPREAD', value: u?.spread?.toFixed(4) || '--', color: '#ffb800' },
                  { label: 'DEPTH', value: u?.depth?.toLocaleString() || '--', color: '#00bfff' },
                  { label: 'VOLATILITY', value: u?.volatility?.toFixed(4) || '--', color: '#a855f7' },
                  { label: 'SPEED', value: `${u?.speed || 1}×`, color: '#f97316' },
                  { label: 'HEALTH', value: u?.liquidity_prediction?.health_score?.toFixed(0) || '--', color: u?.liquidity_prediction?.warning_level === 'safe' ? '#00ff41' : u?.liquidity_prediction?.warning_level === 'caution' ? '#ffb800' : '#ff0040' },
                ].map(m => (
                  <div key={m.label} className="p-3 rounded-lg border border-[#1a1a2e] bg-[#111118]/80">
                    <div className="text-[9px] uppercase tracking-widest text-[#6b7280]">{m.label}</div>
                    <div className="text-lg font-bold mt-0.5" style={{ color: m.color }}>{m.value}</div>
                  </div>
                ))}
              </div>

              {/* Price Chart with Oracle Overlay */}
              <div className="rounded-lg border border-[#1a1a2e] bg-[#111118]/80 p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs uppercase tracking-widest text-[#6b7280]">Price Chart {oracleEnabled && '+ Fundamental Value'}</h3>
                  {u?.oracle && (
                    <span className={`text-xs px-2 py-0.5 rounded ${u.oracle.mispricing > 0 ? 'bg-[#ff0040]/20 text-[#ff0040]' : 'bg-[#00ff41]/20 text-[#00ff41]'}`}>
                      Mispricing: {u.oracle.mispricing_pct > 0 ? '+' : ''}{u.oracle.mispricing_pct.toFixed(2)}%
                    </span>
                  )}
                </div>
                <ResponsiveContainer width="100%" height={280}>
                  <ComposedChart data={priceHistory}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
                    <XAxis dataKey="time" stroke="#3a3a4e" tick={{ fontSize: 10, fill: '#6b7280' }} />
                    <YAxis domain={['auto', 'auto']} stroke="#3a3a4e" tick={{ fontSize: 10, fill: '#6b7280' }} />
                    <Tooltip 
                      contentStyle={{ background: '#111118', border: '1px solid #2a2a3e', borderRadius: 8, fontSize: 11 }} 
                      itemStyle={{ color: '#e0e0e0' }}
                      labelStyle={{ color: '#a0a0b0' }}
                    />
                    <Area type="monotone" dataKey="spread" fill="#ffb800" fillOpacity={0.1} stroke="none" />
                    <Line type="monotone" dataKey="price" stroke="#00ff41" strokeWidth={2} dot={false} />
                    {oracleEnabled && <Line type="monotone" dataKey="fundamental" stroke="#a855f7" strokeWidth={1.5} dot={false} strokeDasharray="5 3" />}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              <div className="grid grid-cols-2 gap-4">
                {/* Order Book Depth */}
                <div className="rounded-lg border border-[#1a1a2e] bg-[#111118]/80 p-4">
                  <h3 className="text-xs uppercase tracking-widest text-[#6b7280] mb-2">Order Book Depth</h3>
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart data={depthData} layout="horizontal">
                      <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
                      <XAxis dataKey="price" tick={{ fontSize: 9, fill: '#6b7280' }} stroke="#3a3a4e" />
                      <YAxis tick={{ fontSize: 9, fill: '#6b7280' }} stroke="#3a3a4e" />
                      <Tooltip 
                        contentStyle={{ background: '#111118', border: '1px solid #2a2a3e', borderRadius: 8, fontSize: 11 }} 
                        itemStyle={{ color: '#e0e0e0' }}
                        labelStyle={{ color: '#a0a0b0' }}
                      />
                      <Bar dataKey="size">
                        {depthData.map((entry: any, i: number) => (
                          <Cell key={i} fill={entry.size < 0 ? '#00ff41' : '#ff0040'} fillOpacity={0.7} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>

                {/* Agent Position/PnL Scatter */}
                <div className="rounded-lg border border-[#1a1a2e] bg-[#111118]/80 p-4">
                  <h3 className="text-xs uppercase tracking-widest text-[#6b7280] mb-2">Agent Scatter (Position × PnL)</h3>
                  <ResponsiveContainer width="100%" height={220}>
                    <ScatterChart>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1a1a2e" />
                      <XAxis dataKey="x" name="Position" tick={{ fontSize: 9, fill: '#6b7280' }} stroke="#3a3a4e" />
                      <YAxis dataKey="y" name="PnL" tick={{ fontSize: 9, fill: '#6b7280' }} stroke="#3a3a4e" />
                      <Tooltip 
                        contentStyle={{ background: '#111118', border: '1px solid #2a2a3e', borderRadius: 8, fontSize: 11 }}
                        itemStyle={{ color: '#e0e0e0' }}
                        labelStyle={{ color: '#a0a0b0' }}
                        formatter={(val: number, name: string) => [typeof val === 'number' ? val.toFixed(2) : val, name]} 
                      />
                      <ReferenceLine y={0} stroke="#3a3a4e" />
                      <ReferenceLine x={0} stroke="#3a3a4e" />
                      <Scatter data={scatterData}>
                        {scatterData.map((d, i) => (
                          <Cell key={i} fill={AGENT_COLORS[d.type] || '#6b7280'} />
                        ))}
                      </Scatter>
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Agent Type Performance Table */}
              <div className="rounded-lg border border-[#1a1a2e] bg-[#111118]/80 p-4">
                <h3 className="text-xs uppercase tracking-widest text-[#6b7280] mb-3">Agent Performance by Type</h3>
                <div className="grid grid-cols-5 gap-2 text-[10px] uppercase text-[#6b7280] mb-2 px-2">
                  <span>Type</span><span className="text-right">Count</span><span className="text-right">Total PnL</span><span className="text-right">Avg PnL</span><span className="text-right">Avg Sharpe</span>
                </div>
                {Object.entries(typeAgg).sort((a, b) => b[1].pnl - a[1].pnl).map(([type, agg]) => (
                  <div key={type} className="grid grid-cols-5 gap-2 text-xs px-2 py-1.5 rounded hover:bg-[#1a1a2e]/50 transition-colors">
                    <span className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full" style={{ background: AGENT_COLORS[type] || '#6b7280' }}></span>
                      {type}
                    </span>
                    <span className="text-right text-[#a0a0b0]">{agg.count}</span>
                    <span className={`text-right font-medium ${agg.pnl >= 0 ? 'text-[#00ff41]' : 'text-[#ff0040]'}`}>
                      {agg.pnl >= 0 ? '+' : ''}{agg.pnl.toFixed(2)}
                    </span>
                    <span className={`text-right ${agg.pnl / agg.count >= 0 ? 'text-[#00ff41]' : 'text-[#ff0040]'}`}>
                      {(agg.pnl / agg.count).toFixed(2)}
                    </span>
                    <span className="text-right text-[#a0a0b0]">{(agg.sharpe / agg.count).toFixed(3)}</span>
                  </div>
                ))}
              </div>

              {/* Large Order Detection */}
              {u?.large_order_detection?.pattern && (
                <div className="rounded-lg border border-[#ffb800]/30 bg-[#ffb800]/5 p-4 animate-pulse">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">🔍</span>
                    <div>
                      <div className="text-sm font-bold text-[#ffb800] uppercase">{u.large_order_detection.pattern} Detected</div>
                      <div className="text-xs text-[#a0a0b0]">
                        Side: {u.large_order_detection.side} | Est. Size: {u.large_order_detection.estimated_size?.toLocaleString()} |
                        Confidence: {(u.large_order_detection.confidence * 100).toFixed(0)}%
                        {u.large_order_detection.impact && ` | Impact: ${u.large_order_detection.impact.market_conditions}`}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
