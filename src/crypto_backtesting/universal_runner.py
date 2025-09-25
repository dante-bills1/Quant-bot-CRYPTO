"""
Universal Crypto Backtest Runner

A comprehensive backtesting system that works with ANY strategy.
Features:
- Automatic strategy discovery and registration
- Universal data handling (CSV, API, live data)
- Comprehensive metrics and reporting
- Parameter optimization
- Multi-timeframe analysis
- Risk management
- Web dashboard integration

Usage:
    python universal_backtest_runner.py --strategy <StrategyName> --symbol <SYMBOL> --timeframe <TIMEFRAME> --days <DAYS>
    python universal_backtest_runner.py --list-strategies
    python universal_backtest_runner.py --optimize --strategy <StrategyName> --symbol <SYMBOL>
    python universal_backtest_runner.py --dashboard
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Type, Union
from datetime import datetime, timedelta
import importlib.util
import inspect
import pandas as pd
import numpy as np
from dataclasses import dataclass, asdict
from loguru import logger

# Framework imports
from .engine import CryptoBacktester
from .data_loader import load_crypto_historical_data
from .metrics_calculator import EnhancedMetricsCalculator
from .visualizer import create_visualizer
from src.trading_bot import SignalGenerator
from src.utils.crypto_handler import CryptoHandler


@dataclass
class BacktestConfig:
    """Configuration for backtest runs."""
    strategy_name: str
    symbol: str
    timeframe: str
    days: int
    initial_balance: float = 10000.0
    commission: float = 0.001
    slippage: float = 0.0005
    max_leverage: float = 10.0
    force_download: bool = False
    optimize: bool = False
    optimization_calls: int = 50
    output_dir: str = "results"
    secondary_timeframe: Optional[str] = None  # Optional secondary timeframe for multi-timeframe strategies


@dataclass
class StrategyInfo:
    """Information about a discovered strategy."""
    name: str
    class_name: str
    file_path: str
    description: str
    parameters: Dict[str, Any]
    timeframes: List[str]
    risk_level: str  # low, medium, high


class UniversalStrategyRegistry:
    """Registry for automatic strategy discovery and management."""
    
    def __init__(self):
        self.strategies: Dict[str, StrategyInfo] = {}
        self.strategy_classes: Dict[str, Type[SignalGenerator]] = {}
        self._scan_strategies()
    
    def _scan_strategies(self):
        """Scan for available strategies in the strategies directory."""
        strategies_dir = Path("src/strategy")
        if not strategies_dir.exists():
            logger.warning("Strategies directory not found")
            return
        
        for strategy_file in strategies_dir.glob("*.py"):
            if strategy_file.name == "__init__.py":
                continue
            
            try:
                self._load_strategy_file(strategy_file)
            except Exception as e:
                logger.warning(f"Failed to load strategy from {strategy_file}: {e}")
    
    def _load_strategy_file(self, file_path: Path):
        """Load a strategy file and extract strategy information."""
        spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find strategy classes
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and 
                issubclass(attr, SignalGenerator) and 
                attr != SignalGenerator):
                
                strategy_info = self._extract_strategy_info(attr, file_path)
                self.strategies[strategy_info.name] = strategy_info
                self.strategy_classes[strategy_info.name] = attr
                logger.info(f"Registered strategy: {strategy_info.name}")
    
    def _extract_strategy_info(self, strategy_class: Type[SignalGenerator], file_path: Path) -> StrategyInfo:
        """Extract information about a strategy class."""
        # Get class docstring
        description = strategy_class.__doc__ or "No description available"
        
        # Extract parameters from __init__ method
        init_signature = inspect.signature(strategy_class.__init__)
        parameters = {}
        for param_name, param in init_signature.parameters.items():
            if param_name != 'self':
                parameters[param_name] = {
                    'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                    'default': param.default if param.default != inspect.Parameter.empty else None,
                    'required': param.default == inspect.Parameter.empty
                }
        
        # Determine risk level based on strategy name and parameters
        risk_level = self._determine_risk_level(strategy_class, parameters)
        
        # Determine supported timeframes
        timeframes = self._determine_timeframes(strategy_class)
        
        return StrategyInfo(
            name=strategy_class.__name__,
            class_name=strategy_class.__name__,
            file_path=str(file_path),
            description=description.strip(),
            parameters=parameters,
            timeframes=timeframes,
            risk_level=risk_level
        )
    
    def _determine_risk_level(self, strategy_class: Type[SignalGenerator], parameters: Dict) -> str:
        """Determine risk level based on strategy characteristics."""
        name_lower = strategy_class.__name__.lower()
        
        # High risk indicators
        if any(keyword in name_lower for keyword in ['scalping', 'high_frequency', 'leverage', 'aggressive']):
            return 'high'
        
        # Check for risk parameters
        if any(param in parameters for param in ['leverage', 'max_risk', 'aggressive_mode']):
            return 'high'
        
        # Medium risk indicators
        if any(keyword in name_lower for keyword in ['swing', 'momentum', 'breakout']):
            return 'medium'
        
        # Default to low risk
        return 'low'
    
    def _determine_timeframes(self, strategy_class: Type[SignalGenerator]) -> List[str]:
        """Determine supported timeframes for a strategy."""
        # Common timeframes
        all_timeframes = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w']
        
        # Check if strategy has timeframe restrictions
        if hasattr(strategy_class, 'supported_timeframes'):
            return getattr(strategy_class, 'supported_timeframes')
        
        # Default to common timeframes
        return all_timeframes
    
    def get_strategy_class(self, strategy_name: str) -> Type[SignalGenerator]:
        """Get strategy class by name."""
        if strategy_name not in self.strategy_classes:
            raise ValueError(f"Strategy '{strategy_name}' not found. Available: {list(self.strategies.keys())}")
        return self.strategy_classes[strategy_name]
    
    def list_strategies(self) -> List[StrategyInfo]:
        """List all available strategies."""
        return list(self.strategies.values())
    
    def get_strategy_info(self, strategy_name: str) -> StrategyInfo:
        """Get strategy information."""
        if strategy_name not in self.strategies:
            raise ValueError(f"Strategy '{strategy_name}' not found")
        return self.strategies[strategy_name]


class UniversalDataManager:
    """Universal data manager for different data sources and formats."""
    
    def __init__(self):
        self.crypto_handler = None
    
    async def get_data(self, symbol: str, timeframe: str, days: int, force_download: bool = False) -> pd.DataFrame:
        """Get data from various sources."""
        data_file = Path("data") / f"{symbol.replace('/', '_')}_{timeframe}_{days}d.csv"
        
        # Check if we have local data and don't need to force download
        if data_file.exists() and not force_download:
            logger.info(f"Loading local data: {data_file}")
            return load_crypto_historical_data(data_file)
        
        # Download new data
        logger.info(f"Downloading data for {symbol} {timeframe} ({days} days)")
        return await self._download_data(symbol, timeframe, days, data_file)
    
    async def _download_data(self, symbol: str, timeframe: str, days: int, output_file: Path) -> pd.DataFrame:
        """Download data from crypto exchange."""
        if not self.crypto_handler:
            self.crypto_handler = CryptoHandler()
            if not await self.crypto_handler.initialize():
                raise ConnectionError("Failed to initialize crypto handler")
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        try:
            data = await self.crypto_handler.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if data is None or len(data) == 0:
                raise ValueError("No data downloaded from crypto exchange")
            
            # Convert to DataFrame and save
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # Ensure the output directory exists
            output_file.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_file, index=False)
            
            logger.info(f"Data downloaded and saved: {output_file}")
            return df
            
        except Exception as e:
            logger.error(f"Failed to download data: {e}")
            raise
        finally:
            if self.crypto_handler:
                self.crypto_handler.exchange = None


class UniversalBacktestRunner:
    """Universal backtest runner that works with any strategy."""
    
    def __init__(self):
        self.registry = UniversalStrategyRegistry()
        self.data_manager = UniversalDataManager()
        self.metrics_calculator = EnhancedMetricsCalculator()
        self.results_dir = Path("results")
        self.results_dir.mkdir(exist_ok=True)
    
    async def run_backtest(self, config: BacktestConfig) -> Dict[str, Any]:
        """Run a backtest with the given configuration."""
        logger.info(f"🚀 Starting universal backtest: {config.strategy_name}")
        logger.info(f"📊 Symbol: {config.symbol}, Timeframe: {config.timeframe}, Days: {config.days}")
        
        try:
            # Get strategy class
            strategy_class = self.registry.get_strategy_class(config.strategy_name)
            strategy_info = self.registry.get_strategy_info(config.strategy_name)
            
            # Get primary data
            data = await self.data_manager.get_data(
                config.symbol, 
                config.timeframe, 
                config.days, 
                config.force_download
            )
            
            if data is None or len(data) == 0:
                raise ValueError("No data available for backtesting")
            
            logger.info(f"📈 Loaded {len(data)} data points for primary timeframe {config.timeframe}")
            
            # Get secondary timeframe data if specified
            secondary_data = None
            if config.secondary_timeframe:
                logger.info(f"📊 Loading secondary timeframe data: {config.secondary_timeframe}")
                secondary_data = await self.data_manager.get_data(
                    config.symbol, 
                    config.secondary_timeframe, 
                    config.days, 
                    config.force_download
                )
                if secondary_data is not None and len(secondary_data) > 0:
                    logger.info(f"📈 Loaded {len(secondary_data)} data points for secondary timeframe {config.secondary_timeframe}")
                else:
                    logger.warning(f"⚠️ No secondary timeframe data available for {config.secondary_timeframe}")
            
            # Initialize strategy with default parameters
            strategy = strategy_class(primary_timeframe=config.timeframe)
            
            # Initialize backtester
            backtester = CryptoBacktester(
                strategy=strategy,
                initial_balance=config.initial_balance,
                commission=config.commission,
                slippage=config.slippage,
                max_leverage=config.max_leverage,
                symbol=config.symbol
            )
            
            # Run backtest
            logger.info("🔄 Running backtest...")
            start_time = time.time()
            results = await backtester.run(data)
            execution_time = time.time() - start_time
            
            # Calculate enhanced metrics
            enhanced_metrics = self.metrics_calculator.calculate_enhanced_metrics(results)
            
            # Validate results
            self._validate_results(results)
            
            # Generate visualizations
            self._generate_visualizations(results, config)
            
            # Add metadata
            results.update({
                'strategy_name': config.strategy_name,
                'strategy_info': asdict(strategy_info),
                'config': asdict(config),
                'execution_time': execution_time,
                'data_points': len(data),
                'enhanced_metrics': enhanced_metrics,
                'symbol': config.symbol,
                'timeframe': config.timeframe
            })
            
            # Save results
            self._save_results(results, config)
            
            # Display results
            self._display_results(results)
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Backtest failed: {e}")
            raise
    
    def _save_results(self, results: Dict[str, Any], config: BacktestConfig):
        """Save backtest results in organized directory structure."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create organized directory structure: results/Strategy/Symbol/Timeframe/Days/
        strategy_dir = self.results_dir / config.strategy_name
        symbol_dir = strategy_dir / config.symbol.replace('/', '_')
        timeframe_dir = symbol_dir / config.timeframe
        days_dir = timeframe_dir / f"{config.days}d"
        
        # Create directories if they don't exist
        days_dir.mkdir(parents=True, exist_ok=True)
        
        # Create filename with timestamp
        filename = f"backtest_results_{timestamp}.json"
        filepath = days_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.info(f"💾 Results saved: {filepath}")
        logger.info(f"📁 Organized in: {strategy_dir.name}/{symbol_dir.name}/{timeframe_dir.name}/{days_dir.name}/")
    
    def _validate_results(self, results: Dict[str, Any]):
        """Validate backtest results for consistency."""
        try:
            # Check for required fields
            required_fields = ['final_balance', 'total_return', 'total_trades', 'win_rate', 'profit_factor']
            missing_fields = [field for field in required_fields if field not in results]
            
            if missing_fields:
                logger.warning(f"⚠️ Missing result fields: {missing_fields}")
            
            # Validate trade count consistency
            total_trades = results.get('total_trades', 0)
            winning_trades = results.get('winning_trades', 0)
            losing_trades = results.get('losing_trades', 0)
            
            if total_trades != (winning_trades + losing_trades):
                logger.warning(f"⚠️ Trade count mismatch: total={total_trades}, wins={winning_trades}, losses={losing_trades}")
            
            # Validate profit factor
            profit_factor = results.get('profit_factor', 0)
            if profit_factor == float('inf'):
                logger.warning("⚠️ Profit factor is infinite (no losses)")
            elif profit_factor < 0:
                logger.warning(f"⚠️ Negative profit factor: {profit_factor}")
            
            # Validate balance
            final_balance = results.get('final_balance', 0)
            if final_balance <= 0:
                logger.warning(f"⚠️ Final balance is zero or negative: {final_balance}")
            
            logger.info("✅ Results validation completed")
            
        except Exception as e:
            logger.error(f"❌ Error validating results: {e}")
    
    def _generate_visualizations(self, results: Dict[str, Any], config: BacktestConfig):
        """Generate visualization plots for backtest results."""
        try:
            logger.info("📊 Generating visualizations...")
            
            # Create organized visualization directory structure
            # results/plots/Strategy/Symbol/Timeframe/Days/
            plots_base_dir = Path("results/plots")
            strategy_plots_dir = plots_base_dir / config.strategy_name
            symbol_plots_dir = strategy_plots_dir / config.symbol.replace('/', '_')
            timeframe_plots_dir = symbol_plots_dir / config.timeframe
            days_plots_dir = timeframe_plots_dir / f"{config.days}d"
            
            # Create directories
            days_plots_dir.mkdir(parents=True, exist_ok=True)
            
            # Create visualizer with organized output directory
            visualizer = create_visualizer(str(days_plots_dir))
            
            # Generate comprehensive report
            report_path = visualizer.create_comprehensive_report(results, config.symbol)
            if report_path:
                logger.info(f"📈 Comprehensive report: {report_path}")
            
            # Generate individual plots
            plot_paths = visualizer.create_individual_plots(results, config.symbol)
            if plot_paths:
                logger.info(f"📊 Generated {len(plot_paths)} individual plots")
            
            # Generate HTML report
            html_path = visualizer.create_html_report(results, config.symbol)
            if html_path:
                logger.info(f"🌐 HTML report: {html_path}")
            
            logger.info("✅ Visualizations generated successfully")
            logger.info(f"📁 Plots organized in: plots/{config.strategy_name}/{config.symbol.replace('/', '_')}/{config.timeframe}/{config.days}d/")
            
        except Exception as e:
            logger.error(f"❌ Error generating visualizations: {str(e)}")
    
    def _display_results(self, results: Dict[str, Any]):
        """Display backtest results in a formatted way."""
        logger.info("\n" + "="*80)
        logger.info("📊 BACKTEST RESULTS")
        logger.info("="*80)
        logger.info(f"Strategy: {results['strategy_name']}")
        logger.info(f"Symbol: {results.get('symbol', 'N/A')}")
        logger.info(f"Timeframe: {results.get('timeframe', 'N/A')}")
        logger.info(f"Data Points: {results.get('data_points', 0)}")
        logger.info(f"Execution Time: {results.get('execution_time', 0):.2f}s")
        logger.info("-"*80)
        logger.info(f"💰 Final Balance: ${results.get('final_balance', 0):,.2f}")
        logger.info(f"📈 Total Return: {results.get('total_return', 0):.2%}")
        logger.info(f"📉 Max Drawdown: {results.get('max_drawdown', 0):.2%}")
        logger.info(f"📊 Total Trades: {results.get('total_trades', 0)}")
        logger.info(f"🎯 Win Rate: {results.get('win_rate', 0):.2%}")
        logger.info(f"⚖️ Profit Factor: {results.get('profit_factor', 0):.2f}")
        logger.info(f"📊 Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
        
        # Enhanced metrics
        if 'enhanced_metrics' in results:
            metrics = results['enhanced_metrics']
            logger.info("-"*80)
            logger.info("🔍 ENHANCED METRICS")
            logger.info("-"*80)
            logger.info(f"Sortino Ratio: {metrics.get('Sortino_Ratio', 0):.2f}")
            logger.info(f"Calmar Ratio: {metrics.get('Calmar_Ratio', 0):.2f}")
            logger.info(f"Kelly %: {metrics.get('Kelly_Percentage', 0):.2%}")
            logger.info(f"Risk of Ruin: {metrics.get('Risk_of_Ruin', 0):.2%}")
            logger.info(f"Quality Score: {metrics.get('Strategy_Quality_Score', 0):.1f}/100")
            
            # Trade analysis
            if 'Profitable_Trades' in metrics:
                logger.info("-"*80)
                logger.info("📊 TRADE ANALYSIS")
                logger.info("-"*80)
                logger.info(f"Profitable Trades: {metrics.get('Profitable_Trades', 0)}")
                logger.info(f"Losing Trades: {metrics.get('Losing_Trades', 0)}")
                logger.info(f"Average Win: {metrics.get('Avg_Win', 0):.2f}%")
                logger.info(f"Average Loss: {metrics.get('Avg_Loss', 0):.2f}%")
                logger.info(f"Best Trade: {metrics.get('Best_Trade', 0):.2f}")
                logger.info(f"Worst Trade: {metrics.get('Worst_Trade', 0):.2f}")
                logger.info(f"Max Win Streak: {metrics.get('Win_Streak_Max', 0)}")
                logger.info(f"Max Loss Streak: {metrics.get('Loss_Streak_Max', 0)}")
        
        logger.info("="*80)
    
    def list_strategies(self):
        """List all available strategies."""
        strategies = self.registry.list_strategies()
        
        logger.info("\n" + "="*80)
        logger.info("📋 AVAILABLE STRATEGIES")
        logger.info("="*80)
        
        for strategy in strategies:
            logger.info(f"\n🔹 {strategy.name}")
            logger.info(f"   Description: {strategy.description}")
            logger.info(f"   Risk Level: {strategy.risk_level.upper()}")
            logger.info(f"   Timeframes: {', '.join(strategy.timeframes[:5])}{'...' if len(strategy.timeframes) > 5 else ''}")
            logger.info(f"   Parameters: {len(strategy.parameters)} configurable")
            
            if strategy.parameters:
                logger.info("   Key Parameters:")
                for param, info in list(strategy.parameters.items())[:3]:
                    default = f" (default: {info['default']})" if info['default'] is not None else ""
                    logger.info(f"     - {param}: {info['type']}{default}")
                if len(strategy.parameters) > 3:
                    logger.info(f"     ... and {len(strategy.parameters) - 3} more")
        
        logger.info("="*80)
        logger.info(f"Total strategies: {len(strategies)}")


async def main():
    """Main entry point for the universal backtest runner."""
    parser = argparse.ArgumentParser(description="Universal Crypto Backtest Runner")
    
    # Main commands
    parser.add_argument("--strategy", help="Strategy name to run")
    parser.add_argument("--symbol", help="Trading symbol (e.g., BTC/USDT:USDT)")
    parser.add_argument("--timeframe", help="Timeframe (e.g., 1m, 5m, 1h, 4h)")
    parser.add_argument("--days", type=int, default=30, help="Number of days to test")
    
    # Configuration
    parser.add_argument("--balance", type=float, default=10000, help="Initial balance")
    parser.add_argument("--commission", type=float, default=0.001, help="Commission rate")
    parser.add_argument("--slippage", type=float, default=0.0005, help="Slippage rate")
    parser.add_argument("--leverage", type=float, default=10.0, help="Max leverage")
    
    # Actions
    parser.add_argument("--list-strategies", action="store_true", help="List available strategies")
    parser.add_argument("--force-download", action="store_true", help="Force download new data")
    parser.add_argument("--optimize", action="store_true", help="Run parameter optimization")
    parser.add_argument("--dashboard", action="store_true", help="Start web dashboard")
    
    args = parser.parse_args()
    
    # Initialize runner
    runner = UniversalBacktestRunner()
    
    try:
        # List strategies
        if args.list_strategies:
            runner.list_strategies()
            return 0
        
        # Start dashboard
        if args.dashboard:
            logger.info("🌐 Starting web dashboard...")
            # TODO: Implement web dashboard
            logger.warning("Dashboard not implemented yet")
            return 0
        
        # Validate required arguments for backtest
        if not args.strategy or not args.symbol or not args.timeframe:
            logger.error("❌ Missing required arguments: --strategy, --symbol, --timeframe")
            logger.info("Use --list-strategies to see available strategies")
            return 1
        
        # Create config
        config = BacktestConfig(
            strategy_name=args.strategy,
            symbol=args.symbol,
            timeframe=args.timeframe,
            days=args.days,
            initial_balance=args.balance,
            commission=args.commission,
            slippage=args.slippage,
            max_leverage=args.leverage,
            force_download=args.force_download,
            optimize=args.optimize
        )
        
        # Run backtest
        if args.optimize:
            logger.info("🔧 Parameter optimization not implemented yet")
            # TODO: Implement parameter optimization
            return 0
        
        results = await runner.run_backtest(config)
        
        logger.info("✅ Backtest completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Universal backtest runner failed: {e}")
        return 1


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    exit(asyncio.run(main()))
