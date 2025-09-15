"""
Test cases for crypto handler
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from src.crypto_handler import CryptoHandler
from src.crypto_exchange import ExchangeFactory


class TestCryptoHandler(unittest.TestCase):
    """Test the CryptoHandler class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            "exchange": "bybit",
            "api_key": "test_key",
            "api_secret": "test_secret",
            "sandbox": True
        }
        self.handler = CryptoHandler(
            exchange_name=self.config["exchange"],
            api_key=self.config["api_key"],
            api_secret=self.config["api_secret"],
            sandbox=self.config["sandbox"]
        )
    
    def test_crypto_handler_initialization(self):
        """Test CryptoHandler initialization"""
        self.assertEqual(self.handler.exchange_name, "bybit")
        self.assertTrue(self.handler.sandbox)
        self.assertEqual(self.handler.api_key, "test_key")
    
    @patch('src.crypto_exchange.ExchangeFactory.create_exchange')
    def test_crypto_handler_connection(self, mock_create_exchange):
        """Test CryptoHandler connection"""
        mock_exchange = Mock()
        mock_exchange.connect.return_value = True
        mock_create_exchange.return_value = mock_exchange
        
        handler = CryptoHandler(
            exchange_name=self.config["exchange"],
            api_key=self.config["api_key"],
            api_secret=self.config["api_secret"],
            sandbox=self.config["sandbox"]
        )
        result = handler.initialize()
        
        self.assertTrue(result)
        mock_exchange.connect.assert_called_once()
    
    async def test_crypto_handler_get_symbol_info(self):
        """Test getting symbol information"""
        # Mock the exchange
        mock_exchange = Mock()
        mock_exchange.get_symbol_info.return_value = {
            "symbol": "BTC/USDT:USDT",
            "base": "BTC",
            "quote": "USDT",
            "precision": {"price": 2, "amount": 6}
        }
        self.handler.exchange = mock_exchange
        
        symbol_info = await self.handler.get_symbol_info("BTC/USDT:USDT")
        
        self.assertIsNotNone(symbol_info)
        self.assertEqual(symbol_info["symbol"], "BTC/USDT:USDT")
        mock_exchange.get_symbol_info.assert_called_once_with("BTC/USDT:USDT")
    
    def test_crypto_handler_get_historical_data(self):
        """Test getting historical data"""
        # Mock the exchange
        mock_exchange = Mock()
        mock_data = [
            [1640995200000, 47000, 48000, 46000, 47500, 1000],
            [1640995260000, 47500, 48500, 47000, 48000, 1200]
        ]
        mock_exchange.get_historical_data.return_value = mock_data
        self.handler.exchange = mock_exchange
        
        data = self.handler.get_historical_data("BTC/USDT:USDT", "1m", 100)
        
        self.assertEqual(len(data), 2)
        self.assertEqual(data, mock_data)
        mock_exchange.get_historical_data.assert_called_once_with("BTC/USDT:USDT", "1m", 100)
    
    def test_crypto_handler_place_order(self):
        """Test placing orders"""
        # Mock the exchange
        mock_exchange = Mock()
        mock_order = {
            "id": "12345",
            "symbol": "BTC/USDT:USDT",
            "side": "buy",
            "amount": 0.001,
            "price": 47000,
            "status": "open"
        }
        mock_exchange.place_order.return_value = mock_order
        self.handler.exchange = mock_exchange
        
        order = self.handler.place_order("BTC/USDT:USDT", "buy", 0.001, 47000)
        
        self.assertEqual(order, mock_order)
        mock_exchange.place_order.assert_called_once_with("BTC/USDT:USDT", "buy", 0.001, 47000)
    
    def test_crypto_handler_get_positions(self):
        """Test getting positions"""
        # Mock the exchange
        mock_exchange = Mock()
        mock_positions = [
            {
                "symbol": "BTC/USDT:USDT",
                "side": "long",
                "size": 0.001,
                "entryPrice": 47000,
                "markPrice": 47500,
                "pnl": 0.5
            }
        ]
        mock_exchange.get_positions.return_value = mock_positions
        self.handler.exchange = mock_exchange
        
        positions = self.handler.get_positions()
        
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions, mock_positions)
        mock_exchange.get_positions.assert_called_once()
    
    def test_crypto_handler_get_balance(self):
        """Test getting account balance"""
        # Mock the exchange
        mock_exchange = Mock()
        mock_balance = {
            "USDT": {"free": 1000.0, "used": 0.0, "total": 1000.0},
            "BTC": {"free": 0.0, "used": 0.0, "total": 0.0}
        }
        mock_exchange.get_balance.return_value = mock_balance
        self.handler.exchange = mock_exchange
        
        balance = self.handler.get_balance()
        
        self.assertEqual(balance, mock_balance)
        mock_exchange.get_balance.assert_called_once()
    
    def test_crypto_handler_error_handling(self):
        """Test error handling in CryptoHandler"""
        # Mock the exchange to raise an exception
        mock_exchange = Mock()
        mock_exchange.get_symbol_info.side_effect = Exception("Connection error")
        self.handler.exchange = mock_exchange
        
        # Should handle exception gracefully
        symbol_info = self.handler.get_symbol_info("BTC/USDT:USDT")
        self.assertIsNone(symbol_info)


if __name__ == "__main__":
    unittest.main()
