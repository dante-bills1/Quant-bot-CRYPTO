# Multi-Timeframe Trading Strategies

This document explains how to create and use multi-timeframe trading strategies in the crypto trading bot.

## Overview

The trading engine now supports strategies that can analyze multiple timeframes simultaneously. This allows for more sophisticated trading logic where:

- **Higher timeframes** (e.g., 4h, 1d) are used for trend direction and overall market context
- **Lower timeframes** (e.g., 1h, 15m) are used for precise entry and exit signals
- **Multiple timeframes** can be combined for comprehensive market analysis

## Architecture

### SignalGenerator Base Class

The `SignalGenerator` base class has been enhanced with multi-timeframe support:

```python
class SignalGenerator:
    def __init__(self, crypto_handler=None, risk_manager=None, **kwargs):
        # Timeframe configuration
        self.primary_timeframe = None      # Main timeframe for strategy
        self.secondary_timeframes = []     # Additional timeframes needed
        self.required_timeframes = []      # Auto-populated from above
        
        # Multi-timeframe data cache
        self._multi_tf_data_cache = {}
```

### Data Flow

1. **Strategy Registration**: Strategies specify their required timeframes
2. **Data Collection**: TradingBot collects data for all required timeframes
3. **Data Passing**: All timeframe data is passed to `generate_signals()`
4. **Strategy Analysis**: Strategies can access any timeframe data they need

## Creating Multi-Timeframe Strategies

### Basic Multi-Timeframe Strategy

```python
from src.trading_bot import SignalGenerator

class MyMultiTimeframeStrategy(SignalGenerator):
    def __init__(self, crypto_handler=None, risk_manager=None, **kwargs):
        super().__init__(crypto_handler, risk_manager, **kwargs)
        
        # Configure timeframes
        self.primary_timeframe = "1h"           # Entry timeframe
        self.secondary_timeframes = ["4h"]     # Trend timeframe
        
        # Strategy parameters
        self.trend_ema_period = 50
        self.entry_rsi_period = 14
    
    async def generate_signals(self, market_data=None, symbol=None, **kwargs):
        if not market_data or not symbol:
            return []
        
        symbol_data = market_data.get(symbol, {})
        
        # Get data for different timeframes
        trend_data = symbol_data.get("4h")      # Higher TF for trend
        entry_data = symbol_data.get("1h")     # Lower TF for entry
        
        if not trend_data or not entry_data:
            return []
        
        # Analyze trend on higher timeframe
        trend_direction = self._analyze_trend(trend_data)
        
        # Generate entry signals on lower timeframe
        signals = self._generate_entry_signals(entry_data, trend_direction)
        
        return signals
```

### Advanced Multi-Timeframe Strategy

```python
class AdvancedMultiTFStrategy(SignalGenerator):
    def __init__(self, crypto_handler=None, risk_manager=None, **kwargs):
        super().__init__(crypto_handler, risk_manager, **kwargs)
        
        # Multiple timeframes for different purposes
        self.primary_timeframe = "15m"                    # Entry signals
        self.secondary_timeframes = ["1h", "4h", "1d"]    # Trend, momentum, context
        
        # Strategy parameters
        self.trend_tf = "4h"      # Trend analysis timeframe
        self.momentum_tf = "1h"   # Momentum analysis timeframe
        self.context_tf = "1d"    # Market context timeframe
    
    async def generate_signals(self, market_data=None, symbol=None, **kwargs):
        symbol_data = market_data.get(symbol, {})
        
        # Get data for all timeframes
        trend_data = symbol_data.get(self.trend_tf)
        momentum_data = symbol_data.get(self.momentum_tf)
        context_data = symbol_data.get(self.context_tf)
        entry_data = symbol_data.get(self.primary_timeframe)
        
        # Multi-timeframe analysis
        trend_score = self._analyze_trend_strength(trend_data)
        momentum_score = self._analyze_momentum(momentum_data)
        context_score = self._analyze_market_context(context_data)
        
        # Generate signals based on combined analysis
        signals = self._generate_combined_signals(
            entry_data, trend_score, momentum_score, context_score
        )
        
        return signals
```

## Example Strategies

### 1. Multi-Timeframe Trend Following

**File**: `src/strategy/multi_timeframe_trend_following.py`

This strategy demonstrates:
- **4h timeframe**: Trend direction using EMA slope
- **1h timeframe**: Entry signals using EMA crossover + RSI
- **Trend alignment**: Only trades in the direction of the higher timeframe trend

```python
# Usage in config
{
    "signal_generators": ["MultiTimeframeTrendFollowing"],
    "symbols": ["BTC/USDT", "ETH/USDT"],
    "timeframes": ["1h", "4h"]  # Both timeframes will be monitored
}
```

