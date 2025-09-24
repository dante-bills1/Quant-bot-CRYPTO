"""
Crypto Data Manager

This module provides data management for crypto trading operations,
replacing the MT5-based DataManager with crypto exchange functionality.
"""

import asyncio
import time
import sqlite3
import json
from typing import Dict, List, Optional, Any, Callable
import pandas as pd
from loguru import logger

from src.crypto_handler import CryptoHandler
from src.websocket_manager import WebSocketManager


class CryptoDataManager:
    """Manages crypto market data and real-time updates."""
    
    def __init__(self, crypto_handler: CryptoHandler):
        """
        Initialize the crypto data manager.
        
        Args:
            crypto_handler: CryptoHandler instance for exchange operations
        """
        self.crypto_handler = crypto_handler
        self.websocket_manager = WebSocketManager(crypto_handler.exchange)
        self.data_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.timeframe_registry: Dict[str, Dict[str, int]] = {}
        self.db_path = "crypto_trading_data.db"
        self._price_callbacks: Dict[str, List[Callable]] = {}

    @property
    def requirements(self):
        """Provide compatibility with old DataManager interface."""
        # Convert timeframe_registry to the format expected by trading_bot.py
        # From: {symbol: {timeframe: lookback}}
        # To: {(symbol, timeframe): lookback}
        reqs = {}
        for symbol, timeframes in self.timeframe_registry.items():
            for timeframe, lookback in timeframes.items():
                reqs[(symbol, timeframe)] = lookback
        return reqs

    async def initialize(self) -> bool:
        """Initialize the data manager."""
        try:
            # Initialize database
            await self.init_db()
            
            # Start WebSocket manager
            await self.websocket_manager.start()
            
            logger.success("CryptoDataManager initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize CryptoDataManager: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown the data manager."""
        try:
            # Stop WebSocket manager
            await self.websocket_manager.stop()
            
            # Close database connection
            if hasattr(self, '_db_connection'):
                self._db_connection.close()
            
            logger.info("CryptoDataManager shutdown complete")
            return True
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            return False
    
    async def init_db(self):
        """Initialize SQLite database for data persistence."""
        try:
            self._db_connection = sqlite3.connect(self.db_path, check_same_thread=False)
            cursor = self._db_connection.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS market_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    UNIQUE(symbol, timeframe, timestamp)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket TEXT UNIQUE NOT NULL,
                    symbol TEXT NOT NULL,
                    type TEXT NOT NULL,
                    volume REAL NOT NULL,
                    price_open REAL NOT NULL,
                    price_close REAL,
                    sl REAL,
                    tp REAL,
                    profit REAL,
                    magic INTEGER,
                    comment TEXT,
                    time_open INTEGER NOT NULL,
                    time_close INTEGER,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    confidence REAL,
                    reason TEXT,
                    timestamp INTEGER NOT NULL,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            ''')
            
            self._db_connection.commit()
            logger.success("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_market_data(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """Get cached market data for a symbol and timeframe."""
        try:
            if symbol in self.data_cache and timeframe in self.data_cache[symbol]:
                return self.data_cache[symbol][timeframe].copy()
            return None
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol} {timeframe}: {e}")
            return None
    
    async def update_real_time_data(self, symbol: str, timeframe: str, tick: dict):
        """Update real-time data with new tick."""
        try:
            if symbol not in self.data_cache:
                self.data_cache[symbol] = {}
            
            if timeframe not in self.data_cache[symbol]:
                # Initialize with historical data
                await self.update_data(symbol, timeframe)
            
            # Update current candle with new tick
            current_time = int(time.time() * 1000)
            current_candle_time = self._get_candle_time(current_time, timeframe)
            
            if current_candle_time not in self.data_cache[symbol][timeframe].index:
                # Create new candle
                new_candle = pd.DataFrame({
                    'open': [tick['price']],
                    'high': [tick['price']],
                    'low': [tick['price']],
                    'close': [tick['price']],
                    'volume': [tick.get('volume', 0)]
                }, index=[pd.to_datetime(current_candle_time, unit='ms', utc=True)])
                
                self.data_cache[symbol][timeframe] = pd.concat([
                    self.data_cache[symbol][timeframe], new_candle
                ])
            else:
                # Update existing candle
                idx = self.data_cache[symbol][timeframe].index.get_loc(
                    pd.to_datetime(current_candle_time, unit='ms', utc=True)
                )
                
                self.data_cache[symbol][timeframe].iloc[idx, 1] = max(
                    self.data_cache[symbol][timeframe].iloc[idx, 1], tick['price']
                )  # high
                self.data_cache[symbol][timeframe].iloc[idx, 2] = min(
                    self.data_cache[symbol][timeframe].iloc[idx, 2], tick['price']
                )  # low
                self.data_cache[symbol][timeframe].iloc[idx, 3] = tick['price']  # close
                self.data_cache[symbol][timeframe].iloc[idx, 4] += tick.get('volume', 0)  # volume
            
            # Notify callbacks
            if symbol in self._price_callbacks:
                for callback in self._price_callbacks[symbol]:
                    try:
                        callback(tick['price'])
                    except Exception as e:
                        logger.error(f"Callback error for {symbol}: {e}")
                        
        except Exception as e:
            logger.error(f"Failed to update real-time data for {symbol}: {e}")
    
    def register_timeframe(self, symbol: str, timeframe: str, lookback: int):
        """Register a symbol-timeframe combination for data tracking."""
        try:
            if symbol not in self.timeframe_registry:
                self.timeframe_registry[symbol] = {}
            
            self.timeframe_registry[symbol][timeframe] = lookback
            logger.info(f"Registered {symbol} {timeframe} with lookback {lookback}")
            
        except Exception as e:
            logger.error(f"Failed to register timeframe {symbol} {timeframe}: {e}")
    
    async def update_data(self, symbol: str, timeframe: str, force: bool = False, num_candles: Optional[int] = None):
        """Update market data for a symbol and timeframe."""
        try:
            # Get lookback period
            lookback = num_candles or self.timeframe_registry.get(symbol, {}).get(timeframe, 1000)
            
            # Fetch data from exchange
            data = await self.crypto_handler.get_market_data(symbol, timeframe, lookback)
            
            if data is not None and not data.empty:
                # Cache the data
                if symbol not in self.data_cache:
                    self.data_cache[symbol] = {}
                
                self.data_cache[symbol][timeframe] = data
                
                # Store in database
                await self._store_market_data(symbol, timeframe, data)
                
                logger.info(f"Updated data for {symbol} {timeframe}: {len(data)} candles")
            else:
                logger.warning(f"No data received for {symbol} {timeframe}")
                
        except Exception as e:
            error_msg = str(e).lower()
            if "does not have market symbol" in error_msg or "symbol" in error_msg and ("not found" in error_msg or "not available" in error_msg):
                logger.warning(f"Symbol {symbol} not supported by {self.crypto_handler.exchange_name} exchange, skipping")
            else:
                logger.error(f"Failed to update data for {symbol} {timeframe}: {e}")
    
    async def get_market_data_for_symbol(self, symbol: str, timeframes: list) -> dict:
        """Get market data for a symbol across multiple timeframes."""
        try:
            result = {}
            
            for tf in timeframes:
                data = self.get_market_data(symbol, tf)
                if data is not None:
                    result[tf] = data
                else:
                    # Try to fetch if not cached
                    await self.update_data(symbol, tf)
                    data = self.get_market_data(symbol, tf)
                    if data is not None:
                        result[tf] = data
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            return {}
    
    async def start_real_time_updates(self, symbol: str, timeframe: str, callback: Callable[[float], None]):
        """Start real-time price updates for a symbol."""
        try:
            # Register callback
            if symbol not in self._price_callbacks:
                self._price_callbacks[symbol] = []
            
            if callback not in self._price_callbacks[symbol]:
                self._price_callbacks[symbol].append(callback)
            
            # Start WebSocket stream
            await self.websocket_manager.start_symbol_stream(symbol, callback)
            
            logger.info(f"Started real-time updates for {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to start real-time updates for {symbol}: {e}")
    
    async def stop_real_time_updates(self, symbol: str, callback: Callable[[float], None]):
        """Stop real-time price updates for a symbol."""
        try:
            # Remove callback
            if symbol in self._price_callbacks and callback in self._price_callbacks[symbol]:
                self._price_callbacks[symbol].remove(callback)
            
            # Stop WebSocket stream if no more callbacks
            if not self._price_callbacks.get(symbol, []):
                await self.websocket_manager.stop_symbol_stream(symbol)
                del self._price_callbacks[symbol]
            
            logger.info(f"Stopped real-time updates for {symbol}")
            
        except Exception as e:
            logger.error(f"Failed to stop real-time updates for {symbol}: {e}")
    
    async def synchronize_historical_trades(self):
        """Synchronize historical trades from exchange."""
        try:
            # This would fetch trade history from exchange
            # Implementation depends on exchange capabilities
            logger.info("Historical trade synchronization not implemented yet")
            
        except Exception as e:
            logger.error(f"Failed to synchronize historical trades: {e}")
    
    async def log_trade(self, trade_data: dict):
        """Log a trade to the database."""
        try:
            cursor = self._db_connection.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO trades (
                    ticket, symbol, type, volume, price_open, price_close,
                    sl, tp, profit, magic, comment, time_open, time_close
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data.get('ticket', ''),
                trade_data.get('symbol', ''),
                trade_data.get('type', ''),
                trade_data.get('volume', 0.0),
                trade_data.get('price_open', 0.0),
                trade_data.get('price_close', 0.0),
                trade_data.get('sl', 0.0),
                trade_data.get('tp', 0.0),
                trade_data.get('profit', 0.0),
                trade_data.get('magic', 0),
                trade_data.get('comment', ''),
                trade_data.get('time_open', 0),
                trade_data.get('time_close', 0)
            ))
            
            self._db_connection.commit()
            logger.debug(f"Logged trade: {trade_data.get('ticket', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Failed to log trade: {e}")
    
    async def log_signal(self, signal_data: dict):
        """Log a signal to the database."""
        try:
            cursor = self._db_connection.cursor()
            
            cursor.execute('''
                INSERT INTO signals (
                    symbol, timeframe, signal_type, entry_price, stop_loss,
                    take_profit, confidence, reason, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_data.get('symbol', ''),
                signal_data.get('timeframe', ''),
                signal_data.get('signal_type', ''),
                signal_data.get('entry_price', 0.0),
                signal_data.get('stop_loss', 0.0),
                signal_data.get('take_profit', 0.0),
                signal_data.get('confidence', 0.0),
                signal_data.get('reason', ''),
                signal_data.get('timestamp', int(time.time() * 1000))
            ))
            
            self._db_connection.commit()
            logger.debug(f"Logged signal: {signal_data.get('symbol', 'unknown')}")
            
        except Exception as e:
            logger.error(f"Failed to log signal: {e}")
    
    async def _store_market_data(self, symbol: str, timeframe: str, data: pd.DataFrame):
        """Store market data in database."""
        try:
            cursor = self._db_connection.cursor()
            
            for timestamp, row in data.iterrows():
                cursor.execute('''
                    INSERT OR REPLACE INTO market_data (
                        symbol, timeframe, timestamp, open, high, low, close, volume
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    symbol,
                    timeframe,
                    int(timestamp.timestamp() * 1000),
                    float(row['open']),
                    float(row['high']),
                    float(row['low']),
                    float(row['close']),
                    float(row['volume'])
                ))
            
            self._db_connection.commit()
            
        except Exception as e:
            logger.error(f"Failed to store market data: {e}")
    
    def _get_candle_time(self, timestamp: int, timeframe: str) -> int:
        """Get the candle start time for a given timestamp and timeframe."""
        try:
            # Convert timeframe to seconds
            tf_seconds = self._timeframe_to_seconds(timeframe)
            
            # Calculate candle start time
            candle_time = (timestamp // (tf_seconds * 1000)) * (tf_seconds * 1000)
            return candle_time
            
        except Exception as e:
            logger.error(f"Failed to get candle time: {e}")
            return timestamp
    
    def _timeframe_to_seconds(self, timeframe: str) -> int:
        """Convert timeframe string to seconds."""
        timeframe_map = {
            '1m': 60,
            '3m': 180,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '2h': 7200,
            '4h': 14400,
            '6h': 21600,
            '8h': 28800,
            '12h': 43200,
            '1d': 86400,
            '3d': 259200,
            '1w': 604800,
            '1M': 2592000
        }
        
        return timeframe_map.get(timeframe, 3600)  # Default to 1 hour
    
    def get_cached_symbols(self) -> List[str]:
        """Get list of cached symbols."""
        return list(self.data_cache.keys())
    
    def get_cached_timeframes(self, symbol: str) -> List[str]:
        """Get list of cached timeframes for a symbol."""
        return list(self.data_cache.get(symbol, {}).keys())
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old market data from database."""
        try:
            cursor = self._db_connection.cursor()
            
            cutoff_time = int((time.time() - (days_to_keep * 24 * 3600)) * 1000)
            
            cursor.execute('''
                DELETE FROM market_data 
                WHERE timestamp < ?
            ''', (cutoff_time,))
            
            deleted_rows = cursor.rowcount
            self._db_connection.commit()
            
            if deleted_rows > 0:
                logger.info(f"Cleaned up {deleted_rows} old market data records")
            
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    def __del__(self):
        """Cleanup on destruction."""
        try:
            if hasattr(self, '_db_connection'):
                self._db_connection.close()
        except Exception:
            pass
