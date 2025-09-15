"""
Performance tests for the crypto trading system
"""
import unittest
import time
import numpy as np
from unittest.mock import Mock, patch
from src.crypto_handler import CryptoHandler
from src.crypto_data_manager import CryptoDataManager
from src.strategy.volume_ma_oscillator import VolumeMAOscillator


class TestPerformance(unittest.TestCase):
    """Test system performance"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.crypto_handler = Mock(spec=CryptoHandler)
        self.crypto_handler.get_symbol_info.return_value = {
            "symbol": "BTC/USDT:USDT",
            "base": "BTC",
            "quote": "USDT",
            "precision": {"price": 2, "amount": 6}
        }
    
    def test_data_processing_performance(self):
        """Test data processing performance"""
        # Generate large dataset
        data_size = 10000
        data = {
            "timestamp": np.arange(1640995200000, 1640995200000 + (data_size * 60000), 60000),
            "open": np.random.uniform(40000, 50000, data_size),
            "high": np.random.uniform(40000, 50000, data_size),
            "low": np.random.uniform(40000, 50000, data_size),
            "close": np.random.uniform(40000, 50000, data_size),
            "volume": np.random.uniform(1000, 2000, data_size)
        }
        
        # Mock historical data
        mock_data = []
        for i in range(data_size):
            mock_data.append([
                data["timestamp"][i],
                data["open"][i],
                data["high"][i],
                data["low"][i],
                data["close"][i],
                data["volume"][i]
            ])
        
        self.crypto_handler.get_historical_data.return_value = mock_data
        
        # Test data manager performance
        data_manager = CryptoDataManager(self.crypto_handler)
        
        start_time = time.time()
        historical_data = data_manager.get_historical_data("BTC/USDT:USDT", "1m", data_size)
        end_time = time.time()
        
        processing_time = end_time - start_time
        self.assertLess(processing_time, 5.0)  # Should process within 5 seconds
        self.assertEqual(len(historical_data), data_size)
    
    def test_strategy_calculation_performance(self):
        """Test strategy calculation performance"""
        # Generate test data
        data_size = 1000
        data = {
            "timestamp": np.arange(1640995200000, 1640995200000 + (data_size * 60000), 60000),
            "open": np.random.uniform(40000, 50000, data_size),
            "high": np.random.uniform(40000, 50000, data_size),
            "low": np.random.uniform(40000, 50000, data_size),
            "close": np.random.uniform(40000, 50000, data_size),
            "volume": np.random.uniform(1000, 2000, data_size)
        }
        
        # Create strategy
        strategy = VolumeMAOscillator(
            crypto_handler=self.crypto_handler,
            risk_manager=Mock(),
            symbol="BTC/USDT:USDT",
            timeframe="1m"
        )
        
        # Test indicator calculation performance
        start_time = time.time()
        indicators = strategy.calculate_indicators(data)
        end_time = time.time()
        
        calculation_time = end_time - start_time
        self.assertLess(calculation_time, 2.0)  # Should calculate within 2 seconds
        self.assertIsNotNone(indicators)
    
    def test_signal_generation_performance(self):
        """Test signal generation performance"""
        # Generate test data
        data_size = 500
        data = {
            "timestamp": np.arange(1640995200000, 1640995200000 + (data_size * 60000), 60000),
            "open": np.random.uniform(40000, 50000, data_size),
            "high": np.random.uniform(40000, 50000, data_size),
            "low": np.random.uniform(40000, 50000, data_size),
            "close": np.random.uniform(40000, 50000, data_size),
            "volume": np.random.uniform(1000, 2000, data_size)
        }
        
        # Create strategy
        strategy = VolumeMAOscillator(
            crypto_handler=self.crypto_handler,
            risk_manager=Mock(),
            symbol="BTC/USDT:USDT",
            timeframe="1m"
        )
        
        # Test signal generation performance
        start_time = time.time()
        signal = strategy.generate_signal(data)
        end_time = time.time()
        
        generation_time = end_time - start_time
        self.assertLess(generation_time, 1.0)  # Should generate signal within 1 second
        self.assertIsNotNone(signal)
    
    def test_memory_usage(self):
        """Test memory usage"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create multiple strategies
        strategies = []
        for i in range(10):
            strategy = VolumeMAOscillator(
                crypto_handler=self.crypto_handler,
                risk_manager=Mock(),
                symbol=f"SYMBOL{i}/USDT:USDT",
                timeframe="1m"
            )
            strategies.append(strategy)
        
        # Get memory usage after creating strategies
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        self.assertLess(memory_increase, 100)
    
    def test_concurrent_processing(self):
        """Test concurrent processing performance"""
        import threading
        import queue
        
        # Create test data
        data_size = 100
        data = {
            "timestamp": np.arange(1640995200000, 1640995200000 + (data_size * 60000), 60000),
            "open": np.random.uniform(40000, 50000, data_size),
            "high": np.random.uniform(40000, 50000, data_size),
            "low": np.random.uniform(40000, 50000, data_size),
            "close": np.random.uniform(40000, 50000, data_size),
            "volume": np.random.uniform(1000, 2000, data_size)
        }
        
        # Create strategy
        strategy = VolumeMAOscillator(
            crypto_handler=self.crypto_handler,
            risk_manager=Mock(),
            symbol="BTC/USDT:USDT",
            timeframe="1m"
        )
        
        # Test concurrent signal generation
        results = queue.Queue()
        
        def generate_signal():
            signal = strategy.generate_signal(data)
            results.put(signal)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=generate_signal)
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Should complete within reasonable time
        self.assertLess(total_time, 5.0)
        
        # Check that all signals were generated
        self.assertEqual(results.qsize(), 5)
        
        # Check signal quality
        while not results.empty():
            signal = results.get()
            self.assertIsNotNone(signal)
            self.assertIn("action", signal)


if __name__ == "__main__":
    unittest.main()
