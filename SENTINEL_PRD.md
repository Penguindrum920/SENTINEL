# SENTINEL — Product Requirements Document
**Smart Early-warning Network for Trading, Institutional orders, and Liquidity Events**

**Version:** 4.0 | **Stack:** Next.js 14 · TypeScript · Tailwind CSS · Python FastAPI · Google Stitch MCP UI Components · Zerodha Kite API  
**Target:** Production-ready handoff for Claude Code / GitHub Copilot

---

## 0. Personas

### 0.1 AI Agent Persona — "The Architect"
> *This section tells Claude Code / Copilot how to think and behave while building SENTINEL.*

**Name:** Sentinel Architect  
**Mindset:** You are a senior quantitative engineer with deep expertise in market microstructure, real-time systems, and ML pipelines. You write production-quality code — typed, tested, and documented. You never cut corners on data integrity or latency.

**Principles:**
- **Precision over speed.** Every order must be matched correctly. A wrong fill is worse than a slow one.
- **Fail loudly.** Raise explicit errors with context. Never silently swallow exceptions in the prediction pipeline.
- **Type everything.** All Python functions have type hints. All TypeScript is strictly typed — no `any`.
- **Test as you build.** Write the unit test alongside every new class, not after.
- **Real-time first.** Design every component assuming it will run at ≥10 Hz. Avoid blocking calls on the hot path.
- **Separation of concerns.** The simulator knows nothing about the API. The dashboard knows nothing about ML internals.
- **When in doubt, ask.** If a spec is ambiguous, surface the ambiguity rather than guessing.

---

### 0.2 User Personas

---

#### Persona 1 — Alex, Quant / Algo Trader
**Age:** 31 | **Location:** Mumbai | **Experience:** 6 years in systematic trading

**Background:** Alex runs a small prop desk and deploys statistical arbitrage strategies. He is comfortable reading order book data, writing Python, and interpreting model outputs. He evaluates tools purely on signal quality and latency.

**Goals:**
- Get 60–90 second advance warning before a liquidity shock wipes out his position
- Confirm whether a large buyer is accumulating before he enters a trade
- Backtest SENTINEL's predictions against historical flash crash data

**Pain points:**
- Existing tools give alerts after the move has already happened
- Vendor dashboards are too slow and not programmable
- Can't easily integrate external market data into his own simulator

**How he uses SENTINEL:** Runs the backend locally, connects via WebSocket to his own custom frontend, and uses the prediction API to gate order entry in his algo.

**Key metric:** Prediction lead time and accuracy. He will immediately discard SENTINEL if the false positive rate exceeds 20%.

---

#### Persona 2 — Priya, Institutional Portfolio Manager
**Age:** 44 | **Location:** Bengaluru | **Experience:** 18 years in buy-side asset management

**Background:** Priya manages a ₹2,000 Cr equity fund. She does not write code but is highly data-literate. She relies on her quant team to deploy tools and briefs her on risk signals before major execution windows.

**Goals:**
- Understand whether the market has sufficient liquidity to execute a large block order without moving the price
- Know if another institution is already executing a large order in the same direction before she starts hers
- Have a clear, printable risk summary for compliance sign-off

**Pain points:**
- Quant team's tools are black boxes — she can't interpret what they're saying in a meeting
- No single view combines liquidity health, large order detection, and price impact in one place
- Compliance needs an audit trail of pre-trade risk assessment

**How she uses SENTINEL:** Views the dashboard on a second monitor during execution. Uses the Liquidity Gauge and Large Order Detector to decide when to start and pause TWAP orders. Exports a snapshot for compliance.

**Key metric:** Dashboard clarity and large order detection accuracy. She needs to trust the signal within 5 seconds of looking at it.

---

#### Persona 3 — Rajan, Retail Trader / Enthusiast
**Age:** 26 | **Location:** Pune | **Experience:** 2 years of active trading, self-taught

**Background:** Rajan trades mid-cap Indian equities on NSE with ₹5L capital. He is passionate about market microstructure and wants to learn how institutional money moves. He discovered SENTINEL on GitHub and is running it locally.

**Goals:**
- Understand what's happening in the order book in real time
- Learn how market makers and HFT agents behave by watching the simulation
- Get alerted when something unusual is happening so he doesn't enter at the wrong time

**Pain points:**
- Professional tools like Bloomberg are out of his budget
- Most open-source projects are either too basic or impossible to run locally
- No visual explanation of why the liquidity health score changes

**How he uses SENTINEL:** Runs the full Docker stack on his laptop, watches the dashboard as an educational tool alongside live NSE data. Reads the agent metrics panel to understand PnL by strategy type.

**Key metric:** Ease of setup and dashboard intuitiveness. If `docker-compose up` doesn't work first time, he will abandon the project.

---

#### Persona 4 — Vikram, Financial Data Engineer
**Age:** 34 | **Location:** Hyderabad | **Experience:** 8 years in data engineering, 3 years in fintech

**Background:** Vikram works at a fintech startup building a market data platform. He was asked to evaluate SENTINEL as a simulation engine to generate synthetic training data for an internal ML model. He will integrate SENTINEL's backend into a data pipeline.

**Goals:**
- Run SENTINEL headlessly (no dashboard) to generate large volumes of synthetic market microstructure data
- Export simulation results to Parquet / CSV for downstream ML training

**Pain points:**
- Most simulation libraries aren't designed for high-throughput data generation
- No easy way to export structured agent-level data from existing tools

**How he uses SENTINEL:** Calls the backend Python API directly, bypasses the FastAPI layer for bulk runs, and exports `simulator.get_results()` to Parquet.

**Key metric:** Simulation throughput (steps/sec) and data export flexibility.

---

### 0.3 Persona × Feature Matrix

| Feature | Alex (Quant) | Priya (PM) | Rajan (Retail) | Vikram (Engineer) |
|---|---|---|---|---|
| Liquidity Shock Predictor | ★★★ Critical | ★★★ Critical | ★★ Nice-to-have | ★ Low |
| Large Order Detector | ★★★ Critical | ★★★ Critical | ★★ Nice-to-have | ★ Low |
| Real-time Dashboard | ★★ Secondary | ★★★ Critical | ★★★ Critical | ✗ Not needed |
| WebSocket API | ★★★ Critical | ✗ Not needed | ★ Low | ★★★ Critical |
| Google Stitch UI Components | ★ Low | ★★ Secondary | ★★ Secondary | ✗ Not needed |
| Agent Metrics Panel | ★★ Secondary | ★ Low | ★★★ Critical | ★★ Secondary |
| Docker Setup | ★★ Secondary | ✗ Not needed | ★★★ Critical | ★★★ Critical |
| Data Export (Parquet/CSV) | ★ Low | ✗ Not needed | ✗ Not needed | ★★★ Critical |

