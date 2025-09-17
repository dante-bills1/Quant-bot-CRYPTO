"""
Bayesian Optimization for Strategy Parameters

This module provides Bayesian optimization capabilities for trading strategy parameters,
using Gaussian Process optimization with Expected Improvement acquisition function.
Based on the reference VWAP swing strategy implementation.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import time
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

try:
    from skopt import gp_minimize
    from skopt.space import Integer, Real, Categorical
    from skopt.utils import use_named_args
    SKOPT_AVAILABLE = True
except ImportError:
    SKOPT_AVAILABLE = False
    print("Warning: scikit-optimize not available. Bayesian optimization disabled.")

from loguru import logger
from backtesting import Backtest

from .base_strategy import CryptoBacktestStrategy


class BayesianOptimizer:
    """
    Bayesian optimization for trading strategy parameters.

    Features:
    - Gaussian Process optimization
    - Expected Improvement acquisition function
    - Multi-parameter optimization
    - Smart initialization with random exploration
    - Performance tracking and logging
    """

    def __init__(self, strategy_class: type, data: pd.DataFrame):
        """
        Initialize Bayesian optimizer.

        Args:
            strategy_class: Strategy class to optimize
            data: Historical data for backtesting
        """
        if not SKOPT_AVAILABLE:
            raise ImportError("scikit-optimize is required for Bayesian optimization")

        self.strategy_class = strategy_class
        self.data = data
        self.strategy_name = strategy_class.__name__

        # Optimization settings
        self.n_calls = 75
        self.n_initial_points = 15
        self.random_state = 42

        # Results tracking
        self.optimization_results = []
        self.best_params = None
        self.best_score = -np.inf

        logger.info(f"BayesianOptimizer initialized for {self.strategy_name}")

    def define_parameter_space(self) -> List:
        """
        Define parameter space for optimization.

        Returns:
            List of parameter space definitions
        """
        if "VWAPSwingADX" in self.strategy_name:
            return self._vwap_swing_parameter_space()
        else:
            return self._default_parameter_space()

    def _vwap_swing_parameter_space(self) -> List:
        """Parameter space for VWAP Swing ADX strategy."""
        return [
            Integer(20, 70, name='swing_period'),           # swing_period
            Integer(15, 30, name='adx_threshold'),          # adx_threshold
            Real(1.0, 5.0, name='stop_loss_pct'),          # stop_loss_pct
            Real(3.0, 10.0, name='take_profit_pct'),       # take_profit_pct
            Real(0.05, 0.20, name='position_size_pct'),    # position_size_pct
            Categorical([True, False], name='use_adx_filter') # use_adx_filter
        ]

    def _default_parameter_space(self) -> List:
        """Default parameter space for unknown strategies."""
        return [
            Real(0.5, 5.0, name='stop_loss_pct'),
            Real(1.0, 15.0, name='take_profit_pct'),
            Real(0.01, 0.2, name='position_size_pct'),
        ]

    def objective_function(self, **params) -> float:
        """
        Objective function for optimization.

        Args:
            **params: Parameter values

        Returns:
            Negative return percentage (for minimization)
        """
        try:
            # Create strategy instance with parameters
            strategy = self.strategy_class()

            # Set parameters dynamically
            for param_name, param_value in params.items():
                if hasattr(strategy, param_name):
                    setattr(strategy, param_name, param_value)

            # Validate parameters
            if not strategy.validate_parameters():
                logger.warning(f"Invalid parameters: {params}")
                return 100  # High penalty

            # Run backtest
            bt = Backtest(self.data, strategy, cash=1000000, commission=0.001)

            try:
                result = bt.run()

                if result is None:
                    return 100  # High penalty for failed backtests

                return_pct = result.get('Return [%]', 0)

                # Penalty for strategies with very few trades
                trades = result.get('# Trades', 0)
                if trades < 5:
                    return 100  # High penalty

                # Log progress
                logger.debug(f"Parameters: {params} -> Return: {return_pct:.2f}%, Trades: {trades}")

                # Return negative for maximization (skopt minimizes)
                return -return_pct

            except Exception as e:
                logger.warning(f"Backtest failed for params {params}: {str(e)}")
                return 100  # High penalty

        except Exception as e:
            logger.error(f"Error in objective function: {str(e)}")
            return 100  # High penalty

    def optimize(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Run Bayesian optimization.

        Returns:
            Tuple of (best_params, optimization_info)
        """
        logger.info(f"Starting Bayesian optimization for {self.strategy_name}")
        logger.info(f"Parameter space: {len(self.define_parameter_space())} parameters")
        logger.info(f"Optimization calls: {self.n_calls} (initial: {self.n_initial_points})")

        start_time = time.time()

        try:
            # Define search space
            search_space = self.define_parameter_space()

            # Global variable for objective function
            global current_optimizer
            current_optimizer = self

            @use_named_args(search_space)
            def objective(**params):
                return current_optimizer.objective_function(**params)

            # Run optimization
            result = gp_minimize(
                func=objective,
                dimensions=search_space,
                n_calls=self.n_calls,
                n_initial_points=self.n_initial_points,
                acq_func='EI',        # Expected Improvement
                random_state=self.random_state,
                verbose=False
            )

            optimization_time = time.time() - start_time

            # Extract best parameters
            if "VWAPSwingADX" in self.strategy_name:
                best_params = {
                    'swing_period': result.x[0],
                    'adx_threshold': result.x[1],
                    'stop_loss_pct': result.x[2],
                    'take_profit_pct': result.x[3],
                    'position_size_pct': result.x[4],
                    'use_adx_filter': result.x[5]
                }
            else:
                best_params = {
                    'stop_loss_pct': result.x[0],
                    'take_profit_pct': result.x[1],
                    'position_size_pct': result.x[2],
                }

            # Store best result
            self.best_params = best_params
            self.best_score = -result.fun  # Convert back to positive return

            # Create optimization info
            optimization_info = {
                'strategy_name': self.strategy_name,
                'total_calls': self.n_calls,
                'best_return': self.best_score,
                'optimization_time': optimization_time,
                'convergence': result.func_vals[-1] if len(result.func_vals) > 0 else None,
                'parameter_names': [dim.name for dim in search_space],
                'search_space_size': len(search_space),
                'acquisition_function': 'EI',
                'optimizer': 'Gaussian Process'
            }

            logger.info("=".center(80, "="))
            logger.info("BAYESIAN OPTIMIZATION COMPLETED")
            logger.info("=".center(80, "="))
            logger.info(f"Strategy: {self.strategy_name}")
            logger.info(f"Best Return: {self.best_score:.2f}%")
            logger.info(f"Optimization Time: {optimization_time/60:.1f} minutes")
            logger.info("Best Parameters:")
            for param, value in best_params.items():
                logger.info(f"  {param}: {value}")
            logger.info("=".center(80, "="))

            return best_params, optimization_info

        except Exception as e:
            logger.error(f"Bayesian optimization failed: {str(e)}")
            return {}, {'error': str(e)}

    def validate_optimization_result(self, best_params: Dict[str, Any]) -> bool:
        """
        Validate optimization result by running final backtest.

        Args:
            best_params: Optimized parameters

        Returns:
            True if validation successful
        """
        try:
            logger.info("Validating optimization result...")

            # Create strategy with best parameters
            strategy = self.strategy_class()
            for param_name, param_value in best_params.items():
                if hasattr(strategy, param_name):
                    setattr(strategy, param_name, param_value)

            # Run validation backtest
            bt = Backtest(self.data, strategy, cash=1000000, commission=0.001)
            result = bt.run()

            if result is None:
                logger.error("Validation backtest failed")
                return False

            validated_return = result.get('Return [%]', 0)
            trades = result.get('# Trades', 0)

            logger.info(f"Validation Result: {validated_return:.2f}% return, {trades} trades")

            # Check if results are reasonable
            if abs(validated_return - self.best_score) > 5.0:  # Allow 5% variance
                logger.warning(f"Validation return differs from optimization: {validated_return:.2f}% vs {self.best_score:.2f}%")
                return False

            return True

        except Exception as e:
            logger.error(f"Validation failed: {str(e)}")
            return False

    def export_results(self, best_params: Dict[str, Any], optimization_info: Dict[str, Any],
                      filepath: Optional[Path] = None) -> str:
        """
        Export optimization results to file.

        Args:
            best_params: Optimized parameters
            optimization_info: Optimization metadata
            filepath: Optional export path

        Returns:
            Export file path
        """
        try:
            if filepath is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = Path(f"optimization_results_{self.strategy_name}_{timestamp}.json")

            results = {
                'strategy_name': self.strategy_name,
                'optimization_info': optimization_info,
                'best_parameters': best_params,
                'best_return': self.best_score,
                'export_time': datetime.now().isoformat(),
                'data_info': {
                    'data_points': len(self.data),
                    'date_range': f"{self.data.index[0]} to {self.data.index[-1]}"
                }
            }

            # Save to JSON
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w') as f:
                import json
                json.dump(results, f, indent=2, default=str)

            logger.info(f"Optimization results exported to: {filepath}")

            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to export results: {str(e)}")
            return ""


