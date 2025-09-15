"""
Test cases for Volume MA Oscillator strategy
"""
import unittest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from src.strategy.volume_ma_oscillator import VolumeMAOscillator
from src.crypto_handler import CryptoHandler


class TestVolumeMAOscillator(unittest.TestCase):
    """Test the Volume MA Oscillator strategy"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.crypto_handler = Mock(spec=CryptoHandler)
        self.risk_manager = Mock()
        
        self.strategy = VolumeMAOscillator(
            crypto_handler=self.crypto_handler,
            risk_manager=self.risk_manager,
            symbol="BTC/USDT:USDT",
            timeframe="1m"
        )
    
    def test_strategy_initialization(self):
        """Test strategy initialization"""
        self.assertEqual(self.strategy.symbol, "BTC/USDT:USDT")
        self.assertEqual(self.strategy.timeframe, "1m")
        self.assertEqual(self.strategy.primary_timeframe, "1m")
        self.assertIsNotNone(self.strategy.indicators)
        self.assertIsNotNone(self.strategy.ma_calculator)
    
    def test_strategy_parameters(self):
        """Test strategy parameters"""
        # Test default parameters
        self.assertEqual(self.strategy.ma_period, 20)
        self.assertEqual(self.strategy.ma_type, "DEMA")
        self.assertEqual(self.strategy.volume_period, 20)
        self.assertEqual(self.strategy.upper_band_multiplier, 2.0)
        self.assertEqual(self.strategy.lower_band_multiplier, 2.0)
        self.assertEqual(self.strategy.smoothing_period, 3)
        self.assertEqual(self.strategy.strategy_mode, "Trend")
    
    def test_ma_calculator_initialization(self):
        """Test MA calculator initialization"""
        self.assertIsNotNone(self.strategy.ma_calculator)
        self.assertEqual(self.strategy.ma_calculator.ma_type, "DEMA")
        self.assertEqual(self.strategy.ma_calculator.period, 20)
    
    def test_indicators_initialization(self):
        """Test indicators initialization"""
        indicators = self.strategy.indicators
        
        # Check that all required indicators are initialized
        self.assertIn("volume_ma", indicators)
        self.assertIn("upper_band", indicators)
        self.assertIn("lower_band", indicators)
        self.assertIn("oscillator", indicators)
        self.assertIn("smoothed_oscillator", indicators)
        self.assertIn("rsi", indicators)
        self.assertIn("adx", indicators)
        self.assertIn("trend_filter", indicators)
    
    def test_calculate_indicators(self):
        """Test indicator calculations"""
        # Create sample data
        data = {
            "timestamp": [1640995200000, 1640995260000, 1640995320000],
            "open": [47000, 47500, 48000],
            "high": [48000, 48500, 49000],
            "low": [46000, 47000, 47500],
            "close": [47500, 48000, 48500],
            "volume": [1000, 1200, 1100]
        }
        
        # Mock the crypto handler
        self.crypto_handler.get_historical_data.return_value = [
            [1640995200000, 47000, 48000, 46000, 47500, 1000],
            [1640995260000, 47500, 48500, 47000, 48000, 1200],
            [1640995320000, 48000, 49000, 47500, 48500, 1100]
        ]
        
        # Calculate indicators
        result = self.strategy.calculate_indicators(data)
        
        # Check that indicators were calculated
        self.assertIsNotNone(result)
        self.assertIn("volume_ma", result)
        self.assertIn("upper_band", result)
        self.assertIn("lower_band", result)
        self.assertIn("oscillator", result)
        self.assertIn("smoothed_oscillator", result)
    
    def test_generate_signal_trend_mode(self):
        """Test signal generation in trend mode"""
        # Set strategy to trend mode
        self.strategy.strategy_mode = "Trend"
        
        # Create sample data with trend
        data = {
            "timestamp": [1640995200000, 1640995260000, 1640995320000],
            "open": [47000, 47500, 48000],
            "high": [48000, 48500, 49000],
            "low": [46000, 47000, 47500],
            "close": [47500, 48000, 48500],
            "volume": [1000, 1200, 1100]
        }
        
        # Mock indicators with trend signal
        indicators = {
            "volume_ma": [1000, 1100, 1200],
            "upper_band": [1200, 1300, 1400],
            "lower_band": [800, 900, 1000],
            "oscillator": [0.1, 0.2, 0.3],
            "smoothed_oscillator": [0.15, 0.25, 0.35],
            "rsi": [60, 65, 70],
            "adx": [25, 30, 35],
            "trend_filter": [1, 1, 1]
        }
        
        # Mock the crypto handler
        self.crypto_handler.get_historical_data.return_value = [
            [1640995200000, 47000, 48000, 46000, 47500, 1000],
            [1640995260000, 47500, 48500, 47000, 48000, 1200],
            [1640995320000, 48000, 49000, 47500, 48500, 1100]
        ]
        
        # Generate signal
        signal = self.strategy.generate_signal(data)
        
        # Check signal structure
        self.assertIsNotNone(signal)
        self.assertIn("action", signal)
        self.assertIn("confidence", signal)
        self.assertIn("reason", signal)
        self.assertIn("timestamp", signal)
    
    def test_generate_signal_reversion_mode(self):
        """Test signal generation in reversion mode"""
        # Set strategy to reversion mode
        self.strategy.strategy_mode = "Reversion"
        
        # Create sample data with reversion signal
        data = {
            "timestamp": [1640995200000, 1640995260000, 1640995320000],
            "open": [47000, 47500, 48000],
            "high": [48000, 48500, 49000],
            "low": [46000, 47000, 47500],
            "close": [47500, 48000, 48500],
            "volume": [1000, 1200, 1100]
        }
        
        # Mock indicators with reversion signal
        indicators = {
            "volume_ma": [1000, 1100, 1200],
            "upper_band": [1200, 1300, 1400],
            "lower_band": [800, 900, 1000],
            "oscillator": [0.8, 0.9, 1.0],  # High oscillator (overbought)
            "smoothed_oscillator": [0.85, 0.95, 1.05],
            "rsi": [80, 85, 90],  # High RSI (overbought)
            "adx": [25, 30, 35],
            "trend_filter": [1, 1, 1]
        }
        
        # Mock the crypto handler
        self.crypto_handler.get_historical_data.return_value = [
            [1640995200000, 47000, 48000, 46000, 47500, 1000],
            [1640995260000, 47500, 48500, 47000, 48000, 1200],
            [1640995320000, 48000, 49000, 47500, 48500, 1100]
        ]
        
        # Generate signal
        signal = self.strategy.generate_signal(data)
        
        # Check signal structure
        self.assertIsNotNone(signal)
        self.assertIn("action", signal)
        self.assertIn("confidence", signal)
        self.assertIn("reason", signal)
        self.assertIn("timestamp", signal)
    
    def test_risk_management_integration(self):
        """Test risk management integration"""
        # Mock risk manager
        self.risk_manager.calculate_position_size.return_value = 0.001
        self.risk_manager.calculate_stop_loss.return_value = 46000
        self.risk_manager.calculate_take_profit.return_value = 49000
        
        # Test that risk manager is called
        data = {
            "timestamp": [1640995200000],
            "open": [47000],
            "high": [48000],
            "low": [46000],
            "close": [47500],
            "volume": [1000]
        }
        
        signal = self.strategy.generate_signal(data)
        
        # Risk manager should be called for position sizing
        self.risk_manager.calculate_position_size.assert_called()
    
    def test_error_handling(self):
        """Test error handling in strategy"""
        # Test with invalid data
        invalid_data = {
            "timestamp": [],
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": []
        }
        
        # Should handle empty data gracefully
        signal = self.strategy.generate_signal(invalid_data)
        self.assertIsNotNone(signal)
        self.assertEqual(signal["action"], "hold")
    
    def test_strategy_modes(self):
        """Test different strategy modes"""
        # Test Trend mode
        self.strategy.strategy_mode = "Trend"
        self.assertEqual(self.strategy.strategy_mode, "Trend")
        
        # Test Reversion mode
        self.strategy.strategy_mode = "Reversion"
        self.assertEqual(self.strategy.strategy_mode, "Reversion")
        
        # Test Hybrid mode
        self.strategy.strategy_mode = "Hybrid"
        self.assertEqual(self.strategy.strategy_mode, "Hybrid")
    
    def test_parameter_validation(self):
        """Test parameter validation"""
        # Test valid parameters
        valid_params = {
            "ma_period": 50,
            "ma_type": "EMA",
            "volume_period": 30,
            "upper_band_multiplier": 3.0,
            "lower_band_multiplier": 3.0,
            "smoothing_period": 5,
            "strategy_mode": "Hybrid"
        }
        
        strategy = VolumeMAOscillator(
            crypto_handler=self.crypto_handler,
            risk_manager=self.risk_manager,
            symbol="BTC/USDT:USDT",
            timeframe="1m",
            **valid_params
        )
        
        self.assertEqual(strategy.ma_period, 50)
        self.assertEqual(strategy.ma_type, "EMA")
        self.assertEqual(strategy.volume_period, 30)
        self.assertEqual(strategy.upper_band_multiplier, 3.0)
        self.assertEqual(strategy.lower_band_multiplier, 3.0)
        self.assertEqual(strategy.smoothing_period, 5)
        self.assertEqual(strategy.strategy_mode, "Hybrid")


if __name__ == "__main__":
    unittest.main()
