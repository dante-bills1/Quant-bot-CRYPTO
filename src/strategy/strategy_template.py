"""
Strategy Template for Crypto Trading Bot

This template demonstrates how to create trading strategies that work with both
the live trading engine and the backtesting framework. It shows:

1. Basic strategy structure
2. Single timeframe strategy example
3. Multi-timeframe strategy example
4. Indicator calculation
5. Signal generation
6. Data format handling
7. Backtesting compatibility

Copy and modify this template to create your own strategies.
"""

from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np
from loguru import logger

from src.trading_bot import SignalGenerator


# =============================================================================
# STRATEGY TEMPLATE - BASIC STRUCTURE
# =============================================================================

class BasicStrategyTemplate(SignalGenerator):
    """
    Basic strategy template showing essential structure.

    This template demonstrates the minimum required components for a strategy
    that works with both live trading and backtesting.
    """

    def __init__(self, crypto_handler=None, risk_manager=None, **kwargs):
        """
        Initialize your strategy.

        Args:
            crypto_handler: CryptoHandler instance for live trading
            risk_manager: RiskManager instance for position sizing
            **kwargs: Strategy-specific parameters
        """
        super().__init__(crypto_handler, risk_manager, **kwargs)

        # Basic configuration - REQUIRED
        self.name = "Basic Strategy Template"
        self.version = "1.0.0"

        # Timeframe configuration - REQUIRED
        # Choose ONE approach:
        # 1. Single timeframe: self.primary_timeframe = "1h"
        # 2. Multi-timeframe: self.primary_timeframe = "1h" + self.secondary_timeframes = ["4h"]
        self.primary_timeframe = "1h"  # Main timeframe for analysis
        self.secondary_timeframes = []  # Additional timeframes if needed

        # Strategy parameters - CUSTOMIZE for your strategy
        self.fast_period = kwargs.get('fast_period', 12)
        self.slow_period = kwargs.get('slow_period', 26)
        self.rsi_period = kwargs.get('rsi_period', 14)

        # Risk management parameters
        self.stop_loss_pct = kwargs.get('stop_loss_pct', 0.02)  # 2%
        self.take_profit_pct = kwargs.get('take_profit_pct', 0.04)  # 4%

        # Minimum data requirements
        self.min_candles = kwargs.get('min_candles', 100)
        self.lookback = kwargs.get('lookback', 200)

        logger.info(f"Initialized {self.name} v{self.version}")

    async def initialize(self) -> bool:
        """
        Initialize the strategy.

        This method is called once when the strategy is loaded.
        Use it for any setup that needs to happen before trading starts.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            # Perform any initialization tasks here
            logger.info(f"{self.name} initialization complete")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize {self.name}: {e}")
            return False

    async def generate_signals(
        self,
        market_data: Optional[Dict[str, Dict[str, pd.DataFrame]]] = None,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """
        Generate trading signals.

        This is the main method called by both live trading and backtesting.

        Args:
            market_data: Dictionary containing market data
                        Format: {symbol: {timeframe: DataFrame}}
            symbol: Trading symbol (e.g., "BTC/USDT")
            timeframe: Primary timeframe (usually your primary_timeframe)
            **kwargs: Additional parameters

        Returns:
            List of signal dictionaries
        """
        try:
            # Input validation
            if not market_data or not symbol:
                logger.debug("No market data or symbol provided")
                return []

            # Get symbol data
            symbol_data = market_data.get(symbol, {})
            if not symbol_data:
                logger.warning(f"No data for symbol {symbol}")
                return []

            # Get primary timeframe data
            primary_data = symbol_data.get(self.primary_timeframe)
            if primary_data is None or primary_data.empty:
                logger.warning(f"No data for {symbol} {self.primary_timeframe}")
                return []

            # Check minimum data requirement
            if len(primary_data) < self.min_candles:
                logger.debug(f"Insufficient data: {len(primary_data)} < {self.min_candles}")
                return []

            # Calculate indicators
            indicators = self._calculate_indicators(primary_data)

            # Generate signals
            signals = self._generate_signals_from_indicators(primary_data, indicators, symbol)

            return signals

        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return []

    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Calculate technical indicators.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dictionary of indicator series
        """
        try:
            # Clean data
            df_clean = df.copy()
            if hasattr(df_clean.index, 'isna'):
                df_clean = df_clean[~df_clean.index.isna()]

            # Example indicators - REPLACE with your strategy's indicators
            close = df_clean['close'].astype(float)

            # Moving averages
            fast_ma = close.ewm(span=self.fast_period).mean()
            slow_ma = close.ewm(span=self.slow_period).mean()

            # RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=self.rsi_period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=self.rsi_period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            return {
                'fast_ma': fast_ma,
                'slow_ma': slow_ma,
                'rsi': rsi,
                'close': close
            }

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return {}

    def _generate_signals_from_indicators(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, pd.Series],
        symbol: str
    ) -> List[Dict]:
        """
        Generate signals based on calculated indicators.

        Args:
            df: Price data
            indicators: Calculated indicators
            symbol: Trading symbol

        Returns:
            List of signal dictionaries
        """
        signals = []

        try:
            # Get latest indicator values
            current_idx = -1  # Latest candle
            prev_idx = -2     # Previous candle

            fast_ma = indicators.get('fast_ma')
            slow_ma = indicators.get('slow_ma')
            rsi = indicators.get('rsi')
            close = indicators.get('close')

            if not all([fast_ma, slow_ma, rsi, close]):
                return signals

            # Example signal logic - REPLACE with your strategy's logic
            # Long signal: Fast MA crosses above Slow MA + RSI oversold
            if (fast_ma.iloc[current_idx] > slow_ma.iloc[current_idx] and
                fast_ma.iloc[prev_idx] <= slow_ma.iloc[prev_idx] and
                rsi.iloc[current_idx] < 30):

                signal = self._create_signal(df, "buy", symbol)
                if signal:
                    signals.append(signal)

            # Short signal: Fast MA crosses below Slow MA + RSI overbought
            elif (fast_ma.iloc[current_idx] < slow_ma.iloc[current_idx] and
                  fast_ma.iloc[prev_idx] >= slow_ma.iloc[prev_idx] and
                  rsi.iloc[current_idx] > 70):

                signal = self._create_signal(df, "sell", symbol)
                if signal:
                    signals.append(signal)

        except Exception as e:
            logger.error(f"Error generating signals from indicators: {e}")

        return signals

    def _create_signal(self, df: pd.DataFrame, direction: str, symbol: str) -> Optional[Dict]:
        """
        Create a trading signal dictionary.

        Args:
            df: Price data
            direction: "buy" or "sell"
            symbol: Trading symbol

        Returns:
            Signal dictionary or None if creation fails
        """
        try:
            current_price = float(df["close"].iloc[-1])

            # Handle timestamp
            timestamp = self._get_timestamp(df)

            # Calculate stop loss and take profit
            if direction == "buy":
                stop_loss = current_price * (1 - self.stop_loss_pct)
                take_profit = current_price * (1 + self.take_profit_pct)
            else:
                stop_loss = current_price * (1 + self.stop_loss_pct)
                take_profit = current_price * (1 - self.take_profit_pct)

            signal = {
                "symbol": symbol,
                "timeframe": self.primary_timeframe,
                "action": direction,
                "signal_type": direction,
                "entry_price": current_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "confidence": 0.8,  # Adjust based on your signal strength
                "reason": f"Template strategy {direction.upper()} signal",
                "timestamp": timestamp,
                "strategy": self.name,
                "strategy_version": self.version
            }

            logger.info(f"Generated {direction.upper()} signal for {symbol} at {current_price:.4f}")
            return signal

        except Exception as e:
            logger.error(f"Error creating signal: {e}")
            return None

    def _get_timestamp(self, df: pd.DataFrame) -> int:
        """Get timestamp from DataFrame index."""
        try:
            index_value = df.index[-1]
            if pd.isna(index_value) or pd.isnull(index_value):
                return int(pd.Timestamp.now().timestamp() * 1000)
            else:
                return int(index_value.timestamp() * 1000)
        except Exception:
            return int(pd.Timestamp.now().timestamp() * 1000)