---

## 1. Executive Summary

SENTINEL is a real-time market microstructure simulator and early-warning system. It simulates a live order book populated by six AI agent types, predicts liquidity crises 60–90 seconds in advance (85% accuracy), and detects hidden institutional orders with 83% accuracy. The system streams live market data to a Next.js dashboard via WebSocket.

**Core capabilities:**
- Multi-agent order book simulation (6 agent types, 1000+ steps/sec)
- Liquidity shock predictor with 60–90 second lead time
- Iceberg and TWAP large-order detector
- Real-time Next.js 14 dashboard (TSX + Tailwind CSS)
- Optional Google Stitch MCP UI components on the frontend (not part of the market-data layer)

---

## 2. Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts, Zustand, Lucide React |
| Backend | Python 3.10, FastAPI, WebSockets, Uvicorn |
| ML | Scikit-learn (RandomForest), XGBoost, NumPy, Pandas |
| Market Data | Zerodha Kite Connect (real-time + historical) |
| UI Components | Google Stitch MCP (frontend-only, optional) |
| Fallback Data | yfinance (historical OHLCV fallback) |
| Infra | Docker, docker-compose |
| Testing | Pytest (backend), Jest (frontend) |

---

## 3. Project Directory Structure

```
sentinel/
├── backend/
│   ├── src/
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── base_agent.py
│   │   │   ├── market_maker.py
│   │   │   ├── hft_agent.py
│   │   │   ├── institutional.py
│   │   │   ├── retail.py
│   │   │   ├── informed.py
│   │   │   └── noise.py
│   │   ├── market/
│   │   │   ├── __init__.py
│   │   │   ├── order.py
│   │   │   ├── trade.py
│   │   │   ├── order_book.py
│   │   │   └── simulator.py
│   │   ├── prediction/
│   │   │   ├── __init__.py
│   │   │   ├── liquidity_shock.py
│   │   │   ├── large_order.py
│   │   │   └── features.py
│   │   ├── data/
│   │   │   ├── base_provider.py
│   │   │   ├── kite_provider.py
│   │   │   ├── kite_auth.py
│   │   │   ├── yfinance_provider.py
│   │   │   ├── nse_csv_provider.py
│   │   │   └── data_manager.py
│   │   ├── mcp/
│   │   │   ├── __init__.py
│   │   │   └── kite_client.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   └── websocket.py
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── config.py
│   │       └── logger.py
│   ├── data/
│   ├── models/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── dashboard/
│   │       └── page.tsx
│   ├── components/
│   │   ├── ui/                        # shadcn/ui primitives
│   │   ├── OrderBookHeatmap.tsx
│   │   ├── LiquidityGauge.tsx
│   │   ├── LargeOrderDetector.tsx
│   │   ├── PriceChart.tsx
│   │   ├── AgentMetricsPanel.tsx
│   │   └── AlertBanner.tsx
│   ├── lib/
│   │   ├── websocket.ts
│   │   ├── api-client.ts
│   │   └── stitch-mcp.ts             # Google Stitch MCP UI wrapper
│   ├── store/
│   │   └── market-store.ts           # Zustand global state
│   ├── types/
│   │   └── market.ts
│   ├── package.json
│   └── tsconfig.json
│
├── docker-compose.yml
└── README.md
```

---

## 4. Dependencies

### backend/requirements.txt
```
numpy==1.24.3
pandas==2.0.3
scikit-learn==1.3.0
xgboost==1.7.6
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
yfinance==0.2.28
pydantic==2.5.0
pytest==7.4.0
python-dotenv==1.0.0
```

### frontend/package.json (key dependencies)
```json
{
  "dependencies": {
    "next": "14.0.4",
    "react": "^18.2.0",
    "typescript": "^5.3.3",
    "tailwindcss": "^3.3.0",
    "recharts": "^2.10.3",
    "socket.io-client": "^4.5.4",
    "zustand": "^4.4.7",
    "lucide-react": "^0.294.0",
    "@radix-ui/react-slot": "^1.0.2",
    "@radix-ui/react-progress": "^1.0.3"
  }
}
```

---

## 5. Phase 1 — Core Data Structures & Agents (Week 1–2)

### 5.1 Order, Trade, OrderBook

Implement the following files exactly as specced:

**`backend/src/market/order.py`** — `Order` dataclass with `OrderSide`, `OrderType`, `OrderStatus` enums. Fields: `order_id`, `agent_id`, `side`, `order_type`, `price`, `quantity`, `timestamp`, `filled_quantity`, `status`. Properties: `remaining_quantity`, `is_filled`. Method: `fill(quantity)`.

**`backend/src/market/trade.py`** — `Trade` dataclass. Fields: `trade_id`, `buyer_order_id`, `seller_order_id`, `buyer_agent_id`, `seller_agent_id`, `price`, `quantity`, `timestamp`. Property: `value`.

**`backend/src/market/order_book.py`** — `OrderBook` class. Maintains sorted `bids` and `asks` lists. Methods: `add_order`, `_match_market_order`, `_match_limit_order`, `_create_trade`, `get_depth(levels=5)`, `get_total_depth(levels=5)`. Properties: `best_bid`, `best_ask`, `mid_price`, `spread`.

### 5.2 Base Agent

**`backend/src/agents/base_agent.py`** — Abstract `BaseAgent`. Constructor fields: `agent_id`, `agent_type`, `initial_capital`, `latency_seconds`. Methods: `decide_action(market_state) → List[Order]` (abstract), `update_position(trade)`, `get_metrics() → Dict` (returns `total_pnl`, `return_pct`, `sharpe_ratio`, `num_trades`).

### 5.3 Six Agent Types

All agents extend `BaseAgent` and implement `decide_action(market_state: Dict) → List[Order]`.

| Agent | File | Capital | Strategy |
|---|---|---|---|
| MarketMaker | `market_maker.py` | $1M | Quote bid/ask with inventory skew, flatten near close |
| HFT | `hft_agent.py` | $5M | Mean reversion (z-score) + short momentum |
| Institutional | `institutional.py` | $100M | TWAP execution over 1-hour window |
| Retail | `retail.py` | $50K | MA crossover (20/50) with stop-loss/take-profit |
| Informed | `informed.py` | $5M | Trades on randomly generated 70%-accurate signals |
| Noise | `noise.py` | $20K | Random orders at configurable rate |

**MarketMaker specifics:** `base_spread=0.001`, `quote_size=100`, `max_inventory=5000`, inventory-proportional skew, halved quotes when inventory > 50%, stops quoting at 90% inventory, flattens position when `time_to_close < 600`.

