"""
Crypto Backtesting Framework

A core backtesting framework for crypto trading strategies,
featuring advanced metrics, data management, and strategy execution.
"""

from .data_fetcher import CryptoDataFetcher, create_data_fetcher
from .data_loader import load_crypto_historical_data, validate_data_quality
from .base_strategy import CryptoBacktestStrategy, strategy_registry, register_strategy
from .metrics_calculator import EnhancedMetricsCalculator
from .visualizer import BacktestVisualizer, create_visualizer
from .universal_runner import UniversalBacktestRunner, BacktestConfig, UniversalStrategyRegistry

__version__ = "1.0.0"
__author__ = "Quant-Bot-Crypto Framework"
__description__ = "Core crypto backtesting framework"

__all__ = [
    # Core classes
    "CryptoDataFetcher",
    "CryptoBacktestStrategy", 
    "EnhancedMetricsCalculator",
    "BacktestVisualizer",
    "UniversalBacktestRunner",
    "UniversalStrategyRegistry",

    # Configuration
    "BacktestConfig",

    # Utility functions
    "create_data_fetcher",
    "load_crypto_historical_data",
    "validate_data_quality",
    "register_strategy",
    "create_visualizer",

    # Registry
    "strategy_registry"
]