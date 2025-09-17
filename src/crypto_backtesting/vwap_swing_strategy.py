"""
VWAP Swing Strategy with ADX Filter

This module implements the Dynamic Swing Anchored VWAP Strategy with ADX Filter,
based on the reference implementation in Vwapswing.txt.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
import talib
from backtesting import Strategy
from loguru import logger

from .base_strategy import CryptoBacktestStrategy, register_strategy


@register_strategy("vwap_swing_adx")
class VWAPSwingADXStrategy(CryptoBacktestStrategy):
    """
    Dynamic Swing Anchored VWAP Strategy with ADX Filter.

    Features:
    - Dynamic swing point detection
    - Anchored VWAP calculation with EWMA adaptation
    - ADX trend filtering
    - Multi-timeframe analysis support
    - Configurable parameters for optimization
    """

    # Strategy parameters (can be optimized)
    swing_period = 50
    base_apt = 20
    use_adapt = False
    vol_bias = 10.0
    atr_length = 50
    adx_period = 14
    adx_threshold = 20
    use_adx_filter = True
    stop_loss_pct = 3.0
    take_profit_pct = 6.0
    position_size_pct = 0.10

    def __init__(self):
        """Initialize VWAP Swing strategy."""
        super().__init__()
        self.strategy_name = "VWAP Swing ADX"
        self.description = "Dynamic Swing Anchored VWAP Strategy with ADX Filter"

        # Initialize arrays for indicators
        self.direction = None
        self.vwap = None
        self.atr = None
        self.adx = None
        self.plus_di = None
        self.minus_di = None
        self.hlc3 = None
        self.high_np = None
        self.low_np = None
        self.close_np = None
        self.volume_np = None

        # Swing detection
        self.swing_highs = []
        self.swing_lows = []

        logger.info("VWAP Swing ADX Strategy initialized")

    def init(self):
        """Initialize strategy indicators and variables."""
        try:
            # Convert data to numpy arrays for performance
            high_np = np.array(self.data.High)
            low_np = np.array(self.data.Low)
            close_np = np.array(self.data.Close)
            volume_np = np.array(self.data.Volume)

            # Calculate HLC3 (typical price)
            self.hlc3 = (high_np + low_np + close_np) / 3

            # Calculate ATR
            self.atr = talib.ATR(high_np, low_np, close_np, timeperiod=self.atr_length)

            # Calculate ADX and Directional Indicators
            self.adx = talib.ADX(high_np, low_np, close_np, timeperiod=self.adx_period)
            self.plus_di = talib.PLUS_DI(high_np, low_np, close_np, timeperiod=self.adx_period)
            self.minus_di = talib.MINUS_DI(high_np, low_np, close_np, timeperiod=self.adx_period)

            # Store arrays as instance variables
            self.high_np = high_np
            self.low_np = low_np
            self.close_np = close_np
            self.volume_np = volume_np

            # Initialize direction and VWAP arrays
            self.direction = np.zeros(len(close_np))
            self.vwap = np.zeros(len(close_np))

            # Calculate swings and VWAP
            self._calculate_swings_and_vwap()

            # Position tracking
            self.entry_price = None
            self.stop_loss_price = None
            self.take_profit_price = None

            logger.info(f"Strategy initialized with {len(close_np)} data points")

        except Exception as e:
            logger.error(f"Error initializing strategy: {str(e)}")

    def _find_swing_points(self) -> Tuple[List[int], List[int]]:
        """
        Find swing highs and lows using dynamic window.

        Returns:
            Tuple of (swing_highs_indices, swing_lows_indices)
        """
        swing_highs = []
        swing_lows = []

        half_period = max(5, self.swing_period // 4)

        for i in range(half_period, len(self.high_np) - half_period):
            window_start = max(0, i - half_period)
            window_end = min(len(self.high_np), i + half_period + 1)

            # Check for swing high
            if self.high_np[i] == np.max(self.high_np[window_start:window_end]):
                swing_highs.append(i)

            # Check for swing low
            if self.low_np[i] == np.min(self.low_np[window_start:window_end]):
                swing_lows.append(i)

        return swing_highs, swing_lows

    def _calculate_swings_and_vwap(self):
        """Calculate swing points and dynamic VWAP with EWMA adaptation."""
        try:
            swing_highs, swing_lows = self._find_swing_points()

            # Combine and sort all swing points
            all_swings = []
            for idx in swing_highs:
                all_swings.append((idx, 'high'))
            for idx in swing_lows:
                all_swings.append((idx, 'low'))

            all_swings.sort(key=lambda x: x[0])

            # Variables for VWAP calculation
            if len(self.close_np) > 0:
                cumulative_pv = self.hlc3[0] * self.volume_np[0]
                cumulative_volume = self.volume_np[0]
            else:
                return

            # Process each bar
            for i in range(len(self.close_np)):
                # Check if current bar is a swing point
                current_swing = None
                for swing_idx, swing_type in all_swings:
                    if swing_idx == i:
                        current_swing = swing_type
                        break

                # Update direction based on swing type
                if current_swing == 'high':
                    self.direction[i] = -1
                    cumulative_pv = self.hlc3[i] * self.volume_np[i]
                    cumulative_volume = self.volume_np[i]

                elif current_swing == 'low':
                    self.direction[i] = 1
                    cumulative_pv = self.hlc3[i] * self.volume_np[i]
                    cumulative_volume = self.volume_np[i]

                else:
                    # Maintain previous direction
                    self.direction[i] = self.direction[i-1] if i > 0 else 0

                    # Calculate alpha for EWMA
                    apt = self.base_apt
                    decay = np.exp(-np.log(2.0) / max(1.0, apt))
                    alpha = 1.0 - decay

                    # Update cumulative values using EWMA
                    pv = self.hlc3[i] * self.volume_np[i]
                    cumulative_pv = (1.0 - alpha) * cumulative_pv + alpha * pv
                    cumulative_volume = (1.0 - alpha) * cumulative_volume + alpha * self.volume_np[i]

                # Calculate VWAP
                if cumulative_volume > 0:
                    self.vwap[i] = cumulative_pv / cumulative_volume
                else:
                    self.vwap[i] = self.hlc3[i]

        except Exception as e:
            logger.error(f"Error calculating swings and VWAP: {str(e)}")

    def generate_signals(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate trading signals based on VWAP swing strategy.

        Args:
            data: Current market data

        Returns:
            List of signal dictionaries
        """
        try:
            signals = []
            idx = len(self.data) - 1

            # Skip if not enough data
            if idx < self.swing_period or idx >= len(self.direction):
                return signals

            # Get current indicators
            current_direction = self.direction[idx]
            prev_direction = self.direction[idx-1] if idx > 0 else 0

            # Get ADX values with safety checks
            current_adx = self.adx[idx] if idx < len(self.adx) and not np.isnan(self.adx[idx]) else 0
            current_plus_di = self.plus_di[idx] if idx < len(self.plus_di) and not np.isnan(self.plus_di[idx]) else 0
            current_minus_di = self.minus_di[idx] if idx < len(self.minus_di) and not np.isnan(self.minus_di[idx]) else 0

            # Get current price and VWAP
            current_price = data['close']
            current_vwap = self.vwap[idx] if idx < len(self.vwap) else current_price

            # Check for direction change
            direction_changed = current_direction != prev_direction and prev_direction != 0

            # ENTRY LOGIC
            if not self.position:
                long_condition = False

                # Primary condition: Direction change to bullish
                if direction_changed and current_direction > 0:
                    long_condition = True

                # Alternative condition: Strong bullish direction
                elif current_direction > 0 and idx > 100:
                    bars_since_direction_change = 0
                    for j in range(idx-1, max(0, idx-50), -1):
                        if j < len(self.direction) and self.direction[j] != current_direction:
                            bars_since_direction_change = idx - j
                            break

                    if bars_since_direction_change < 20 and abs(current_price - current_vwap) / current_price < 0.02:
                        long_condition = True

                if long_condition:
                    # Apply filters
                    adx_filter = True
                    if self.use_adx_filter:
                        adx_filter = current_adx > self.adx_threshold

                    di_filter = True
                    if current_plus_di > 0 and current_minus_di > 0:
                        di_filter = current_plus_di > current_minus_di

                    if adx_filter and di_filter:
                        signal = {
                            'timestamp': data['timestamp'],
                            'symbol': 'BTC/USDT',  # Default symbol
                            'action': 'buy',
                            'confidence': 0.8,
                            'price': current_price,
                            'reason': f'VWAP Swing: direction={current_direction}, adx={current_adx:.1f}',
                            'indicators': {
                                'vwap': current_vwap,
                                'direction': current_direction,
                                'adx': current_adx,
                                'plus_di': current_plus_di,
                                'minus_di': current_minus_di
                            }
                        }
                        signals.append(signal)

            # EXIT LOGIC
            else:
                should_exit = False
                exit_reason = ""

                # Exit conditions
                if direction_changed and current_direction < 0:
                    should_exit = True
                    exit_reason = "Direction change to bearish"
                elif self.stop_loss_price and current_price <= self.stop_loss_price:
                    should_exit = True
                    exit_reason = "Stop loss hit"
                elif self.take_profit_price and current_price >= self.take_profit_price:
                    should_exit = True
                    exit_reason = "Take profit hit"
                elif current_price < current_vwap * 0.98:
                    should_exit = True
                    exit_reason = "Price below VWAP threshold"

                if should_exit:
                    signal = {
                        'timestamp': data['timestamp'],
                        'symbol': 'BTC/USDT',  # Default symbol
                        'action': 'sell',
                        'confidence': 0.9,
                        'price': current_price,
                        'reason': exit_reason,
                        'indicators': {
                            'vwap': current_vwap,
                            'direction': current_direction,
                            'adx': current_adx
                        }
                    }
                    signals.append(signal)

            return signals

        except Exception as e:
            logger.error(f"Error generating signals: {str(e)}")
            return []

    def calculate_indicators(self):
        """Calculate technical indicators (already done in init)."""
        # Indicators are calculated in init() method
        pass

    def validate_parameters(self) -> bool:
        """Validate strategy parameters."""
        try:
            if not (10 <= self.swing_period <= 100):
                logger.error(f"Invalid swing_period: {self.swing_period} (must be 10-100)")
                return False

            if not (5 <= self.base_apt <= 50):
                logger.error(f"Invalid base_apt: {self.base_apt} (must be 5-50)")
                return False

            if not (10 <= self.adx_threshold <= 40):
                logger.error(f"Invalid adx_threshold: {self.adx_threshold} (must be 10-40)")
                return False

            if not (0.5 <= self.stop_loss_pct <= 10):
                logger.error(f"Invalid stop_loss_pct: {self.stop_loss_pct} (must be 0.5-10)")
                return False

            if not (1 <= self.take_profit_pct <= 20):
                logger.error(f"Invalid take_profit_pct: {self.take_profit_pct} (must be 1-20)")
                return False

            return True

        except Exception as e:
            logger.error(f"Parameter validation error: {str(e)}")
            return False

    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information and current parameters."""
        base_info = super().get_strategy_info()
        base_info.update({
            'swing_parameters': {
                'swing_period': self.swing_period,
                'base_apt': self.base_apt,
                'use_adapt': self.use_adapt,
                'vol_bias': self.vol_bias,
            },
            'filter_parameters': {
                'adx_period': self.adx_period,
                'adx_threshold': self.adx_threshold,
                'use_adx_filter': self.use_adx_filter,
            },
            'risk_parameters': {
                'atr_length': self.atr_length,
                'stop_loss_pct': self.stop_loss_pct,
                'take_profit_pct': self.take_profit_pct,
                'position_size_pct': self.position_size_pct,
            }
        })
        return base_info