**HFT specifics:** `position_limit=1000`, 100-bar price history deque, z-score threshold=2.0, momentum threshold=0.001.

**Institutional specifics:** TWAP slicing every 60 seconds, `execution_window=3600`, max `slice_size=1000`.

**Retail specifics:** `stop_loss=0.02`, `take_profit=0.05`.

**Informed specifics:** 1% chance per step to receive information, signal lasts 120 seconds, max position ±5000.

**Noise specifics:** `order_rate=0.1`, random sizes 10–200, 50% market / 50% limit.

### 5.4 Market Simulator

**`backend/src/market/simulator.py`** — `MarketSimulator` class.

Constructor: `agents`, `initial_price=100.0`, `duration_seconds=23400`.

Methods:
- `run(steps=None) → Dict` — runs full simulation, logs every 1000 steps
- `step()` — processes one time step: sorts agents by latency, calls `decide_action`, submits orders, updates positions, records state
- `get_market_state() → Dict` — returns `current_time`, `mid_price`, `best_bid`, `best_ask`, `spread`, `bid_depth`, `ask_depth`, `total_depth`, `current_price`, `time_to_close`, `volatility`, `agents`
- `get_results() → Dict` — returns history, final price, total trades, agent metrics

Volatility: annualised log-return std over 20-bar window (`std * sqrt(252 * 390)`).

---

## 6. Phase 2 — Liquidity Shock Predictor (Week 2–3)

### 6.1 Feature Extractor

**`backend/src/prediction/features.py`** — `FeatureExtractor` class.

Method: `extract_liquidity_features(market_state, lookback=60) → Dict`

Features to extract:
- `spread_ratio` — current spread / `mid_price` divided by `baseline_spread` (0.001)
- `depth_ratio` — `total_depth` / `baseline_depth` (1000)
- `volatility_ratio` — current volatility / `baseline_volatility` (0.02)
- `mm_inventory_stress` — mean absolute inventory ratio across all MarketMaker agents
- `active_mm_count` — count of MarketMakers with `|position| < 4500`
- `time_to_close` — seconds remaining in session

### 6.2 Liquidity Shock Predictor

**`backend/src/prediction/liquidity_shock.py`** — `LiquidityShockPredictor` class.

Model: `RandomForestClassifier(n_estimators=100, max_depth=10, class_weight='balanced', random_state=42)`

Labelling rule: a liquidity shock occurs if within the next 60 steps, `depth_ratio < 0.5` OR `spread_ratio > 3.0`.

Prediction output:
```json
{
  "probability": 0.23,
  "health_score": 77.0,
  "warning_level": "caution",
  "features": { ... },
  "timestamp": 1234.5
}
```

Warning levels: `safe` (≥80), `caution` (≥60), `warning` (≥40), `critical` (<40).

Training data generation: `generate_training_data(num_simulations=100)` — runs 3600-step simulations with 3 MMs, 5 HFTs, 10 Retail, 10 Noise agents.

---

## 7. Phase 3 — Large Order Detector (Week 3–4)

**`backend/src/prediction/large_order.py`** — `LargeOrderDetector` class. `min_order_size=10000`, 300-bar order history deque.

### Iceberg Detection (`detect_iceberg`)
- Group recent orders by side
- Flag if `size_std / size_mean < 0.1` (consistent sizes) AND `time_diff_std < 10` (consistent timing)
- `estimated_size = size_mean * count * 2`
- Return with `confidence=0.85`

### TWAP Detection (`detect_twap`)
- Group recent orders by side
- Flag if `time_diff_std / time_diff_mean < 0.2` (regular intervals)
- `estimated_size = executed_so_far * 3`
- Return with `confidence=0.78`, `completion_pct=33`

### Impact Prediction (`predict_impact`)
- `size_ratio = estimated_size / total_depth`
- `base_impact = size_ratio * 0.01`
- `expected_impact_pct = base_impact * (volatility / 0.02)`
- Return `expected_impact_pct`, `expected_impact_dollars`, `size_vs_depth_ratio`, `market_conditions`

---

## 8. Phase 4 — Google Stitch MCP UI Components (Week 4)

Stitch is **frontend-only** in SENTINEL. It is used for UI composition and widgets, not for market data, simulator seeding, prediction calibration, or backend services.

**`frontend/lib/stitch-mcp.ts`** — TypeScript UI wrapper.

```typescript
export class StitchMCPUI {
  constructor(private root: HTMLElement) {}

  mount(componentName: string, props?: Record<string, unknown>): void
  unmount(): void
}
```

**Integration points:**
- Mount optional Google Stitch MCP UI components inside dashboard cards, side panels, or modal workflows
- Keep all market data, predictions, and order-book state sourced from SENTINEL's own backend and provider layer
- Do not introduce any backend dependency on Stitch for quotes, trades, OHLCV, or calibration

---

---

## 9. Phase 5 — Data Layer: Zerodha Kite API (Week 4–5)

### 9.1 Overview

SENTINEL uses **Zerodha Kite Connect** as its primary data provider for both real-time streaming and historical data across NSE equities, BSE equities, F&O, and indices.

**Kite API credentials required (add to `backend/.env`):**
```
KITE_API_KEY=your_api_key
KITE_API_SECRET=your_api_secret
KITE_ACCESS_TOKEN=generated_per_session
KITE_DEFAULT_SYMBOL=NSE:RELIANCE
```

Access token expires daily — SENTINEL must handle re-authentication automatically on startup via `kite_auth.py`.

Add to `backend/requirements.txt`:
```
kiteconnect==4.2.0
```

---

### 9.2 Directory Additions

```
backend/src/data/
├── __init__.py
├── base_provider.py          # Abstract DataProvider
├── kite_provider.py          # Zerodha Kite implementation
├── kite_auth.py              # Daily token refresh helper
├── yfinance_provider.py      # Fallback for historical data
├── nse_csv_provider.py       # NSE official CSV loader (flash crash backtest)
└── data_manager.py           # Unified interface with fallback switching
```

---

### 9.3 Abstract DataProvider

**`backend/src/data/base_provider.py`**

```python
from abc import ABC, abstractmethod
from typing import List, Dict

class DataProvider(ABC):

    @abstractmethod
    async def get_quote(self, symbol: str) -> Dict:
        """Returns current bid, ask, last price, volume, OHLC."""
        ...

    @abstractmethod
    async def get_order_book(self, symbol: str) -> Dict:
        """Returns Level 2 order book: top 5 bid/ask prices and sizes."""
        ...

    @abstractmethod
    async def get_historical_ohlcv(
        self, symbol: str, interval: str, from_date: str, to_date: str
    ) -> List[Dict]:
        """
        Returns OHLCV bars.
        interval: 'minute' | '3minute' | '5minute' | '15minute' | 'day'
        from_date / to_date: 'YYYY-MM-DD'
        """
        ...

    @abstractmethod
    async def stream_ticks(self, symbols: List[str], on_tick) -> None:
        """Streams live ticks, calls on_tick(tick: Dict) on each update."""
        ...

    @abstractmethod
    def get_instrument_token(self, symbol: str) -> int:
        """Resolves symbol string to Kite instrument token."""
        ...
```

