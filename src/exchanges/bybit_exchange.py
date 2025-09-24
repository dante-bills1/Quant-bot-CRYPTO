"""
Bybit Exchange Implementation

This module implements the Bybit exchange interface for the crypto trading bot.
Based on the reference file's Bybit integration patterns.
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

from crypto_exchange import (
    CryptoExchange, Order, Position, Balance, Ticker, 
    OrderType, OrderSide, OrderStatus
)


class BybitExchange(CryptoExchange):
    """Bybit exchange implementation."""
    
    def __init__(self, api_key: str, api_secret: str, sandbox: bool = False):
        super().__init__(api_key, api_secret, sandbox)
        self.exchange = None
        self.ws_url = "wss://stream.bybit.com/v5/public/linear" if not sandbox else "wss://stream-testnet.bybit.com/v5/public/linear"
        self._ws_connections = {}
        self._ws_callbacks = {}
        self.network_error_count = 0
        self.last_network_error_time = 0

    def _handle_network_error(self, operation: str, symbol: str = "") -> None:
        """Handle network errors and track consecutive failures."""
        current_time = time.time()
        self.network_error_count += 1

        # Reset counter if it's been more than 5 minutes since last error
        if current_time - self.last_network_error_time > 300:  # 5 minutes
            self.network_error_count = 1

        self.last_network_error_time = current_time

        if self.network_error_count >= 5:
            logger.error(f"🚨 Bybit exchange appears to be down or unreachable ({self.network_error_count} consecutive network errors)")
            logger.error("Consider switching to live mode by setting CRYPTO_SANDBOX=false in your .env file")
        else:
            logger.warning(f"Network error during {operation} for {symbol or 'exchange'} ({self.network_error_count} consecutive errors)")

    async def connect(self) -> bool:
        """Connect to Bybit exchange."""
        try:
            self.exchange = ccxt.bybit({
                "apiKey": self.api_key,
                "secret": self.api_secret,
                "enableRateLimit": True,
                "options": {"defaultType": "swap"}  # perpetual futures
            })
            
            # Set sandbox mode
            if hasattr(self.exchange, 'set_sandbox_mode'):
                self.exchange.set_sandbox_mode(self.sandbox)
            
            # Load markets
            await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.load_markets
            )
            
            self.connected = True
            logger.success(f"Connected to Bybit {'sandbox' if self.sandbox else 'live'} mode")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Bybit: {e}")
            self.connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Disconnect from Bybit exchange."""
        try:
            # Close all WebSocket connections
            for symbol, ws in self._ws_connections.items():
                if ws:
                    ws.close()
            
            self._ws_connections.clear()
            self._ws_callbacks.clear()
            self.connected = False
            
            logger.info("Disconnected from Bybit")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting from Bybit: {e}")
            return False
    
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information."""
        try:
            balance = await asyncio.get_event_loop().run_in_executor(
                None, self.exchange.fetch_balance, {"type": "swap"}
            )
            
            return {
                "account_id": "bybit_account",
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
                None, self.exchange.fetch_balance, {"type": "swap"}
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
                None, self.exchange.fetch_ticker, symbol, {"category": "linear"}
            )

            return Ticker(
                symbol=symbol,
                bid=float(ticker.get("bid") or 0),
                ask=float(ticker.get("ask") or 0),
                last=float(ticker.get("last") or 0),
                high=float(ticker.get("high") or 0),
                low=float(ticker.get("low") or 0),
                volume=float(ticker.get("baseVolume") or 0),
                timestamp=int(ticker.get("timestamp") or (time.time() * 1000))
            )

        except Exception as e:
            error_msg = str(e).lower()
            if "network" in error_msg or "connection" in error_msg or "resolve" in error_msg or "timeout" in error_msg:
                self._handle_network_error("ticker fetch", symbol)
                return Ticker(symbol=symbol, bid=0, ask=0, last=0, high=0, low=0, volume=0, timestamp=int(time.time() * 1000))
            else:
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
            # Try linear (futures) first
            ohlcv = await asyncio.get_event_loop().run_in_executor(
                None,
                self.exchange.fetch_ohlcv,
                symbol,
                timeframe,
                None,
                limit,
                {"category": "linear"}
            )

            # If no data from linear, try spot market
            if not ohlcv:
                logger.info(f"No linear data for {symbol}, trying spot market")
                ohlcv = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.exchange.fetch_ohlcv,
                    symbol,
                    timeframe,
                    None,
                    limit,
                    {"category": "spot"}
                )

            if ohlcv:
                df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
                df.set_index("timestamp", inplace=True)
                return df
            else:
                logger.warning(f"No historical data available for {symbol}")
                return None

        except Exception as e:
            error_msg = str(e).lower()
            if "network" in error_msg or "connection" in error_msg or "resolve" in error_msg or "timeout" in error_msg:
                self._handle_network_error("historical data fetch", symbol)
                return None
            else:
                logger.error(f"Failed to get historical data for {symbol}: {e}")
                return None
    
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
            # Validate and adjust order amount to meet minimum requirements
            try:
                market = self.exchange.market(symbol)
                min_amount = market.get("limits", {}).get("amount", {}).get("min", 1.0)
                amount_precision = market.get("precision", {}).get("amount", 1.0)

                # Ensure amount meets minimum requirement
                if amount < min_amount:
                    logger.warning(f"Order amount {amount} below minimum {min_amount} for {symbol}, adjusting to minimum")
                    amount = min_amount

                # Round amount to appropriate precision
                if amount_precision > 0:
                    amount = round(amount / amount_precision) * amount_precision

            except Exception as e:
                logger.warning(f"Could not validate order amount for {symbol}: {e}")

            # Convert to Bybit order type
            bybit_side = "buy" if side == OrderSide.BUY else "sell"
            bybit_type = "market" if order_type == OrderType.MARKET else "limit"

            params = {"category": "linear"}
            if client_order_id:
                params["clientOrderId"] = client_order_id

            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self.exchange.create_order,
                symbol,
                bybit_type,
                bybit_side,
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
                symbol,
                {"category": "linear"}
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
                symbol,
                {"category": "linear"}
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
                symbol,
                None,
                None,
                {"category": "linear"}
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
                [symbol] if symbol else None,
                {"category": "linear"}
            )
            
            result = []
            for pos in positions:
                # Handle None values properly
                contracts = pos.get("contracts")
                if contracts is None:
                    contracts = 0

                size = float(contracts)
                if abs(size) > 0:  # Only include positions with size > 0
                    result.append(Position(
                        symbol=pos.get("symbol", ""),
                        side="long" if size > 0 else "short",
                        size=abs(size),
                        entry_price=float(pos.get("entryPrice") or 0),
                        mark_price=float(pos.get("markPrice") or 0),
                        unrealized_pnl=float(pos.get("unrealizedPnl") or 0),
                        realized_pnl=float(pos.get("realizedPnl") or 0),
                        margin=float(pos.get("initialMargin") or 0),
                        leverage=float(pos.get("leverage") or 1),
                        timestamp=int(time.time() * 1000)
                    ))
            
            return result
            
        except Exception as e:
            error_msg = str(e).lower()
            if "network" in error_msg or "connection" in error_msg or "resolve" in error_msg or "timeout" in error_msg:
                self._handle_network_error("positions fetch")
                return []
            else:
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
            # Check if exchange is initialized
            if not self.exchange:
                logger.error(f"Exchange not initialized for {symbol}")
                return {}

            # Get market information from CCXT
            if hasattr(self.exchange, 'market') and symbol in self.exchange.markets:
                market = self.exchange.market(symbol)

                # Safely extract nested values with proper None handling
                limits = market.get("limits") or {}
                amount_limits = limits.get("amount") or {}
                cost_limits = limits.get("cost") or {}
                precision = market.get("precision") or {}

                # Ensure all numeric values are properly handled
                try:
                    min_amount = amount_limits.get("min")
                    if min_amount is None:
                        min_amount = 0.001
                    min_amount = float(min_amount)

                    max_amount = amount_limits.get("max")
                    if max_amount is None:
                        max_amount = 0
                    max_amount = float(max_amount)

                    min_cost = cost_limits.get("min")
                    if min_cost is None:
                        min_cost = 0
                    min_cost = float(min_cost)

                    amount_precision = precision.get("amount")
                    if amount_precision is None:
                        amount_precision = 8
                    amount_precision = int(amount_precision)

                    price_precision = precision.get("price")
                    if price_precision is None:
                        price_precision = 4
                    price_precision = int(price_precision)

                except (ValueError, TypeError) as e:
                    logger.warning(f"Error parsing numeric values for {symbol}, using defaults: {e}")
                    min_amount = 0.001
                    max_amount = 0
                    min_cost = 0
                    amount_precision = 8
                    price_precision = 4

                return {
                    "symbol": symbol,
                    "base": market.get("base", ""),
                    "quote": market.get("quote", ""),
                    "min_amount": min_amount,
                    "max_amount": max_amount,
                    "amount_precision": amount_precision,
                    "price_precision": price_precision,
                    "min_cost": min_cost,
                    "active": market.get("active", True)
                }
            else:
                # Fallback: return default values if market not found
                logger.warning(f"Market {symbol} not found in exchange markets, using defaults")

                # Safe symbol parsing
                try:
                    base = symbol.split('/')[0] if '/' in symbol and len(symbol.split('/')) > 0 else ""
                    quote = symbol.split('/')[1] if '/' in symbol and len(symbol.split('/')) > 1 else ""
                except Exception:
                    base = ""
                    quote = ""

                return {
                    "symbol": symbol,
                    "base": base,
                    "quote": quote,
                    "min_amount": 0.001,
                    "max_amount": 0,
                    "amount_precision": 8,
                    "price_precision": 4,
                    "min_cost": 0,
                    "active": True
                }

        except Exception as e:
            logger.error(f"Failed to get symbol info for {symbol}: {e}")
            # Return safe defaults with proper error handling
            try:
                base = symbol.split('/')[0] if '/' in symbol and len(symbol.split('/')) > 0 else ""
                quote = symbol.split('/')[1] if '/' in symbol and len(symbol.split('/')) > 1 else ""
            except Exception:
                base = ""
                quote = ""

            return {
                "symbol": symbol,
                "base": base,
                "quote": quote,
                "min_amount": 0.001,
                "max_amount": 0,
                "amount_precision": 8,
                "price_precision": 4,
                "min_cost": 0,
                "active": True
            }
    
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
            
            # Convert symbol to Bybit format
            ws_symbol = symbol.replace("/", "").replace(":USDT", "USDT")
            topic = f"publicTrade.{ws_symbol}"
            
            def on_message(ws, message):
                try:
                    data = json.loads(message)
                    if data.get("topic") == topic:
                        for trade in data.get("data", []):
                            price = float(trade.get("p", 0))
                            callback(price)
                except Exception as e:
                    logger.error(f"WebSocket message error: {e}")
            
            def on_open(ws):
                subscribe_msg = {"op": "subscribe", "args": [topic]}
                ws.send(json.dumps(subscribe_msg))
                logger.info(f"WebSocket subscribed to {topic}")
            
            def on_error(ws, error):
                logger.error(f"WebSocket error for {symbol}: {error}")
            
            def on_close(ws, close_status_code, close_msg):
                logger.warning(f"WebSocket closed for {symbol}")
                if symbol in self._ws_connections:
                    del self._ws_connections[symbol]
                if symbol in self._ws_callbacks:
                    del self._ws_callbacks[symbol]
            
            def run_ws():
                ws = websocket.WebSocketApp(
                    self.ws_url,
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
