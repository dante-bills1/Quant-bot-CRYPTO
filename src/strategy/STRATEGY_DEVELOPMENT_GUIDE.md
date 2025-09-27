# Strategy Development Guide

This guide shows you how to create custom trading strategies that work seamlessly with both the live trading engine and the backtesting framework.

## Quick Start

1. **Copy the template**: Start with `src/strategy/strategy_template.py`
2. **Customize**: Modify the strategy logic to match your trading ideas
3. **Test**: Use the backtesting framework to validate your strategy
4. **Deploy**: Use in live trading once backtesting shows promise

## Strategy Architecture

### Core Components

Every strategy must extend `SignalGenerator` and implement these methods:

```python
class MyStrategy(SignalGenerator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Configuration here

    async def initialize(self) -> bool:
        # Initialization logic
        return True

    async def generate_signals(self, market_data, symbol, **kwargs) -> List[Dict]:
        # Signal generation logic
        return []
```

### Required Properties

```python
# Basic info
self.name = "My Strategy"
self.version = "1.0.0"

# Timeframe configuration (REQUIRED)
self.primary_timeframe = "1h"          # Main analysis timeframe
self.secondary_timeframes = []         # Additional timeframes

# Data requirements
self.min_candles = 100                 # Minimum candles needed
self.lookback = 200                    # Lookback for indicators
```

## Single Timeframe Strategies

Simple strategies that analyze one timeframe:

```python
class SingleTimeframeStrategy(SignalGenerator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "Single TF Strategy"
        self.primary_timeframe = "1h"  # Only timeframe needed
        self.secondary_timeframes = []

        # Your parameters
        self.ema_period = kwargs.get('ema_period', 20)

    async def generate_signals(self, market_data, symbol, **kwargs):
        # Get data for primary timeframe only
        symbol_data = market_data.get(symbol, {})
        df = symbol_data.get(self.primary_timeframe)

        if df is None or len(df) < self.min_candles:
            return []

        # Calculate indicators
        indicators = self._calculate_indicators(df)

        # Generate signals
        return self._generate_signals(df, indicators, symbol)
```

## Multi-Timeframe Strategies

Advanced strategies using multiple timeframes:

```python
class MultiTimeframeStrategy(SignalGenerator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "Multi-TF Strategy"
        self.primary_timeframe = "15m"     # Entry timeframe
        self.secondary_timeframes = ["1h"] # Trend timeframe

    async def generate_signals(self, market_data, symbol, **kwargs):
        symbol_data = market_data.get(symbol, {})

        # Get data for all timeframes
        trend_data = symbol_data.get("1h")  # Higher TF
        entry_data = symbol_data.get("15m") # Lower TF

        if trend_data is None or entry_data is None:
            return []

        # Multi-timeframe analysis
        trend = self._analyze_trend(trend_data)
        signals = self._generate_entries(entry_data, trend)

        return signals
```

## Data Format Handling

The strategy must handle different data formats:

### Live Trading Format
```python
# Format: {symbol: {timeframe: DataFrame}}
market_data = {
    "BTC/USDT": {
        "1h": DataFrame(...),
        "4h": DataFrame(...)
    }
}
```

### Backtesting Format
```python
# Single row format
current_data = {
    'timestamp': 1640995200000,
    'open': 50000,
    'high': 51000,
    'low': 49500,
    'close': 50500,
    'volume': 1000
}

# Or DataFrame format
df = DataFrame with OHLCV columns
```

### Universal Data Handler

```python
async def generate_signals(self, market_data, symbol, **kwargs):
    # Handle backtesting single row
    if isinstance(market_data, dict) and 'close' in market_data:
        return self._handle_single_row(market_data, symbol)

    # Handle live trading format
    elif isinstance(market_data, dict) and symbol in market_data:
        return self._handle_multi_timeframe(market_data, symbol)

    # Handle DataFrame format
    elif isinstance(market_data, pd.DataFrame):
        return self._handle_dataframe(market_data, symbol)

    return []
```

## Indicator Calculation

### Basic Indicators