---

### 9.4 Kite Provider

**`backend/src/data/kite_provider.py`**

Constructor: `KiteProvider(api_key, access_token)` — initialises `KiteConnect` and `KiteTicker`, caches instrument tokens on first call.

**`get_quote(symbol)`** — calls `kite.quote([symbol])`, returns:
```python
{
  "symbol": "NSE:RELIANCE",
  "last_price": 2450.50,
  "bid": 2450.00,
  "ask": 2451.00,
  "volume": 1234567,
  "ohlc": { "open": 2430, "high": 2460, "low": 2420, "close": 2448 }
}
```

**`get_order_book(symbol)`** — extracts `depth.buy` and `depth.sell` from `kite.quote()`, returns 5 bid/ask levels:
```python
{
  "bids": [{"price": 2450.00, "size": 500}, ...],
  "asks": [{"price": 2451.00, "size": 300}, ...]
}
```

**`get_historical_ohlcv(symbol, interval, from_date, to_date)`** — calls `kite.historical_data(instrument_token, from_date, to_date, interval)`. Returns list of `{"timestamp", "open", "high", "low", "close", "volume"}`.

**`stream_ticks(symbols, on_tick)`** — subscribes via `KiteTicker`, sets mode to `FULL` (includes depth), calls `on_tick` on each tick.

**`get_instrument_token(symbol)`** — loads instruments CSV on first call, caches `symbol → token`. Example: `"NSE:RELIANCE" → 738561`.

**`backend/src/data/kite_auth.py`** — daily token refresh:
```python
async def refresh_access_token(api_key: str, api_secret: str, request_token: str) -> str:
    kite = KiteConnect(api_key=api_key)
    data = kite.generate_session(request_token, api_secret=api_secret)
    return data["access_token"]
```

---

### 9.5 Historical Data: Four Use Cases

**1. ML Model Training**

Extend `LiquidityShockPredictor.generate_training_data()` to optionally seed each simulation episode with real historical volatility and spread baselines from Kite (200 days of minute OHLCV). This makes synthetic training data statistically realistic for Indian equities.

```python
async def generate_training_data_with_kite(
    self, provider: KiteProvider, symbol: str, num_simulations: int = 100
) -> List: ...
```

**2. Feature Baseline Calibration**

On startup, `FeatureExtractor` calls Kite to set realistic baselines from 30 days of minute bars (50th percentile of spread, depth, volatility distributions):

```python
async def calibrate_from_kite(self, provider: KiteProvider, symbol: str):
    # Sets self.baseline_spread, self.baseline_depth, self.baseline_volatility
```

**3. Flash Crash Backtesting**

Load NSE official intraday CSVs for known crash dates (March 23 2020, Jan 15 2015) via `NseCsvProvider`, replay through `LiquidityShockPredictor`, measure lead time and accuracy:

```python
class BacktestRunner:
    def run(self, provider: DataProvider, crash_date: str, symbol: str) -> Dict:
        # Returns: prediction_lead_time_seconds, accuracy, false_positive_rate
```

**4. Simulator Price Seeding**

On simulation start, fetch current quote + order book from Kite and use as `initial_price` and order book warm-up state:

```python
async def seed_simulator_from_kite(simulator: MarketSimulator, provider: KiteProvider, symbol: str):
    quote = await provider.get_quote(symbol)
    order_book = await provider.get_order_book(symbol)
    simulator.initial_price = quote["last_price"]
    # Pre-populate order book with real depth levels
```

---

### 9.6 Real-time Streaming: Two Use Cases

Kite tick stream runs as a **parallel background task** alongside the simulation:

**1. Price Anchoring** — every 5 seconds, nudge `simulator.current_price` toward the real Kite last price (weight=0.05) to prevent unrealistic drift:

```python
async def handle_kite_tick(tick: Dict):
    if simulator:
        simulator.anchor_price(tick["last_price"], weight=0.05)
    await manager.broadcast({"type": "real_trade", "tick": tick})
```

Start on FastAPI startup:
```python
@app.on_event("startup")
async def start_kite_stream():
    asyncio.create_task(
        kite_provider.stream_ticks([settings.KITE_DEFAULT_SYMBOL], handle_kite_tick)
    )
```

**2. Dashboard Real Trade Overlay** — real Kite trades are forwarded as `type: "real_trade"` WebSocket events, overlaid as dots on the frontend PriceChart.

---

### 9.7 Data Manager

**`backend/src/data/data_manager.py`** — unified interface with automatic fallback:

```python
class DataManager:
    def __init__(self, primary: DataProvider, fallback: DataProvider = None):
        ...
    async def get_quote(self, symbol: str) -> Dict:
        try:
            return await self.primary.get_quote(symbol)
        except Exception:
            if self.fallback:
                return await self.fallback.get_quote(symbol)
            raise
```

Default setup: `DataManager(primary=KiteProvider(...), fallback=YFinanceProvider(...))`.

---

### 9.8 New REST Endpoints (Data Layer)

| Method | Path | Description |
|---|---|---|
| POST | `/api/data/symbol` | Switch active symbol `{ "symbol": "NSE:INFY" }` |
| GET | `/api/data/quote` | Current quote for active symbol |
| GET | `/api/data/depth` | Current Level 2 order book |
| GET | `/api/data/historical` | OHLCV bars `?symbol=NSE:RELIANCE&interval=minute&from=2024-01-01&to=2024-01-31` |
| POST | `/api/backtest/run` | Run flash crash backtest `{ "crash_date": "2020-03-23", "symbol": "NSE:NIFTY 50" }` |

---

### 9.9 Supported Instruments

| Symbol | Exchange | Instrument Token | Asset Class |
|---|---|---|---|
| `NSE:RELIANCE` | NSE | 738561 | Equity |
| `NSE:NIFTY 50` | NSE | 256265 | Index |
| `NSE:BANKNIFTY` | NSE | 260105 | Index |
| `BSE:SENSEX` | BSE | 265 | Index |
| `NSE:INFY` | NSE | 408065 | Equity |
| `NSE:HDFCBANK` | NSE | 341249 | Equity |

Any Kite-tradeable instrument can be used by updating `KITE_DEFAULT_SYMBOL` in `.env`.

---

