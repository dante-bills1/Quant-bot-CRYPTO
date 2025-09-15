"""
Crypto Risk Manager

This module provides risk management functionality specifically designed for crypto trading,
replacing the MT5-based risk manager with crypto-specific calculations and controls.
"""

from datetime import datetime, UTC
from typing import Dict, List, Optional, Any, TYPE_CHECKING
from loguru import logger
import pandas as pd
import numpy as np

# Use TYPE_CHECKING for import that's only used for type hints
if TYPE_CHECKING:
    from src.crypto_handler import CryptoHandler
from config.config import TRADING_CONFIG
from src.utils.market_utils import calculate_tick_value, convert_price_to_ticks

# Singleton instance for global reference
_crypto_risk_manager_instance = None

# Custom Exceptions for CryptoRiskManager
class CryptoRiskManagerError(Exception):
    """Base class for exceptions in CryptoRiskManager."""
    pass

class InsufficientBalanceError(CryptoRiskManagerError):
    """Raised when account balance is insufficient for an operation."""
    pass

class InvalidRiskParameterError(CryptoRiskManagerError):
    """Raised when a risk parameter (e.g., risk percent, SL) is invalid."""
    pass

class RiskCalculationError(CryptoRiskManagerError):
    """Raised when there's an error during risk calculation (e.g., position sizing)."""
    pass

