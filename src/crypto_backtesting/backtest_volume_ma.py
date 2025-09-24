"""
Backtest Volume MA Oscillator Strategy

This script demonstrates how to backtest the Volume MA Oscillator strategy
using the crypto backtesting framework.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add the parent directory to the path to import existing strategies
sys.path.append(str(Path(__file__).parent.parent))

from crypto_backtesting import run_single_backtest, run_bayesian_optimization
from src.strategy.volume_ma_oscillator import VolumeMAOscillator


async def backtest_volume_ma_oscillator():
    """
    Backtest the Volume MA Oscillator strategy with different configurations.
    """

    print("🚀 Backtesting Volume MA Oscillator Strategy")
    print("=" * 60)

    # Test different configurations
    configs = [
        {
            "name": "Default Config",
            "symbol": "BTCUSDT",
            "timeframe": "4h",
            "params": {}  # Use default parameters
        },
        {
            "name": "Optimized Trend Config",
            "symbol": "ETHUSDT",
            "timeframe": "1h",
            "params": {
                "strategy_mode": "Trend",
                "ma_length": 100,
                "band_length": 15,
                "stop_loss_pct": 2.0,
                "take_profit_pct": 4.0
            }
        },
        {
            "name": "Conservative Config",
            "symbol": "ADAUSDT",
            "timeframe": "4h",
            "params": {
                "strategy_mode": "Hybrid",
                "ma_length": 60,
                "band_length": 8,
                "stop_loss_pct": 1.5,
                "take_profit_pct": 3.0,
                "max_risk_percent": 1.5
            }
        }
    ]

    results = []

    for config in configs:
        print(f"\n📊 Testing: {config['name']}")
        print("-" * 40)
        print(f"Symbol: {config['symbol']}")
        print(f"Timeframe: {config['timeframe']}")
        print(f"Parameters: {config['params']}")

        try:
            # Run backtest
            result = await run_single_backtest(
                config['symbol'],
                config['timeframe'],
                strategy_params=config['params']
            )

            if "error" not in result:
                print("✅ Backtest completed successfully!")
                print(f"📈 Return: {result['enhanced_metrics']['Return']:.2f}%")
                print(f"📊 Sharpe: {result['enhanced_metrics']['Sharpe']:.2f}")
                print(f"📊 Trades: {result['enhanced_metrics']['Trades']}")
                print(f"🎯 Win Rate: {result['enhanced_metrics']['Win_Rate']:.1f}%")

                results.append({
                    "config": config,
                    "result": result
                })
            else:
                print(f"❌ Backtest failed: {result['error']}")

        except Exception as e:
            print(f"❌ Error running backtest: {str(e)}")

    # Compare results
    if results:
        print(f"\n🏆 RESULTS COMPARISON")
        print("=" * 60)

        for i, result_data in enumerate(results, 1):
            config = result_data['config']
            metrics = result_data['result']['enhanced_metrics']

            print(f"{i}. {config['name']}")
            print(f"   Symbol: {config['symbol']} | Timeframe: {config['timeframe']}")
            print(f"   Return: {metrics['Return']:.2f}% | Sharpe: {metrics['Sharpe']:.2f}")
            print(f"   Trades: {metrics['Trades']} | Win Rate: {metrics['Win_Rate']:.1f}%")
            print()

    print("🎉 Volume MA Oscillator backtesting completed!")


async def optimize_volume_ma_strategy():
    """
    Run Bayesian optimization on the Volume MA Oscillator strategy.
    """

    print("🎯 Bayesian Optimization for Volume MA Oscillator")
    print("=" * 60)

    try:
        # Run optimization
        opt_result = await run_bayesian_optimization(
            "BTCUSDT",
            "4h",
            n_calls=25  # Reduced for demo, increase for better results
        )

        if "error" not in opt_result:
            print("✅ Optimization completed!")
            print(f"📊 Best Return: {opt_result['best_return']:.2f}%")
            print("Best parameters:")
            for param, value in opt_result['best_params'].items():
                print(f"  {param}: {value}")

            print(f"\nOptimization completed! Results saved to JSON file.")        
        else:
            print(f"❌ Optimization failed: {opt_result['error']}")

    except Exception as e:
        print(f"❌ Error during optimization: {str(e)}")


async def main():
    """
    Main function - choose what to run.
    """
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "backtest":
            await backtest_volume_ma_oscillator()
        elif command == "optimize":
            await optimize_volume_ma_strategy()
        else:
            print("Usage:")
            print("  python backtest_volume_ma.py backtest    # Run multiple backtests")
            print("  python backtest_volume_ma.py optimize    # Run Bayesian optimization")
    else:
        # Default: run backtests
        await backtest_volume_ma_oscillator()


if __name__ == "__main__":
    asyncio.run(main())