## 10. Phase 6 — FastAPI Backend (Week 5)

**`backend/src/api/main.py`**

CORS: allow `http://localhost:3000`.

Global singletons: `simulator`, `liquidity_predictor`, `large_order_detector`, `ConnectionManager`.

### REST Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Returns `{"status": "healthy"}` |
| POST | `/api/simulation/start` | Initialises simulator with full agent set, returns agent count |
| POST | `/api/simulation/stop` | Stops simulator loop |
| GET | `/api/prediction/liquidity` | Returns current liquidity shock prediction |
| GET | `/api/prediction/large-order` | Returns current large-order detection + impact |
| GET | `/api/agents/metrics` | Returns PnL/Sharpe metrics per agent |
| GET | `/api/market/snapshot` | Returns current order book depth snapshot |

### WebSocket `/ws`

Streams JSON every 100ms:
```json
{
  "type": "market_update",
  "timestamp": 1234.5,
  "price": 100.23,
  "spread": 0.05,
  "depth": 5420,
  "order_book": { "bids": [...], "asks": [...] },
  "liquidity_prediction": { "health_score": 77, "warning_level": "caution", ... },
  "large_order_detection": { "pattern": "twap", "side": "buy", "confidence": 0.78, ... },
  "agent_metrics": { "MM_0": { "total_pnl": 1234, "sharpe_ratio": 1.2 }, ... }
}
```

---

## 11. Phase 7 — Next.js Frontend (Week 5–6)

### 10.1 TypeScript Types

**`frontend/types/market.ts`**

```typescript
export interface OrderLevel { price: number; size: number; }
export interface OrderBook { bids: OrderLevel[]; asks: OrderLevel[]; }
export interface LiquidityPrediction {
  probability: number;
  health_score: number;
  warning_level: 'safe' | 'caution' | 'warning' | 'critical';
  features: Record<string, number>;
  timestamp: number;
}
export interface LargeOrderDetection {
  pattern: 'iceberg' | 'twap';
  side: 'buy' | 'sell';
  estimated_size: number;
  confidence: number;
  impact?: { expected_impact_pct: number; expected_impact_dollars: number; };
}
export interface MarketUpdate {
  type: 'market_update';
  timestamp: number;
  price: number;
  spread: number;
  depth: number;
  order_book: OrderBook;
  liquidity_prediction: LiquidityPrediction;
  large_order_detection: LargeOrderDetection | null;
  agent_metrics: Record<string, { total_pnl: number; sharpe_ratio: number; }>;
}
```

### 10.2 Zustand Store

**`frontend/store/market-store.ts`**

```typescript
interface MarketStore {
  marketData: MarketUpdate | null;
  priceHistory: { time: number; price: number }[];
  connected: boolean;
  alerts: Alert[];
  setMarketData: (data: MarketUpdate) => void;
  addAlert: (alert: Alert) => void;
  clearAlerts: () => void;
}
```

Price history: capped at 500 data points (rolling window).

### 10.3 WebSocket Hook

**`frontend/lib/websocket.ts`** — `useMarketWebSocket()` hook. Auto-reconnects on disconnect (exponential backoff, max 5 retries). Pushes updates to Zustand store.

### 10.4 Components

**`app/dashboard/page.tsx`** — Dashboard layout. Full-width header with SENTINEL logo, connection status badge, simulation start/stop button. 2-column grid: LiquidityGauge + LargeOrderDetector on top row, PriceChart + OrderBookHeatmap on bottom row. AlertBanner anchored at top when warning level is not `safe`.

**`components/LiquidityGauge.tsx`**

- Circular gauge (SVG arc or Recharts RadialBar) showing `health_score` 0–100
- Colour: green (safe), yellow (caution), orange (warning), red (critical)
- Shows `warning_level` label and shock probability percentage
- Animated transition on score change

**`components/LargeOrderDetector.tsx`**

- Card showing detected pattern (ICEBERG / TWAP badge), side (BUY green / SELL red badge), estimated size, confidence bar
- Expected price impact in % and $ if available
- "No large orders detected" empty state

**`components/PriceChart.tsx`**

- Recharts `LineChart` with 500-point rolling price history
- Secondary Y-axis for spread
- Optional UI annotations may be layered independently without affecting price data
- Time formatted as HH:MM:SS

**`components/OrderBookHeatmap.tsx`**

- Horizontal bar heatmap of 10 bid/ask levels
- Bids green, asks red, bar width proportional to size
- Mid-price line in centre
- Auto-scales to current price range

**`components/AgentMetricsPanel.tsx`**

- Collapsible panel listing each agent's `total_pnl` and `sharpe_ratio`
- Colour-coded by agent type

**`components/AlertBanner.tsx`**

- Slides in from top when `warning_level` is `warning` or `critical`
- Shows warning message, timestamp, and dismiss button
- Auto-dismisses after 10 seconds on `caution`

### 10.5 Root Page

**`app/page.tsx`** — Redirects to `/dashboard`.

**`app/layout.tsx`** — Sets `<html lang="en">`, imports Tailwind globals, wraps in dark-mode-compatible body.

---

## 12. Docker Deployment

### docker-compose.yml
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
      - ./data:/data
    env_file: ./backend/.env
    command: uvicorn src.api.main:app --host 0.0.0.0 --reload

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000
    depends_on:
      - backend
    command: npm run dev
```

### backend/Dockerfile
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### frontend/Dockerfile
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm install
COPY . .
CMD ["npm", "run", "dev"]
```

---

## 13. Environment Variables

**`backend/.env`**
```
SIMULATION_DURATION=23400
INITIAL_PRICE=100.0
```

**`frontend/.env.local`**
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

## 14. Testing Requirements

### Backend (Pytest)
- `test_order_book.py` — limit/market matching, price-time priority, partial fills
- `test_agents.py` — each agent produces valid orders, position tracking, PnL calculation
- `test_simulator.py` — 100-step smoke test, price stays in reasonable range
- `test_predictor.py` — feature extraction, prediction output schema, warning level mapping
- `test_detector.py` — iceberg pattern detection, TWAP pattern detection, impact calc

### Frontend (Jest + React Testing Library)
- `LiquidityGauge.test.tsx` — renders all 4 warning states correctly
- `LargeOrderDetector.test.tsx` — renders detection card and empty state
- `websocket.test.ts` — reconnect logic, store update

---

## 15. Build & Run Commands

```bash
# Full stack (Docker)
docker-compose up --build

# Backend only (local dev)
cd backend
pip install -r requirements.txt
uvicorn src.api.main:app --reload --port 8000

# Frontend only (local dev)
cd frontend
npm install
npm run dev

# Train ML models
cd backend
python -c "
from src.prediction.liquidity_shock import LiquidityShockPredictor
p = LiquidityShockPredictor()
data = p.generate_training_data(num_simulations=50)
p.train(data)
"

# Run tests
cd backend && pytest tests/ -v
cd frontend && npm run test
```