### 2. Enhanced Volume MA Oscillator

**File**: `src/strategy/volume_ma_oscillator.py`

The existing VolumeMAOscillator has been enhanced with optional trend filtering:

```python
# Enable trend filtering
strategy = VolumeMAOscillator(
    primary_timeframe="4h",
    secondary_timeframes=["1d"],  # For trend filtering
    use_trend_filter=True,
    trend_timeframe="1d"
)
```

## Configuration

### Basic Configuration

```json
{
    "signal_generators": ["MultiTimeframeTrendFollowing"],
    "symbols": ["BTC/USDT"],
    "timeframes": ["1h", "4h"]
}
```

### Advanced Configuration

```json
{
    "signal_generators": [
        {
            "name": "MultiTimeframeTrendFollowing",
            "primary_timeframe": "1h",
            "secondary_timeframes": ["4h"],
            "trend_ema_period": 50,
            "entry_ema_fast": 12,
            "entry_ema_slow": 26
        }
    ],
    "symbols": ["BTC/USDT", "ETH/USDT"],
    "timeframes": ["1h", "4h", "1d"]
}
```

## Best Practices

### 1. Timeframe Selection

- **Trend Timeframes**: Use 4h, 1d, or higher for trend analysis
- **Entry Timeframes**: Use 1h, 15m, or lower for precise entries
- **Avoid**: Too many timeframes (performance impact)
- **Recommended**: 2-3 timeframes maximum for most strategies

### 2. Data Requirements

- **Minimum Candles**: Ensure sufficient historical data for indicators
- **Lookback Periods**: Configure appropriate lookback for each timeframe
- **Data Quality**: Handle missing or invalid data gracefully

### 3. Signal Generation

```python
async def generate_signals(self, market_data=None, symbol=None, **kwargs):
    try:
        # Validate input data
        if not market_data or not symbol:
            return []
        
        symbol_data = market_data.get(symbol, {})
        
        # Check data availability
        required_tfs = [self.primary_timeframe] + self.secondary_timeframes
        for tf in required_tfs:
            if tf not in symbol_data or symbol_data[tf] is None:
                logger.warning(f"Missing data for {symbol} {tf}")
                return []
        
        # Perform multi-timeframe analysis
        signals = self._analyze_multi_timeframe(symbol_data)
        
        return signals
        
    except Exception as e:
        logger.error(f"Error in multi-timeframe analysis: {e}")
        return []
```

### 4. Performance Considerations

- **Data Caching**: Use the built-in data cache efficiently
- **Indicator Calculation**: Calculate indicators once per timeframe
- **Signal Filtering**: Filter signals early to reduce processing
- **Logging**: Use appropriate log levels (debug vs info)

## Troubleshooting

### Common Issues

1. **Missing Timeframe Data**
   ```
   Warning: No data available for BTC/USDT 4h
   ```
   - Ensure the timeframe is registered in the data manager
   - Check if the exchange supports the timeframe
   - Verify sufficient historical data is available

2. **Strategy Not Receiving Data**
   ```python
   # Check required_timeframes is populated
   logger.info(f"Required timeframes: {self.required_timeframes}")
   ```

3. **Performance Issues**
   - Reduce the number of timeframes
   - Optimize indicator calculations
   - Use appropriate lookback periods

### Debug Mode

Enable debug logging to troubleshoot multi-timeframe strategies:

```python
import logging
logging.getLogger().setLevel(logging.DEBUG)
```

## Migration Guide

### Updating Existing Strategies

1. **Add Timeframe Configuration**:
   ```python
   def __init__(self, **kwargs):
       super().__init__(**kwargs)
       self.primary_timeframe = "4h"  # Your main timeframe
       self.secondary_timeframes = []  # Add if needed
   ```

2. **Update generate_signals Method**:
   ```python
   async def generate_signals(self, market_data=None, symbol=None, **kwargs):
       # Access multi-timeframe data
       symbol_data = market_data.get(symbol, {})
       primary_data = symbol_data.get(self.primary_timeframe)
       # ... rest of your logic
   ```

3. **Test with Multiple Timeframes**:
   ```json
   {
       "timeframes": ["1h", "4h", "1d"]
   }
   ```

## Conclusion

Multi-timeframe strategies provide powerful capabilities for sophisticated trading logic. By combining trend analysis from higher timeframes with precise entry signals from lower timeframes, strategies can achieve better risk-adjusted returns while maintaining robust market context awareness.

The architecture is designed to be flexible and performant, allowing strategies to use as many or as few timeframes as needed for their specific trading logic.