```python
def _calculate_indicators(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
    close = df['close'].astype(float)

    # Moving averages
    sma = close.rolling(window=20).mean()
    ema = close.ewm(span=20).mean()

    # RSI
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    return {
        'sma': sma,
        'ema': ema,
        'rsi': rsi
    }
```

### Advanced Indicators

```python
def _calculate_advanced_indicators(self, df: pd.DataFrame) -> Dict[str, pd.Series]:
    high = df['high']
    low = df['low']
    close = df['close']
    volume = df['volume']

    # ATR (Average True Range)
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=14).mean()

    # MACD
    ema_fast = close.ewm(span=12).mean()
    ema_slow = close.ewm(span=26).mean()
    macd = ema_fast - ema_slow
    signal = macd.ewm(span=9).mean()

    # Bollinger Bands
    sma = close.rolling(window=20).mean()
    std = close.rolling(window=20).std()
    upper_band = sma + (std * 2)
    lower_band = sma - (std * 2)

    return {
        'atr': atr,
        'macd': macd,
        'macd_signal': signal,
        'bb_upper': upper_band,
        'bb_lower': lower_band
    }
```

## Signal Generation

### Basic Signal Logic

```python
def _generate_signals(self, df, indicators, symbol):
    signals = []

    # Get current and previous values
    current = -1
    previous = -2

    ema = indicators['ema']
    rsi = indicators['rsi']

    # Long signal
    if (ema.iloc[current] > ema.iloc[previous] and
        rsi.iloc[current] < 30):

        signal = self._create_signal(df, "buy", symbol)
        if signal:
            signals.append(signal)

    # Short signal
    if (ema.iloc[current] < ema.iloc[previous] and
        rsi.iloc[current] > 70):

        signal = self._create_signal(df, "sell", symbol)
        if signal:
            signals.append(signal)

    return signals
```

### Signal Dictionary Format

```python
def _create_signal(self, df, direction, symbol):
    current_price = float(df["close"].iloc[-1])

    return {
        "symbol": symbol,
        "timeframe": self.primary_timeframe,
        "action": direction,          # "buy" or "sell"
        "signal_type": direction,     # Same as action
        "entry_price": current_price,
        "stop_loss": stop_loss_price,
        "take_profit": take_profit_price,
        "confidence": 0.8,           # 0.0 to 1.0
        "reason": "Your signal reason",
        "timestamp": timestamp,
        "strategy": self.name,
        "strategy_version": self.version
    }
```

## Configuration Examples

### Basic Strategy Config

```json
{
    "signal_generators": [
        {
            "name": "MyStrategy",
            "primary_timeframe": "1h",
            "ema_period": 20,
            "rsi_period": 14,
            "stop_loss_pct": 0.02,
            "take_profit_pct": 0.04
        }
    ],
    "symbols": ["BTC/USDT", "ETH/USDT"],
    "timeframes": ["1h"]
}
```

### Multi-Timeframe Config

```json
{
    "signal_generators": [
        {
            "name": "MultiTimeframeStrategy",
            "primary_timeframe": "15m",
            "secondary_timeframes": ["1h", "4h"],
            "trend_ema_period": 50,
            "entry_fast_period": 12,
            "entry_slow_period": 26
        }
    ],
    "symbols": ["BTC/USDT"],
    "timeframes": ["15m", "1h", "4h"]
}
```

## Backtesting Your Strategy

### 1. Basic Backtest

```python
from src.crypto_backtesting.universal_runner import UniversalBacktestRunner
from src.strategy.my_strategy import MyStrategy

# Create strategy
strategy = MyStrategy(primary_timeframe="1h")

# Run backtest
runner = UniversalBacktestRunner()
results = await runner.run_backtest({
    'strategy': strategy,
    'symbol': 'BTC/USDT',
    'timeframe': '1h',
    'days': 30
})
```

### 2. Multi-Timeframe Backtest

```python
# Multi-timeframe strategy automatically gets data for all required timeframes
results = await runner.run_backtest({
    'strategy': MyMultiTimeframeStrategy(),
    'symbol': 'BTC/USDT',
    'timeframe': '15m',  # Primary timeframe
    'days': 30
})
```

### 3. Backtest with Custom Parameters

