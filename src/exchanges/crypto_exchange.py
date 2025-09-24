"""
Crypto Exchange Abstraction Layer

This module provides a unified interface for different crypto exchanges,
allowing the trading bot to work with multiple exchanges seamlessly.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
import pandas as pd
from dataclasses import dataclass
from enum import Enum
from loguru import logger


class OrderType(Enum):
    """Order types supported by crypto exchanges."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order sides."""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order statuses."""
    PENDING = "pending"
    OPEN = "open"
    CLOSED = "closed"
    CANCELED = "canceled"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"


@dataclass
class Order:
    """Represents a trading order."""
    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    amount: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled: float = 0.0
    remaining: float = 0.0
    timestamp: Optional[int] = None
    client_order_id: Optional[str] = None


@dataclass
class Position:
    """Represents a trading position."""
    symbol: str
    side: str  # 'long' or 'short'
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float
    realized_pnl: float
    margin: float
    leverage: float
    timestamp: Optional[int] = None


@dataclass
class Balance:
    """Represents account balance."""
    currency: str
    free: float
    used: float
    total: float


@dataclass
class Ticker:
    """Represents market ticker data."""
    symbol: str
    bid: float
    ask: float
    last: float
    high: float
    low: float
    volume: float
    timestamp: int


class CryptoExchange(ABC):
    """Abstract base class for crypto exchanges."""
    
    def __init__(self, api_key: str, api_secret: str, sandbox: bool = False):
        """
        Initialize the exchange.
        
        Args:
            api_key: Exchange API key
            api_secret: Exchange API secret
            sandbox: Whether to use sandbox/testnet
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox
        self.connected = False
        self._ws_connections: Dict[str, Any] = {}
        
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to the exchange."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from the exchange."""
        pass
    
    @abstractmethod
    async def get_account_info(self) -> Dict[str, Any]:
        """Get account information."""
        pass
    
    @abstractmethod
    async def get_balance(self) -> List[Balance]:
        """Get account balance."""
        pass
    
    @abstractmethod
    async def get_ticker(self, symbol: str) -> Ticker:
        """Get ticker for a symbol."""
        pass
    
    @abstractmethod
    async def get_historical_data(
        self, 
        symbol: str, 
        timeframe: str, 
        limit: int = 1000
    ) -> pd.DataFrame:
        """Get historical OHLCV data."""
        pass
    
    @abstractmethod
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
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> bool:
        """Cancel an order."""
        pass
    
    @abstractmethod
    async def get_order(self, order_id: str, symbol: str) -> Optional[Order]:
        """Get order details."""
        pass
    
    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """Get open orders."""
        pass
    
    @abstractmethod
    async def get_positions(self, symbol: Optional[str] = None) -> List[Position]:
        """Get open positions."""
        pass
    
    @abstractmethod
    async def close_position(self, symbol: str, side: str) -> bool:
        """Close a position."""
        pass
    
    @abstractmethod
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """Get symbol information (min/max amounts, precision, etc.)."""
        pass
    
    @abstractmethod
    async def set_leverage(self, symbol: str, leverage: int) -> bool:
        """Set leverage for a symbol."""
        pass
    
    @abstractmethod
    async def start_websocket(self, symbol: str, callback) -> bool:
        """Start WebSocket connection for real-time data."""
        pass
    
    @abstractmethod
    async def stop_websocket(self, symbol: str) -> bool:
        """Stop WebSocket connection."""
        pass
    
    def is_connected(self) -> bool:
        """Check if exchange is connected."""
        return self.connected
    
    def get_exchange_name(self) -> str:
        """Get the name of the exchange."""
        return self.__class__.__name__.replace("Exchange", "").lower()

    def parse_timeframe(self, timeframe: str) -> int:
        """
        Parse timeframe string to seconds.

        Args:
            timeframe: Timeframe string (e.g., '1m', '5m', '1h', '1d')

        Returns:
            Timeframe in seconds
        """
        timeframe_map = {
            '1m': 60,
            '3m': 180,
            '5m': 300,
            '15m': 900,
            '30m': 1800,
            '1h': 3600,
            '2h': 7200,
            '4h': 14400,  # Added 4h timeframe
            '6h': 21600,
            '8h': 28800,
            '12h': 43200,
            '1d': 86400,
            '3d': 259200,
            '1w': 604800,
            '1M': 2592000
        }

        return timeframe_map.get(timeframe, 3600)  # Default to 1 hour


class ExchangeFactory:
    """Factory for creating exchange instances."""
    
    _exchanges = {}
    
    @classmethod
    def register_exchange(cls, name: str, exchange_class):
        """Register an exchange class."""
        cls._exchanges[name.lower()] = exchange_class
    
    @classmethod
    def create_exchange(
        cls, 
        name: str, 
        api_key: str, 
        api_secret: str, 
        sandbox: bool = False
    ) -> CryptoExchange:
        """Create an exchange instance."""
        name = name.lower()
        if name not in cls._exchanges:
            raise ValueError(f"Exchange '{name}' not supported. Available: {list(cls._exchanges.keys())}")
        
        exchange_class = cls._exchanges[name]
        return exchange_class(api_key, api_secret, sandbox)
    
    @classmethod
    def get_supported_exchanges(cls) -> List[str]:
        """Get list of supported exchanges."""
        return list(cls._exchanges.keys())


# Register exchanges
from exchanges.bybit_exchange import BybitExchange
from exchanges.binance_exchange import BinanceExchange

ExchangeFactory.register_exchange("bybit", BybitExchange)
ExchangeFactory.register_exchange("binance", BinanceExchange)
