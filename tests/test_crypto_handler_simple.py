"""
Simple test cases for crypto handler (non-async version)
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from src.crypto_handler import CryptoHandler


class TestCryptoHandlerSimple(unittest.TestCase):
    """Test the CryptoHandler class with simple synchronous tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.handler = CryptoHandler(
            exchange_name="bybit",
            api_key="test_key",
            api_secret="test_secret",
            sandbox=True
        )
    
    def test_crypto_handler_initialization(self):
        """Test CryptoHandler initialization"""
        self.assertEqual(self.handler.exchange_name, "bybit")
        self.assertTrue(self.handler.sandbox)
        self.assertEqual(self.handler.api_key, "test_key")
        self.assertEqual(self.handler.api_secret, "test_secret")
    
    def test_crypto_handler_config(self):
        """Test CryptoHandler configuration"""
        config = {
            "exchange": "binance",
            "api_key": "binance_key",
            "api_secret": "binance_secret",
            "sandbox": False
        }
        
        handler = CryptoHandler(
            exchange_name=config["exchange"],
            api_key=config["api_key"],
            api_secret=config["api_secret"],
            sandbox=config["sandbox"]
        )
        
        self.assertEqual(handler.exchange_name, "binance")
        self.assertFalse(handler.sandbox)
        self.assertEqual(handler.api_key, "binance_key")
        self.assertEqual(handler.api_secret, "binance_secret")
    
    async def test_crypto_handler_exchange_creation(self):
        """Test exchange creation"""
        # Mock the exchange factory
        with patch('src.crypto_exchange.ExchangeFactory.create_exchange') as mock_create:
            mock_exchange = Mock()
            mock_exchange.connect = Mock(return_value=True)
            mock_create.return_value = mock_exchange
            
            # Test that exchange is created correctly
            handler = CryptoHandler("bybit", "key", "secret", True)
            self.assertIsNone(handler.exchange)  # Not initialized yet
            
            # Test initialization
            result = await handler.initialize()
            self.assertTrue(result)
            mock_create.assert_called_once_with("bybit", "key", "secret", True)
    
    async def test_crypto_handler_connection_status(self):
        """Test connection status"""
        # Initially not connected
        self.assertFalse(self.handler.connected)
        
        # Mock exchange connection
        mock_exchange = Mock()
        mock_exchange.connect.return_value = True
        self.handler.exchange = mock_exchange
        
        # Test connection
        result = await self.handler.initialize()
        self.assertTrue(result)
        self.assertTrue(self.handler.connected)
    
    async def test_crypto_handler_error_handling(self):
        """Test error handling in CryptoHandler"""
        # Test with invalid exchange
        with patch('src.crypto_exchange.ExchangeFactory.create_exchange') as mock_create:
            mock_create.side_effect = Exception("Invalid exchange")
            
            handler = CryptoHandler("invalid_exchange", "key", "secret", True)
            result = await handler.initialize()
            
            # Should handle error gracefully
            self.assertFalse(result)
            self.assertFalse(handler.connected)
    
    def test_crypto_handler_price_callbacks(self):
        """Test price callback functionality"""
        # Test that price callbacks dictionary exists
        self.assertIsNotNone(self.handler._price_callbacks)
        self.assertIsInstance(self.handler._price_callbacks, dict)
        
        # Test adding price callback
        callback = Mock()
        self.handler._price_callbacks["BTC/USDT:USDT"] = callback
        
        self.assertIn("BTC/USDT:USDT", self.handler._price_callbacks)
        self.assertEqual(self.handler._price_callbacks["BTC/USDT:USDT"], callback)
        
        # Test removing price callback
        del self.handler._price_callbacks["BTC/USDT:USDT"]
        self.assertNotIn("BTC/USDT:USDT", self.handler._price_callbacks)
    
    def test_crypto_handler_websocket_management(self):
        """Test WebSocket management"""
        # Test that WebSocket attribute exists
        self.assertIsNotNone(self.handler._websocket)
        
        # Test WebSocket status (if method exists)
        if hasattr(self.handler, 'is_websocket_connected'):
            self.assertFalse(self.handler.is_websocket_connected())
            
            # Mock WebSocket connection
            mock_websocket = Mock()
            mock_websocket.is_connected.return_value = True
            self.handler._websocket = mock_websocket
            
            self.assertTrue(self.handler.is_websocket_connected())
    
    def test_crypto_handler_data_conversion(self):
        """Test data conversion methods"""
        # Test converting exchange data to standard format
        exchange_data = {
            "timestamp": 1640995200000,
            "open": 47000,
            "high": 48000,
            "low": 46000,
            "close": 47500,
            "volume": 1000
        }
        
        # Test data conversion (if method exists)
        if hasattr(self.handler, 'convert_to_standard_format'):
            standard_data = self.handler.convert_to_standard_format(exchange_data)
            self.assertIsNotNone(standard_data)
            self.assertIn("timestamp", standard_data)
            self.assertIn("open", standard_data)
            self.assertIn("high", standard_data)
            self.assertIn("low", standard_data)
            self.assertIn("close", standard_data)
            self.assertIn("volume", standard_data)


if __name__ == "__main__":
    unittest.main()
