"""FastAPI application — REST endpoints and WebSocket for SENTINEL."""

from contextlib import asynccontextmanager
from typing import Optional
import asyncio

from pydantic import BaseModel
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .websocket import ConnectionManager
from ..market.simulator import MarketSimulator, get_sandbox_presets, create_sandbox_agents
from ..market.oracle import OracleConfig
from ..market.latency_model import LatencyConfig, LatencyMode
from ..market.market_data import fetch_stock, build_oracle_path, POPULAR_TICKERS
from ..agents.market_maker import MarketMakerAgent
from ..agents.hft_agent import HFTAgent
from ..agents.institutional import InstitutionalAgent
from ..agents.retail import RetailAgent
from ..agents.informed import InformedAgent
from ..agents.noise import NoiseAgent
from ..agents.momentum import MomentumAgent
from ..agents.mean_reversion import MeanReversionAgent
from ..agents.spoofing import SpoofingAgent
from ..agents.sentiment import SentimentAgent
from ..agents.rl_agent import RLAgent
from ..prediction.liquidity_shock import LiquidityShockPredictor
from ..prediction.large_order import LargeOrderDetector
from ..market.rl_policy import RLPolicyController
from ..utils.logger import get_logger
from ..utils.config import config

logger = get_logger("api")

# Global singletons
simulator: Optional[MarketSimulator] = None
liquidity_predictor = LiquidityShockPredictor()
large_order_detector = LargeOrderDetector()
rl_policy = RLPolicyController(model_path=config.rl_model_path) if config.rl_policy_enabled else None
manager = ConnectionManager()

# Simulation task handle
_sim_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("SENTINEL API starting up")
    yield
    logger.info("SENTINEL API shutting down")


app = FastAPI(
    title="SENTINEL API",
    description="Smart Early-warning Network for Trading, Institutional orders, and Liquidity Events",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── REST Endpoints ──────────────────────────────────────────────────────────


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "simulation_active": simulator is not None and simulator.running,
        "connected_clients": manager.client_count,
        "mode": simulator.mode if simulator else config.simulation_mode,
        "rl_policy_ready": rl_policy.ready if rl_policy else False,
    }


class ModeRequest(BaseModel):
    mode: str

@app.post("/api/simulation/mode")
async def set_simulation_mode(request: ModeRequest):
    if request.mode not in ["SANDBOX", "LIVE_SHADOW"]:
        return {"error": "Invalid mode"}
    
    config.simulation_mode = request.mode
    if simulator:
        simulator.mode = request.mode
        
    return {"status": "mode_updated", "mode": request.mode}


@app.post("/api/simulation/start")
async def start_simulation():
    global simulator, _sim_task

    if simulator and simulator.running:
        return {"status": "already_running", "step": simulator.step_count}

    large_order_detector.reset()
    if rl_policy:
        rl_policy.reload()

    # Create full agent set
    agents = (
        ([RLAgent("RL_MM", initial_capital=100000.0)] if rl_policy and rl_policy.ready else [])
        + [MarketMakerAgent(f"MM_{i}") for i in range(3)]
        + [HFTAgent(f"HFT_{i}") for i in range(2)]
        + [InstitutionalAgent(f"INST_{i}") for i in range(2)]
        + [RetailAgent(f"RET_{i}") for i in range(10)]
        + [InformedAgent(f"INF_{i}") for i in range(3)]
        + [NoiseAgent(f"NOISE_{i}") for i in range(10)]
        + [MomentumAgent(f"MOM_{i}") for i in range(2)]
        + [MeanReversionAgent(f"MR_{i}") for i in range(2)]
        + [SpoofingAgent(f"SPOOF_0")]
        + [SentimentAgent(f"SENT_{i}") for i in range(5)]
    )

    simulator = MarketSimulator(
        agents,
        initial_price=config.initial_price,
        duration_seconds=config.simulation_duration,
        mode=config.simulation_mode,
    )

    # Run simulation in background task
    _sim_task = asyncio.create_task(_run_simulation_loop())

    return {
        "status": "started",
        "agents": len(agents),
        "initial_price": config.initial_price,
        "rl_policy_active": bool(rl_policy and rl_policy.ready),
    }


@app.post("/api/simulation/stop")
async def stop_simulation():
    global simulator, _sim_task

    if simulator:
        simulator.stop()
    if _sim_task:
        _sim_task.cancel()
        _sim_task = None

    large_order_detector.reset()

    return {"status": "stopped"}


@app.get("/api/prediction/liquidity")
async def get_liquidity_prediction():
    if simulator is None:
        return {"error": "No active simulation"}
    state = simulator.get_market_state()
    return liquidity_predictor.predict(state)


@app.get("/api/prediction/large-order")
async def get_large_order_detection():
    if simulator is None:
        return {"error": "No active simulation"}
    state = simulator.get_market_state()
    detection = large_order_detector.detect(state)
    return detection or {"pattern": None, "message": "No large orders detected"}


