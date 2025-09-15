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
                        "active": True
                    }
                    self.callbacks[symbol] = [callback]
                    logger.success(f"Started WebSocket stream for {symbol}")
                    return True
                else:
                    logger.error(f"Failed to start WebSocket stream for {symbol}")
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
