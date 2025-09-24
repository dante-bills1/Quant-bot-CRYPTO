"""
Crypto Backtest Runner

This script is the main entry point for running crypto backtests. It combines data
downloading and backtesting into a single, seamless process for crypto trading.

Usage:
    python crypto_backtest_runner.py --strategy <StrategyClassName> --symbol <SYMBOL> --timeframe <TIMEFRAME> --days <DAYS>

Example:
    python crypto_backtest_runner.py --strategy VolumeMAOscillator --symbol BTC/USDT:USDT --timeframe 1m --days 30
"""

import argparse
import asyncio
from pathlib import Path
import importlib.util
import re
from typing import Type
from datetime import datetime, timedelta

from loguru import logger

# Framework imports
from src.crypto_backtesting.engine import CryptoBacktester
from src.crypto_backtesting.data_loader import load_crypto_historical_data
from src.trading_bot import SignalGenerator
from src.utils.crypto_handler import CryptoHandler

async def _download_data_if_needed(symbol: str, timeframe: str, days: int) -> Path:
    """
    Checks if data exists, and if not, downloads it from crypto exchange.
    Returns the path to the data file.
    """
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    file_path = data_dir / f"{symbol.replace('/', '_')}_{timeframe}_{days}d.csv"

    if file_path.exists():
        logger.info(f"Data file found locally: {file_path}")
        return file_path

    logger.warning(f"Data file not found. Attempting to download from crypto exchange...")
    logger.info(f"For fully repeatable tests, it's best to use pre-downloaded data.")

    crypto_handler = CryptoHandler()
    if not await crypto_handler.initialize():
        raise ConnectionError("Failed to initialize crypto handler. Cannot download data.")

    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    try:
        # Download historical data
        data = await crypto_handler.get_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        if data is None or len(data) == 0:
            raise ValueError("No data downloaded from crypto exchange")
        
        # Save data to CSV
        import pandas as pd
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df.to_csv(file_path, index=False)
        
        logger.info(f"Data downloaded and saved to: {file_path}")
        return file_path
        
    except Exception as e:
        logger.error(f"Failed to download data: {str(e)}")
        raise
    finally:
        # CryptoHandler doesn't have a close method, just set to None
        crypto_handler.exchange = None

def _load_strategy_class(strategy_name: str) -> Type[SignalGenerator]:
    """
    Dynamically loads a strategy class from the strategies directory.
    
    Args:
        strategy_name: Name of the strategy class
        
    Returns:
        Strategy class
    """
    strategies_dir = Path("src/strategy")
    
    # Look for strategy files
    strategy_files = list(strategies_dir.glob("*.py"))
    
    for strategy_file in strategy_files:
        if strategy_file.name == "__init__.py":
            continue
            
        try:
            # Load module
            spec = importlib.util.spec_from_file_location(
                strategy_file.stem, 
                strategy_file
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for strategy class
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, SignalGenerator) and 
                    attr_name == strategy_name):
                    logger.info(f"Found strategy class: {attr_name}")
                    return attr
                    
        except Exception as e:
            logger.warning(f"Error loading {strategy_file}: {str(e)}")
            continue
    
    raise ImportError(f"Strategy class '{strategy_name}' not found in strategies directory")

async def run_backtest(
    strategy_class: Type[SignalGenerator],
    symbol: str,
    timeframe: str,
    days: int,
    data_file: Path
):
    """
    Run the backtest with the given parameters.
    
    Args:
        strategy_class: Strategy class to test
        symbol: Trading symbol
        timeframe: Timeframe
        days: Number of days to test
        data_file: Path to data file
    """
    try:
        logger.info(f"Starting backtest for {strategy_class.__name__}")
        logger.info(f"Symbol: {symbol}, Timeframe: {timeframe}, Days: {days}")
        
        # Load historical data
        logger.info("Loading historical data...")
        data = load_crypto_historical_data(data_file)
        
        if data is None or len(data) == 0:
            raise ValueError("No data loaded for backtesting")
        
        logger.info(f"Loaded {len(data)} data points")
        
        # Initialize strategy
        logger.info("Initializing strategy...")
        strategy = strategy_class(
            symbol=symbol,
            timeframe=timeframe
        )
        
        # Initialize backtester
        logger.info("Initializing backtester...")
        backtester = CryptoBacktester(
            strategy=strategy,
            initial_balance=10000,  # $10,000 starting balance
            commission=0.001,  # 0.1% commission
            slippage=0.0005  # 0.05% slippage
        )
        
        # Run backtest
        logger.info("Running backtest...")
        results = await backtester.run(data)
        
        # Display results
        logger.info("Backtest completed!")
        logger.info(f"Final Balance: ${results['final_balance']:,.2f}")
        logger.info(f"Total Return: {results['total_return']:.2%}")
        logger.info(f"Max Drawdown: {results['max_drawdown']:.2%}")
        logger.info(f"Total Trades: {results['total_trades']}")
        logger.info(f"Win Rate: {results['win_rate']:.2%}")
        logger.info(f"Profit Factor: {results['profit_factor']:.2f}")
        logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        
        # Save results
        results_file = data_file.parent / f"results_{strategy_class.__name__}_{symbol.replace('/', '_')}_{timeframe}_{days}d.json"
        import json
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"Results saved to: {results_file}")
        
    except Exception as e:
        logger.error(f"Backtest failed: {str(e)}")
        raise

async def main():
    """Main entry point for the crypto backtest runner."""
    parser = argparse.ArgumentParser(description="Run crypto backtests")
    parser.add_argument("--strategy", required=True, help="Strategy class name")
    parser.add_argument("--symbol", required=True, help="Trading symbol (e.g., BTC/USDT:USDT)")
    parser.add_argument("--timeframe", required=True, help="Timeframe (e.g., 1m, 5m, 1h, 1d)")
    parser.add_argument("--days", type=int, default=30, help="Number of days to test (default: 30)")
    parser.add_argument("--force-download", action="store_true", help="Force download new data")
    
    args = parser.parse_args()
    
    try:
        # Load strategy class
        strategy_class = _load_strategy_class(args.strategy)
        
        # Download data if needed
        if args.force_download:
            data_file = await _download_data_if_needed(args.symbol, args.timeframe, args.days)
        else:
            data_file = Path("data") / f"{args.symbol.replace('/', '_')}_{args.timeframe}_{args.days}d.csv"
            if not data_file.exists():
                data_file = await _download_data_if_needed(args.symbol, args.timeframe, args.days)
        
        # Run backtest
        await run_backtest(
            strategy_class=strategy_class,
            symbol=args.symbol,
            timeframe=args.timeframe,
            days=args.days,
            data_file=data_file
        )
        
    except Exception as e:
        logger.error(f"Backtest runner failed: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))