@app.get("/api/agents/metrics")
async def get_agent_metrics():
    if simulator is None:
        return {"error": "No active simulation"}
    metrics = {}
    for agent in simulator.agents:
        metrics[agent.agent_id] = agent.get_metrics(simulator.current_price)
    return metrics


@app.get("/api/market/snapshot")
async def get_market_snapshot():
    if simulator is None:
        return {"error": "No active simulation"}
    state = simulator.get_market_state()
    return {
        "price": state["current_price"],
        "mid_price": state["mid_price"],
        "spread": state["spread"],
        "best_bid": state["best_bid"],
        "best_ask": state["best_ask"],
        "depth": state["total_depth"],
        "order_book": {
            "bids": state["bid_levels"],
            "asks": state["ask_levels"],
        },
        "volatility": state["volatility"],
        "step": state["step"],
    }


# ── Sandbox Endpoints ─────────────────────────────────────────────────────────


@app.get("/api/sandbox/presets")
async def list_sandbox_presets():
    return get_sandbox_presets()


class SandboxCreateRequest(BaseModel):
    preset: str = "balanced"
    initial_price: float = 100.0
    oracle_enabled: bool = False
    oracle_kappa: float = 0.05
    oracle_sigma: float = 0.02
    latency_mode: str = "deterministic"
    speed: float = 1.0
    custom_agents: Optional[dict] = None


@app.post("/api/sandbox/create")
async def create_sandbox(request: SandboxCreateRequest):
    global simulator, _sim_task

    if simulator and simulator.running:
        simulator.stop()
        if _sim_task:
            _sim_task.cancel()

    large_order_detector.reset()
    if rl_policy:
        rl_policy.reload()

    # Create agents from preset or custom config
    agents = create_sandbox_agents(request.preset, request.custom_agents)

    # Add RL agent if policy is available
    if rl_policy and rl_policy.ready:
        agents.append(RLAgent("RL_MM", initial_capital=100000.0))

    # Configure oracle
    oracle_cfg = OracleConfig(
        r_bar=request.initial_price,
        kappa=request.oracle_kappa,
        sigma_s=request.oracle_sigma,
        enabled=request.oracle_enabled,
    )

    # Configure latency model
    mode_map = {"zero": LatencyMode.ZERO, "deterministic": LatencyMode.DETERMINISTIC, "cubic": LatencyMode.CUBIC}
    latency_cfg = LatencyConfig(mode=mode_map.get(request.latency_mode, LatencyMode.DETERMINISTIC))

    simulator = MarketSimulator(
        agents,
        initial_price=request.initial_price,
        duration_seconds=config.simulation_duration,
        mode=config.simulation_mode,
        oracle_config=oracle_cfg,
        latency_config=latency_cfg,
        speed_multiplier=request.speed,
    )

    _sim_task = asyncio.create_task(_run_simulation_loop())

    return {
        "status": "started",
        "preset": request.preset,
        "agents": len(agents),
        "oracle_enabled": request.oracle_enabled,
        "latency_mode": request.latency_mode,
        "speed": request.speed,
    }


class SpeedRequest(BaseModel):
    speed: float


@app.put("/api/sandbox/speed")
async def set_sandbox_speed(request: SpeedRequest):
    if simulator is None:
        return {"error": "No active simulation"}
    simulator.speed_multiplier = max(0.1, min(20.0, request.speed))
    return {"speed": simulator.speed_multiplier}


@app.get("/api/sandbox/oracle")
async def get_oracle_data():
    if simulator is None:
        return {"error": "No active simulation"}
    return {
        **simulator.oracle.describe(),
        "recent_history": simulator.oracle.get_recent_history(240),
    }


# ── Stock Replay Endpoints ────────────────────────────────────────────────────


@app.get("/api/sandbox/stocks/popular")
async def list_popular_stocks():
    """Return list of popular tickers for the UI picker."""
    return POPULAR_TICKERS


class StockFetchRequest(BaseModel):
    ticker: str
    period: str = "3mo"    # 1d 5d 1mo 3mo 6mo 1y 2y 5y
    interval: str = "1d"   # 1m 5m 15m 1h 1d 1wk


@app.post("/api/sandbox/stock/fetch")
async def fetch_stock_data(request: StockFetchRequest):
    """Fetch real OHLCV data for a ticker and return calibration stats."""
    try:
        info = fetch_stock(
            ticker=request.ticker,
            period=request.period,
            interval=request.interval,
        )
        return {
            "ticker": info.ticker,
            "name": info.name,
            "currency": info.currency,
            "last_close": info.last_close,
            "period_start": info.period_start,
            "period_end": info.period_end,
            "bars": info.bars,
            "realized_vol": info.realized_vol,
            "mean_return": info.mean_return,
            "price_preview": info.prices[-60:],  # last 60 bars for chart preview
        }
    except ValueError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to fetch {request.ticker}: {e}"}


