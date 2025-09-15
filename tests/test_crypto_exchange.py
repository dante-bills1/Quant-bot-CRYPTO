"""
Test cases for crypto exchange abstraction layer
"""
import pytest
import unittest
from unittest.mock import Mock, patch, MagicMock
from src.crypto_exchange import CryptoExchange, ExchangeFactory
from src.exchanges.bybit_exchange import BybitExchange
from src.exchanges.binance_exchange import BinanceExchange


class TestCryptoExchange(unittest.TestCase):
    """Test the base CryptoExchange class"""
    
    def test_crypto_exchange_interface(self):
        """Test that CryptoExchange is an abstract base class"""
        with self.assertRaises(TypeError):
            CryptoExchange()
    
    def test_exchange_factory_registration(self):
        """Test exchange factory registration"""
        # Test that exchanges are registered
        self.assertIn("bybit", ExchangeFactory._exchanges)
        self.assertIn("binance", ExchangeFactory._exchanges)
        
        # Test getting exchange classes
        bybit_class = ExchangeFactory.get_exchange_class("bybit")
        binance_class = ExchangeFactory.get_exchange_class("binance")
        
        self.assertEqual(bybit_class, BybitExchange)
        self.assertEqual(binance_class, BinanceExchange)
    
    def test_exchange_factory_invalid_exchange(self):
        """Test getting invalid exchange"""
        with self.assertRaises(ValueError):
            ExchangeFactory.get_exchange_class("invalid_exchange")
    
    def test_exchange_factory_create_exchange(self):
        """Test creating exchange instances"""
        config = {
            "api_key": "test_key",
            "api_secret": "test_secret",
            "sandbox": True
        }
        
        bybit_exchange = ExchangeFactory.create_exchange("bybit", config)
        binance_exchange = ExchangeFactory.create_exchange("binance", config)
        
        self.assertIsInstance(bybit_exchange, BybitExchange)
        self.assertIsInstance(binance_exchange, BinanceExchange)


class TestBybitExchange(unittest.TestCase):
    """Test Bybit exchange implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            "api_key": "test_key",
            "api_secret": "test_secret",
            "sandbox": True
        }
        self.exchange = BybitExchange(self.config)
    
    def test_bybit_initialization(self):
        """Test Bybit exchange initialization"""
        self.assertEqual(self.exchange.exchange_name, "bybit")
        self.assertTrue(self.exchange.sandbox)
        self.assertEqual(self.exchange.api_key, "test_key")
    
    @patch('ccxt.bybit')
    def test_bybit_connection(self, mock_bybit):
        """Test Bybit exchange connection"""
        mock_exchange = Mock()
        mock_bybit.return_value = mock_exchange
        
        exchange = BybitExchange(self.config)
        exchange.connect()
        
        mock_bybit.assert_called_once()
        mock_exchange.load_markets.assert_called_once()
    
    def test_bybit_get_symbol_info(self):
        """Test getting symbol information"""
        # Mock the exchange instance
        mock_exchange = Mock()
        mock_exchange.markets = {
            "BTC/USDT:USDT": {
                "id": "BTCUSDT",
                "symbol": "BTC/USDT:USDT",
                "base": "BTC",
                "quote": "USDT",
                "precision": {"price": 2, "amount": 6},
                "limits": {"amount": {"min": 0.00001, "max": 1000}}
            }
        }
        self.exchange.exchange = mock_exchange
        
        symbol_info = self.exchange.get_symbol_info("BTC/USDT:USDT")
        
        self.assertIsNotNone(symbol_info)
        self.assertEqual(symbol_info["symbol"], "BTC/USDT:USDT")
        self.assertEqual(symbol_info["base"], "BTC")
        self.assertEqual(symbol_info["quote"], "USDT")
    
    def test_bybit_get_historical_data(self):
        """Test getting historical data"""
        # Mock the exchange instance
        mock_exchange = Mock()
        mock_exchange.fetch_ohlcv.return_value = [
            [1640995200000, 47000, 48000, 46000, 47500, 1000],
            [1640995260000, 47500, 48500, 47000, 48000, 1200]
        ]
        self.exchange.exchange = mock_exchange
        
        data = self.exchange.get_historical_data("BTC/USDT:USDT", "1m", 100)
        
        self.assertEqual(len(data), 2)
        self.assertEqual(len(data[0]), 6)  # OHLCV + timestamp
        mock_exchange.fetch_ohlcv.assert_called_once()
    
    def test_bybit_place_order(self):
        """Test placing orders"""
        # Mock the exchange instance
        mock_exchange = Mock()
        mock_exchange.create_order.return_value = {
            "id": "12345",
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "amount": 0.001,
            "price": 47000,
            "status": "open"
        }
        self.exchange.exchange = mock_exchange
        
        order = self.exchange.place_order("BTC/USDT:USDT", "buy", 0.001, 47000)
        
        self.assertIsNotNone(order)
        self.assertEqual(order["symbol"], "BTC/USDT:USDT")
        self.assertEqual(order["side"], "buy")
        mock_exchange.create_order.assert_called_once()
    
    def test_bybit_get_positions(self):
        """Test getting positions"""
        # Mock the exchange instance
        mock_exchange = Mock()
        mock_exchange.fetch_positions.return_value = [
            {
                "symbol": "BTC/USDT:USDT",
                "side": "long",
                "size": 0.001,
                "entryPrice": 47000,
                "markPrice": 47500,
                "pnl": 0.5
            }
        ]
        self.exchange.exchange = mock_exchange
        
        positions = self.exchange.get_positions()
        
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["symbol"], "BTC/USDT:USDT")
        mock_exchange.fetch_positions.assert_called_once()


class TestBinanceExchange(unittest.TestCase):
    """Test Binance exchange implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            "api_key": "test_key",
            "api_secret": "test_secret",
            "sandbox": True
        }
        self.exchange = BinanceExchange(self.config)
    
    def test_binance_initialization(self):
        """Test Binance exchange initialization"""
        self.assertEqual(self.exchange.exchange_name, "binance")
        self.assertTrue(self.exchange.sandbox)
        self.assertEqual(self.exchange.api_key, "test_key")
    
    @patch('ccxt.binance')
    def test_binance_connection(self, mock_binance):
        """Test Binance exchange connection"""
        mock_exchange = Mock()
        mock_binance.return_value = mock_exchange
        
        exchange = BinanceExchange(self.config)
        exchange.connect()
        
        mock_binance.assert_called_once()
        mock_exchange.load_markets.assert_called_once()
    
    def test_binance_get_symbol_info(self):
        """Test getting symbol information"""
        # Mock the exchange instance
        mock_exchange = Mock()
        mock_exchange.markets = {
            "BTC/USDT": {
                "id": "BTCUSDT",
                "symbol": "BTC/USDT",
                "base": "BTC",
                "quote": "USDT",
                "precision": {"price": 2, "amount": 6},
                "limits": {"amount": {"min": 0.00001, "max": 1000}}
            }
        }
        self.exchange.exchange = mock_exchange
        
        symbol_info = self.exchange.get_symbol_info("BTC/USDT")
        
        self.assertIsNotNone(symbol_info)
        self.assertEqual(symbol_info["symbol"], "BTC/USDT")
        self.assertEqual(symbol_info["base"], "BTC")
        self.assertEqual(symbol_info["quote"], "USDT")


if __name__ == "__main__":
    unittest.main()
