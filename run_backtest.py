"""
Command-line interface for running crypto backtests with visualization.

This script provides an easy way to run backtests using the universal runner
with full visualization support.
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent / "src"))

from src.crypto_backtesting.universal_runner import UniversalBacktestRunner, BacktestConfig


async def main():
    """Main entry point for the backtest runner."""
    parser = argparse.ArgumentParser(description="Crypto Backtest Runner with Visualization")
    
    # Required arguments
    parser.add_argument("--strategy", required=True, help="Strategy name to run")
    parser.add_argument("--symbol", required=True, help="Trading symbol (e.g., BTC/USDT)")
    parser.add_argument("--timeframe", required=True, help="Timeframe (e.g., 1h, 4h, 1d)")
    
    # Optional arguments
    parser.add_argument("--days", type=int, default=30, help="Number of days to test (default: 30)")
    parser.add_argument("--balance", type=float, default=10000, help="Initial balance (default: 10000)")
    parser.add_argument("--commission", type=float, default=0.001, help="Commission rate (default: 0.001)")
    parser.add_argument("--force-download", action="store_true", help="Force download new data")
    
    # Visualization options
    parser.add_argument("--no-plots", action="store_true", help="Skip generating plots")
    parser.add_argument("--plots-only", action="store_true", help="Generate only plots (no backtest)")
    
    # List strategies
    parser.add_argument("--list-strategies", action="store_true", help="List available strategies")
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = UniversalBacktestRunner()
    
    try:
        # List strategies
        if args.list_strategies:
            runner.list_strategies()
            return 0
        
        # Create config
        config = BacktestConfig(
            strategy_name=args.strategy,
            symbol=args.symbol,
            timeframe=args.timeframe,
            days=args.days,
            initial_balance=args.balance,
            commission=args.commission,
            force_download=args.force_download
        )
        
        # Run backtest
        print(f"🚀 Starting backtest: {config.strategy_name} on {config.symbol} {config.timeframe}")
        print(f"📊 Testing {config.days} days with ${config.initial_balance:,.2f} initial balance")
        
        results = await runner.run_backtest(config)
        
        print("\n✅ Backtest completed successfully!")
        print(f"📈 Final balance: ${results.get('final_balance', 0):,.2f}")
        print(f"📊 Total return: {results.get('total_return', 0):.2%}")
        print(f"🎯 Win rate: {results.get('win_rate', 0):.1%}")
        
        # Show visualization info
        if not args.no_plots:
            print("\n📊 Visualizations generated:")
            print("   - Comprehensive performance report (PNG)")
            print("   - Individual plots (equity curve, drawdown, trade analysis)")
            print("   - Interactive HTML report")
            print(f"   - Organized in: results/plots/{config.strategy_name}/{config.symbol.replace('/', '_')}/{config.timeframe}/{config.days}d/")
        
        return 0
        
    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
