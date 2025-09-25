"""
Multi-Timeframe Trend Following Strategy

This strategy demonstrates how to use multiple timeframes for analysis:
- Higher timeframe (4h) for trend direction
- Lower timeframe (1h) for entry signals
- Combines trend confirmation with precise entry timing

Strategy Logic:
1. Use 4h timeframe to determine overall trend direction (EMA slope)
2. Use 1h timeframe for entry signals (RSI oversold/overbought + EMA cross)
3. Only take trades in the direction of the higher timeframe trend
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from loguru import logger

from src.trading_bot import SignalGenerator


class MultiTimeframeTrendFollowing(SignalGenerator):
    """
    Multi-timeframe trend following strategy.
    
    Uses higher timeframe for trend direction and lower timeframe for entry signals.
    """
    
    def __init__(self, crypto_handler=None, risk_manager=None, **kwargs):
        super().__init__(crypto_handler, risk_manager, **kwargs)
        
        # Timeframe configuration
        self.primary_timeframe = "1h"  # Entry timeframe
        self.secondary_timeframes = ["4h"]  # Trend timeframe
        
        # Strategy parameters
        self.trend_ema_period = 50  # EMA period for trend detection
        self.entry_ema_fast = 12    # Fast EMA for entry signals
        self.entry_ema_slow = 26    # Slow EMA for entry signals
        self.rsi_period = 14        # RSI period for overbought/oversold
        self.rsi_overbought = 70   # RSI overbought level
        self.rsi_oversold = 30     # RSI oversold level
        
        # Risk management
        self.stop_loss_pct = 0.02   # 2% stop loss
        self.take_profit_pct = 0.04 # 4% take profit (2:1 R/R)
        
        # Minimum candles required for analysis
        self.min_candles = max(self.trend_ema_period, self.entry_ema_slow, self.rsi_period) + 10
        
        logger.info(f"MultiTimeframeTrendFollowing initialized with primary TF: {self.primary_timeframe}, secondary TF: {self.secondary_timeframes}")
    
    async def initialize(self) -> bool:
        """Initialize the strategy."""
        await super().initialize()
        logger.info(f"MultiTimeframeTrendFollowing initialized successfully")
        return True
    
    async def generate_signals(
        self,
        market_data: Optional[Dict[str, Dict[str, pd.DataFrame]]] = None,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        Generate trading signals using multi-timeframe analysis.
        
        Args:
            market_data: Dictionary of market data by symbol and timeframe
            symbol: Trading symbol
            timeframe: Timeframe (ignored, we use our own timeframes)
            **kwargs: Additional arguments
            
        Returns:
            List of signal dictionaries
        """
        try:
            if not market_data or not symbol:
                return []
            
            symbol_data = market_data.get(symbol, {})
            if not symbol_data:
                logger.warning(f"No market data for symbol {symbol}")
                return []
            
            # Get data for both timeframes
            trend_data = symbol_data.get(self.secondary_timeframes[0])  # 4h data
            entry_data = symbol_data.get(self.primary_timeframe)       # 1h data
            
            if trend_data is None or entry_data is None:
                logger.warning(f"Missing timeframe data for {symbol}: trend={trend_data is not None}, entry={entry_data is not None}")
                return []
            
            # Check if we have enough data
            if len(trend_data) < self.min_candles or len(entry_data) < self.min_candles:
                logger.debug(f"Insufficient data for {symbol}: trend={len(trend_data)}, entry={len(entry_data)}")
                return []
            
            # Analyze trend direction on higher timeframe
            trend_direction = self._analyze_trend_direction(trend_data)
            if trend_direction == "neutral":
                logger.debug(f"Neutral trend on {self.secondary_timeframes[0]} for {symbol}")
                return []
            
            # Analyze entry signals on lower timeframe
            entry_signals = self._analyze_entry_signals(entry_data, trend_direction)
            
            # Filter signals based on trend direction
            filtered_signals = []
            for signal in entry_signals:
                if self._is_signal_aligned_with_trend(signal, trend_direction):
                    # Add trend context to signal
                    signal['trend_direction'] = trend_direction
                    signal['trend_timeframe'] = self.secondary_timeframes[0]
                    signal['entry_timeframe'] = self.primary_timeframe
                    signal['symbol'] = symbol
                    signal['strategy'] = self.name
                    
                    filtered_signals.append(signal)
            
            if filtered_signals:
                logger.info(f"Generated {len(filtered_signals)} multi-timeframe signals for {symbol}")
                for signal in filtered_signals:
                    logger.info(f"  {signal['action'].upper()} signal: {signal['confidence']:.2f} confidence, trend: {signal['trend_direction']}")
            
            return filtered_signals
            
        except Exception as e:
            logger.error(f"Error generating multi-timeframe signals for {symbol}: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _analyze_trend_direction(self, trend_data: pd.DataFrame) -> str:
        """
        Analyze trend direction on higher timeframe.
        
        Args:
            trend_data: DataFrame with OHLCV data for trend timeframe
            
        Returns:
            "bullish", "bearish", or "neutral"
        """
        try:
            # Calculate trend EMA
            trend_ema = trend_data['close'].ewm(span=self.trend_ema_period).mean()
            
            # Get recent EMA values
            current_ema = trend_ema.iloc[-1]
            prev_ema = trend_ema.iloc[-2]
            
            # Calculate EMA slope (trend strength)
            ema_slope = (current_ema - prev_ema) / prev_ema
            
            # Determine trend direction
            if ema_slope > 0.001:  # 0.1% threshold
                return "bullish"
            elif ema_slope < -0.001:  # -0.1% threshold
                return "bearish"
            else:
                return "neutral"
                
        except Exception as e:
            logger.error(f"Error analyzing trend direction: {e}")
            return "neutral"
    
    def _analyze_entry_signals(self, entry_data: pd.DataFrame, trend_direction: str) -> List[Dict]:
        """
        Analyze entry signals on lower timeframe.
        
        Args:
            entry_data: DataFrame with OHLCV data for entry timeframe
            trend_direction: Current trend direction from higher timeframe
            
        Returns:
            List of entry signal dictionaries
        """
        try:
            signals = []
            
            # Calculate indicators
            fast_ema = entry_data['close'].ewm(span=self.entry_ema_fast).mean()
            slow_ema = entry_data['close'].ewm(span=self.entry_ema_slow).mean()
            
            # Calculate RSI
            delta = entry_data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # Get current values
            current_price = entry_data['close'].iloc[-1]
            current_fast_ema = fast_ema.iloc[-1]
            current_slow_ema = slow_ema.iloc[-1]
            current_rsi = rsi.iloc[-1]
            
            # Previous values for crossover detection
            prev_fast_ema = fast_ema.iloc[-2]
            prev_slow_ema = slow_ema.iloc[-2]
            
            # Check for bullish signals (EMA cross + RSI oversold)
            if (current_fast_ema > current_slow_ema and 
                prev_fast_ema <= prev_slow_ema and 
                current_rsi < self.rsi_overbought):
                
                confidence = self._calculate_signal_confidence(
                    current_rsi, self.rsi_oversold, self.rsi_overbought, 
                    current_fast_ema, current_slow_ema, "bullish"
                )
                
                signals.append({
                    'action': 'buy',
                    'confidence': confidence,
                    'price': current_price,
                    'stop_loss': current_price * (1 - self.stop_loss_pct),
                    'take_profit': current_price * (1 + self.take_profit_pct),
                    'reason': f'EMA cross + RSI {current_rsi:.1f}',
                    'indicators': {
                        'fast_ema': current_fast_ema,
                        'slow_ema': current_slow_ema,
                        'rsi': current_rsi
                    }
                })
            
            # Check for bearish signals (EMA cross + RSI overbought)
            elif (current_fast_ema < current_slow_ema and 
                  prev_fast_ema >= prev_slow_ema and 
                  current_rsi > self.rsi_overbought):
                
                confidence = self._calculate_signal_confidence(
                    current_rsi, self.rsi_oversold, self.rsi_overbought, 
                    current_fast_ema, current_slow_ema, "bearish"
                )
                
                signals.append({
                    'action': 'sell',
                    'confidence': confidence,
                    'price': current_price,
                    'stop_loss': current_price * (1 + self.stop_loss_pct),
                    'take_profit': current_price * (1 - self.take_profit_pct),
                    'reason': f'EMA cross + RSI {current_rsi:.1f}',
                    'indicators': {
                        'fast_ema': current_fast_ema,
                        'slow_ema': current_slow_ema,
                        'rsi': current_rsi
                    }
                })
            
            return signals
            
        except Exception as e:
            logger.error(f"Error analyzing entry signals: {e}")
            return []
    
    def _is_signal_aligned_with_trend(self, signal: Dict, trend_direction: str) -> bool:
        """
        Check if signal is aligned with trend direction.
        
        Args:
            signal: Signal dictionary
            trend_direction: Current trend direction
            
        Returns:
            True if signal aligns with trend
        """
        signal_action = signal.get('action', '').lower()
        
        if trend_direction == "bullish" and signal_action == "buy":
            return True
        elif trend_direction == "bearish" and signal_action == "sell":
            return True
        else:
            logger.debug(f"Signal {signal_action} not aligned with trend {trend_direction}")
            return False
    
    def _calculate_signal_confidence(self, rsi: float, oversold: float, overbought: float, 
                                   fast_ema: float, slow_ema: float, signal_type: str) -> float:
        """
        Calculate signal confidence based on indicator values.
        
        Args:
            rsi: Current RSI value
            oversold: RSI oversold threshold
            overbought: RSI overbought threshold
            fast_ema: Fast EMA value
            slow_ema: Slow EMA value
            signal_type: "bullish" or "bearish"
            
        Returns:
            Confidence score between 0.0 and 1.0
        """
        try:
            # Base confidence from RSI
            if signal_type == "bullish":
                rsi_confidence = max(0, (oversold - rsi) / oversold)  # Lower RSI = higher confidence
            else:  # bearish
                rsi_confidence = max(0, (rsi - overbought) / (100 - overbought))  # Higher RSI = higher confidence
            
            # EMA separation confidence
            ema_separation = abs(fast_ema - slow_ema) / slow_ema
            ema_confidence = min(1.0, ema_separation * 100)  # Scale to 0-1
            
            # Combine confidences
            total_confidence = (rsi_confidence * 0.6 + ema_confidence * 0.4)
            
            return min(1.0, max(0.0, total_confidence))
            
        except Exception as e:
            logger.error(f"Error calculating signal confidence: {e}")
            return 0.5  # Default moderate confidence
