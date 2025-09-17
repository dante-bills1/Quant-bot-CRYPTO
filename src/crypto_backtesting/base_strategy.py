"""
Base Strategy Framework

This module provides the abstract base strategy class for crypto backtesting,
integrating with backtesting.py library and providing common functionality.
Based on the VWAP swing strategy reference implementation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
from backtesting import Strategy
from loguru import logger

from .data_fetcher import CryptoDataFetcher


class CryptoBacktestStrategy(Strategy, ABC):
    """
    Abstract base class for crypto trading strategies.

    This class integrates with backtesting.py and provides:
    - Common strategy infrastructure
    - Parameter management
    - Signal generation framework
    - Risk management hooks
    - Performance tracking
    """

    def __init__(self):
        """Initialize the strategy."""
        super().__init__()

        # Strategy metadata
        self.strategy_name = self.__class__.__name__
        self.description = "Base crypto strategy"

        # Data fetcher for external data if needed
        self.data_fetcher = None

        # Signal tracking
        self.signals = []
        self.last_signal = None
        self.signal_confidence = 0.0

        # Risk management parameters
        self.stop_loss_pct = 3.0
        self.take_profit_pct = 6.0
        self.max_position_size_pct = 0.1

        # Performance tracking
        self.entry_price = None
        self.position_size = 0

        logger.info(f"Initialized {self.strategy_name}")

    def init(self):
        """Initialize strategy indicators and parameters."""
        # Override in subclasses
        pass

    @abstractmethod
    def generate_signals(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate trading signals.

        Args:
            data: Current market data dictionary

        Returns:
            List of signal dictionaries
        """
        pass

    @abstractmethod
    def calculate_indicators(self):
        """Calculate technical indicators used by the strategy."""
        pass

    def next(self):
        """Execute strategy logic for each new candle."""
        try:
            # Prepare current data
            current_data = {
                'timestamp': self.data.index[-1],
                'open': self.data.Open[-1],
                'high': self.data.High[-1],
                'low': self.data.Low[-1],
                'close': self.data.Close[-1],
                'volume': self.data.Volume[-1]
            }

            # Generate signals
            signals = self.generate_signals(current_data)

            # Process signals
            for signal in signals:
                self._process_signal(signal, current_data)

        except Exception as e:
            logger.error(f"Error in strategy next(): {str(e)}")

    def _process_signal(self, signal: Dict[str, Any], current_data: Dict[str, Any]):
        """
        Process a trading signal.

        Args:
            signal: Signal dictionary
            current_data: Current market data
        """
        try:
            action = signal.get('action', '').lower()
            confidence = signal.get('confidence', 0.0)

            # Skip low confidence signals
            if confidence < 0.6:
                return

            current_price = current_data['close']

            if action == 'buy' and not self.position:
                self._execute_buy(signal, current_price)
            elif action == 'sell' and self.position:
                self._execute_sell(signal, current_price)

        except Exception as e:
            logger.error(f"Error processing signal: {str(e)}")

    def _execute_buy(self, signal: Dict[str, Any], price: float):
        """
        Execute buy order.

        Args:
            signal: Buy signal
            price: Current price
        """
        try:
            # Calculate position size
            position_size = self._calculate_position_size(price)

            if position_size > 0:
                # Execute buy
                self.buy(size=position_size)

                # Store position info
                self.entry_price = price
                self.position_size = position_size

                # Set risk management
                self._set_risk_management(price, 'buy')

                logger.info(f"BUY signal executed: {position_size:.4f} @ {price:.4f}")

        except Exception as e:
            logger.error(f"Error executing buy: {str(e)}")

    def _execute_sell(self, signal: Dict[str, Any], price: float):
        """
        Execute sell order.

        Args:
            signal: Sell signal
            price: Current price
        """
        try:
            # Close position
            self.position.close()

            # Calculate P&L
            if self.entry_price:
                pnl_pct = (price - self.entry_price) / self.entry_price * 100
                logger.info(f"SELL signal executed: {price:.4f} (P&L: {pnl_pct:.2f}%)")

            # Reset position tracking
            self.entry_price = None
            self.position_size = 0

        except Exception as e:
            logger.error(f"Error executing sell: {str(e)}")

    def _calculate_position_size(self, price: float) -> float:
        """
        Calculate position size based on risk management.

        Args:
            price: Current price

        Returns:
            Position size
        """
        try:
            # Get available equity
            equity = float(self.equity)

            # Calculate position size as percentage of equity
            dollar_amount = equity * self.max_position_size_pct
            position_size = dollar_amount / price

            # Ensure minimum size
            min_size = 0.001
            if position_size < min_size:
                return 0.0

            return position_size

        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0.0

    def _set_risk_management(self, entry_price: float, side: str):
        """
        Set stop loss and take profit levels.

        Args:
            entry_price: Entry price
            side: 'buy' or 'sell'
        """
        try:
            if side.lower() == 'buy':
                self.stop_loss_price = entry_price * (1 - self.stop_loss_pct / 100)
                self.take_profit_price = entry_price * (1 + self.take_profit_pct / 100)
            else:  # sell
                self.stop_loss_price = entry_price * (1 + self.stop_loss_pct / 100)
                self.take_profit_price = entry_price * (1 - self.take_profit_pct / 100)

        except Exception as e:
            logger.error(f"Error setting risk management: {str(e)}")

    def validate_parameters(self) -> bool:
        """
        Validate strategy parameters.

        Returns:
            True if valid, False otherwise
        """
        try:
            # Validate risk parameters
            if not (0 < self.stop_loss_pct < 50):
                logger.error(f"Invalid stop_loss_pct: {self.stop_loss_pct}")
                return False

            if not (0 < self.take_profit_pct < 200):
                logger.error(f"Invalid take_profit_pct: {self.take_profit_pct}")
                return False

            if not (0 < self.max_position_size_pct <= 1):
                logger.error(f"Invalid max_position_size_pct: {self.max_position_size_pct}")
                return False

            return True

        except Exception as e:
            logger.error(f"Parameter validation error: {str(e)}")
            return False

    def get_strategy_info(self) -> Dict[str, Any]:
        """
        Get strategy information and current parameters.

        Returns:
            Dictionary with strategy information
        """
        return {
            'name': self.strategy_name,
            'description': self.description,
            'parameters': {
                'stop_loss_pct': self.stop_loss_pct,
                'take_profit_pct': self.take_profit_pct,
                'max_position_size_pct': self.max_position_size_pct,
            },
            'current_position': {
                'size': self.position_size,
                'entry_price': self.entry_price,
            }
        }

    def log_signal(self, signal: Dict[str, Any]):
        """
        Log trading signal for analysis.

        Args:
            signal: Signal dictionary
        """
        try:
            signal_entry = {
                'timestamp': signal.get('timestamp'),
                'symbol': signal.get('symbol', 'UNKNOWN'),
                'action': signal.get('action', 'UNKNOWN'),
                'confidence': signal.get('confidence', 0.0),
                'price': signal.get('price'),
                'reason': signal.get('reason', ''),
            }

            self.signals.append(signal_entry)
            self.last_signal = signal_entry

        except Exception as e:
            logger.error(f"Error logging signal: {str(e)}")


