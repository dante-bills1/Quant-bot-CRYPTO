# Crypto Backtesting with Visualization

This document explains how to use the enhanced crypto backtesting framework with comprehensive visualization capabilities.

## 🎯 Features

- **Comprehensive Performance Reports**: Multi-panel visualizations showing equity curves, drawdown, trade analysis, and risk metrics
- **Individual Plots**: Separate high-quality plots for each metric
- **Interactive HTML Reports**: Web-based reports with embedded visualizations
- **Universal Strategy Support**: Works with any strategy that implements the SignalGenerator interface

## 📊 Generated Visualizations

### 1. Comprehensive Report (PNG)
- **Equity Curve**: Shows account value over time
- **Drawdown Chart**: Visualizes maximum drawdown periods
- **Trade Analysis**: Bar chart of individual trade P&L
- **Performance Metrics**: Key statistics dashboard
- **Risk Metrics**: P&L distribution histogram
- **Trade Distribution**: Pie chart of trade sides
- **Monthly Returns**: Heatmap of monthly performance

### 2. Individual Plots
- `equity_curve_[symbol]_[timestamp].png`
- `drawdown_[symbol]_[timestamp].png`
- `trade_analysis_[symbol]_[timestamp].png`

### 3. HTML Report
- Interactive web-based report
- Embedded performance charts
- Detailed metrics summary
- Trade breakdown

## 🚀 Usage

### Command Line Interface

```bash
# Run a backtest with visualization
python run_backtest.py --strategy VolumeMAOscillator --symbol BTC/USDT --timeframe 4h --days 30

# List available strategies
python run_backtest.py --list-strategies

# Run with custom parameters
python run_backtest.py --strategy VolumeMAOscillator --symbol ETH/USDT --timeframe 1h --days 60 --balance 50000
```

### Programmatic Usage

```python
import asyncio
from src.crypto_backtesting.universal_runner import UniversalBacktestRunner, BacktestConfig

async def run_backtest():
    runner = UniversalBacktestRunner()
    
    config = BacktestConfig(
        strategy_name="VolumeMAOscillator",
        symbol="BTC/USDT",
        timeframe="4h",
        days=30,
        initial_balance=10000
    )
    
    results = await runner.run_backtest(config)
    print(f"Final balance: ${results['final_balance']:,.2f}")

asyncio.run(run_backtest())
```

### Direct Visualization

```python
from src.crypto_backtesting.visualizer import create_visualizer

# Create visualizer
visualizer = create_visualizer("my_plots")

# Generate comprehensive report
report_path = visualizer.create_comprehensive_report(results, "BTC/USDT")

# Generate individual plots
plot_paths = visualizer.create_individual_plots(results, "BTC/USDT")

# Generate HTML report
html_path = visualizer.create_html_report(results, "BTC/USDT")
```

## 📁 Output Structure

The results are now organized in a hierarchical directory structure for easy navigation:

```
results/
├── [StrategyName]/
│   └── [Symbol]/
│       └── [Timeframe]/
│           └── [Days]d/
│               └── backtest_results_[timestamp].json
└── plots/
    └── [StrategyName]/
        └── [Symbol]/
            └── [Timeframe]/
                └── [Days]d/
                    ├── backtest_report_[Symbol]_[timestamp].png
                    ├── equity_curve_[Symbol]_[timestamp].png
                    ├── drawdown_[Symbol]_[timestamp].png
                    ├── trade_analysis_[Symbol]_[timestamp].png
                    └── backtest_report_[Symbol]_[timestamp].html
```

### Example Structure:
```
results/
├── VolumeMAOscillator/
│   └── BTC_USDT/
│       ├── 4h/
│       │   ├── 7d/
│       │   │   └── backtest_results_20250925_071935.json
│       │   └── 30d/
│       │       └── backtest_results_20250925_072000.json
│       └── 1h/
│           └── 7d/
│               └── backtest_results_20250925_072100.json
└── plots/
    └── VolumeMAOscillator/
        └── BTC_USDT/
            ├── 4h/
            │   ├── 7d/
            │   │   ├── backtest_report_BTC_USDT_20250925_071935.png
            │   │   ├── equity_curve_BTC_USDT_20250925_071935.png
            │   │   ├── drawdown_BTC_USDT_20250925_071935.png
            │   │   ├── trade_analysis_BTC_USDT_20250925_071935.png
            │   │   └── backtest_report_BTC_USDT_20250925_071935.html
            │   └── 30d/
            │       └── [similar files for 30d backtest]
            └── 1h/
                └── 7d/
                    └── [similar files for 1h backtest]
```

## 🎨 Visualization Components

### Equity Curve
- Shows account value progression over time
- Includes both equity and balance lines
- Properly formatted date axis

### Drawdown Chart
- Visualizes drawdown periods
- Shows maximum drawdown reached
- Red-filled area for easy identification

### Trade Analysis
- Bar chart of individual trade P&L
- Color-coded (green for profits, red for losses)
- Includes trade statistics overlay

### Performance Metrics
- Horizontal bar chart of key metrics
- Includes: Total Return, Sharpe Ratio, Max Drawdown, Win Rate, Profit Factor
- Value labels on each bar

### Risk Metrics
- P&L distribution histogram
- Shows break-even line and mean P&L
- Helps assess trade consistency

### Trade Distribution
- Pie chart showing long vs short trades
- Percentage breakdown of trade sides

### Monthly Returns Heatmap
- Calendar-style heatmap of monthly performance
- Color-coded (green for profits, red for losses)

## 🔧 Configuration Options

### BacktestConfig Parameters
- `strategy_name`: Name of the strategy to run
- `symbol`: Trading symbol (e.g., "BTC/USDT")
- `timeframe`: Timeframe (e.g., "1h", "4h", "1d")
- `days`: Number of days to test
- `initial_balance`: Starting balance
- `commission`: Commission rate
- `slippage`: Slippage rate
- `max_leverage`: Maximum leverage allowed

### Visualization Options
- `output_dir`: Directory to save plots
- `symbol`: Symbol for plot titles and filenames
- `timestamp`: Automatic timestamping for unique filenames

## 📋 Requirements

Make sure you have the required dependencies installed:

```bash
pip install matplotlib seaborn pandas numpy loguru
```

## 🎯 Example Output

After running a backtest, you'll see:

```
📊 Generating visualizations...
📈 Comprehensive report: results/plots/VolumeMAOscillator/backtest_report_BTC_USDT_20241225_143022.png
📊 Generated 3 individual plots
🌐 HTML report: results/plots/VolumeMAOscillator/backtest_report_BTC_USDT_20241225_143022.html
✅ Visualizations generated successfully
```

## 🔍 Troubleshooting

### Common Issues

1. **Missing matplotlib/seaborn**: Install with `pip install matplotlib seaborn`
2. **No trades generated**: Check strategy parameters and data availability
3. **Empty plots**: Ensure backtest results contain trade data
4. **Import errors**: Make sure you're running from the project root directory

### Debug Mode

Enable debug logging to see detailed information:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🎉 Benefits

- **Visual Performance Analysis**: Easily identify trends and patterns
- **Professional Reports**: Generate publication-ready charts
- **Interactive Analysis**: HTML reports for detailed exploration
- **Comprehensive Metrics**: All key performance indicators in one place
- **Easy Integration**: Works seamlessly with existing strategies
