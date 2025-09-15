"""
Pytest configuration and fixtures
"""
import pytest
import os
import sys
from unittest.mock import Mock, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

@pytest.fixture
def mock_crypto_handler():
    """Mock crypto handler for testing"""
    handler = Mock()
    handler.connect.return_value = True
    handler.get_symbol_info.return_value = {
        "symbol": "BTC/USDT:USDT",
        "base": "BTC",
        "quote": "USDT",
        "precision": {"price": 2, "amount": 6}
    }
    handler.get_historical_data.return_value = [
        [1640995200000, 47000, 48000, 46000, 47500, 1000],
        [1640995260000, 47500, 48500, 47000, 48000, 1200],
        [1640995320000, 48000, 49000, 47500, 48500, 1100]
    ]
    handler.get_positions.return_value = []
    handler.get_balance.return_value = {
        "USDT": {"free": 1000.0, "used": 0.0, "total": 1000.0}
    }
    return handler

@pytest.fixture
def mock_risk_manager():
    """Mock risk manager for testing"""
    manager = Mock()
    manager.calculate_position_size.return_value = 0.001
    manager.calculate_stop_loss.return_value = 46000
    manager.calculate_take_profit.return_value = 49000
    return manager

@pytest.fixture
def sample_crypto_data():
    """Sample crypto data for testing"""
    return {
        "timestamp": [1640995200000, 1640995260000, 1640995320000],
        "open": [47000, 47500, 48000],
        "high": [48000, 48500, 49000],
        "low": [46000, 47000, 47500],
        "close": [47500, 48000, 48500],
        "volume": [1000, 1200, 1100]
    }

@pytest.fixture
def crypto_config():
    """Crypto configuration for testing"""
    return {
        "exchange": "bybit",
        "api_key": "test_key",
        "api_secret": "test_secret",
        "sandbox": True,
        "timeout": 10,
        "retry_attempts": 3,
        "rate_limit": True
    }

@pytest.fixture
def trading_config():
    """Trading configuration for testing"""
    return {
        "account_type": "demo",
        "magic_number": 1235,
        "symbols": ["BTC/USDT:USDT", "ETH/USDT:USDT"],
        "signal_generators": ["VolumeMAOscillator"],
        "risk_management": {
            "max_risk_per_trade": 0.02,
            "max_daily_risk": 0.1,
            "stop_loss_atr_multiplier": 2.0,
            "take_profit_atr_multiplier": 3.0
        }
    }