class StrategyRegistry:
    """
    Registry for managing multiple trading strategies.
    """

    def __init__(self):
        self.strategies = {}

    def register_strategy(self, name: str, strategy_class):
        """
        Register a strategy class.

        Args:
            name: Strategy name
            strategy_class: Strategy class
        """
        self.strategies[name] = strategy_class
        logger.info(f"Registered strategy: {name}")

    def get_strategy(self, name: str):
        """
        Get strategy class by name.

        Args:
            name: Strategy name

        Returns:
            Strategy class or None
        """
        return self.strategies.get(name)

    def list_strategies(self) -> List[str]:
        """List all registered strategies."""
        return list(self.strategies.keys())

    def create_strategy(self, name: str, **kwargs):
        """
        Create strategy instance.

        Args:
            name: Strategy name
            **kwargs: Strategy parameters

        Returns:
            Strategy instance or None
        """
        strategy_class = self.get_strategy(name)
        if strategy_class:
            try:
                strategy = strategy_class(**kwargs)
                return strategy
            except Exception as e:
                logger.error(f"Error creating strategy {name}: {str(e)}")
                return None
        else:
            logger.error(f"Strategy not found: {name}")
            return None


# Global strategy registry
strategy_registry = StrategyRegistry()


def register_strategy(name: str):
    """
    Decorator to register a strategy.

    Args:
        name: Strategy name
    """
    def decorator(strategy_class):
        strategy_registry.register_strategy(name, strategy_class)
        return strategy_class
    return decorator