class MultiSymbolBayesianOptimizer:
    """
    Bayesian optimizer for multiple symbols/timeframes.
    """

    def __init__(self, strategy_class: type, symbols: List[str], timeframes: List[str],
                 start_date: datetime, end_date: datetime):
        """
        Initialize multi-symbol optimizer.

        Args:
            strategy_class: Strategy class to optimize
            symbols: List of symbols to optimize for
            timeframes: List of timeframes to optimize for
            start_date: Start date for data
            end_date: End date for data
        """
        self.strategy_class = strategy_class
        self.symbols = symbols
        self.timeframes = timeframes
        self.start_date = start_date
        self.end_date = end_date

        self.results = {}
        self.optimizers = {}

    def optimize_all(self) -> Dict[str, Any]:
        """
        Optimize strategy for all symbol/timeframe combinations.

        Returns:
            Dictionary with all optimization results
        """
        from .data_fetcher import CryptoDataFetcher

        data_fetcher = CryptoDataFetcher()
        total_combinations = len(self.symbols) * len(self.timeframes)
        completed = 0

        logger.info("=".center(80, "="))
        logger.info("MULTI-SYMBOL BAYESIAN OPTIMIZATION")
        logger.info("=".center(80, "="))
        logger.info(f"Strategy: {self.strategy_class.__name__}")
        logger.info(f"Total combinations: {total_combinations}")
        logger.info(f"Symbols: {', '.join(self.symbols)}")
        logger.info(f"Timeframes: {', '.join(self.timeframes)}")
        logger.info("=".center(80, "="))

        start_time = time.time()

        for symbol in self.symbols:
            for timeframe in self.timeframes:
                completed += 1
                progress = (completed / total_combinations) * 100

                logger.info("=".center(80, "="))
                logger.info("f OPTIMIZATION {completed}/{total_combinations} ({progress:.1f}%): {symbol} - {timeframe} ")
                logger.info("=".center(80, "="))

                try:
                    # Fetch data
                    data = data_fetcher.fetch_ohlcv(symbol, timeframe, self.start_date, self.end_date)

                    if data is None or len(data) < 200:
                        logger.warning(f"Insufficient data for {symbol} {timeframe}")
                        continue

                    # Create optimizer
                    optimizer = BayesianOptimizer(self.strategy_class, data)

                    # Run optimization
                    best_params, opt_info = optimizer.optimize()

                    if best_params:
                        key = f"{symbol}_{timeframe}"
                        self.results[key] = {
                            'symbol': symbol,
                            'timeframe': timeframe,
                            'best_params': best_params,
                            'optimization_info': opt_info,
                            'best_return': optimizer.best_score
                        }

                        # Export individual results
                        export_path = f"optimization_{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                        optimizer.export_results(best_params, opt_info, Path(export_path))

                except Exception as e:
                    logger.error(f"Optimization failed for {symbol} {timeframe}: {str(e)}")
                    continue

        total_time = time.time() - start_time

        # Generate summary
        self._generate_summary(total_time)

        return self.results

    def _generate_summary(self, total_time: float):
        """Generate optimization summary."""
        if not self.results:
            logger.warning("No successful optimizations completed")
            return

        logger.info("=".center(80, "="))
        logger.info("MULTI-SYMBOL OPTIMIZATION SUMMARY")
        logger.info("=".center(80, "="))
        logger.info(f"Total optimization time: {total_time/60:.1f} minutes")
        logger.info(f"Successful optimizations: {len(self.results)}")

        # Best performing combinations
        sorted_results = sorted(self.results.items(), key=lambda x: x[1]['best_return'], reverse=True)

        logger.info(f"\nTOP PERFORMING OPTIMIZATIONS:")
        for i, (key, result) in enumerate(sorted_results[:10]):
            logger.info(f"{i+1:2d} {key:<15} Return: {result['best_return']:6.2f}%")

        # Average performance
        returns = [r['best_return'] for r in self.results.values()]
        avg_return = np.mean(returns)
        best_return = max(returns)
        worst_return = min(returns)

        logger.info(f"\nPERFORMANCE STATISTICS:")
        logger.info(f"Average optimized return: {avg_return:.2f}%")
        logger.info(f"Best optimized return: {best_return:.2f}%")
        logger.info(f"Worst optimized return: {worst_return:.2f}%")

        logger.info("=".center(80, "="))


# Global variable for objective function
current_optimizer = None