class CryptoRiskManager:
    """Crypto risk manager handles position sizing, risk control, and trade management for crypto trading."""

    def __init__(self, crypto_handler=None):
        """
        Initialize the crypto risk manager with a crypto handler and configuration.
        
        Args:
            crypto_handler: CryptoHandler instance (optional)
        """
        # Singleton pattern
        global _crypto_risk_manager_instance
        
        # If an instance already exists, use it
        if _crypto_risk_manager_instance is not None:
            logger.info("Using existing CryptoRiskManager instance")
            self.__dict__ = _crypto_risk_manager_instance.__dict__
            return
        
        # Set this instance as the global singleton
        _crypto_risk_manager_instance = self
        
        self.crypto_handler = crypto_handler
        self.config = TRADING_CONFIG.get("risk_management", {})
        
        # Risk management parameters
        self.max_risk_per_trade = self.config.get("max_risk_per_trade", 0.02)  # 2% max risk per trade
        self.max_daily_risk = self.config.get("max_daily_risk", 0.1)  # 10% max daily risk
        self.max_total_risk = self.config.get("max_total_risk", 0.2)  # 20% max total risk
        self.stop_loss_atr_multiplier = self.config.get("stop_loss_atr_multiplier", 2.0)
        self.take_profit_atr_multiplier = self.config.get("take_profit_atr_multiplier", 3.0)
        self.max_leverage = self.config.get("max_leverage", 10.0)  # Maximum leverage allowed
        self.min_position_size = self.config.get("min_position_size", 0.001)  # Minimum position size
        self.max_position_size = self.config.get("max_position_size", 1.0)  # Maximum position size
        
        # Risk tracking
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.daily_trades = 0
        self.max_daily_trades = self.config.get("max_daily_trades", 50)
        
        # Position tracking
        self.open_positions = {}
        self.daily_risk_used = 0.0
        self.total_risk_used = 0.0
        
        logger.info(f"CryptoRiskManager initialized with max_risk_per_trade={self.max_risk_per_trade}")
    
    async def get_account_balance(self) -> Dict[str, float]:
        """
        Get account balance from crypto handler.
        
        Returns:
            Dict containing balance information
        """
        try:
            if self.crypto_handler is None:
                raise CryptoRiskManagerError("CryptoHandler not available")
            
            balance = await self.crypto_handler.get_balance()
            return balance
        except Exception as e:
            logger.error(f"Failed to get account balance: {str(e)}")
            raise CryptoRiskManagerError(f"Failed to get account balance: {str(e)}")
    
    async def get_symbol_info(self, symbol: str) -> Dict[str, Any]:
        """
        Get symbol information from crypto handler.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT:USDT')
            
        Returns:
            Dict containing symbol information
        """
        try:
            if self.crypto_handler is None:
                raise CryptoRiskManagerError("CryptoHandler not available")
            
            symbol_info = await self.crypto_handler.get_symbol_info(symbol)
            return symbol_info
        except Exception as e:
            logger.error(f"Failed to get symbol info for {symbol}: {str(e)}")
            raise CryptoRiskManagerError(f"Failed to get symbol info for {symbol}: {str(e)}")
    
    def calculate_atr(self, data: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR) for crypto data.
        
        Args:
            data: DataFrame with OHLCV data
            period: ATR period (default 14)
            
        Returns:
            Series with ATR values
        """
        try:
            high = data['high']
            low = data['low']
            close = data['close']
            
            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Calculate ATR
            atr = true_range.rolling(window=period).mean()
            
            return atr
        except Exception as e:
            logger.error(f"Error calculating ATR: {str(e)}")
            raise RiskCalculationError(f"Error calculating ATR: {str(e)}")
    
    def calculate_position_size(
        self, 
        symbol: str, 
        entry_price: float, 
        stop_loss: float, 
        risk_amount: float = None,
        leverage: float = 1.0
    ) -> float:
        """
        Calculate position size based on risk parameters.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_amount: Risk amount in base currency (optional)
            leverage: Leverage to use (default 1.0)
            
        Returns:
            Position size in base currency
        """
        try:
            # Validate inputs
            if entry_price <= 0:
                raise InvalidRiskParameterError("Entry price must be positive")
            if stop_loss <= 0:
                raise InvalidRiskParameterError("Stop loss must be positive")
            if leverage <= 0 or leverage > self.max_leverage:
                raise InvalidRiskParameterError(f"Leverage must be between 0 and {self.max_leverage}")
            
            # Calculate risk per unit
            risk_per_unit = abs(entry_price - stop_loss)
            if risk_per_unit <= 0:
                raise InvalidRiskParameterError("Invalid risk per unit calculation")
            
            # Use provided risk amount or calculate from account balance
            if risk_amount is None:
                # This would need to be async in real implementation
                # For now, use a default risk amount
                risk_amount = 100.0  # Default risk amount
            
            # Calculate position size
            position_size = (risk_amount * leverage) / risk_per_unit
            
            # Apply position size limits
            position_size = max(self.min_position_size, min(position_size, self.max_position_size))
            
            logger.debug(f"Calculated position size for {symbol}: {position_size}")
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            raise RiskCalculationError(f"Error calculating position size: {str(e)}")
    
    def calculate_stop_loss(
        self, 
        symbol: str, 
        entry_price: float, 
        side: str, 
        atr: float = None,
        atr_multiplier: float = None
    ) -> float:
        """
        Calculate stop loss price based on ATR or fixed percentage.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            side: Trade side ('buy' or 'sell')
            atr: ATR value (optional)
            atr_multiplier: ATR multiplier (optional)
            
        Returns:
            Stop loss price
        """
        try:
            if atr_multiplier is None:
                atr_multiplier = self.stop_loss_atr_multiplier
            
            if atr is not None:
                # Use ATR-based stop loss
                if side.lower() == 'buy':
                    stop_loss = entry_price - (atr * atr_multiplier)
                else:  # sell
                    stop_loss = entry_price + (atr * atr_multiplier)
            else:
                # Use fixed percentage stop loss (2%)
                stop_loss_percentage = 0.02
                if side.lower() == 'buy':
                    stop_loss = entry_price * (1 - stop_loss_percentage)
                else:  # sell
                    stop_loss = entry_price * (1 + stop_loss_percentage)
            
            # Ensure stop loss is positive
            stop_loss = max(stop_loss, 0.01)
            
            logger.debug(f"Calculated stop loss for {symbol}: {stop_loss}")
            return stop_loss
            
        except Exception as e:
            logger.error(f"Error calculating stop loss: {str(e)}")
            raise RiskCalculationError(f"Error calculating stop loss: {str(e)}")
    
    def calculate_take_profit(
        self, 
        symbol: str, 
        entry_price: float, 
        side: str, 
        atr: float = None,
        atr_multiplier: float = None
    ) -> float:
        """
        Calculate take profit price based on ATR or fixed ratio.
        
        Args:
            symbol: Trading symbol
            entry_price: Entry price
            side: Trade side ('buy' or 'sell')
            atr: ATR value (optional)
            atr_multiplier: ATR multiplier (optional)
            
        Returns:
            Take profit price
        """
        try:
            if atr_multiplier is None:
                atr_multiplier = self.take_profit_atr_multiplier
            
            if atr is not None:
                # Use ATR-based take profit
                if side.lower() == 'buy':
                    take_profit = entry_price + (atr * atr_multiplier)
                else:  # sell
                    take_profit = entry_price - (atr * atr_multiplier)
            else:
                # Use fixed ratio take profit (1:2 risk-reward)
                take_profit_percentage = 0.04  # 4% take profit
                if side.lower() == 'buy':
                    take_profit = entry_price * (1 + take_profit_percentage)
                else:  # sell
                    take_profit = entry_price * (1 - take_profit_percentage)
            
            # Ensure take profit is positive
            take_profit = max(take_profit, 0.01)
            
            logger.debug(f"Calculated take profit for {symbol}: {take_profit}")
            return take_profit
            
        except Exception as e:
            logger.error(f"Error calculating take profit: {str(e)}")
            raise RiskCalculationError(f"Error calculating take profit: {str(e)}")
    
    def validate_trade_risk(self, symbol: str, position_size: float, entry_price: float) -> bool:
        """
        Validate if a trade meets risk requirements.
        
        Args:
            symbol: Trading symbol
            position_size: Position size
            entry_price: Entry price
            
        Returns:
            True if trade is valid, False otherwise
        """
        try:
            # Check position size limits
            if position_size < self.min_position_size:
                logger.warning(f"Position size {position_size} below minimum {self.min_position_size}")
                return False
            
            if position_size > self.max_position_size:
                logger.warning(f"Position size {position_size} above maximum {self.max_position_size}")
                return False
            
            # Check daily trade limit
            if self.daily_trades >= self.max_daily_trades:
                logger.warning(f"Daily trade limit {self.max_daily_trades} reached")
                return False
            
            # Check daily risk limit
            trade_value = position_size * entry_price
            if trade_value > self.daily_risk_used + (self.max_daily_risk * 1000):  # Assuming 1000 base currency
                logger.warning(f"Trade would exceed daily risk limit")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating trade risk: {str(e)}")
            return False
    
    def update_position(self, symbol: str, position_data: Dict[str, Any]):
        """
        Update position tracking.
        
        Args:
            symbol: Trading symbol
            position_data: Position data dictionary
        """
        try:
            self.open_positions[symbol] = position_data
            logger.debug(f"Updated position for {symbol}")
        except Exception as e:
            logger.error(f"Error updating position for {symbol}: {str(e)}")
    
    def remove_position(self, symbol: str):
        """
        Remove position from tracking.
        
        Args:
            symbol: Trading symbol
        """
        try:
            if symbol in self.open_positions:
                del self.open_positions[symbol]
                logger.debug(f"Removed position for {symbol}")
        except Exception as e:
            logger.error(f"Error removing position for {symbol}: {str(e)}")
    
    def update_daily_stats(self, pnl: float):
        """
        Update daily statistics.
        
        Args:
            pnl: Profit/Loss for the day
        """
        try:
            self.daily_pnl += pnl
            self.total_pnl += pnl
            self.daily_trades += 1
            
            logger.debug(f"Updated daily stats: PnL={pnl}, Total PnL={self.total_pnl}")
        except Exception as e:
            logger.error(f"Error updating daily stats: {str(e)}")
    
    def reset_daily_stats(self):
        """Reset daily statistics."""
        try:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.daily_risk_used = 0.0
            logger.info("Daily statistics reset")
        except Exception as e:
            logger.error(f"Error resetting daily stats: {str(e)}")
    
    def get_risk_summary(self) -> Dict[str, Any]:
        """
        Get risk management summary.
        
        Returns:
            Dict containing risk summary
        """
        try:
            return {
                "max_risk_per_trade": self.max_risk_per_trade,
                "max_daily_risk": self.max_daily_risk,
                "max_total_risk": self.max_total_risk,
                "daily_pnl": self.daily_pnl,
                "total_pnl": self.total_pnl,
                "daily_trades": self.daily_trades,
                "max_daily_trades": self.max_daily_trades,
                "open_positions": len(self.open_positions),
                "daily_risk_used": self.daily_risk_used,
                "total_risk_used": self.total_risk_used
            }
        except Exception as e:
            logger.error(f"Error getting risk summary: {str(e)}")
            return {}
    
    def set_crypto_handler(self, crypto_handler):
        """Set the crypto handler instance."""
        self.crypto_handler = crypto_handler
        logger.info("CryptoHandler set for CryptoRiskManager")


# Global instance getter
def get_crypto_risk_manager() -> CryptoRiskManager:
    """Get the global CryptoRiskManager instance."""
    global _crypto_risk_manager_instance
    if _crypto_risk_manager_instance is None:
        _crypto_risk_manager_instance = CryptoRiskManager()
    return _crypto_risk_manager_instance
