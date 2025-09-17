"""
Volume MA Oscillator Strategy

This strategy is ported from the reference file volume_ma_live_updated_v3.py
and adapted for the crypto trading bot framework.
"""

import asyncio
import time
import math
import json
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
import pandas as pd
from loguru import logger

from src.trading_bot import SignalGenerator


@dataclass
class VolumeMAOscillatorParams:
    """Parameters for the Volume MA Oscillator strategy."""
    source: str = "close"
    ma_type: str = "DEMA"
    ma_length: int = 84
    band_length: int = 10
    band_smoothing: float = 0.5042647916652371
    upper_mult: float = 0.9321998763220779
    lower_mult: float = -2.928308594400491
    strategy_mode: str = "Hybrid"  # Trend | Reversion | Hybrid
    enable_long: bool = True
    enable_short: bool = True
    atr_length: int = 6
    sl_atr_mult: float = 2.0
    tp_atr_mult: float = 2.0
    risk_reward: float = 1.0
    max_risk_percent: float = 2.0
    commission_rate: float = 0.001
    enable_volume_filter: bool = True
    volume_ma_length: int = 20
    volume_threshold: float = 1.2
    enable_trend_filter: bool = True
    trend_ma_length: int = 40
    enable_rsi_filter: bool = False
    rsi_length: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    enable_adx_filter: bool = False
    adx_length: int = 7
    adx_threshold: float = 18.0
    enable_divergence_filter: bool = False
    divergence_lookback: int = 5
    exact_exit_logic: bool = True