# =============================================================================
# SINGLE TIMEFRAME STRATEGY EXAMPLE
# =============================================================================

class SingleTimeframeExample(SignalGenerator):
    """
    Example strategy using only one timeframe.

    This demonstrates a simple strategy that analyzes price action
    and generates signals based on a single timeframe.
    """

    def __init__(self, crypto_handler=None, risk_manager=None, **kwargs):
        super().__init__(crypto_handler, risk_manager, **kwargs)

        # Single timeframe configuration
        self.name = "Single Timeframe Example"
        self.primary_timeframe = "1h"  # Only timeframe needed
        self.secondary_timeframes = []  # No additional timeframes

        # Strategy parameters
        self.ema_fast = kwargs.get('ema_fast', 12)
        self.ema_slow = kwargs.get('ema_slow', 26)
        self.rsi_period = kwargs.get('rsi_period', 14)
        self.min_candles = 100

        logger.info(f"Initialized {self.name} on {self.primary_timeframe}")

    async def generate_signals(self, market_data=None, symbol=None, **kwargs) -> List[Dict]:
        """Generate signals using single timeframe analysis."""
        if not market_data or not symbol:
            return []

        symbol_data = market_data.get(symbol, {})
        df = symbol_data.get(self.primary_timeframe)

        if df is None or len(df) < self.min_candles:
            return []

        # Calculate indicators
        indicators = self._calculate_indicators(df)

        # Generate signals
        return self._generate_signals_from_indicators(df, indicators, symbol)