class StockReplayRequest(BaseModel):
    ticker: str
    period: str = "3mo"
    interval: str = "1d"
    preset: str = "balanced"
    custom_agents: Optional[dict] = None
    latency_mode: str = "deterministic"
    speed: float = 1.0


@app.post("/api/sandbox/stock/replay")
async def start_stock_replay(request: StockReplayRequest):
    """Start a simulation where the oracle follows real historical prices.

    The agent population trades against this real price path — you can
    see how different market participants might have behaved during a
    real event (e.g. earnings, crash, rally).
    """
    global simulator, _sim_task

    try:
        info = fetch_stock(
            ticker=request.ticker,
            period=request.period,
            interval=request.interval,
        )
    except (ValueError, Exception) as e:
        return {"error": str(e)}

    if simulator and simulator.running:
        simulator.stop()
        if _sim_task:
            _sim_task.cancel()

    large_order_detector.reset()

    # Build oracle path from real prices
    oracle_path = build_oracle_path(info, target_steps=500)
    initial_price = float(info.prices[0])

    oracle_cfg = OracleConfig(
        r_bar=initial_price,
        kappa=0.05,
        sigma_s=max(0.001, info.realized_vol / 252),  # calibrated daily vol
        enabled=True,
        replay_path=oracle_path,
    )

    mode_map = {"zero": LatencyMode.ZERO, "deterministic": LatencyMode.DETERMINISTIC, "cubic": LatencyMode.CUBIC}
    latency_cfg = LatencyConfig(mode=mode_map.get(request.latency_mode, LatencyMode.DETERMINISTIC))

    agents = create_sandbox_agents(request.preset, request.custom_agents)

    simulator = MarketSimulator(
        agents,
        initial_price=initial_price,
        duration_seconds=config.simulation_duration,
        mode=config.simulation_mode,
        oracle_config=oracle_cfg,
        latency_config=latency_cfg,
        speed_multiplier=request.speed,
    )

    _sim_task = asyncio.create_task(_run_simulation_loop())

    return {
        "status": "started",
        "ticker": info.ticker,
        "name": info.name,
        "initial_price": initial_price,
        "bars": info.bars,
        "realized_vol": info.realized_vol,
        "agents": len(agents),
        "oracle_path_length": len(oracle_path),
    }


# ── WebSocket ───────────────────────────────────────────────────────────────


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive, receive any client messages
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


# ── Simulation Loop ─────────────────────────────────────────────────────────


async def _run_simulation_loop():
    """Run the simulation and broadcast updates via WebSocket."""
    global simulator

    if simulator is None:
        return

    simulator.running = True
    logger.info("Simulation loop started")

    try:
        while simulator.running and simulator.current_time < simulator.duration_seconds:
            if rl_policy and rl_policy.ready:
                try:
                    rl_policy.prepare_step(simulator)
                except Exception as exc:
                    logger.error(f"RL policy inference failed: {exc}")

            # Run a step
            state = simulator.step()

            # Get predictions
            liquidity_pred = liquidity_predictor.predict(state)
            large_order_det = large_order_detector.detect(state)

            # Get agent metrics
            agent_metrics = {}
            for agent in simulator.agents:
                m = agent.get_metrics(simulator.current_price)
                agent_metrics[agent.agent_id] = {
                    "total_pnl": m["total_pnl"],
                    "realized_pnl": m["realized_pnl"],
                    "unrealized_pnl": m["unrealized_pnl"],
                    "sharpe_ratio": m["sharpe_ratio"],
                    "agent_type": m["agent_type"],
                    "position": m["position"],
                    "num_trades": m["num_trades"],
                }

            # Build the update message
            update = {
                "type": "market_update",
                "timestamp": state["current_time"],
                "price": state["current_price"],
                "spread": state["spread"],
                "depth": state["total_depth"],
                "order_book": {
                    "bids": state["bid_levels"][:10],
                    "asks": state["ask_levels"][:10],
                },
                "liquidity_prediction": liquidity_pred,
                "large_order_detection": large_order_det,
                "agent_metrics": agent_metrics,
                "step": state["step"],
                "volatility": state["volatility"],
                "mode": simulator.mode,
                "speed": simulator.speed_multiplier,
            }

            # Include oracle data if enabled
            if "oracle" in state:
                update["oracle"] = state["oracle"]

            # Broadcast to all connected clients
            if manager.client_count > 0:
                await manager.broadcast(update)

            # Speed-adjusted tick rate: base 100ms / speed_multiplier
            sleep_time = max(0.02, 0.1 / simulator.speed_multiplier)
            await asyncio.sleep(sleep_time)

    except asyncio.CancelledError:
        logger.info("Simulation loop cancelled")
    except Exception as e:
        logger.error(f"Simulation loop error: {e}")
    finally:
        if simulator:
            simulator.running = False
        logger.info("Simulation loop ended")
