"""
Crypto Backtesting Framework

A comprehensive backtesting framework for crypto trading strategies,
featuring Bayesian optimization, advanced metrics, and VWAP swing strategies.
Based on the reference VWAP swing strategy implementation.
"""

from .data_fetcher import CryptoDataFetcher, create_data_fetcher
from .base_strategy import CryptoBacktestStrategy, strategy_registry, register_strategy
from .vwap_swing_strategy import VWAPSwingADXStrategy
from .volume_ma_backtest_adapter import VolumeMABacktestAdapter, create_adapted_volume_ma_strategy
from .bayesian_optimizer import BayesianOptimizer, MultiSymbolBayesianOptimizer
from .metrics_calculator import EnhancedMetricsCalculator
from .main import (
    run_single_backtest,
    run_bayesian_optimization,
    run_multi_symbol_optimization,
    demonstrate_framework
)

__version__ = "1.0.0"
__author__ = "Quant-Bot-Crypto Framework"
__description__ = "Advanced crypto backtesting framework with Bayesian optimization"

__all__ = [
    # Core classes
    "CryptoDataFetcher",
    "CryptoBacktestStrategy",
    "VWAPSwingADXStrategy",
    "VolumeMABacktestAdapter",
    "BayesianOptimizer",
    "MultiSymbolBayesianOptimizer",
    "EnhancedMetricsCalculator",

    # Utility functions
    "create_data_fetcher",
    "register_strategy",
    "create_adapted_volume_ma_strategy",

    # Main execution functions
    "run_single_backtest",
    "run_bayesian_optimization",
    "run_multi_symbol_optimization",
    "demonstrate_framework",

    # Registry
    "strategy_registry"
]