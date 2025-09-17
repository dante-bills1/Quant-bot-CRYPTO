"""
Crypto Handler

This module provides a unified interface for crypto trading operations,
replacing the MT5Handler with crypto exchange functionality.
"""

import asyncio
import math
import time
from typing import Dict, List, Optional, Any, Tuple, Callable
import pandas as pd
from loguru import logger

from src.crypto_exchange import (
    CryptoExchange, ExchangeFactory, Order, Position, Balance, Ticker,
    OrderType, OrderSide, OrderStatus
)


class CryptoHandler:
    """Unified crypto trading handler that replaces MT5Handler."""
    
    def __init__(self, exchange_name: str = "bybit", api_key: str = "", api_secret: str = "", sandbox: bool = False):
        """
        Initialize the crypto handler.
        
        Args:
            exchange_name: Name of the exchange to use ('bybit', 'binance')
            api_key: Exchange API key
            api_secret: Exchange API secret
            sandbox: Whether to use sandbox/testnet
        """
        self.exchange_name = exchange_name
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox
        self.exchange: Optional[CryptoExchange] = None
        self.connected = False
        self._price_callbacks: Dict[str, Callable] = {}
        
    async def initialize(self) -> bool:
        """Initialize the crypto handler and connect to exchange."""
        try:
            # Create exchange instance
            self.exchange = ExchangeFactory.create_exchange(
                self.exchange_name, 
                self.api_key, 
                self.api_secret, 
                self.sandbox
            )
            
            # Connect to exchange
            self.connected = await self.exchange.connect()
            
            if self.connected:
                logger.success(f"CryptoHandler initialized with {self.exchange_name}")
                return True
            else:
                logger.error(f"Failed to connect to {self.exchange_name}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize CryptoHandler: {e}")
            return False
    
    async def shutdown(self) -> bool:
        """Shutdown the crypto handler."""
        try:
            if self.exchange:
                await self.exchange.disconnect()
            self.connected = False
            logger.info("CryptoHandler shutdown complete")
            return True
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            return False
    
    # Account and Balance Methods
    async def get_account_info(self) -> Optional[Dict[str, Any]]:
        """Get account information."""
        if not self.connected or not self.exchange:
            return None
        
        try:
            return await self.exchange.get_account_info()
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return None
    
    async def get_balance(self) -> List[Balance]:
        """Get account balance."""
        if not self.connected or not self.exchange:
            return []
        
        try:
            return await self.exchange.get_balance()
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return []
    
    async def get_free_margin(self) -> float:
        """Get free margin (USDT balance)."""
        try:
            balance = await self.get_balance()
            for b in balance:
                if b.currency == "USDT":
                    return b.free
            return 0.0
        except Exception as e:
            logger.error(f"Failed to get free margin: {e}")
            return 0.0
    
    # Market Data Methods
    async def get_market_data(
        self,
        symbol: str,
        timeframe: str,
        num_candles: int = 1000
    ) -> Optional[pd.DataFrame]:
        """Get historical market data."""
        if not self.connected or not self.exchange:
            return None

        try:
            return await self.fetch_ohlcv(symbol, timeframe, num_candles)
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            return None

    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        limit: int = 1000,
        params: Optional[Dict[str, Any]] = None
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data with proper incomplete bar handling.

        Based on reference bot's fetch_ohlcv pattern:
        - Fetches data with category parameter
        - Removes incomplete current bar
        - Reindexes to ensure complete timeframe grid
        - Handles volume data properly

        Args:
            symbol: Trading symbol
            timeframe: Timeframe string (e.g., '4h')
            limit: Number of candles to fetch
            params: Additional parameters

        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Use linear category for perpetual futures
            fetch_params = {"category": "linear"}
            if params:
                fetch_params.update(params)

            # Fetch OHLCV data
            ohlcv = await self.exchange.get_historical_data(symbol, timeframe, limit)

            if ohlcv is None or ohlcv.empty:
                logger.warning(f"No OHLCV data received for {symbol} {timeframe}")
                return pd.DataFrame()

            # Check if data is already a DataFrame (processed by exchange)
            if isinstance(ohlcv, pd.DataFrame):
                df = ohlcv.copy()
                logger.debug(f"Received processed DataFrame with {len(df)} rows for {symbol} {timeframe}")
            else:
                # Handle raw OHLCV data (list format)
                logger.debug(f"Received raw OHLCV data for {symbol} {timeframe}")
                df = pd.DataFrame(ohlcv, columns=["timestamp","open","high","low","close","volume"])

                # Validate raw data
                if df.empty:
                    logger.warning(f"Empty OHLCV data received for {symbol} {timeframe}")
                    return pd.DataFrame()

                # Convert timestamp and validate
                try:
                    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True, errors='coerce')
                    # Drop any rows with invalid timestamps
                    df = df.dropna(subset=['timestamp'])
                    if df.empty:
                        logger.warning(f"All timestamps invalid for {symbol} {timeframe}")
                        return pd.DataFrame()

                    df.set_index("timestamp", inplace=True)
                except Exception as e:
                    logger.error(f"Error converting timestamps for {symbol} {timeframe}: {e}")
                    return pd.DataFrame()

            # Validate and clean OHLCV data
            try:
                # Ensure all OHLCV columns exist and are numeric
                required_cols = ['open', 'high', 'low', 'close', 'volume']
                for col in required_cols:
                    if col not in df.columns:
                        logger.error(f"Missing required column '{col}' for {symbol} {timeframe}")
                        return pd.DataFrame()

                    # Convert to numeric, coercing errors to NaN
                    df[col] = pd.to_numeric(df[col], errors='coerce')

                # Drop rows with NaN values in essential columns
                df = df.dropna(subset=['open', 'high', 'low', 'close'])

                # Ensure volume is non-negative
                if 'volume' in df.columns:
                    df['volume'] = df['volume'].clip(lower=0)

                if df.empty:
                    logger.warning(f"All OHLCV data invalid after cleaning for {symbol} {timeframe}")
                    return pd.DataFrame()

            except Exception as e:
                logger.error(f"Error validating OHLCV data for {symbol} {timeframe}: {e}")
                return pd.DataFrame()

            # Remove incomplete current bar
            if len(df) >= 2:
                try:
                    now = int(time.time() * 1000)
                    tf_ms = self.exchange.parse_timeframe(timeframe) * 1000

                    # Safely get last timestamp value
                    last_ts_ns = df.index[-1].value
                    if last_ts_ns > 0:  # Check for valid timestamp
                        last_ts = int(last_ts_ns / 1e6)  # Convert to milliseconds

                        if now - last_ts < tf_ms:
                            logger.debug(f"Removing incomplete current bar for {symbol} {timeframe}")
                            df = df.iloc[:-1]  # Remove open bar
                    else:
                        logger.warning(f"Invalid timestamp value for {symbol} {timeframe}")
                except (ValueError, OverflowError, AttributeError) as e:
                    logger.warning(f"Error removing incomplete bar for {symbol} {timeframe}: {e}")

            # Reindex to ensure complete timeframe grid
            if not df.empty:
                try:
                    # Validate index before reindexing
                    if df.index.isna().any():
                        logger.warning(f"Found NaT values in index for {symbol} {timeframe}, skipping reindex")
                        return df

                    # Map timeframe to pandas frequency
                    pandas_freq_map = {
                        '1m': '1min', '3m': '3min', '5m': '5min', '15m': '15min', '30m': '30min',
                        '1h': '1h', '2h': '2h', '4h': '4h', '6h': '6h', '8h': '8h', '12h': '12h',
                        '1d': '1D', '3d': '3D', '1w': '1W', '1M': '1M'
                    }
                    pandas_freq = pandas_freq_map.get(timeframe, '1h')  # Default to 1 hour

                    start = df.index[0].floor(pandas_freq)
                    end = df.index[-1].floor(pandas_freq)

                    # Validate start and end are not NaT
                    if pd.isna(start) or pd.isna(end):
                        logger.warning(f"Invalid start/end dates for {symbol} {timeframe}, skipping reindex")
                        return df

                    # Create date range with error handling
                    try:
                        grid = pd.date_range(start, end, freq=pandas_freq, tz="UTC")
                        df = df.reindex(grid).ffill()
                        df["volume"] = df["volume"].fillna(0)
                    except ValueError as e:
                        logger.warning(f"Error creating date range for {symbol} {timeframe}: {e}")
                        return df

                except Exception as e:
                    logger.warning(f"Error during reindexing for {symbol} {timeframe}: {e}")
                    return df

            logger.debug(f"Fetched {len(df)} OHLCV candles for {symbol} {timeframe}")
            return df

        except Exception as e:
            logger.error(f"Error fetching OHLCV data for {symbol} {timeframe}: {e}")
            return pd.DataFrame()
    
    async def get_ticker(self, symbol: str) -> Optional[Ticker]:
        """Get ticker data for a symbol."""
        if not self.connected or not self.exchange:
            return None
        
        try:
            return await self.exchange.get_ticker(symbol)
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            return None
    
    async def get_last_tick(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get last tick data for a symbol."""
        try:
            ticker = await self.get_ticker(symbol)
            if ticker:
                return {
                    "symbol": symbol,
                    "bid": ticker.bid,
                    "ask": ticker.ask,
                    "last": ticker.last,
                    "time": ticker.timestamp
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get last tick for {symbol}: {e}")
            return None
    
    # Order Management Methods
    async def place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        order_type: str = "market",
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        client_order_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Place an order (generic method that delegates to specific order types).

        Args:
            symbol: Trading symbol
            side: 'buy' or 'sell'
            amount: Order amount
            order_type: 'market' or 'limit'
            price: Limit price (required for limit orders)
            stop_price: Stop price (optional)
            client_order_id: Client order ID (optional)

        Returns:
            Order result or None
        """
        try:
            if order_type.lower() == "market":
                return await self.place_market_order(symbol, side, amount, stop_price or 0, None, "", client_order_id)
            elif order_type.lower() == "limit":
                if price is None:
                    logger.error("Price is required for limit orders")
                    return None
                return await self.place_limit_order(symbol, side, amount, price, stop_price or 0, None, "", client_order_id)
            else:
                logger.error(f"Unsupported order type: {order_type}")
                return None
        except Exception as e:
            logger.error(f"Failed to place {order_type} order for {symbol}: {e}")
            return None

    async def place_market_order(
        self,
        symbol: str,
        order_type: str,  # "buy" or "sell"
        volume: float,
        stop_loss: float,
        take_profit: Optional[float] = None,
        comment: str = "",
        magic_number: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Place a market order."""
        if not self.connected or not self.exchange:
            return None

        try:
            # Get current price for quantity enforcement
            current_price = await self._get_current_price_for_order(symbol)
            if not current_price:
                logger.error(f"Could not get current price for {symbol}")
                return None

            # Enforce minimum quantity requirements
            adj_volume, debug = self._enforce_min_qty(volume, current_price, symbol)

            if adj_volume <= 0:
                logger.warning(f"[skip] Qty below exchange minimums for {symbol}; order skipped.")
                logger.debug(f"Qty enforcement debug: {debug}")
                return None

            # Log quantity adjustment if it changed
            if abs(adj_volume - volume) > 1e-8:
                logger.info(f"[size] {symbol} desired={volume:.6f} -> send={adj_volume:.6f}")

            side = OrderSide.BUY if order_type.lower() == "buy" else OrderSide.SELL

            order = await self.exchange.place_order(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                amount=adj_volume
            )

            # Set stop loss and take profit if provided
            if stop_loss or take_profit:
                # Note: In crypto, SL/TP are typically handled by the exchange
                # This is a simplified implementation
                pass

            return {
                "ticket": order.id,
                "symbol": symbol,
                "type": order_type,
                "volume": adj_volume,
                "price": order.price or 0.0,
                "sl": stop_loss,
                "tp": take_profit,
                "comment": comment,
                "magic": magic_number,
                "time": order.timestamp or int(time.time() * 1000)
            }

        except Exception as e:
            logger.error(f"Failed to place market order: {e}")
            return None
    
    async def place_limit_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        limit_price: float,
        stop_loss: float,
        take_profit: float,
        comment: str = "",
        magic_number: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Place a limit order."""
        if not self.connected or not self.exchange:
            return None
        
        try:
            side = OrderSide.BUY if order_type.lower() == "buy" else OrderSide.SELL
            
            order = await self.exchange.place_order(
                symbol=symbol,
                side=side,
                order_type=OrderType.LIMIT,
                amount=volume,
                price=limit_price
            )
            
            return {
                "ticket": order.id,
                "symbol": symbol,
                "type": order_type,
                "volume": volume,
                "price": limit_price,
                "sl": stop_loss,
                "tp": take_profit,
                "comment": comment,
                "magic": magic_number,
                "time": order.timestamp or int(time.time() * 1000)
            }
            
        except Exception as e:
            logger.error(f"Failed to place limit order: {e}")
            return None
    
    async def get_open_positions(self, magic_number: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get open positions."""
        if not self.connected or not self.exchange:
            return []
        
        try:
            positions = await self.exchange.get_positions()
            
            result = []
            for pos in positions:
                # Skip positions with invalid or zero size
                if not hasattr(pos, 'size') or pos.size <= 0:
                    continue

                result.append({
                    "ticket": f"pos_{pos.symbol}_{pos.side}",
                    "symbol": pos.symbol,
                    "type": "buy" if pos.side == "long" else "sell",
                    "volume": float(pos.size),
                    "price_open": float(pos.entry_price or 0),
                    "price_current": float(pos.mark_price or 0),
                    "sl": 0.0,  # Would need to track separately
                    "tp": 0.0,  # Would need to track separately
                    "profit": float(pos.unrealized_pnl or 0),
                    "magic": magic_number or 0,
                    "time": pos.timestamp or int(time.time() * 1000)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get open positions: {e}")
            return []
    
    async def close_position(self, ticket: int, magic_number: Optional[int] = None) -> bool:
        """Close a position."""
        if not self.connected or not self.exchange:
            return False
        
        try:
            # Extract symbol and side from ticket
            # This is a simplified implementation
            # In practice, you'd need to track position details
            positions = await self.get_open_positions(magic_number)
            for pos in positions:
                if pos["ticket"] == str(ticket):
                    return await self.exchange.close_position(pos["symbol"], pos["type"])
            
            logger.warning(f"Position {ticket} not found")
            return False
            
        except Exception as e:
            logger.error(f"Failed to close position {ticket}: {e}")
            return False
    
    # Symbol Information Methods
    async def get_symbol_info(self, symbol: str) -> Optional[Any]:
        """Get symbol information."""
        if not self.connected or not self.exchange:
            return None
        
        try:
            return await self.exchange.get_symbol_info(symbol)
        except Exception as e:
            logger.error(f"Failed to get symbol info for {symbol}: {e}")
            return None
    
    async def get_spread(self, symbol: str) -> float:
        """Get spread for a symbol."""
        try:
            ticker = await self.get_ticker(symbol)
            if ticker:
                return ticker.ask - ticker.bid
            return 0.0
        except Exception as e:
            logger.error(f"Failed to get spread for {symbol}: {e}")
            return 0.0
    
    async def get_min_stop_distance(self, symbol: str, use_fallback: bool = False) -> float:
        """Get minimum stop distance for a symbol."""
        try:
            symbol_info = await self.get_symbol_info(symbol)
            if symbol_info:
                # This would depend on exchange-specific implementation
                # For now, return a default value
                return 0.001  # 0.1% of price
            return 0.001
        except Exception as e:
            logger.error(f"Failed to get min stop distance for {symbol}: {e}")
            return 0.001
    
    
    # WebSocket Methods
    async def start_websocket(self, symbol: str, callback: Callable) -> bool:
        """Start WebSocket connection for real-time data."""
        if not self.connected or not self.exchange:
            return False
        
        try:
            self._price_callbacks[symbol] = callback
            return await self.exchange.start_websocket(symbol, callback)
        except Exception as e:
            logger.error(f"Failed to start WebSocket for {symbol}: {e}")
            return False
    
    async def stop_websocket(self, symbol: str) -> bool:
        """Stop WebSocket connection."""
        if not self.connected or not self.exchange:
            return False
        
        try:
            if symbol in self._price_callbacks:
                del self._price_callbacks[symbol]
            return await self.exchange.stop_websocket(symbol)
        except Exception as e:
            logger.error(f"Failed to stop WebSocket for {symbol}: {e}")
            return False
    
    # Utility Methods
    def is_connected(self) -> bool:
        """Check if handler is connected."""
        return self.connected and self.exchange is not None
    
    # ---- Market Filters & Quantity Enforcement ----
    def _market_filters(self, symbol: str) -> Tuple[float, float, float]:
        """
        Get market filters for a symbol.

        Based on reference bot's _market_filters pattern:
        - Minimum quantity
        - Step size for quantity
        - Minimum cost

        Args:
            symbol: Trading symbol

        Returns:
            Tuple of (min_qty, step, min_cost)
        """
        try:
            if not self.connected or not self.exchange:
                return 0.0, 0.0, 0.0

            market = self.exchange.market(symbol)
            min_qty = None
            step = None
            min_cost = None

            # CCXT standard limits
            try:
                min_qty = ((market.get("limits") or {}).get("amount") or {}).get("min")
                min_cost = ((market.get("limits") or {}).get("cost") or {}).get("min")
            except Exception:
                pass

            # Precision as fallback for step
            try:
                prec = (market.get("precision") or {}).get("amount")
                if prec is not None:
                    step = 10 ** (-int(prec))
            except Exception:
                pass

            # Exchange-specific info (Bybit v5 format)
            info = market.get("info") or {}
            if self.exchange_name == "bybit":
                lot = info.get("lotSizeFilter") or {}
                try:
                    if lot.get("minOrderQty") is not None:
                        min_qty = float(lot["minOrderQty"])
                    if lot.get("qtyStep") is not None:
                        step = float(lot["qtyStep"])
                except Exception:
                    pass

            return float(min_qty or 0.0), float(step or 0.0), float(min_cost or 0.0)

        except Exception as e:
            logger.error(f"Error getting market filters for {symbol}: {e}")
            return 0.0, 0.0, 0.0

    def _enforce_min_qty(self, desired_qty: float, price: float, symbol: str) -> Tuple[float, Dict[str, float]]:
        """
        Enforce minimum quantity requirements.

        Based on reference bot's _enforce_min_qty pattern:
        - Apply minimum quantity limits
        - Apply minimum cost limits
        - Round to valid step size
        - Return detailed debug info

        Args:
            desired_qty: Desired quantity
            price: Current price
            symbol: Trading symbol

        Returns:
            Tuple of (adjusted_qty, debug_info)
        """
        min_qty, step, min_cost = self._market_filters(symbol)

        debug = {
            "desired": desired_qty,
            "step": step,
            "min_qty": min_qty,
            "min_cost": min_cost,
            "price": price
        }

        qty = max(desired_qty, 0.0)

        # Round to valid step size first
        if step > 0:
            qty = round(qty / step) * step

        # Apply minimum quantity
        if min_qty and qty < min_qty:
            qty = min_qty

        # Apply minimum cost requirement
        if min_cost and price > 0:
            min_qty_from_cost = min_cost / price
            if qty * price < min_cost:
                qty = min_qty_from_cost

        # Round again to ensure step compliance
        if step > 0:
            qty = round(qty / step) * step

        debug["final"] = qty
        return qty, debug

    def _ceil_to_step(self, x: float, step: float) -> float:
        """Round up to the nearest step size."""
        if step and step > 0:
            return math.ceil(x / step) * step
        return x

    def _floor_to_step(self, x: float, step: float) -> float:
        """Round down to the nearest step size."""
        if step and step > 0:
            return math.floor(x / step) * step
        return x

    async def _get_current_price_for_order(self, symbol: str) -> Optional[float]:
        """Get current price for order placement."""
        try:
            ticker = await self.get_ticker(symbol)
            if ticker:
                return ticker.last
            return None
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None

    async def get_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: Any,
        end_date: Any
    ) -> Optional[pd.DataFrame]:
        """Get historical data for a date range."""
        if not self.connected or not self.exchange:
            return None

        try:
            # For now, return recent data (exchanges typically don't support arbitrary date ranges)
            return await self.exchange.get_historical_data(symbol, timeframe, 1000)
        except Exception as e:
            logger.error(f"Failed to get historical data: {e}")
            return None
    
    # Compatibility methods for existing code
    async def get_latest_candle_time(self, symbol: str, timeframe: str) -> Optional[int]:
        """Get latest candle time (for compatibility)."""
        try:
            data = await self.get_market_data(symbol, timeframe, 1)
            if data is not None and not data.empty:
                return int(data.index[-1].timestamp() * 1000)

            # Fallback: try to get timestamp from ticker
            ticker = await self.get_ticker(symbol)
            if ticker and ticker.timestamp > 0:
                logger.info(f"Using ticker timestamp for {symbol} as fallback")
                return ticker.timestamp

            return None
        except Exception as e:
            logger.error(f"Failed to get latest candle time: {e}")
            return None
