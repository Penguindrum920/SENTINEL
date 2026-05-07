"""Real-world market data fetcher for SENTINEL sandbox replay.

Fetches OHLCV history via yfinance and converts it into a form the
simulator can consume:
  - Prices fed step-by-step into the oracle as the "fundamental value"
  - Initial price seeds the order book
  - Intraday volatility calibrates agent parameters
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np


@dataclass
class StockInfo:
    ticker: str
    name: str
    currency: str
    last_close: float
    period_start: str
    period_end: str
    bars: int
    prices: List[float]          # close prices — used as oracle path
    volumes: List[float]
    highs: List[float]
    lows: List[float]
    returns: List[float]         # log returns
    realized_vol: float          # annualised realized volatility
    mean_return: float           # mean log return per bar


def fetch_stock(
    ticker: str,
    period: str = "1mo",
    interval: str = "1d",
) -> StockInfo:
    """Download OHLCV data from Yahoo Finance and return a StockInfo.

    Args:
        ticker:   Yahoo Finance ticker symbol, e.g. "AAPL", "TSLA", "^NSEI"
        period:   lookback window  — "1d","5d","1mo","3mo","6mo","1y","2y","5y"
        interval: bar interval    — "1m","5m","15m","1h","1d","1wk"

    Returns:
        StockInfo with price path and calibrated statistics.

    Raises:
        ValueError if no data is returned (bad ticker / outside trading hours).
    """
    try:
        import yfinance as yf
    except ImportError:
        raise RuntimeError("yfinance is not installed. Run: pip install yfinance")

    tkr = yf.Ticker(ticker)
    hist = tkr.history(period=period, interval=interval, auto_adjust=True)

    if hist.empty:
        raise ValueError(
            f"No data returned for ticker '{ticker}'. "
            "Check the symbol and try a different period/interval."
        )

    closes = hist["Close"].dropna().tolist()
    volumes = hist["Volume"].dropna().tolist()
    highs = hist["High"].dropna().tolist()
    lows = hist["Low"].dropna().tolist()

    # Align lengths
    n = min(len(closes), len(volumes), len(highs), len(lows))
    closes = closes[:n]
    volumes = volumes[:n]
    highs = highs[:n]
    lows = lows[:n]

    if n < 2:
        raise ValueError(f"Not enough data for '{ticker}' ({n} bars). Try a longer period.")

    # Log returns
    log_returns = [
        float(np.log(closes[i] / closes[i - 1]))
        for i in range(1, n)
        if closes[i] > 0 and closes[i - 1] > 0
    ]

    # Annualised realized vol (assume 252 trading days, or 390 min/day for intraday)
    bars_per_year = {
        "1m": 252 * 390,
        "5m": 252 * 78,
        "15m": 252 * 26,
        "1h": 252 * 6.5,
        "1d": 252,
        "1wk": 52,
    }.get(interval, 252)

    std = float(np.std(log_returns)) if log_returns else 0.01
    realized_vol = std * float(np.sqrt(bars_per_year))
    mean_return = float(np.mean(log_returns)) if log_returns else 0.0

    # Friendly name fallback
    try:
        info = tkr.fast_info
        name = getattr(info, "long_name", None) or ticker
        currency = getattr(info, "currency", "USD") or "USD"
    except Exception:
        name = ticker
        currency = "USD"

    index = hist.index
    return StockInfo(
        ticker=ticker.upper(),
        name=str(name),
        currency=str(currency),
        last_close=float(closes[-1]),
        period_start=str(index[0].date()) if hasattr(index[0], "date") else str(index[0])[:10],
        period_end=str(index[-1].date()) if hasattr(index[-1], "date") else str(index[-1])[:10],
        bars=n,
        prices=closes,
        volumes=volumes,
        highs=highs,
        lows=lows,
        returns=log_returns,
        realized_vol=round(realized_vol, 4),
        mean_return=round(mean_return, 6),
    )


def build_oracle_path(info: StockInfo, target_steps: int = 500) -> List[float]:
    """Resample / extend the real price path to exactly target_steps values.

    If we have fewer bars than target_steps, the path is extended with
    a bootstrapped Ornstein-Uhlenbeck continuation that matches the
    historical vol and drift.
    """
    prices = info.prices[:]

    if len(prices) >= target_steps:
        # Downsample evenly
        indices = [int(i * (len(prices) - 1) / (target_steps - 1)) for i in range(target_steps)]
        return [prices[i] for i in indices]

    # Extend via OU bootstrap
    rng = np.random.RandomState(42)
    sigma = info.realized_vol / np.sqrt(252)   # per-step vol
    kappa = 0.05
    r_bar = info.last_close

    extended = list(prices)
    while len(extended) < target_steps:
        prev = extended[-1]
        drift = kappa * (r_bar - prev)
        noise = sigma * rng.randn()
        nxt = max(0.01, prev + drift + noise)
        extended.append(float(nxt))

    return extended[:target_steps]


POPULAR_TICKERS = [
    {"ticker": "AAPL",  "name": "Apple Inc."},
    {"ticker": "TSLA",  "name": "Tesla Inc."},
    {"ticker": "MSFT",  "name": "Microsoft Corp."},
    {"ticker": "GOOGL", "name": "Alphabet Inc."},
    {"ticker": "AMZN",  "name": "Amazon.com Inc."},
    {"ticker": "NVDA",  "name": "NVIDIA Corp."},
    {"ticker": "META",  "name": "Meta Platforms"},
    {"ticker": "NFLX",  "name": "Netflix Inc."},
    {"ticker": "SPY",   "name": "S&P 500 ETF"},
    {"ticker": "BTC-USD","name": "Bitcoin / USD"},
    {"ticker": "^NSEI", "name": "NIFTY 50 (India)"},
    {"ticker": "^BSESN","name": "SENSEX (India)"},
]
