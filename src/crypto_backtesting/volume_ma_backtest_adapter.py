"""
Volume MA Oscillator Backtest Adapter

This module adapts the existing VolumeMAOscillator strategy to work with
the crypto backtesting framework.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from backtesting import Strategy
import asyncio

from .base_strategy import CryptoBacktestStrategy, register_strategy
from src.strategy.volume_ma_oscillator import VolumeMAOscillator


@register_strategy("volume_ma_adapted")
class VolumeMABacktestAdapter(CryptoBacktestStrategy):
    """
    Adapter to use the existing VolumeMAOscillator strategy with the backtesting framework.

    This class wraps the existing SignalGenerator-based strategy to work with
    the backtesting.py library.
    """

    def __init__(self, **kwargs):
        """Initialize the adapted strategy."""
        super().__init__()
        self.strategy_name = "Volume MA Oscillator (Adapted)"
        self.description = "Adapted Volume MA Oscillator for backtesting"

        # Initialize the original strategy
        self.volume_ma_strategy = VolumeMAOscillator(**kwargs)

        # Store parameters
        self.strategy_params = kwargs

        # Signal tracking
        self.last_signal = None
        self.current_position = None

    def init(self):
        """Initialize strategy indicators."""
        try:
            # The original strategy doesn't need explicit initialization for backtesting
            # All calculations are done in the next() method
            pass
        except Exception as e:
            print(f"Error initializing adapted strategy: {e}")

    def calculate_indicators(self):
        """Calculate technical indicators used by the strategy."""
        try:
            # Indicators are calculated in the original strategy
            # This is a placeholder for the abstract method
            pass
        except Exception as e:
            print(f"Error calculating indicators: {e}")

    def generate_signals(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate trading signals.

        Args:
            data: Current market data dictionary

        Returns:
            List of signal dictionaries
        """
        try:
            # This method is called by the base strategy framework
            # The actual signal generation happens in next() method
            return []
        except Exception as e:
            print(f"Error generating signals: {e}")
            return []

    def next(self):
        """Execute strategy logic for each new candle."""
        try:
            # Prepare market data in the format expected by the original strategy
            market_data = {
                self._get_symbol(): {
                    self._get_timeframe(): pd.DataFrame({
                        'open': [self.data.Open[-1]],
                        'high': [self.data.High[-1]],
                        'low': [self.data.Low[-1]],
                        'close': [self.data.Close[-1]],
                        'volume': [self.data.Volume[-1]]
                    }, index=[self.data.index[-1]])
                }
            }

            # Generate signals using the original strategy
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            try:
                signals = loop.run_until_complete(
                    self.volume_ma_strategy.generate_signals(market_data)
                )

                # Process signals
                for signal in signals:
                    self._process_signal(signal)

            finally:
                loop.close()

        except Exception as e:
            print(f"Error in adapted strategy next(): {e}")

    def _process_signal(self, signal: Dict[str, Any]):
        """Process a signal from the original strategy."""
        try:
            signal_type = signal.get('signal_type', '').lower()
            entry_price = signal.get('entry_price', self.data.Close[-1])

            if signal_type == 'buy' and not self.position:
                # Calculate position size (simplified)
                position_size = self._calculate_position_size(entry_price)
                if position_size > 0:
                    self.buy(size=position_size)
                    self.current_position = 'long'

            elif signal_type == 'sell' and self.position:
                self.position.close()
                self.current_position = None

        except Exception as e:
            print(f"Error processing signal: {e}")

    def _calculate_position_size(self, price: float) -> float:
        """Calculate position size based on risk management."""
        try:
            # Use a simple position sizing based on available equity
            equity = float(self.equity)
            risk_amount = equity * 0.02  # 2% risk per trade
            stop_distance = price * 0.02  # 2% stop loss

            if stop_distance > 0:
                position_size = risk_amount / stop_distance
                return min(position_size, equity / price)  # Don't risk more than available equity
            return 0.0

        except Exception as e:
            print(f"Error calculating position size: {e}")
            return 0.0

    def _get_symbol(self) -> str:
        """Get the symbol from strategy parameters or use default."""
        return self.strategy_params.get('symbol', 'BTCUSDT')

    def _get_timeframe(self) -> str:
        """Get the timeframe from strategy parameters or use default."""
        return self.strategy_params.get('timeframe', '4h')

    def validate_parameters(self) -> bool:
        """Validate strategy parameters."""
        try:
            # Basic validation - the original strategy handles detailed validation
            return True
        except Exception as e:
            print(f"Parameter validation error: {e}")
            return False

    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information."""
        base_info = super().get_strategy_info()
        base_info.update({
            'original_strategy': self.volume_ma_strategy.get_strategy_info(),
            'adaptation_info': {
                'adapter_version': '1.0.0',
                'adapted_from': 'VolumeMAOscillator SignalGenerator',
                'framework': 'backtesting.py'
            }
        })
        return base_info


# Convenience function to create adapted strategy
def create_adapted_volume_ma_strategy(**kwargs) -> VolumeMABacktestAdapter:
    """
    Create an adapted Volume MA Oscillator strategy for backtesting.

    Args:
        **kwargs: Parameters to pass to the original strategy

    Returns:
        Adapted strategy instance
    """
    return VolumeMABacktestAdapter(**kwargs)
