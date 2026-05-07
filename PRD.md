# SENTINEL Product Requirements Document

Date: 2026-05-05

## 1. Purpose
SENTINEL provides a real-time market microstructure simulator and early-warning signals for liquidity shocks and large institutional orders. The product serves quant traders, institutional PMs, and research teams that need interpretable, low-latency visibility into order-book dynamics.

## 2. Goals
- Deliver real-time market state and risk indicators with sub-second latency.
- Provide explainable liquidity health and large-order detection signals.
- Offer a dashboard that is clear, stable, and responsive during simulations.
- Support local development and single-node deployment via Docker or direct run.

## 3. Non-Goals
- Provide live brokerage trading or order execution.
- Replace institutional market data terminals.
- Run multi-node stateful simulations without additional orchestration.

## 4. Personas
- Quant trader who needs actionable early-warning signals and APIs.
- Institutional PM who needs clarity and a compliant summary view.
- Retail trader who uses simulations to learn market dynamics.
- Data engineer who needs simulation data for ML pipelines.

## 5. User Stories
- As a quant trader, I can start and stop simulations via API to test signals.
- As a PM, I can view liquidity health and large-order alerts in one panel.
- As a retail trader, I can watch agent activity to understand market behavior.
- As a data engineer, I can run the simulator headlessly and export results.

## 6. Functional Requirements
### 6.1 Simulation Control
- Start, stop, and switch simulation modes via REST endpoints.
- Return health status, active mode, and connected client counts.

### 6.2 Market State and Predictions
- Provide live order-book snapshot including price, spread, and depth.
- Compute liquidity health score with warning levels.
- Detect large-order patterns and return impact estimates when available.

### 6.3 Real-Time Streaming
- Broadcast market updates via WebSocket.
- Frontend buffers and renders updates at a stable cadence.

### 6.4 Dashboard
- Display price chart, order book heatmap, liquidity gauge, large-order detector.
- Show agent metrics and event tape for simulation behavior.
- Provide clear connection and simulation status indicators.

## 7. Non-Functional Requirements
- Latency: end-to-end updates rendered within 1 second of simulation step.
- Reliability: backend continues running without UI clients connected.
- Maintainability: typed interfaces and structured modules for agents, market, and prediction.
- Security: CORS restricted to configured origins in production.

## 8. Metrics and Success Criteria
- Simulation runs at 10+ steps per second on a developer laptop.
- WebSocket feed delivers updates without stalls for at least 1 hour.
- Liquidity warnings align with synthetic shocks in test scenarios.

## 9. Risks and Mitigations
- In-memory state limits scaling: document single-instance requirement.
- Model dependencies may be heavy: allow disabling RL policy.
- UI overload on frequent updates: buffer updates in the frontend hook.

## 10. Milestones
- M1: Simulation core with agent strategies and stable order book.
- M2: Prediction modules wired to API endpoints.
- M3: Dashboard panels and real-time WebSocket feed.
- M4: Deployment via Docker and cloud hosting.

## 11. Open Questions
- Do we need persistent storage for simulation results and audit logs?
- Should the backend expose a bulk export endpoint for CSV or Parquet?
- What live data provider integration is prioritized first?