# =============================================================================
# MULTI-TIMEFRAME STRATEGY EXAMPLE
# =============================================================================

class MultiTimeframeExample(SignalGenerator):
    """
    Example strategy using multiple timeframes.

    This demonstrates how to use higher timeframe for trend analysis
    and lower timeframe for entry signals.
    """

    def __init__(self, crypto_handler=None, risk_manager=None, **kwargs):
        super().__init__(crypto_handler, risk_manager, **kwargs)

        # Multi-timeframe configuration
        self.name = "Multi-Timeframe Example"
        self.primary_timeframe = "15m"        # Entry timeframe
        self.secondary_timeframes = ["1h"]    # Trend timeframe

        # Strategy parameters
        self.trend_ema_period = kwargs.get('trend_ema_period', 50)
        self.entry_fast_period = kwargs.get('entry_fast_period', 12)
        self.entry_slow_period = kwargs.get('entry_slow_period', 26)
        self.min_candles = 100

        logger.info(f"Initialized {self.name}: entry={self.primary_timeframe}, trend={self.secondary_timeframes}")

    async def generate_signals(self, market_data=None, symbol=None, **kwargs) -> List[Dict]:
        """Generate signals using multi-timeframe analysis."""
        if not market_data or not symbol:
            return []

        symbol_data = market_data.get(symbol, {})

        # Get data for all required timeframes
        trend_data = symbol_data.get(self.secondary_timeframes[0])  # 1h data
        entry_data = symbol_data.get(self.primary_timeframe)       # 15m data

        if trend_data is None or entry_data is None:
            logger.warning(f"Missing timeframe data for {symbol}")
            return []

        if len(trend_data) < self.min_candles or len(entry_data) < self.min_candles:
            return []

        # Analyze trend on higher timeframe
        trend_direction = self._analyze_trend_direction(trend_data)

        # Generate entry signals on lower timeframe
        indicators = self._calculate_entry_indicators(entry_data)
        signals = self._generate_entry_signals(entry_data, indicators, trend_direction, symbol)

        return signals

    def _analyze_trend_direction(self, trend_data: pd.DataFrame) -> str:
        """Analyze trend direction on higher timeframe."""
        try:
            close = trend_data['close']
            ema = close.ewm(span=self.trend_ema_period).mean()

            # Simple trend detection
            slope = (ema.iloc[-1] - ema.iloc[-5]) / ema.iloc[-5]

            if slope > 0.001:
                return "bullish"
            elif slope < -0.001:
                return "bearish"
            else:
                return "neutral"

        except Exception as e:
            logger.error(f"Error analyzing trend: {e}")
            return "neutral"

    def _calculate_entry_indicators(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate indicators for entry signals."""
        close = df['close'].astype(float)

        fast_ma = close.ewm(span=self.entry_fast_period).mean()
        slow_ma = close.ewm(span=self.entry_slow_period).mean()

        # RSI calculation
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return {
            'fast_ma': fast_ma,
            'slow_ma': slow_ma,
            'rsi': rsi,
            'close': close
        }

    def _generate_entry_signals(
        self,
        df: pd.DataFrame,
        indicators: Dict[str, pd.Series],
        trend_direction: str,
        symbol: str
    ) -> List[Dict]:
        """Generate entry signals based on trend and indicators."""
        signals = []

        try:
            fast_ma = indicators['fast_ma']
            slow_ma = indicators['slow_ma']
            rsi = indicators['rsi']
            close = indicators['close']

            current = -1
            previous = -2

            # Only trade in trend direction
            if trend_direction == "bullish":
                # Long signal: Fast MA crosses above Slow MA + RSI not overbought
                if (fast_ma.iloc[current] > slow_ma.iloc[current] and
                    fast_ma.iloc[previous] <= slow_ma.iloc[previous] and
                    rsi.iloc[current] < 70):

                    signal = self._create_signal(df, "buy", symbol)
                    if signal:
                        signals.append(signal)

            elif trend_direction == "bearish":
                # Short signal: Fast MA crosses below Slow MA + RSI not oversold
                if (fast_ma.iloc[current] < slow_ma.iloc[current] and
                    fast_ma.iloc[previous] >= slow_ma.iloc[previous] and
                    rsi.iloc[current] > 30):

                    signal = self._create_signal(df, "sell", symbol)
                    if signal:
                        signals.append(signal)

        except Exception as e:
            logger.error(f"Error generating entry signals: {e}")

        return signals


# =============================================================================
# BACKTESTING COMPATIBILITY
# =============================================================================

class BacktestCompatibleStrategy(SignalGenerator):
    """
    Strategy optimized for backtesting.

    This example shows how to handle different data formats that come
    from the backtesting engine vs live trading.
    """

    def __init__(self, crypto_handler=None, risk_manager=None, **kwargs):
        super().__init__(crypto_handler, risk_manager, **kwargs)

        self.name = "Backtest Compatible Strategy"
        self.primary_timeframe = "1h"
        self.secondary_timeframes = []

        # Strategy parameters
        self.ema_period = kwargs.get('ema_period', 20)
        self.min_candles = 50

        # For backtesting compatibility
        self._historical_data = None  # Store historical data for backtesting

    async def generate_signals(self, market_data=None, symbol=None, **kwargs) -> List[Dict]:
        """
        Generate signals compatible with both live and backtest data formats.

        The backtesting engine passes data differently than live trading:
        - Live: {symbol: {timeframe: DataFrame}}
        - Backtest: Single row dict or DataFrame
        """
        try:
            # Handle backtesting single row format
            if isinstance(market_data, dict) and 'close' in market_data:
                return self._handle_backtest_single_row(market_data, symbol)

            # Handle live trading format
            elif isinstance(market_data, dict) and symbol in market_data:
                return self._handle_live_trading_format(market_data, symbol)

            # Handle single DataFrame (another backtest format)
            elif isinstance(market_data, pd.DataFrame):
                return self._handle_dataframe_format(market_data, symbol)

            else:
                logger.warning(f"Unknown market_data format: {type(market_data)}")
                return []

        except Exception as e:
            logger.error(f"Error in generate_signals: {e}")
            return []

    def _handle_backtest_single_row(self, row_data: Dict, symbol: str) -> List[Dict]:
        """Handle single row data from backtesting engine."""
        try:
            # Convert single row to DataFrame format
            if self._historical_data is None:
                # First row - create initial DataFrame
                df = pd.DataFrame([row_data], index=[row_data['timestamp']])
                self._historical_data = df
            else:
                # Append new row to historical data
                new_row = pd.DataFrame([row_data], index=[row_data['timestamp']])
                self._historical_data = pd.concat([self._historical_data, new_row])

            # Use recent data for analysis
            recent_data = self._historical_data.tail(self.lookback)

            if len(recent_data) < self.min_candles:
                return []

            # Calculate indicators and generate signals
            indicators = self._calculate_indicators(recent_data)
            return self._generate_signals_from_indicators(recent_data, indicators, symbol)

        except Exception as e:
            logger.error(f"Error handling backtest single row: {e}")
            return []

    def _handle_live_trading_format(self, market_data: Dict, symbol: str) -> List[Dict]:
        """Handle live trading data format."""
        symbol_data = market_data.get(symbol, {})
        df = symbol_data.get(self.primary_timeframe)

        if df is None or len(df) < self.min_candles:
            return []

        indicators = self._calculate_indicators(df)
        return self._generate_signals_from_indicators(df, indicators, symbol)

    def _handle_dataframe_format(self, df: pd.DataFrame, symbol: str) -> List[Dict]:
        """Handle single DataFrame format."""
        if len(df) < self.min_candles:
            return []

        indicators = self._calculate_indicators(df)
        return self._generate_signals_from_indicators(df, indicators, symbol)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def create_strategy_template(timeframe: str = "1h", **kwargs) -> BasicStrategyTemplate:
    """
    Factory function to create a strategy template.

    Args:
        timeframe: Primary timeframe for the strategy
        **kwargs: Strategy parameters

    Returns:
        Configured strategy instance
    """
    return BasicStrategyTemplate(
        primary_timeframe=timeframe,
        **kwargs
    )


def create_single_timeframe_strategy(timeframe: str = "1h", **kwargs) -> SingleTimeframeExample:
    """Factory function for single timeframe strategy."""
    return SingleTimeframeExample(
        primary_timeframe=timeframe,
        **kwargs
    )


def create_multi_timeframe_strategy(
    entry_timeframe: str = "15m",
    trend_timeframe: str = "1h",
    **kwargs
) -> MultiTimeframeExample:
    """Factory function for multi-timeframe strategy."""
    return MultiTimeframeExample(
        primary_timeframe=entry_timeframe,
        secondary_timeframes=[trend_timeframe],
        **kwargs
    )


# =============================================================================
# USAGE EXAMPLES
# =============================================================================

"""
USAGE EXAMPLES:

1. Basic Strategy:
   strategy = BasicStrategyTemplate(
       primary_timeframe="1h",
       fast_period=12,
       slow_period=26,
       stop_loss_pct=0.02
   )

2. Single Timeframe Strategy:
   strategy = SingleTimeframeExample(
       primary_timeframe="4h",
       ema_fast=10,
       ema_slow=30
   )

3. Multi-Timeframe Strategy:
   strategy = MultiTimeframeExample(
       primary_timeframe="15m",
       secondary_timeframes=["1h"],
       trend_ema_period=50,
       entry_fast_period=12
   )

4. Backtesting Compatible Strategy:
   strategy = BacktestCompatibleStrategy(
       primary_timeframe="1h",
       ema_period=20
   )

5. Using Factory Functions:
   strategy = create_strategy_template("4h", fast_period=10, slow_period=30)
   multi_strategy = create_multi_timeframe_strategy("15m", "1h", trend_ema_period=50)
"""
