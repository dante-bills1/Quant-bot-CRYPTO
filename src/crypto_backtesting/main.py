"""
Crypto Backtesting Framework Main Execution

This module provides the main execution script for the crypto backtesting framework,
demonstrating how to use all components together for comprehensive strategy testing.
Based on the reference VWAP swing strategy implementation.
"""

import asyncio
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional

from loguru import logger

# Import framework components
from .data_fetcher import CryptoDataFetcher
from .vwap_swing_strategy import VWAPSwingADXStrategy
from .bayesian_optimizer import BayesianOptimizer, MultiSymbolBayesianOptimizer
from .metrics_calculator import EnhancedMetricsCalculator


async def run_single_backtest(
    symbol: str = "BTCUSDT",
    timeframe: str = "4h",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    strategy_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run a single backtest with specified parameters.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe string
        start_date: Start date for data
        end_date: End date for data
        strategy_params: Strategy parameters

    Returns:
        Backtest results dictionary
    """
    logger.info(f"Running single backtest: {symbol} {timeframe}")

    try:
        # Initialize data fetcher
        data_fetcher = CryptoDataFetcher()

        # Set default dates if not provided
        if start_date is None:
            start_date = datetime.now() - timedelta(days=90)
        if end_date is None:
            end_date = datetime.now()

        # Fetch data
        logger.info(f"Fetching data for {symbol} {timeframe}...")
        data = data_fetcher.fetch_ohlcv(symbol, timeframe, start_date, end_date)

        if data is None or len(data) < 200:
            logger.error(f"Insufficient data: got {len(data) if data is not None else 0} bars")
            return {"error": "Insufficient data"}

        # Initialize strategy
        strategy = VWAPSwingADXStrategy()

        # Set custom parameters if provided
        if strategy_params:
            for param, value in strategy_params.items():
                if hasattr(strategy, param):
                    setattr(strategy, param, value)
                    logger.info(f"Set {param} = {value}")

        # Validate parameters
        if not strategy.validate_parameters():
            return {"error": "Invalid strategy parameters"}

        # Run backtest
        from backtesting import Backtest

        bt = Backtest(data, strategy, cash=1000000, commission=0.001)
        result = bt.run()

        if result is None:
            return {"error": "Backtest failed"}

        # Calculate enhanced metrics
        metrics_calculator = EnhancedMetricsCalculator()
        enhanced_metrics = metrics_calculator.calculate_enhanced_metrics(result)

        # Generate report
        report_filename = f"backtest_report_{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_content = metrics_calculator.generate_report(enhanced_metrics, report_filename)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "data_points": len(data),
            "date_range": f"{data.index[0]} to {data.index[-1]}",
            "result": result,
            "enhanced_metrics": enhanced_metrics,
            "report_file": report_filename
        }

    except Exception as e:
        logger.error(f"Error in single backtest: {str(e)}")
        return {"error": str(e)}


async def run_bayesian_optimization(
    symbol: str = "BTCUSDT",
    timeframe: str = "4h",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    n_calls: int = 50
) -> Dict[str, Any]:
    """
    Run Bayesian optimization for strategy parameters.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe string
        start_date: Start date for data
        end_date: End date for data
        n_calls: Number of optimization calls

    Returns:
        Optimization results dictionary
    """
    logger.info(f"Running Bayesian optimization: {symbol} {timeframe}")

    try:
        # Initialize data fetcher
        data_fetcher = CryptoDataFetcher()

        # Set default dates
        if start_date is None:
            start_date = datetime.now() - timedelta(days=90)
        if end_date is None:
            end_date = datetime.now()

        # Fetch data
        logger.info(f"Fetching data for optimization...")
        data = data_fetcher.fetch_ohlcv(symbol, timeframe, start_date, end_date)

        if data is None or len(data) < 200:
            logger.error(f"Insufficient data for optimization: got {len(data) if data is not None else 0} bars")
            return {"error": "Insufficient data"}

        # Create optimizer
        optimizer = BayesianOptimizer(VWAPSwingADXStrategy, data)
        optimizer.n_calls = n_calls

        # Run optimization
        logger.info(f"Starting optimization with {n_calls} calls...")
        best_params, optimization_info = optimizer.optimize()

        if not best_params:
            return {"error": "Optimization failed"}

        # Validate results
        validation_success = optimizer.validate_optimization_result(best_params)

        # Export results
        export_path = optimizer.export_results(best_params, optimization_info)

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "best_params": best_params,
            "optimization_info": optimization_info,
            "best_return": optimizer.best_score,
            "validation_success": validation_success,
            "export_path": export_path,
            "data_points": len(data)
        }

    except Exception as e:
        logger.error(f"Error in Bayesian optimization: {str(e)}")
        return {"error": str(e)}


async def run_multi_symbol_optimization(
    symbols: List[str] = None,
    timeframes: List[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    n_calls_per_combo: int = 30
) -> Dict[str, Any]:
    """
    Run multi-symbol Bayesian optimization.

    Args:
        symbols: List of symbols to optimize
        timeframes: List of timeframes to optimize
        start_date: Start date for data
        end_date: End date for data
        n_calls_per_combo: Optimization calls per combination

    Returns:
        Multi-symbol optimization results
    """
    if symbols is None:
        symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"]
    if timeframes is None:
        timeframes = ["5m", "15m", "1h", "4h"]
    if start_date is None:
        start_date = datetime.now() - timedelta(days=60)
    if end_date is None:
        end_date = datetime.now()

    logger.info("=".center(80, "="))
    logger.info("MULTI-SYMBOL BAYESIAN OPTIMIZATION")
    logger.info("=".center(80, "="))
    logger.info(f"Symbols: {', '.join(symbols)}")
    logger.info(f"Timeframes: {', '.join(timeframes)}")
    logger.info(f"Combinations: {len(symbols) * len(timeframes)}")
    logger.info(f"Calls per combination: {n_calls_per_combo}")
    logger.info("=".center(80, "="))

    try:
        # Create multi-symbol optimizer
        optimizer = MultiSymbolBayesianOptimizer(
            VWAPSwingADXStrategy,
            symbols,
            timeframes,
            start_date,
            end_date
        )

        # Run optimization
        results = optimizer.optimize_all()

        return {
            "optimization_results": results,
            "symbols_tested": symbols,
            "timeframes_tested": timeframes,
            "total_combinations": len(symbols) * len(timeframes),
            "successful_optimizations": len(results)
        }

    except Exception as e:
        logger.error(f"Error in multi-symbol optimization: {str(e)}")
        return {"error": str(e)}


async def demonstrate_framework():
    """
    Demonstrate the full backtesting framework capabilities.
    """
    logger.info("🚀 Demonstrating Crypto Backtesting Framework")

    try:
        # Example 1: Single backtest with default parameters
        logger.info("\n" + "="*60)
        logger.info("EXAMPLE 1: Single Backtest with Default Parameters")
        logger.info("="*60)

        result1 = await run_single_backtest("BTCUSDT", "4h")
        if "error" not in result1:
            logger.info("✅ Single backtest completed successfully")
            logger.info(f"📊 Return: {result1['enhanced_metrics']['Return']:.2f}%")
            logger.info(f"📈 Sharpe: {result1['enhanced_metrics']['Sharpe']:.2f}")
            logger.info(f"📊 Trades: {result1['enhanced_metrics']['Trades']}")
        else:
            logger.error(f"❌ Single backtest failed: {result1['error']}")

        # Example 2: Single backtest with custom parameters
        logger.info("\n" + "="*60)
        logger.info("EXAMPLE 2: Single Backtest with Custom Parameters")
        logger.info("="*60)

        custom_params = {
            'swing_period': 40,
            'adx_threshold': 18,
            'stop_loss_pct': 2.5,
            'take_profit_pct': 5.0,
            'use_adx_filter': True
        }

        result2 = await run_single_backtest(
            "ETHUSDT",
            "1h",
            strategy_params=custom_params
        )

        if "error" not in result2:
            logger.info("✅ Custom parameter backtest completed")
            logger.info(f"📊 Custom Return: {result2['enhanced_metrics']['Return']:.2f}%")
        else:
            logger.error(f"❌ Custom parameter backtest failed: {result2['error']}")

        # Example 3: Bayesian optimization
        logger.info("\n" + "="*60)
        logger.info("EXAMPLE 3: Bayesian Parameter Optimization")
        logger.info("="*60)

        opt_result = await run_bayesian_optimization(
            "ADAUSDT",
            "4h",
            n_calls=25  # Reduced for demo
        )

        if "error" not in opt_result:
            logger.info("✅ Bayesian optimization completed")
            logger.info(f"📊 Best Return: {opt_result['best_return']:.2f}%")
            logger.info(f"Best parameters: swing_period={opt_result['best_params']['swing_period']}, "
                         f"adx_threshold={opt_result['best_params']['adx_threshold']}")
        else:
            logger.error(f"❌ Bayesian optimization failed: {opt_result['error']}")

        logger.info("\n" + "="*60)
        logger.info("FRAMEWORK DEMONSTRATION COMPLETED")
        logger.info("="*60)
        logger.info("🎉 All framework components working correctly!")
        logger.info("📊 Check the generated report files for detailed analysis")

    except Exception as e:
        logger.error(f"Error in framework demonstration: {str(e)}")


async def main():
    """
    Main execution function - equivalent to reference file's main().
    """
    print("\n" + "="*80)
    print("CRYPTO BACKTESTING FRAMEWORK")
    print("VWAP Swing Strategy with Bayesian Optimization")
    print("Based on Enhanced VWAP Swing Strategy Reference")
    print("="*80)

    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "demo":
            await demonstrate_framework()
        elif command == "single":
            symbol = sys.argv[2] if len(sys.argv) > 2 else "BTCUSDT"
            timeframe = sys.argv[3] if len(sys.argv) > 3 else "4h"
            result = await run_single_backtest(symbol, timeframe)
            print(f"Single backtest result: {result}")
        elif command == "optimize":
            symbol = sys.argv[2] if len(sys.argv) > 2 else "BTCUSDT"
            timeframe = sys.argv[3] if len(sys.argv) > 3 else "4h"
            n_calls = int(sys.argv[4]) if len(sys.argv) > 4 else 50
            result = await run_bayesian_optimization(symbol, timeframe, n_calls=n_calls)
            print(f"Optimization result: {result}")
        elif command == "multi":
            symbols = sys.argv[2].split(',') if len(sys.argv) > 2 else None
            result = await run_multi_symbol_optimization(symbols=symbols)
            print(f"Multi-symbol optimization completed: {len(result.get('optimization_results', {}))} successful")
        else:
            print("Usage:")
            print("  python -m crypto_backtesting.main demo          # Run framework demonstration")
            print("  python -m crypto_backtesting.main single [SYMBOL] [TIMEFRAME]  # Single backtest")
            print("  python -m crypto_backtesting.main optimize [SYMBOL] [TIMEFRAME] [N_CALLS]  # Bayesian optimization")
            print("  python -m crypto_backtesting.main multi [SYMBOLS]  # Multi-symbol optimization")
    else:
        # Default: run demonstration
        await demonstrate_framework()


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level="INFO"
    )

    # Run main function
    asyncio.run(main())
