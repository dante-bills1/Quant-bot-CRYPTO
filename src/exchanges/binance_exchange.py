"""
Binance Exchange Implementation

This module implements the Binance exchange interface for the crypto trading bot.
"""

import asyncio
import json
import time
import websocket
import threading
from typing import Dict, List, Optional, Any, Callable
import pandas as pd
import ccxt
from loguru import logger

from src.crypto_exchange import (
    CryptoExchange, Order, Position, Balance, Ticker, 
    OrderType, OrderSide, OrderStatus
)


class BinanceExchange(CryptoExchange):
    """Binance exchange implementation."""
    
    def __init__(self, api_key: str, api_secret: str, sandbox: bool = False):
        super().__init__(api_key, api_secret, sandbox)
        self.exchange = None
        self.ws_url = "wss://fstream.binance.com/ws" if not sandbox else "wss://stream.binancefuture.com/ws"
        self._ws_connections = {}
        self._ws_callbacks = {}
        
    async def connect(self) -> bool:
        """Connect to Binance exchange."""
        try:
            self.exchange = ccxt.binance({
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "future"}  # futures
            })
            
            # Set sandbox mode
            if hasattr(self.exchange, 'set_sandbox_mode'):
                self.exchange.set_sandbox_mode(self.sandbox)
            
            # Load markets
            await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.load_markets
            )
            
            self.connected = True
            logger.success(f"Connected to Binance {'sandbox' if self.sandbox else 'live'} mode")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Binance: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Binance exchange."""
        try:
            # Close all WebSocket connections
            for symbol, ws in self._ws_connections.items():
                if ws:
                    ws.close()
            
            self._ws_connections.clear()
            self._ws_callbacks.clear()
            self.connected = False
            
            logger.info("Disconnected from Binance")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Binance: {e}")
            return False
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information."""
        try:
            balance = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_balance
            )
            
            return {
                "account_id": "binance_account",
                "balance": balance.get("USDT", {}).get("total", 0.0),
                "free_margin": balance.get("USDT", {}).get("free", 0.0),
                "used_margin": balance.get("USDT", {}).get("used", 0.0),
                "equity": balance.get("USDT", {}).get("total", 0.0),
                "currency": "USDT"
            }
            
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {}
    
    async def get_balance(self) -> List[Balance]:
        """Get account balance."""
        try:
            balance = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_balance
            )
            
            balances = []
            for currency, data in balance.items():
                if isinstance(data, dict) and currency != "info":
                    balances.append(Balance(
                        currency=currency,
                        free=float(data.get("free", 0)),
                        used=float(data.get("used", 0)),
                        total=float(data.get("total", 0))
                    ))
            
            return balances
            
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            return []
    
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get ticker for a symbol."""
        try:
            ticker = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_ticker, symbol
            )
            
            return Ticker(
                symbol=symbol,
                bid=float(ticker.get("bid", 0)),
                ask=float(ticker.get("ask", 0)),
                last=float(ticker.get("last", 0)),
                high=float(ticker.get("high", 0)),
                low=float(ticker.get("low", 0)),
                volume=float(ticker.get("baseVolume", 0)),
                timestamp=int(ticker.get("timestamp", time.time() * 1000))
            )
            
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol}: {e}")
            return Ticker(symbol=symbol, bid=0, ask=0, last=0, high=0, low=0, volume=0, timestamp=0)
    
    async def get_historical_data(
        self, 
        symbol: str, 
        timeframe: str, 
        limit: int = 1000
    ) -> pd.DataFrame:
        """Get historical OHLCV data."""
        try:
            ohlcv = await asyncio.get_event_loop().run_in_executor(
                None, 
                self.exchange.fetch_ohlcv, 
                symbol, 
                timeframe, 
                None, 
                limit
            )
            
            df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return pd.DataFrame()
    
    async def place_order(
        self,
        symbol: str,
        side: OrderSide,
        order_type: OrderType,
        amount: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        client_order_id: Optional[str] = None
    ) -> Order:
        """Place a new order."""
        try:
            # Convert to Binance order type
            binance_side = "buy" if side == OrderSide.BUY else "sell"
            binance_type = "market" if order_type == OrderType.MARKET else "limit"
            
            params = {}
            if client_order_id:
                params["newClientOrderId"] = client_order_id
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self.exchange.create_order,
                symbol,
                binance_type,
                binance_side,
                amount,
                price,
                params
            )
            
            return Order(
                id=str(result.get("id", "")),
                symbol=symbol,
                side=side,
                type=order_type,
                amount=amount,
                price=price,
                stop_price=stop_price,
                status=OrderStatus.PENDING,
                filled=0.0,
                remaining=amount,
                timestamp=int(time.time() * 1000),
                client_order_id=client_order_id
            )
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise
    
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.exchange.cancel_order,
                order_id,
                symbol
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    async def get_order(self, order_id: str, symbol: str) -> Optional[Order]:
        """Get order details."""
        try:
            order = await asyncio.get_event_loop().run_in_executor(
                None,
                self.exchange.fetch_order,
                order_id,
                symbol
            )
            
            return Order(
                id=str(order.get("id", "")),
                symbol=symbol,
                side=OrderSide.BUY if order.get("side") == "buy" else OrderSide.SELL,
                type=OrderType.MARKET if order.get("type") == "market" else OrderType.LIMIT,
                amount=float(order.get("amount", 0)),
                price=float(order.get("price", 0)) if order.get("price") else None,
                status=OrderStatus.FILLED if order.get("status") == "closed" else OrderStatus.PENDING,
                filled=float(order.get("filled", 0)),
                remaining=float(order.get("remaining", 0)),
                timestamp=int(order.get("timestamp", time.time() * 1000))
            )
            
        except Exception as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return None
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get open orders."""
        try:
            orders = await asyncio.get_event_loop().run_in_executor(
                None,
                self.exchange.fetch_open_orders,
                symbol
            )
            
            result = []
            for order in orders:
                result.append(Order(
                    id=str(order.get("id", "")),
                    symbol=order.get("symbol", ""),
                    side=OrderSide.BUY if order.get("side") == "buy" else OrderSide.SELL,
                    type=OrderType.MARKET if order.get("type") == "market" else OrderType.LIMIT,
                    amount=float(order.get("amount", 0)),
                    price=float(order.get("price", 0)) if order.get("price") else None,
                    status=OrderStatus.PENDING,
                    filled=float(order.get("filled", 0)),
                    remaining=float(order.get("remaining", 0)),
                    timestamp=int(order.get("timestamp", time.time() * 1000))
                ))
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get open positions."""
        try:
            positions = await asyncio.get_event_loop().run_in_executor(
                None,
                self.exchange.fetch_positions,
                [symbol] if symbol else None
            )
            
            result = []
            for pos in positions:
                size = float(pos.get("contracts", 0))
                if abs(size) > 0:  # Only include positions with size > 0
                    result.append(Position(
                        symbol=pos.get("symbol", ""),
                        side="long" if size > 0 else "short",
                        size=abs(size),
                        entry_price=float(pos.get("entryPrice", 0)),
                        mark_price=float(pos.get("markPrice", 0)),
                        unrealized_pnl=float(pos.get("unrealizedPnl", 0)),
                        realized_pnl=float(pos.get("realizedPnl", 0)),
                        margin=float(pos.get("initialMargin", 0)),
                        leverage=float(pos.get("leverage", 1)),
                        timestamp=int(time.time() * 1000)
                    ))
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    async def close_position(self, symbol: str, side: str) -> bool:
        """Close a position."""
        try:
            positions = await self.get_positions(symbol)
            for pos in positions:
                if pos.symbol == symbol and pos.side == side:
                    # Place opposite order to close
                    close_side = OrderSide.SELL if side == "long" else OrderSide.BUY
                    await self.place_order(
                        symbol=symbol,
                        side=close_side,
                        order_type=OrderType.MARKET,
                        amount=pos.size
                    )
                    return True
            
            logger.warning(f"No position found to close for {symbol} {side}")
            return False
            
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            return False
    
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information."""
        try:
            market = self.exchange.market(symbol)
            return {
                "symbol": symbol,
                "base": market.get("base", ""),
                "quote": market.get("quote", ""),
                "min_amount": float(market.get("limits", {}).get("amount", {}).get("min", 0)),
                "max_amount": float(market.get("limits", {}).get("amount", {}).get("max", 0)),
                "amount_precision": market.get("precision", {}).get("amount", 0),
                "price_precision": market.get("precision", {}).get("price", 0),
                "min_cost": float(market.get("limits", {}).get("cost", {}).get("min", 0)),
                "active": market.get("active", False)
            }
            
        except Exception as e:
            logger.error(f"Failed to get symbol info for {symbol}: {e}")
            return {}
    
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for a symbol."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.exchange.set_leverage,
                leverage,
                symbol
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to set leverage for {symbol}: {e}")
            return False
    
    async def start_websocket(self, symbol: str, callback: Callable) -> bool:
        """Start WebSocket connection for real-time data."""
        try:
            if symbol in self._ws_connections:
                logger.warning(f"WebSocket already exists for {symbol}")
                return True
            
            # Convert symbol to Binance format
            ws_symbol = symbol.lower().replace("/", "")
            stream = f"{ws_symbol}@trade"
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    if "p" in data:  # Price data
                        price = float(data["p"])
                        callback(price)
                except Exception as e:
                    logger.error(f"WebSocket message error: {e}")
            
            def on_open(ws):
                logger.info(f"WebSocket connected for {symbol}")
            
            def on_error(ws, error):
                logger.error(f"WebSocket error for {symbol}: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                logger.warning(f"WebSocket closed for {symbol}")
                if symbol in self._ws_connections:
                    del self._ws_connections[symbol]
                if symbol in self._ws_callbacks:
                    del self._ws_callbacks[symbol]
            
            def run_ws():
                ws_url = f"{self.ws_url}/{stream}"
                ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close
                )
                ws.run_forever(ping_interval=20, ping_timeout=10, reconnect=5)
            
            # Start WebSocket in a separate thread
            ws_thread = threading.Thread(target=run_ws, daemon=True)
            ws_thread.start()
            
            self._ws_connections[symbol] = ws_thread
            self._ws_callbacks[symbol] = callback
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start WebSocket for {symbol}: {e}")
            return False
    
    async def stop_websocket(self, symbol: str) -> bool:
        """Stop WebSocket connection."""
        try:
            if symbol in self._ws_connections:
                # Note: WebSocket closing is handled in on_close callback
                del self._ws_connections[symbol]
            if symbol in self._ws_callbacks:
                del self._ws_callbacks[symbol]
            
            logger.info(f"WebSocket stopped for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop WebSocket for {symbol}: {e}")
            return False