**URLs after startup:**
- Frontend Dashboard: http://localhost:3000/dashboard
- Backend API: http://localhost:8000
- API Docs (Swagger): http://localhost:8000/docs
- WebSocket: ws://localhost:8000/ws

---


---

## 17. Error Handling & Edge Cases

### 17.1 Kite API Failures

| Scenario | Behaviour |
|---|---|
| Access token expired | On 403, auto-trigger `refresh_access_token()`, retry once, then raise `KiteAuthError` with clear message |
| Kite WebSocket disconnect | Reconnect with exponential backoff (1s, 2s, 4s, 8s, max 60s). Log each attempt. After 5 failures, fall back to `YFinanceProvider` and emit `{"type": "data_source_fallback"}` WebSocket event to dashboard |
| Quote endpoint timeout (>3s) | Return last cached quote with `{"stale": true, "stale_since": timestamp}` flag |
| Instrument token not found | Raise `UnknownSymbolError(symbol)` with list of valid symbols in message |

### 17.2 Order Book Edge Cases

| Scenario | Behaviour |
|---|---|
| Empty order book (no bids or asks) | `mid_price` returns `None`. All agents that depend on `mid_price` must guard with `if mid_price is None: return []` |
| Market order with no opposing liquidity | Order partially fills what is available, remaining quantity is cancelled. Trade list returned contains only partial fills |
| Negative or zero price | Raise `InvalidPriceError(price)` before inserting into book |
| Order quantity = 0 | Raise `InvalidQuantityError` before processing |
| Agent submits order for unknown agent_id | Log warning, skip order, do not crash simulator |

### 17.3 ML Pipeline Edge Cases

| Scenario | Behaviour |
|---|---|
| `predict()` called before `train()` | Raise `ModelNotTrainedError` with message: "Call train() or load a saved model before predicting" |
| Feature vector contains NaN | Replace NaN with feature-specific baseline value, log warning with feature name |
| All market makers have zero position | `mm_inventory_stress = 0.0`, `active_mm_count = 0` — do not divide by zero |
| Predictor returns probability outside [0, 1] | Clamp to [0, 1] and log warning |

### 17.4 WebSocket Edge Cases

| Scenario | Behaviour |
|---|---|
| Client connects before simulation starts | Send `{"type": "waiting", "message": "Simulation not started"}` every 2s until started |
| Simulator crashes mid-session | Catch exception, broadcast `{"type": "simulation_error", "message": str(e)}`, reset simulator to `None` |
| Client sends unexpected message | Log and ignore — never crash the server on bad client input |
| >50 concurrent WebSocket connections | Enforce connection limit, return HTTP 429 to new connections beyond limit |

### 17.5 Frontend Edge Cases

| Scenario | Behaviour |
|---|---|
| WebSocket disconnects | Show "Reconnecting..." overlay on dashboard, attempt reconnect with backoff |
| `health_score` is `null` | LiquidityGauge shows "—" instead of score, grey colour, "Awaiting data" label |
| `large_order_detection` is `null` | LargeOrderDetector shows empty state: "No large orders detected" |
| Price history > 500 points | Slice to last 500 — never grow unboundedly |
| `NaN` in price data | Skip that data point in chart, do not render gap or crash |

---

## 18. Simulation State Machine

The simulator has 5 explicit states. Claude Code must implement this as an enum and enforce valid transitions.

```
IDLE → INITIALISING → RUNNING → PAUSED → STOPPED
                                    ↑         |
                                    └─────────┘ (resume)
         RUNNING → ERROR (on unhandled exception)
         ERROR   → IDLE  (on reset)
```

### States

| State | Description |
|---|---|
| `IDLE` | No simulator instance exists. Default on startup. |
| `INITIALISING` | `POST /api/simulation/start` called. Agents being created, Kite seeding in progress. |
| `RUNNING` | Simulator step loop active. WebSocket streaming live data. |
| `PAUSED` | Step loop suspended. WebSocket still connected, last state frozen on dashboard. |
| `STOPPED` | Step loop ended. Results available. Simulator instance still in memory for export. |
| `ERROR` | Unhandled exception in step loop. Error message stored, broadcast to clients. |

### Valid Transitions

| From | To | Trigger |
|---|---|---|
| `IDLE` | `INITIALISING` | `POST /api/simulation/start` |
| `INITIALISING` | `RUNNING` | Seeding complete |
| `INITIALISING` | `ERROR` | Kite auth failure or agent init error |
| `RUNNING` | `PAUSED` | `POST /api/simulation/pause` |
| `RUNNING` | `STOPPED` | `POST /api/simulation/stop` or duration elapsed |
| `RUNNING` | `ERROR` | Unhandled exception in step loop |
| `PAUSED` | `RUNNING` | `POST /api/simulation/resume` |
| `PAUSED` | `STOPPED` | `POST /api/simulation/stop` |
| `STOPPED` | `IDLE` | `POST /api/simulation/reset` |
| `ERROR` | `IDLE` | `POST /api/simulation/reset` |

### New REST Endpoints

| Method | Path | Valid from states | Description |
|---|---|---|---|
| `POST` | `/api/simulation/start` | `IDLE` | Initialise and start |
| `POST` | `/api/simulation/pause` | `RUNNING` | Pause step loop |
| `POST` | `/api/simulation/resume` | `PAUSED` | Resume step loop |
| `POST` | `/api/simulation/stop` | `RUNNING`, `PAUSED` | Stop and finalise |
| `POST` | `/api/simulation/reset` | `STOPPED`, `ERROR` | Reset to IDLE |
| `GET` | `/api/simulation/status` | Any | Returns current state + metadata |

`GET /api/simulation/status` response:
```json
{
  "state": "RUNNING",
  "current_step": 1234,
  "current_time": 1234.5,
  "current_price": 2451.50,
  "num_agents": 61,
  "symbol": "NSE:RELIANCE",
  "started_at": "2024-01-15T09:15:00Z",
  "elapsed_seconds": 1234
}
```

### Frontend State Handling

The dashboard must reflect simulation state visually:

| State | Dashboard behaviour |
|---|---|
| `IDLE` | "Start Simulation" button active, all charts empty |
| `INITIALISING` | Loading spinner, "Connecting to Kite..." message |
| `RUNNING` | Live data streaming, "Pause" and "Stop" buttons visible |
| `PAUSED` | Charts frozen, "Resume" and "Stop" buttons visible, "PAUSED" badge on header |
| `STOPPED` | Charts frozen at last state, "Export" and "Reset" buttons visible |
| `ERROR` | Red error banner with message, "Reset" button only |

