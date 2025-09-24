"""
WebSocket Manager

This module provides centralized WebSocket management for real-time crypto data.
Based on the reference file's WebSocket implementation patterns.
"""

import asyncio
import json
import time
import threading
from typing import Dict, List, Optional, Callable, Any
from loguru import logger

from src.crypto_exchange import CryptoExchange


class WebSocketManager:
    """Manages WebSocket connections for real-time crypto data."""
    
    def __init__(self, exchange: CryptoExchange):
        """
        Initialize WebSocket manager.
        
        Args:
            exchange: Crypto exchange instance
        """
        self.exchange = exchange
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.callbacks: Dict[str, List[Callable]] = {}
        self.running = False
        self._lock = threading.Lock()
        
    async def start(self) -> bool:
        """Start the WebSocket manager."""
        try:
            self.running = True
            logger.success("WebSocketManager started")
            return True
        except Exception as e:
            logger.error(f"Failed to start WebSocketManager: {e}")
            return False
    
    async def stop(self) -> bool:
        """Stop the WebSocket manager."""
        try:
            self.running = False
            
            # Stop all connections
            for symbol in list(self.connections.keys()):
                await self.stop_symbol_stream(symbol)
            
            logger.info("WebSocketManager stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop WebSocketManager: {e}")
            return False
    
    async def start_symbol_stream(
        self, 
        symbol: str, 
        callback: Callable[[float], None],
        stream_type: str = "trade"
    ) -> bool:
        """
        Start WebSocket stream for a symbol.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT:USDT')
            callback: Function to call with price updates
            stream_type: Type of stream ('trade', 'ticker', 'orderbook')
        """
        try:
            with self._lock:
                if symbol in self.connections:
                    logger.warning(f"Stream already exists for {symbol}")
                    # Add callback to existing stream
                    if callback not in self.callbacks.get(symbol, []):
                        self.callbacks[symbol].append(callback)
                    return True
                
                # Create price callback wrapper
                def price_callback(price: float):
                    if self.running and symbol in self.callbacks:
                        for cb in self.callbacks[symbol]:
                            try:
                                cb(price)
                            except Exception as e:
                                logger.error(f"Callback error for {symbol}: {e}")
                
                # Start exchange WebSocket
                success = await self.exchange.start_websocket(symbol, price_callback)
                
                if success:
                    self.connections[symbol] = {
                        "stream_type": stream_type,
                        "started_at": time.time(),
                        "active": True,
                        "websocket_active": True,
                        "rest_fallback_active": False,
                        "last_price_update": time.time()
                    }
                    self.callbacks[symbol] = [callback]
                    logger.success(f"Started WebSocket stream for {symbol}")
                    return True
                else:
                    logger.warning(f"WebSocket failed for {symbol}, starting REST fallback")
                    # Start REST fallback
                    success = await self._start_rest_fallback(symbol, callback)
                    if success:
                        self.connections[symbol] = {
                            "stream_type": stream_type,
                            "started_at": time.time(),
                            "active": True,
                            "websocket_active": False,
                            "rest_fallback_active": True,
                            "last_price_update": time.time()
                        }
                        self.callbacks[symbol] = [callback]
                        logger.info(f"Started REST fallback for {symbol}")
                        return True
                    else:
                        logger.error(f"Failed to start any stream for {symbol}")
                        return False
                    
        except Exception as e:
            logger.error(f"Error starting symbol stream for {symbol}: {e}")
            return False
    
    async def stop_symbol_stream(self, symbol: str) -> bool:
        """Stop WebSocket stream for a symbol."""
        try:
            with self._lock:
                if symbol not in self.connections:
                    logger.warning(f"No stream found for {symbol}")
                    return True
                
                # Stop exchange WebSocket
                await self.exchange.stop_websocket(symbol)
                
                # Clean up
                del self.connections[symbol]
                if symbol in self.callbacks:
                    del self.callbacks[symbol]
                
                logger.info(f"Stopped WebSocket stream for {symbol}")
                return True
                
        except Exception as e:
            logger.error(f"Error stopping symbol stream for {symbol}: {e}")
            return False
    
    def add_callback(self, symbol: str, callback: Callable[[float], None]) -> bool:
        """Add a callback to an existing stream."""
        try:
            with self._lock:
                if symbol not in self.connections:
                    logger.warning(f"No stream found for {symbol}")
                    return False
                
                if symbol not in self.callbacks:
                    self.callbacks[symbol] = []
                
                if callback not in self.callbacks[symbol]:
                    self.callbacks[symbol].append(callback)
                    logger.info(f"Added callback for {symbol}")
                    return True
                else:
                    logger.warning(f"Callback already exists for {symbol}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error adding callback for {symbol}: {e}")
            return False
    
    def remove_callback(self, symbol: str, callback: Callable[[float], None]) -> bool:
        """Remove a callback from a stream."""
        try:
            with self._lock:
                if symbol not in self.callbacks:
                    return False
                
                if callback in self.callbacks[symbol]:
                    self.callbacks[symbol].remove(callback)
                    logger.info(f"Removed callback for {symbol}")
                    
                    # If no more callbacks, stop the stream
                    if not self.callbacks[symbol]:
                        asyncio.create_task(self.stop_symbol_stream(symbol))
                    
                    return True
                else:
                    logger.warning(f"Callback not found for {symbol}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error removing callback for {symbol}: {e}")
            return False
    
    def get_active_streams(self) -> List[str]:
        """Get list of active stream symbols."""
        with self._lock:
            return list(self.connections.keys())
    
    def get_stream_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get information about a stream."""
        with self._lock:
            return self.connections.get(symbol)

    async def _start_rest_fallback(self, symbol: str, callback: Callable[[float], None]) -> bool:
        """
        Start REST API polling as fallback for WebSocket.

        Based on reference bot's REST fallback pattern:
        - Periodic price polling when WebSocket fails
        - Configurable polling interval
        - Error handling and reconnection logic
        """
        try:
            # Import here to avoid circular imports
            from src.crypto_handler import CryptoHandler

            # Create a background task for REST polling
            async def rest_polling_task():
                logger.info(f"Starting REST polling for {symbol} (fallback mode)")

                while self.running and symbol in self.connections:
                    try:
                        # Get current price via REST API
                        # This would need access to crypto_handler, simplified for now
                        price = await self._get_price_via_rest(symbol)

                        if price is not None:
                            # Update last price time
                            with self._lock:
                                if symbol in self.connections:
                                    self.connections[symbol]["last_price_update"] = time.time()

                            # Call callbacks
                            if symbol in self.callbacks:
                                for cb in self.callbacks[symbol]:
                                    try:
                                        cb(price)
                                    except Exception as e:
                                        logger.error(f"REST callback error for {symbol}: {e}")

                        # Wait before next poll (configurable)
                        poll_interval = getattr(self, 'rest_poll_interval', 2.0)  # 2 seconds default
                        await asyncio.sleep(poll_interval)

                    except Exception as e:
                        logger.error(f"REST polling error for {symbol}: {e}")
                        await asyncio.sleep(5)  # Wait longer on error

                logger.info(f"REST polling stopped for {symbol}")

            # Start the polling task
            asyncio.create_task(rest_polling_task())
            return True

        except Exception as e:
            logger.error(f"Failed to start REST fallback for {symbol}: {e}")
            return False

    async def _get_price_via_rest(self, symbol: str) -> Optional[float]:
        """
        Get current price via REST API.

        This is a simplified implementation. In practice, this would
        use the crypto_handler to get price data.
        """
        try:
            # This would integrate with crypto_handler
            # For now, return None to indicate REST fallback is not fully implemented
            logger.debug(f"REST price fetch for {symbol} (placeholder)")
            return None
        except Exception as e:
            logger.error(f"Error getting price via REST for {symbol}: {e}")
            return None

    async def _start_websocket_health_check(self, symbol: str):
        """
        Start health monitoring for WebSocket connection.

        Based on reference bot's connection monitoring:
        - Periodic health checks
        - Automatic reconnection on failure
        - Fallback to REST when needed
        """
        try:
            async def health_check_task():
                logger.debug(f"Starting WebSocket health check for {symbol}")

                while self.running and symbol in self.connections:
                    try:
                        connection_info = self.connections.get(symbol, {})

                        if connection_info.get("websocket_active"):
                            # Check if we've received recent price updates
                            last_update = connection_info.get("last_price_update", 0)
                            time_since_update = time.time() - last_update

                            # If no updates for more than 30 seconds, consider WS dead
                            if time_since_update > 30:
                                logger.warning(f"WebSocket stale for {symbol} ({time_since_update:.1f}s), switching to REST")

                                # Stop WebSocket
                                await self.exchange.stop_websocket(symbol)

                                # Start REST fallback
                                if symbol in self.callbacks:
                                    await self._start_rest_fallback(symbol, self.callbacks[symbol][0])

                                # Update connection status
                                with self._lock:
                                    if symbol in self.connections:
                                        self.connections[symbol]["websocket_active"] = False
                                        self.connections[symbol]["rest_fallback_active"] = True

                        # Health check every 60 seconds
                        await asyncio.sleep(60)

                    except Exception as e:
                        logger.error(f"Health check error for {symbol}: {e}")
                        await asyncio.sleep(10)

                logger.debug(f"Health check stopped for {symbol}")

            # Start the health check task
            asyncio.create_task(health_check_task())

        except Exception as e:
            logger.error(f"Failed to start health check for {symbol}: {e}")

    def _update_price_timestamp(self, symbol: str):
        """Update the last price update timestamp for a symbol."""
        with self._lock:
            if symbol in self.connections:
                self.connections[symbol]["last_price_update"] = time.time()
    
    def is_stream_active(self, symbol: str) -> bool:
        """Check if a stream is active."""
        with self._lock:
            return symbol in self.connections and self.connections[symbol].get("active", False)
    
    async def restart_stream(self, symbol: str) -> bool:
        """Restart a stream (useful for reconnection)."""
        try:
            # Get current callbacks
            callbacks = self.callbacks.get(symbol, [])
            
            # Stop current stream
            await self.stop_symbol_stream(symbol)
            
            # Wait a bit
            await asyncio.sleep(1)
            
            # Restart stream with callbacks
            for callback in callbacks:
                await self.start_symbol_stream(symbol, callback)
            
            logger.info(f"Restarted stream for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error restarting stream for {symbol}: {e}")
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all streams."""
        try:
            health_info = {
                "total_streams": len(self.connections),
                "active_streams": 0,
                "inactive_streams": 0,
                "streams": {}
            }
            
            for symbol, info in self.connections.items():
                is_active = info.get("active", False)
                if is_active:
                    health_info["active_streams"] += 1
                else:
                    health_info["inactive_streams"] += 1
                
                health_info["streams"][symbol] = {
                    "active": is_active,
                    "started_at": info.get("started_at", 0),
                    "uptime": time.time() - info.get("started_at", 0),
                    "callbacks": len(self.callbacks.get(symbol, []))
                }
            
            return health_info
            
        except Exception as e:
            logger.error(f"Error during health check: {e}")
            return {"error": str(e)}
    
    async def cleanup_inactive_streams(self) -> int:
        """Clean up inactive streams."""
        try:
            cleaned = 0
            current_time = time.time()
            
            with self._lock:
                inactive_symbols = []
                
                for symbol, info in self.connections.items():
                    # Consider stream inactive if no callbacks and old
                    uptime = current_time - info.get("started_at", 0)
                    if (not self.callbacks.get(symbol) and uptime > 300) or not info.get("active", False):
                        inactive_symbols.append(symbol)
                
                for symbol in inactive_symbols:
                    await self.stop_symbol_stream(symbol)
                    cleaned += 1
            
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} inactive streams")
            
            return cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning up inactive streams: {e}")
            return 0