```python
results = await runner.run_backtest({
    'strategy': MyStrategy(
        primary_timeframe="4h",
        ema_period=25,
        rsi_period=21
    ),
    'symbol': 'ETH/USDT',
    'timeframe': '4h',
    'days': 60
})
```

## Testing Your Strategy

### 1. Unit Testing Indicators

```python
import pytest
import pandas as pd

def test_my_indicators():
    # Create test data
    data = pd.DataFrame({
        'close': [100, 101, 102, 103, 104],
        'high': [101, 102, 103, 104, 105],
        'low': [99, 100, 101, 102, 103],
        'volume': [1000, 1100, 1200, 1300, 1400]
    })

    strategy = MyStrategy()
    indicators = strategy._calculate_indicators(data)

    # Assert indicator calculations
    assert 'ema' in indicators
    assert 'rsi' in indicators
    assert len(indicators['ema']) == len(data)
```

### 2. Integration Testing

```python
async def test_strategy_signals():
    # Create test market data
    market_data = {
        "BTC/USDT": {
            "1h": create_test_dataframe()
        }
    }

    strategy = MyStrategy()
    signals = await strategy.generate_signals(market_data, "BTC/USDT")

    # Assert signal format
    assert isinstance(signals, list)
    if signals:
        signal = signals[0]
        assert "action" in signal
        assert "entry_price" in signal
        assert "stop_loss" in signal
```

## Debugging Strategies

### Enable Debug Logging

```python
import logging
logging.getLogger('src.strategy.my_strategy').setLevel(logging.DEBUG)
```

### Common Issues

1. **Missing Timeframe Data**
   ```python
   # Check if timeframe exists
   if self.primary_timeframe not in symbol_data:
       logger.warning(f"Missing {self.primary_timeframe} data")
       return []
   ```

2. **Insufficient Data**
   ```python
   if len(df) < self.min_candles:
       logger.debug(f"Need {self.min_candles}, got {len(df)}")
       return []
   ```

3. **NaN Values**
   ```python
   # Clean data before calculations
   df_clean = df.dropna()
   if df_clean.empty:
       return []
   ```

## Best Practices

### 1. Data Validation
```python
def _validate_data(self, df: pd.DataFrame) -> bool:
    """Validate input data."""
    if df is None or df.empty:
        return False

    required_cols = ['open', 'high', 'low', 'close', 'volume']
    return all(col in df.columns for col in required_cols)
```

### 2. Error Handling
```python
async def generate_signals(self, market_data, symbol, **kwargs):
    try:
        # Your logic here
        return signals
    except Exception as e:
        logger.error(f"Strategy error: {e}")
        return []
```

### 3. Performance Optimization
```python
# Cache expensive calculations
@property
def expensive_calculation(self):
    if not hasattr(self, '_cache'):
        self._cache = self._calculate_expensive_thing()
    return self._cache
```

### 4. Parameter Validation
```python
def __init__(self, **kwargs):
    super().__init__(**kwargs)

    # Validate parameters
    if self.ema_period <= 0:
        raise ValueError("EMA period must be positive")

    if self.stop_loss_pct >= 1:
        raise ValueError("Stop loss percentage must be < 1.0")
```

## Example Implementations

See `src/strategy/strategy_template.py` for complete examples:

- `BasicStrategyTemplate`: Minimal working strategy
- `SingleTimeframeExample`: Single timeframe strategy
- `MultiTimeframeExample`: Multi-timeframe strategy
- `BacktestCompatibleStrategy`: Backtesting-optimized strategy

## Next Steps

1. **Start Simple**: Begin with `BasicStrategyTemplate`
2. **Add Indicators**: Implement your technical indicators
3. **Test Thoroughly**: Use backtesting to validate
4. **Optimize**: Improve performance and accuracy
5. **Deploy**: Use in live trading with caution

## Support

- Template: `src/strategy/strategy_template.py`
- Examples: `src/strategy/multi_timeframe_trend_following.py`
- Documentation: `MULTI_TIMEFRAME_STRATEGIES.md`
- Backtesting: `src/crypto_backtesting/universal_runner.py`

Happy strategy development! 🚀