---

## 19. API Security & Authentication

### 19.1 Backend API Key Auth

All REST endpoints and the WebSocket connection require a static API key passed as a header. This prevents unauthorised access to the simulation and Kite data.

**Header:** `X-API-Key: <key>`

Set in `backend/.env`:
```
SENTINEL_API_KEY=generate_a_long_random_string_here
```

FastAPI dependency:
```python
from fastapi import Security, HTTPException
from fastapi.security.api_key import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    if api_key != settings.SENTINEL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
```

Apply to all routes:
```python
@app.post("/api/simulation/start", dependencies=[Depends(verify_api_key)])
```

**WebSocket auth** — pass key as query param (headers not supported in browser WebSocket):
```
ws://localhost:8000/ws?api_key=your_key
```

Validate on connect:
```python
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, api_key: str = Query(...)):
    if api_key != settings.SENTINEL_API_KEY:
        await websocket.close(code=4003)
        return
```

### 19.2 Frontend Key Storage

Store API key in `frontend/.env.local` — never hardcode or commit:
```
NEXT_PUBLIC_SENTINEL_API_KEY=your_key_here
```

Pass in all API calls via `api-client.ts`:
```typescript
const headers = {
  "Content-Type": "application/json",
  "X-API-Key": process.env.NEXT_PUBLIC_SENTINEL_API_KEY!
}
```

### 19.3 Kite Secret Protection

- `KITE_API_SECRET` and `KITE_ACCESS_TOKEN` must never be exposed via any REST endpoint or WebSocket message
- Add to `.gitignore`: `.env`, `backend/.env`, `frontend/.env.local`
- Provide `.env.example` files with placeholder values in the repo root

### 19.4 CORS

Restrict to known origins in production:
```python
allow_origins = [
    "http://localhost:3000",
    os.getenv("FRONTEND_URL", "http://localhost:3000")
]
```

---

## 20. Alert History & Notification Thresholds

### 20.1 Alert Model

```python
# backend/src/utils/alert_manager.py
@dataclass
class Alert:
    alert_id: str
    alert_type: str          # "liquidity_shock" | "large_order" | "system_error" | "data_fallback"
    severity: str            # "info" | "warning" | "critical"
    message: str
    data: Dict               # Raw prediction/detection payload
    triggered_at: float      # Simulation timestamp
    wall_time: str           # ISO8601 real-world time
    acknowledged: bool = False
```

### 20.2 Trigger Thresholds

| Alert Type | Trigger Condition | Severity | Auto-clear |
|---|---|---|---|
| Liquidity shock | `health_score < 60` | warning | When `health_score ≥ 70` for 10s |
| Liquidity shock | `health_score < 40` | critical | When `health_score ≥ 50` for 10s |
| Large order detected | Any TWAP/Iceberg detection | warning | After 60s |
| Large order — high impact | `expected_impact_pct > 0.5%` | critical | After 30s |
| Kite data fallback | Provider switched to yfinance | info | When Kite reconnects |
| Simulation error | State transitions to ERROR | critical | On manual reset |

### 20.3 Backend Alert Manager

**`backend/src/utils/alert_manager.py`** — `AlertManager` class:

```python
class AlertManager:
    def __init__(self, max_history: int = 500):
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []   # capped at max_history
        self.broadcast_fn = None               # injected from WebSocket manager

    def trigger(self, alert_type: str, severity: str, message: str, data: Dict) -> Alert
    def acknowledge(self, alert_id: str) -> bool
    def auto_clear(self, alert_type: str) -> None
    def get_active(self) -> List[Alert]
    def get_history(self, limit: int = 50) -> List[Alert]
```

Alerts are broadcast immediately via WebSocket:
```json
{
  "type": "alert",
  "alert_id": "abc123",
  "alert_type": "liquidity_shock",
  "severity": "critical",
  "message": "Liquidity health critical: 34/100",
  "triggered_at": 1234.5
}
```

### 20.4 New REST Endpoints (Alerts)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/alerts/active` | All currently active alerts |
| `GET` | `/api/alerts/history` | Last 50 alerts (paginated with `?limit=&offset=`) |
| `POST` | `/api/alerts/{alert_id}/acknowledge` | Mark alert as acknowledged |
| `DELETE` | `/api/alerts/history` | Clear alert history |

### 20.5 Frontend Alert Components

**`AlertBanner.tsx`** (update from Phase 7 spec):
- Shows all active critical alerts stacked at top of dashboard
- Each alert has: severity icon, message, timestamp, acknowledge (✕) button
- Warning alerts auto-dismiss after 10s, critical alerts persist until acknowledged

**New: `AlertHistoryPanel.tsx`**:
- Collapsible side panel listing last 50 alerts
- Colour-coded by severity
- Shows acknowledged vs unacknowledged status
- "Clear history" button at bottom

**Zustand store addition:**
```typescript
alerts: Alert[]
activeAlerts: Alert[]
addAlert: (alert: Alert) => void
acknowledgeAlert: (alertId: string) => void
clearHistory: () => void
```

---

## 21. Data Export (Parquet / CSV)

### 21.1 What Can Be Exported

| Dataset | Format | Description |
|---|---|---|
| Price history | CSV, Parquet | Timestamped price, spread, depth per step |
| Trade log | CSV, Parquet | All matched trades with buyer/seller agent IDs |
| Agent metrics | CSV | PnL, Sharpe, trade count per agent |
| Prediction log | CSV, Parquet | Timestamped liquidity predictions + features |
| Alert history | CSV | All triggered alerts with severity and payload |
| Order book snapshots | Parquet | Depth snapshots every N steps |

### 21.2 Export Manager

**`backend/src/utils/export_manager.py`**

```python
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

class ExportManager:
    def __init__(self, simulator: MarketSimulator, predictor: LiquidityShockPredictor,
                 alert_manager: AlertManager):
        ...

    def export_price_history(self, fmt: str = "parquet") -> bytes
    def export_trade_log(self, fmt: str = "parquet") -> bytes
    def export_agent_metrics(self, fmt: str = "csv") -> bytes
    def export_prediction_log(self, fmt: str = "parquet") -> bytes
    def export_all(self) -> bytes   # Returns ZIP of all datasets as Parquet
```

Add to `backend/requirements.txt`:
```
pyarrow==14.0.1
```

### 21.3 Export REST Endpoints

