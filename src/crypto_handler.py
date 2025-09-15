"""
Crypto Handler

This module provides a unified interface for crypto trading operations,
replacing the MT5Handler with crypto exchange functionality.
"""

import asyncio
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
            return await self.exchange.get_historical_data(symbol, timeframe, num_candles)
        except Exception as e:
            logger.error(f"Failed to get market data for {symbol}: {e}")
            return None
    
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
            side = OrderSide.BUY if order_type.lower() == "buy" else OrderSide.SELL
            
            order = await self.exchange.place_order(
                symbol=symbol,
                side=side,
                order_type=OrderType.MARKET,
                amount=volume
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
                "volume": volume,
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
                result.append({
                    "ticket": f"pos_{pos.symbol}_{pos.side}",
                    "symbol": pos.symbol,
                    "type": "buy" if pos.side == "long" else "sell",
                    "volume": pos.size,
                    "price_open": pos.entry_price,
                    "price_current": pos.mark_price,
                    "sl": 0.0,  # Would need to track separately
                    "tp": 0.0,  # Would need to track separately
                    "profit": pos.unrealized_pnl,
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
    
    # Position Sizing Methods
    async def calculate_position_size(
        self, 
        symbol: str, 
        price: Optional[float] = None, 
        risk_amount: Optional[float] = None, 
        risk_percent: Optional[float] = None, 
        entry_price: Optional[float] = None, 
        stop_loss_price: Optional[float] = None
    ) -> float:
        """Calculate position size based on risk parameters."""
        try:
            if not price and not entry_price:
                ticker = await self.get_ticker(symbol)
                if ticker:
                    price = ticker.last
                else:
                    return 0.0
            
            current_price = price or entry_price
            if not current_price or not stop_loss_price:
                return 0.0
            
            # Get account balance
            balance = await self.get_free_margin()
            if not balance:
                return 0.0
            
            # Calculate risk amount
            if risk_percent:
                risk_amount = balance * (risk_percent / 100.0)
            
            if not risk_amount:
                return 0.0
            
            # Calculate position size
            risk_per_trade = abs(current_price - stop_loss_price)
            if risk_per_trade == 0:
                return 0.0
            
            position_size = risk_amount / risk_per_trade
            
            # Apply symbol limits
            symbol_info = await self.get_symbol_info(symbol)
            if symbol_info:
                min_amount = symbol_info.get("min_amount", 0)
                max_amount = symbol_info.get("max_amount", float('inf'))
                position_size = max(min_amount, min(position_size, max_amount))
            
            return position_size
            
        except Exception as e:
            logger.error(f"Failed to calculate position size: {e}")
            return 0.0
    
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
            return None
        except Exception as e:
            logger.error(f"Failed to get latest candle time: {e}")
            return None
