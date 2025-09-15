"""
Integration tests for the complete crypto trading system
"""
import unittest
import time
from unittest.mock import Mock, patch, MagicMock
from src.crypto_handler import CryptoHandler
from src.crypto_data_manager import CryptoDataManager
from src.strategy.volume_ma_oscillator import VolumeMAOscillator
from src.trading_bot import TradingBot
from config.config import CRYPTO_CONFIG, TRADING_CONFIG


class TestCryptoTradingIntegration(unittest.TestCase):
    """Test the complete crypto trading system integration"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = CRYPTO_CONFIG.copy()
        self.trading_config = TRADING_CONFIG.copy()
        
        # Mock the crypto handler
        self.crypto_handler = Mock(spec=CryptoHandler)
        self.crypto_handler.connect.return_value = True
        self.crypto_handler.get_symbol_info.return_value = {
            "symbol": "BTC/USDT:USDT",
            "base": "BTC",
            "quote": "USDT",
            "precision": {"price": 2, "amount": 6}
        }
        
        # Mock historical data
        self.mock_historical_data = [
            [1640995200000, 47000, 48000, 46000, 47500, 1000],
            [1640995260000, 47500, 48500, 47000, 48000, 1200],
            [1640995320000, 48000, 49000, 47500, 48500, 1100],
            [1640995380000, 48500, 49500, 48000, 49000, 1300],
            [1640995440000, 49000, 50000, 48500, 49500, 1400]
        ]
        
        self.crypto_handler.get_historical_data.return_value = self.mock_historical_data
        
        # Mock positions and balance
        self.crypto_handler.get_positions.return_value = []
        self.crypto_handler.get_balance.return_value = {
            "USDT": {"free": 1000.0, "used": 0.0, "total": 1000.0}
        }
    
    def test_crypto_handler_integration(self):
        """Test crypto handler integration"""
        # Test connection
        result = self.crypto_handler.connect()
        self.assertTrue(result)
        
        # Test symbol info
        symbol_info = self.crypto_handler.get_symbol_info("BTC/USDT:USDT")
        self.assertIsNotNone(symbol_info)
        self.assertEqual(symbol_info["symbol"], "BTC/USDT:USDT")
        
        # Test historical data
        data = self.crypto_handler.get_historical_data("BTC/USDT:USDT", "1m", 100)
        self.assertEqual(len(data), 5)
        self.assertEqual(len(data[0]), 6)  # OHLCV + timestamp
    
    def test_crypto_data_manager_integration(self):
        """Test crypto data manager integration"""
        # Create data manager
        data_manager = CryptoDataManager(self.crypto_handler)
        
        # Test data fetching
        data = data_manager.get_historical_data("BTC/USDT:USDT", "1m", 100)
        self.assertIsNotNone(data)
        self.assertEqual(len(data), 5)
        
        # Test data caching
        cached_data = data_manager.get_historical_data("BTC/USDT:USDT", "1m", 100)
        self.assertEqual(data, cached_data)
    
    def test_volume_ma_oscillator_integration(self):
        """Test Volume MA Oscillator strategy integration"""
        # Create strategy
        strategy = VolumeMAOscillator(
            crypto_handler=self.crypto_handler,
            risk_manager=Mock(),
            symbol="BTC/USDT:USDT",
            timeframe="1m"
        )
        
        # Test strategy initialization
        self.assertEqual(strategy.symbol, "BTC/USDT:USDT")
        self.assertEqual(strategy.timeframe, "1m")
        
        # Test indicator calculation
        data = {
            "timestamp": [1640995200000, 1640995260000, 1640995320000],
            "open": [47000, 47500, 48000],
            "high": [48000, 48500, 49000],
            "low": [46000, 47000, 47500],
            "close": [47500, 48000, 48500],
            "volume": [1000, 1200, 1100]
        }
        
        indicators = strategy.calculate_indicators(data)
        self.assertIsNotNone(indicators)
        self.assertIn("volume_ma", indicators)
        self.assertIn("oscillator", indicators)
        
        # Test signal generation
        signal = strategy.generate_signal(data)
        self.assertIsNotNone(signal)
        self.assertIn("action", signal)
        self.assertIn("confidence", signal)
    
    def test_trading_bot_integration(self):
        """Test complete trading bot integration"""
        # Mock the trading bot dependencies
        with patch('src.trading_bot.CryptoHandler') as mock_crypto_handler_class:
            mock_crypto_handler_class.return_value = self.crypto_handler
            
            # Create trading bot
            bot = TradingBot(
                config=self.config,
                trading_config=self.trading_config
            )
            
            # Test bot initialization
            self.assertIsNotNone(bot.crypto_handler)
            self.assertIsNotNone(bot.data_manager)
            self.assertIsNotNone(bot.signal_generators)
            
            # Test signal generation
            signals = bot.generate_signals("BTC/USDT:USDT")
            self.assertIsNotNone(signals)
    
    def test_end_to_end_trading_flow(self):
        """Test complete end-to-end trading flow"""
        # Mock order placement
        mock_order = {
            "id": "12345",
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "amount": 0.001,
            "price": 47000,
            "status": "open"
        }
        self.crypto_handler.place_order.return_value = mock_order
        
        # Mock risk manager
        risk_manager = Mock()
        risk_manager.calculate_position_size.return_value = 0.001
        risk_manager.calculate_stop_loss.return_value = 46000
        risk_manager.calculate_take_profit.return_value = 49000
        
        # Create strategy
        strategy = VolumeMAOscillator(
            crypto_handler=self.crypto_handler,
            risk_manager=risk_manager,
            symbol="BTC/USDT:USDT",
            timeframe="1m"
        )
        
        # Test complete flow
        data = {
            "timestamp": [1640995200000, 1640995260000, 1640995320000],
            "open": [47000, 47500, 48000],
            "high": [48000, 48500, 49000],
            "low": [46000, 47000, 47500],
            "close": [47500, 48000, 48500],
            "volume": [1000, 1200, 1100]
        }
        
        # Generate signal
        signal = strategy.generate_signal(data)
        self.assertIsNotNone(signal)
        
        # Test order placement (if signal is buy/sell)
        if signal["action"] in ["buy", "sell"]:
            order = self.crypto_handler.place_order(
                "BTC/USDT:USDT",
                signal["action"],
                0.001,
                47000
            )
            self.assertIsNotNone(order)
            self.assertEqual(order["symbol"], "BTC/USDT:USDT")
    
    def test_error_handling_integration(self):
        """Test error handling across the system"""
        # Test with invalid symbol
        self.crypto_handler.get_symbol_info.return_value = None
        
        strategy = VolumeMAOscillator(
            crypto_handler=self.crypto_handler,
            risk_manager=Mock(),
            symbol="INVALID/SYMBOL",
            timeframe="1m"
        )
        
        # Should handle invalid symbol gracefully
        data = {
            "timestamp": [1640995200000],
            "open": [47000],
            "high": [48000],
            "low": [46000],
            "close": [47500],
            "volume": [1000]
        }
        
        signal = strategy.generate_signal(data)
        self.assertIsNotNone(signal)
        self.assertEqual(signal["action"], "hold")
    
    def test_performance_integration(self):
        """Test system performance"""
        # Test with larger dataset
        large_data = []
        for i in range(1000):
            timestamp = 1640995200000 + (i * 60000)  # 1 minute intervals
            open_price = 47000 + (i * 0.1)
            high_price = open_price + 100
            low_price = open_price - 100
            close_price = open_price + 50
            volume = 1000 + (i * 0.1)
            
            large_data.append([timestamp, open_price, high_price, low_price, close_price, volume])
        
        self.crypto_handler.get_historical_data.return_value = large_data
        
        # Test performance
        start_time = time.time()
        
        strategy = VolumeMAOscillator(
            crypto_handler=self.crypto_handler,
            risk_manager=Mock(),
            symbol="BTC/USDT:USDT",
            timeframe="1m"
        )
        
        data = {
            "timestamp": [row[0] for row in large_data[-100:]],  # Last 100 bars
            "open": [row[1] for row in large_data[-100:]],
            "high": [row[2] for row in large_data[-100:]],
            "low": [row[3] for row in large_data[-100:]],
            "close": [row[4] for row in large_data[-100:]],
            "volume": [row[5] for row in large_data[-100:]]
        }
        
        signal = strategy.generate_signal(data)
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should process within reasonable time (less than 1 second)
        self.assertLess(processing_time, 1.0)
        self.assertIsNotNone(signal)


if __name__ == "__main__":
    unittest.main()