| Method | Path | Query params | Description |
|---|---|---|---|
| `GET` | `/api/export/price-history` | `?format=csv\|parquet` | Download price/spread/depth history |
| `GET` | `/api/export/trades` | `?format=csv\|parquet` | Download full trade log |
| `GET` | `/api/export/agents` | `?format=csv` | Download agent PnL metrics |
| `GET` | `/api/export/predictions` | `?format=csv\|parquet` | Download prediction log |
| `GET` | `/api/export/all` | — | Download ZIP of all datasets as Parquet |

All endpoints return appropriate `Content-Disposition` headers for browser download. Only available when simulation state is `STOPPED` or `PAUSED`.

### 21.4 Frontend Export Button

Add "Export" button to dashboard header, visible when state is `STOPPED`. Opens a small modal with checkboxes for each dataset and format selector (CSV / Parquet). Calls the relevant export endpoint and triggers browser download.

---

## 22. Logging & Observability

### 22.1 Structured Logging

**`backend/src/utils/logger.py`** — configure structured JSON logging for all backend components:

```python
import logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage(),
            "extra": getattr(record, "extra", {})
        })
```

Log levels by component:

| Component | Level | Key events to log |
|---|---|---|
| Simulator | INFO | Step milestones (every 1000), price at each milestone |
| Order book | WARNING | Empty book on market order, partial fill |
| Kite provider | INFO/ERROR | Connect, disconnect, fallback trigger, token refresh |
| ML predictor | INFO | Model trained (accuracy), prediction (health score + level) |
| Alert manager | INFO | Alert triggered, acknowledged, auto-cleared |
| FastAPI | INFO | Request method + path + status + latency |
| WebSocket | DEBUG | Connect, disconnect, broadcast errors |

### 22.2 Log Output

In development: stdout with JSON formatter.

In Docker: logs collected by docker-compose, viewable via `docker-compose logs -f backend`.

Add a log file sink for persistent storage:
```python
# Rotates daily, keeps 7 days
handler = TimedRotatingFileHandler("logs/sentinel.log", when="midnight", backupCount=7)
```

### 22.3 Health & Metrics Endpoint

Expand `GET /api/health` to return full observability snapshot:

```json
{
  "status": "healthy",
  "simulation_state": "RUNNING",
  "current_step": 1234,
  "websocket_connections": 3,
  "kite_connected": true,
  "kite_data_source": "primary",
  "last_prediction_ms": 12.4,
  "active_alerts": 1,
  "uptime_seconds": 3600,
  "log_level": "INFO"
}
```

### 22.4 Frontend Observability

Add a small status bar at the bottom of the dashboard showing:
- WebSocket latency (ms) — measured as time between send and receive of heartbeat ping
- Last update timestamp
- Data source badge: "Kite Live" (green) / "yFinance Fallback" (yellow) / "Disconnected" (red)
- Active alert count badge

---

## 23. CI/CD — GitHub Actions

### 23.1 Pipeline Overview

Two workflows triggered on push/PR to `main`:

```
.github/workflows/
├── backend-ci.yml     # Python tests + lint
└── frontend-ci.yml    # TypeScript build + tests
```

### 23.2 Backend CI (`backend-ci.yml`)

```yaml
name: Backend CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with: { python-version: "3.10" }
      - run: pip install -r backend/requirements.txt
      - run: pip install ruff pytest-cov
      - name: Lint
        run: ruff check backend/src/
      - name: Test
        run: pytest backend/tests/ -v --cov=backend/src --cov-report=xml
        env:
          KITE_API_KEY: mock_key
          KITE_ACCESS_TOKEN: mock_token
          SENTINEL_API_KEY: test_key
      - name: Coverage gate
        run: |
          coverage_pct=$(python -c "import xml.etree.ElementTree as ET; t = ET.parse('coverage.xml').getroot(); print(float(t.get('line-rate'))*100)")
          echo "Coverage: $coverage_pct%"
```

**Coverage requirement:** ≥ 70% line coverage. Pipeline fails below this threshold.

**Lint:** `ruff` — no unused imports, no bare `except`, type hints required on all public functions.

### 23.3 Frontend CI (`frontend-ci.yml`)

```yaml
name: Frontend CI
on: [push, pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with: { node-version: "18" }
      - run: cd frontend && npm ci
      - name: Type check
        run: cd frontend && npx tsc --noEmit
      - name: Test
        run: cd frontend && npm run test -- --coverage
      - name: Build
        run: cd frontend && npm run build
        env:
          NEXT_PUBLIC_API_URL: http://localhost:8000
          NEXT_PUBLIC_WS_URL: ws://localhost:8000
          NEXT_PUBLIC_SENTINEL_API_KEY: test_key
```

**TypeScript:** zero type errors (`tsc --noEmit` must pass).

**Build:** `next build` must succeed — no broken imports or missing env vars.

### 23.4 Docker Build Check

Add a third workflow `docker-ci.yml` that runs `docker-compose build` on every PR to catch Dockerfile regressions early:

```yaml
name: Docker Build
on: [pull_request]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: docker-compose build
```

### 23.5 Branch Strategy

| Branch | Purpose | CI | Deploy |
|---|---|---|---|
| `main` | Production-ready code | Full CI | Manual |
| `develop` | Integration branch | Full CI | — |
| `feature/*` | Feature branches | Full CI on PR | — |
| `hotfix/*` | Emergency fixes | Full CI | Fast-track to main |

PR to `main` requires: all CI checks green + at least one approval.

---

## 24. Acceptance Criteria

| Feature | Criterion |
|---|---|
| Order Book | Price-time priority matching with no dropped orders |
| Simulation speed | ≥ 1000 steps/sec on a standard laptop |
| Liquidity predictor | Trains without error, predicts in < 100ms |
| Large order detector | Correctly flags TWAP and Iceberg patterns in unit tests |
| WebSocket | Dashboard receives updates at ≥ 10 Hz |
| Kite API | Real quote returned for `NSE:RELIANCE` within 500ms |
| Kite fallback | Auto-switches to yfinance on Kite disconnect, dashboard shows fallback badge |
| State machine | All 6 state transitions trigger correct UI state on dashboard |
| API auth | Requests without valid `X-API-Key` return HTTP 403 |
| Alerts | Critical alert appears within 1 WebSocket cycle of threshold breach |
| Alert history | Last 50 alerts retrievable via `GET /api/alerts/history` |
| Data export | `GET /api/export/all` returns valid ZIP with Parquet files after simulation stops |
| Logging | All ERROR-level events appear in `logs/sentinel.log` within 1 second |
| CI | Both GitHub Actions workflows pass on a clean `main` branch push |
| Dashboard | All components render without error on fresh WS connection |
| Docker | `docker-compose up` brings full stack online in < 2 minutes |
| Coverage | Backend test coverage ≥ 70% |
| TypeScript | `tsc --noEmit` passes with zero errors |

---

*End of SENTINEL PRD v2.0*
