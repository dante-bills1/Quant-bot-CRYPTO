"""
Crypto Service

A service class to interact with the CryptoHandler for live data.
This acts as a bridge between the API and the core crypto connection logic.
"""

import sys
import os
from typing import List, Dict, Any, Optional

# Add the project root to the Python path to allow for absolute imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.crypto_handler import CryptoHandler
from src.crypto_risk_manager import CryptoRiskManager
from src.crypto_position_manager import CryptoPositionManager
from loguru import logger

class CryptoService:
    """
    A service class to interact with the CryptoHandler for live data.
    This acts as a bridge between the API and the core crypto connection logic.
    """
    _instance: Optional['CryptoService'] = None
    _crypto_handler: Optional[CryptoHandler] = None
    _risk_manager: Optional[CryptoRiskManager] = None
    _position_manager: Optional[CryptoPositionManager] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CryptoService, cls).__new__(cls)
            cls._instance._initialize_handlers()
        return cls._instance

    def _initialize_handlers(self):
        """Initializes the crypto handler instances."""
        if CryptoService._crypto_handler is None:
            logger.info("Initializing CryptoService and creating new CryptoHandler instance...")
            try:
                CryptoService._crypto_handler = CryptoHandler()
                CryptoService._risk_manager = CryptoRiskManager(CryptoService._crypto_handler)
                CryptoService._position_manager = CryptoPositionManager(
                    crypto_handler=CryptoService._crypto_handler,
                    risk_manager=CryptoService._risk_manager
                )
                logger.info("CryptoService initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize CryptoService: {str(e)}")
                CryptoService._crypto_handler = None
                CryptoService._risk_manager = None
                CryptoService._position_manager = None

    @property
    def crypto_handler(self) -> Optional[CryptoHandler]:
        """Get the crypto handler instance."""
        return CryptoService._crypto_handler

    @property
    def risk_manager(self) -> Optional[CryptoRiskManager]:
        """Get the risk manager instance."""
        return CryptoService._risk_manager

    @property
    def position_manager(self) -> Optional[CryptoPositionManager]:
        """Get the position manager instance."""
        return CryptoService._position_manager

    async def get_account_info(self) -> Dict[str, Any]:
        """
        Retrieves account information from the crypto exchange.

        Returns:
            Dict containing account information or error details
        """
        try:
            if self.crypto_handler is None:
                return {
                    "success": False,
                    "error": "Crypto handler not initialized"
                }

            # Get balance information
            balance = await self.crypto_handler.get_balance()

            if balance:
                return {
                    "success": True,
                    "balance": balance,
                    "exchange": self.crypto_handler.exchange_name,
                    "connected": self.crypto_handler.connected
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to retrieve balance"
                }

        except Exception as e:
            logger.error(f"Error retrieving account info: {str(e)}")
            return {
                "success": False,
                "error": f"Exception occurred: {str(e)}"
            }

    async def get_positions(self) -> Dict[str, Any]:
        """
        Retrieves current positions from the crypto exchange.

        Returns:
            Dict containing positions information or error details
        """
        try:
            if self.position_manager is None:
                return {
                    "success": False,
                    "error": "Position manager not initialized"
                }

            positions = await self.position_manager.get_open_positions()

            return {
                "success": True,
                "positions": positions,
                "count": len(positions)
            }

        except Exception as e:
            logger.error(f"Error retrieving positions: {str(e)}")
            return {
                "success": False,
                "error": f"Exception occurred: {str(e)}"
            }

    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Retrieves symbol information from the crypto exchange.

        Args:
            symbol: Trading symbol

        Returns:
            Dict containing symbol information or error details
        """
        try:
            if self.crypto_handler is None:
                return {
                    "success": False,
                    "error": "Crypto handler not initialized"
                }

            symbol_info = await self.crypto_handler.get_symbol_info(symbol)

            if symbol_info:
                return {
                    "success": True,
                    "symbol": symbol,
                    "info": symbol_info
                }
            else:
                return {
                    "success": False,
                    "error": f"Symbol {symbol} not found"
                }

        except Exception as e:
            logger.error(f"Error retrieving symbol info for {symbol}: {str(e)}")
            return {
                "success": False,
                "error": f"Exception occurred: {str(e)}"
            }

    async def get_historical_data(self, symbol: str, timeframe: str = "1h", limit: int = 100) -> Dict[str, Any]:
        """
        Retrieves historical data for a symbol.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (1m, 5m, 1h, 1d)
            limit: Number of data points

        Returns:
            Dict containing historical data or error details
        """
        try:
            if self.crypto_handler is None:
                return {
                    "success": False,
                    "error": "Crypto handler not initialized"
                }

            # This would need to be implemented with proper date ranges
            # For now, return a mock response
            return {
                "success": True,
                "symbol": symbol,
                "timeframe": timeframe,
                "limit": limit,
                "message": "Historical data retrieval not fully implemented yet"
            }

        except Exception as e:
            logger.error(f"Error retrieving historical data for {symbol}: {str(e)}")
            return {
                "success": False,
                "error": f"Exception occurred: {str(e)}"
            }

    async def get_risk_summary(self) -> Dict[str, Any]:
        """
        Retrieves risk management summary.

        Returns:
            Dict containing risk summary or error details
        """
        try:
            if self.risk_manager is None:
                return {
                    "success": False,
                    "error": "Risk manager not initialized"
                }

            summary = self.risk_manager.get_risk_summary()

            return {
                "success": True,
                "risk_summary": summary
            }

        except Exception as e:
            logger.error(f"Error retrieving risk summary: {str(e)}")
            return {
                "success": False,
                "error": f"Exception occurred: {str(e)}"
            }

    def get_connection_status(self) -> Dict[str, Any]:
        """
        Gets the connection status of the crypto service.

        Returns:
            Dict containing connection status information
        """
        return {
            "connected": self.crypto_handler is not None and self.crypto_handler.connected,
            "exchange": self.crypto_handler.exchange_name if self.crypto_handler else None,
            "risk_manager_initialized": self.risk_manager is not None,
            "position_manager_initialized": self.position_manager is not None
        }

    async def close_position(self, symbol: str, reason: str = "Manual close") -> Dict[str, Any]:
        """
        Closes a position for a symbol.

        Args:
            symbol: Trading symbol
            reason: Reason for closing

        Returns:
            Dict containing close result
        """
        try:
            if self.position_manager is None:
                return {
                    "success": False,
                    "error": "Position manager not initialized"
                }

            result = await self.position_manager.close_position(symbol, reason)

            return {
                "success": result,
                "symbol": symbol,
                "reason": reason
            }

        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {str(e)}")
            return {
                "success": False,
                "error": f"Exception occurred: {str(e)}"
            }

# Global instance getter
def get_crypto_service() -> CryptoService:
    """Get the global CryptoService instance."""
    return CryptoService()