class VolumeMAOscillator(SignalGenerator):
    """Volume MA Oscillator strategy for crypto trading."""
    
    def __init__(
        self,
        primary_timeframe: str = "4h",
        risk_percent: float = 2.0,
        min_risk_reward: float = 1.0,
        **kwargs
    ):
        """
        Initialize the Volume MA Oscillator strategy.
        
        Args:
            primary_timeframe: Primary timeframe for the strategy
            risk_percent: Risk percentage per trade
            min_risk_reward: Minimum risk-reward ratio
            **kwargs: Additional parameters
        """
        super().__init__(**kwargs)
        
        self.name = "Volume MA Oscillator"
        self.version = "1.0.0"
        self.primary_timeframe = primary_timeframe
        self.risk_percent = risk_percent
        self.min_risk_reward = min_risk_reward
        
        # Strategy parameters
        self.params = VolumeMAOscillatorParams()
        
        # Update parameters from kwargs
        for key, value in kwargs.items():
            if hasattr(self.params, key):
                setattr(self.params, key, value)
        
        # Load timeframe-specific configuration
        self._load_timeframe_profile()

        # State tracking
        self.last_signal_time = None
        self.position_state = None

        logger.info(f"Initialized {self.name} v{self.version} for {primary_timeframe}")
    
    def _load_timeframe_profile(self):
        """Load timeframe-specific configuration."""
        timeframe_profiles = {
            "1m": {"lookback": 200, "min_candles": 100},
            "5m": {"lookback": 500, "min_candles": 200},
            "15m": {"lookback": 1000, "min_candles": 500},
            "1h": {"lookback": 2000, "min_candles": 1000},
            "4h": {"lookback": 1000, "min_candles": 500},
            "1d": {"lookback": 500, "min_candles": 200}
        }
        
        profile = timeframe_profiles.get(self.primary_timeframe, timeframe_profiles["4h"])
        self.lookback = profile["lookback"]
        self.min_candles = profile["min_candles"]
        
        logger.info(f"Loaded timeframe profile for {self.primary_timeframe}: lookback={self.lookback}")
    
    @property
    def required_timeframes(self) -> List[str]:
        """Required timeframes for this strategy."""
        return [self.primary_timeframe]
    
    def prepare_data(self, market_data: Dict[str, Dict[str, pd.DataFrame]]) -> Dict[str, Dict[str, pd.DataFrame]]:
        """Prepare market data for strategy analysis."""
        try:
            prepared_data = {}
            
            for symbol, timeframes in market_data.items():
                prepared_data[symbol] = {}
                
                for timeframe, df in timeframes.items():
                    if df is None or df.empty:
                        continue
                    
                    # Ensure we have required columns
                    required_cols = ['open', 'high', 'low', 'close', 'volume']
                    if not all(col in df.columns for col in required_cols):
                        logger.warning(f"Missing required columns in {symbol} {timeframe}")
                        continue
                    
                    # Clean data
                    df_clean = df.copy()
                    df_clean = df_clean.dropna()
                    
                    if len(df_clean) < self.min_candles:
                        logger.warning(f"Insufficient data for {symbol} {timeframe}: {len(df_clean)} < {self.min_candles}")
                        continue
                    
                    prepared_data[symbol][timeframe] = df_clean
            
            return prepared_data
            
        except Exception as e:
            logger.error(f"Error preparing data: {e}")
            return market_data
    
    async def initialize(self) -> bool:
        """Initialize the strategy."""
        try:
            self._load_timeframe_profile()
            logger.success(f"Volume MA Oscillator initialized for {self.primary_timeframe}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize Volume MA Oscillator: {e}")
            return False
    
    async def generate_signals(
        self,
        market_data: Optional[Dict[str, Dict[str, pd.DataFrame]]] = None,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        **kwargs
    ) -> List[Dict]:
        """Generate trading signals based on Volume MA Oscillator."""
        try:
            if not market_data:
                return []
            
            signals = []
            
            for sym, timeframes in market_data.items():
                if self.primary_timeframe not in timeframes:
                    continue
                
                df = timeframes[self.primary_timeframe]
                if df is None or df.empty or len(df) < self.min_candles:
                    continue
                
                # Calculate indicators
                indicators = self._calculate_indicators(df)
                
                # Check for signals
                signal = self._check_signal(df, indicators, sym)
                if signal:
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return []
    
    def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate all indicators for the strategy."""
        try:
            # Get source data
            src = df[self.params.source].astype(float)
            vol = df["volume"].astype(float)
            
            # Calculate volume weighted moving average
            ma_series = self._volume_weighted_ma(src, vol, self.params.ma_length, self.params.ma_type)
            
            # Calculate price difference percentage
            price_diff = ((src - ma_series) / ma_series) * 100.0
            
            # Calculate standard deviation
            std = price_diff.rolling(self.params.band_length, min_periods=self.params.band_length).std()
            
            # Calculate upper and lower bands
            upper_raw = std * self.params.upper_mult
            lower_raw = std * self.params.lower_mult
            
            # Apply smoothing
            upper = self._smooth_series(upper_raw, self.params.band_smoothing)
            lower = self._smooth_series(lower_raw, self.params.band_smoothing)
            
            # Calculate ATR
            atr = self._calculate_atr(df, self.params.atr_length)
            
            # Calculate filters
            volume_filter = self._calculate_volume_filter(df)
            trend_filter = self._calculate_trend_filter(df)
            
            # Calculate crossover signals
            trend_long = self._crossover(price_diff, upper)
            trend_short = self._crossunder(price_diff, lower)
            reversion_long = self._crossover(price_diff, lower)
            reversion_short = self._crossunder(price_diff, upper)
            
            # Combine signals based on strategy mode
            if self.params.strategy_mode == "Trend":
                long_sig, short_sig = trend_long, trend_short
            elif self.params.strategy_mode == "Reversion":
                long_sig, short_sig = reversion_long, reversion_short
            else:  # Hybrid
                long_sig = trend_long | reversion_long
                short_sig = trend_short | reversion_short
            
            # Apply filters
            if not self.params.enable_long:
                long_sig = pd.Series(False, index=df.index)
            if not self.params.enable_short:
                short_sig = pd.Series(False, index=df.index)
            
            long_cond = long_sig & volume_filter & trend_filter
            short_cond = short_sig & volume_filter & trend_filter
            
            return {
                "price_diff": price_diff,
                "upper": upper,
                "lower": lower,
                "atr": atr,
                "long_cond": long_cond,
                "short_cond": short_cond,
                "ma_series": ma_series
            }
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return {}
    
    def _volume_weighted_ma(self, src: pd.Series, vol: pd.Series, n: int, ma_type: str) -> pd.Series:
        """Calculate volume weighted moving average."""
        try:
            if ma_type.upper() == "VWMA":
                pv = (src * vol).rolling(n, min_periods=n).sum()
                vv = vol.rolling(n, min_periods=n).sum()
                return pv / vv
            
            # Apply MA to price * volume and volume separately
            num = self._apply_ma(src * vol, n, ma_type)
            den = self._apply_ma(vol, n, ma_type)
            return num / den
            
        except Exception as e:
            logger.error(f"Error calculating volume weighted MA: {e}")
            return src.rolling(n).mean()
    
    def _apply_ma(self, x: pd.Series, n: int, ma: str) -> pd.Series:
        """Apply moving average based on type."""
        ma = ma.upper()
        
        if ma == "SMA":
            return x.rolling(n, min_periods=n).mean()
        elif ma == "EMA":
            return x.ewm(span=n, adjust=False).mean()
        elif ma == "DEMA":
            e1 = x.ewm(span=n, adjust=False).mean()
            return 2 * e1 - e1.ewm(span=n, adjust=False).mean()
        elif ma == "TEMA":
            e1 = x.ewm(span=n, adjust=False).mean()
            e2 = e1.ewm(span=n, adjust=False).mean()
            e3 = e2.ewm(span=n, adjust=False).mean()
            return 3 * (e1 - e2) + e3
        elif ma == "WMA":
            weights = np.arange(1, n + 1)
            return x.rolling(n).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
        else:
            return x.ewm(span=n, adjust=False).mean()  # Default to EMA
    
    def _smooth_series(self, series: pd.Series, smoothing: float) -> pd.Series:
        """Apply smoothing to a series."""
        try:
            result = pd.Series(np.nan, index=series.index)
            
            for i in range(len(series)):
                if i == 0 or np.isnan(result.iloc[i-1]):
                    prev = 0.0
                else:
                    prev = result.iloc[i-1]
                
                current = series.iloc[i]
                if np.isfinite(current):
                    result.iloc[i] = current * smoothing + prev * (1.0 - smoothing)
                else:
                    result.iloc[i] = prev
            
            return result
            
        except Exception as e:
            logger.error(f"Error smoothing series: {e}")
            return series
    
    def _calculate_atr(self, df: pd.DataFrame, n: int) -> pd.Series:
        """
        Calculate Average True Range using enhanced method from reference bot.

        Based on reference bot's ATR calculation pattern:
        - Proper true range calculation
        - Rolling mean with minimum periods
        - Forward/backward fill for edge cases
        - Enhanced error handling
        """
        try:
            if df is None or df.empty:
                logger.warning("No data provided for ATR calculation")
                return pd.Series(dtype=float)

            required_columns = ['high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                logger.error(f"Missing required columns for ATR: {missing_columns}")
                return pd.Series(dtype=float)

            high = df['high']
            low = df['low']
            close = df['close']

            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))

            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # Calculate ATR using rolling mean with minimum periods (reference bot pattern)
            atr = true_range.rolling(window=n, min_periods=n).mean()

            # Handle edge cases with forward/backward fill
            if not atr.empty:
                atr = atr.fillna(method='bfill').fillna(method='ffill').fillna(0.0)

            logger.debug(f"Calculated ATR with period {n}: {len(atr)} values")
            return atr

        except Exception as e:
            logger.error(f"Error calculating ATR: {str(e)}")
            return pd.Series(dtype=float)
    
    def _calculate_volume_filter(self, df: pd.DataFrame) -> pd.Series:
        """Calculate volume filter."""
        if not self.params.enable_volume_filter:
            return pd.Series(True, index=df.index)
        
        try:
            vol_ma = df["volume"].rolling(self.params.volume_ma_length).mean()
            return df["volume"] > vol_ma * self.params.volume_threshold
        except Exception as e:
            logger.error(f"Error calculating volume filter: {e}")
            return pd.Series(True, index=df.index)
    
    def _calculate_trend_filter(self, df: pd.DataFrame) -> pd.Series:
        """Calculate trend filter."""
        if not self.params.enable_trend_filter:
            return pd.Series(True, index=df.index)
        
        try:
            tma = df["close"].ewm(span=self.params.trend_ma_length, adjust=False).mean()
            return df["close"] > tma
        except Exception as e:
            logger.error(f"Error calculating trend filter: {e}")
            return pd.Series(True, index=df.index)
    
    def _crossover(self, a: pd.Series, b: pd.Series) -> pd.Series:
        """Check for crossover between two series."""
        return (a.shift(1) <= b.shift(1)) & (a > b)
    
    def _crossunder(self, a: pd.Series, b: pd.Series) -> pd.Series:
        """Check for crossunder between two series."""
        return (a.shift(1) >= b.shift(1)) & (a < b)
    
    def _check_signal(self, df: pd.DataFrame, indicators: Dict[str, pd.Series], symbol: str) -> Optional[Dict]:
        """Check for trading signals."""
        try:
            if not indicators or len(df) < 2:
                return None
            
            # Get latest values
            long_cond = indicators.get("long_cond", pd.Series(False, index=df.index))
            short_cond = indicators.get("short_cond", pd.Series(False, index=df.index))
            atr = indicators.get("atr", pd.Series(0, index=df.index))
            
            # Check for long signal
            if long_cond.iloc[-1] and not long_cond.iloc[-2]:
                return self._create_signal(df, "buy", atr.iloc[-1], symbol)
            
            # Check for short signal
            if short_cond.iloc[-1] and not short_cond.iloc[-2]:
                return self._create_signal(df, "sell", atr.iloc[-1], symbol)
            
            return None
            
        except Exception as e:
            logger.error(f"Error checking signal: {e}")
            return None
    
    def _create_signal(self, df: pd.DataFrame, direction: str, atr: float, symbol: str) -> Dict:
        """Create a trading signal."""
        try:
            current_price = float(df["close"].iloc[-1])
            timestamp = int(df.index[-1].timestamp() * 1000)
            
            # Calculate stop loss and take profit
            sl_distance = self.params.sl_atr_mult * atr
            tp_distance = self.params.tp_atr_mult * atr * self.params.risk_reward
            
            if direction == "buy":
                stop_loss = current_price - sl_distance
                take_profit = current_price + tp_distance
            else:
                stop_loss = current_price + sl_distance
                take_profit = current_price - tp_distance
            
            signal = {
                "symbol": symbol,
                "timeframe": self.primary_timeframe,
                "signal_type": direction,
                "entry_price": current_price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "confidence": 0.8,  # Default confidence
                "reason": f"Volume MA Oscillator {direction.upper()} signal",
                "timestamp": timestamp,
                "strategy": self.name,
                "strategy_version": self.version,
                "risk_reward": self.params.risk_reward,
                "atr": atr,
                "sl_distance": sl_distance,
                "tp_distance": tp_distance
            }
            
            logger.info(f"Generated {direction.upper()} signal for {symbol} at {current_price:.4f}")
            return signal
            
        except Exception as e:
            logger.error(f"Error creating signal: {e}")
            return None
    
    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information."""
        return {
            "name": self.name,
            "version": self.version,
            "timeframe": self.primary_timeframe,
            "risk_percent": self.risk_percent,
            "min_risk_reward": self.min_risk_reward,
            "parameters": self.params.__dict__,
            "lookback": self.lookback,
            "min_candles": self.min_candles
        }
