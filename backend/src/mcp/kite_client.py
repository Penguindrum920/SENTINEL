"""Stub client for future Zerodha Kite API integration."""

import asyncio
from typing import Dict, Optional, Callable
from ..utils.logger import get_logger

logger = get_logger("kite_client")

class KiteClient:
    """
    Connects to the Zerodha Kite WebSocket to stream live Level 2 tick data.
    When in LIVE_SHADOW mode, this data replaces the internal OrderBook generation.
    """

    def __init__(self, api_key: str = "", access_token: str = ""):
        self.api_key = api_key
        self.access_token = access_token
        self.connected = False
        self._on_tick_callback: Optional[Callable[[Dict], None]] = None

    async def connect(self):
        """Establish WebSocket connection to Kite."""
        if not self.api_key or not self.access_token:
            logger.warning("Kite API credentials missing. Running in stub mode.")
            self.connected = True
            return

        # Future implementation:
        # self.ws = KiteTicker(self.api_key, self.access_token)
        # self.ws.on_ticks = self._handle_ticks
        # self.ws.connect(threaded=True)
        self.connected = True
        logger.info("Connected to Kite API")

    def subscribe(self, instrument_tokens: list[int]):
        """Subscribe to live market depth for specific tokens."""
        if not self.connected:
            return
        logger.info(f"Subscribed to instruments: {instrument_tokens}")
        # Future implementation:
        # self.ws.subscribe(instrument_tokens)
        # self.ws.set_mode(self.ws.MODE_FULL, instrument_tokens)

    def set_callback(self, callback: Callable[[Dict], None]):
        """Set the function to call when a new tick (OrderBook snapshot) arrives."""
        self._on_tick_callback = callback

    def _handle_ticks(self, ws, ticks):
        """Internal handler for incoming Kite WebSocket ticks."""
        if not self._on_tick_callback:
            return

        for tick in ticks:
            # Parse the Kite MODE_FULL tick into our internal generic OrderBook format
            parsed_data = {
                "instrument_token": tick.get("instrument_token"),
                "last_price": tick.get("last_price"),
                "depth": tick.get("depth"), # Contains dict of 'buy' and 'sell' level arrays
            }
            self._on_tick_callback(parsed_data)

    async def close(self):
        """Terminate the Kite connection."""
        self.connected = False
        # Future implementation:
        # if self.ws:
        #     self.ws.close()
        logger.info("Closed Kite API connection")
