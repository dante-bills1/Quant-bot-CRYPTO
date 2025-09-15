"""
Crypto Position Manager

This module provides position management functionality specifically designed for crypto trading,
replacing the MT5-based position manager with crypto-specific trade management.
"""

import traceback
from typing import Dict, List, Any, Optional, Tuple
from loguru import logger
import time

from src.telegram.telegram_bot import TelegramBot
from src.crypto_handler import CryptoHandler
from src.utils.market_utils import calculate_tick_value, convert_price_to_ticks
from src.crypto_risk_manager import CryptoRiskManager

class CryptoPositionManager:
    """
    Handles position management functionality for the crypto trading bot.
    
    This class is responsible for:
    - Managing open trades (stop loss, take profit, trailing stop)
    - Updating trade records in the database
    - Closing pending trades
    - Reconciling trade records with crypto exchange data
    """
    
    def __init__(self, crypto_handler=None, risk_manager=None, telegram_bot=None, config=None):
        """
        Initialize the CryptoPositionManager.
        
        Args:
            crypto_handler: CryptoHandler instance
            risk_manager: CryptoRiskManager instance
            telegram_bot: Telegram bot instance
            config: Configuration dictionary
        """
        self.crypto_handler = crypto_handler if crypto_handler else CryptoHandler()
        self.risk_manager = risk_manager if risk_manager else CryptoRiskManager()
        self.telegram_bot = telegram_bot if telegram_bot else TelegramBot.get_instance()
        self.config = config or {}
        
        # State tracking for trailing stops
        self.active_trades = {}
        self.trailing_stop_data = {}
        self.trailing_stop_enabled = self.config.get('use_trailing_stop', True)
        
        # State tracking for multi-TP partial closes
        self.managed_positions: Dict[str, Dict[str, Any]] = {}
        
        # Scalping configuration
        self.scalping_enabled = self.config.get('scalping_enabled', False)
        self.scalping_profit_target = self.config.get('scalping_profit_target', 0.001)  # 0.1% profit target
        self.scalping_stop_loss = self.config.get('scalping_stop_loss', 0.0005)  # 0.05% stop loss
        
        # Position management settings
        self.max_positions = self.config.get('max_positions', 10)
        self.position_timeout = self.config.get('position_timeout', 3600)  # 1 hour timeout
        
        logger.info("CryptoPositionManager initialized")
    
    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Get open positions from crypto exchange.
        
        Returns:
            List of open positions
        """
        try:
            if self.crypto_handler is None:
                logger.warning("CryptoHandler not available")
                return []
            
            positions = await self.crypto_handler.get_open_positions()
            return positions
        except Exception as e:
            logger.error(f"Error getting open positions: {str(e)}")
            return []
    
    async def get_position_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position information for a specific symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Position information or None
        """
        try:
            positions = await self.get_open_positions()
            for position in positions:
                if position.get('symbol') == symbol:
                    return position
            return None
        except Exception as e:
            logger.error(f"Error getting position info for {symbol}: {str(e)}")
            return None
    
    async def close_position(self, symbol: str, reason: str = "Manual close") -> bool:
        """
        Close a position for a specific symbol.
        
        Args:
            symbol: Trading symbol
            reason: Reason for closing
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.crypto_handler is None:
                logger.error("CryptoHandler not available")
                return False
            
            # Get current position
            position = await self.get_position_info(symbol)
            if not position:
                logger.warning(f"No open position found for {symbol}")
                return False
            
            # Determine close side (opposite of open side)
            close_side = "sell" if position.get('side', '').lower() == 'long' else "buy"
            
            # Close position
            result = await self.crypto_handler.place_order(
                symbol=symbol,
                side=close_side,
                amount=position.get('size', 0),
                price=None,  # Market order
                order_type="market"
            )
            
            if result:
                logger.info(f"Position closed for {symbol}: {reason}")
                
                # Update risk manager
                self.risk_manager.remove_position(symbol)
                
                # Remove from active trades
                if symbol in self.active_trades:
                    del self.active_trades[symbol]
                
                # Send notification
                if self.telegram_bot:
                    await self.telegram_bot.send_message(
                        f"🔴 Position Closed: {symbol}\n"
                        f"Reason: {reason}\n"
                        f"Size: {position.get('size', 0)}\n"
                        f"Side: {position.get('side', 'Unknown')}"
                    )
                
                return True
            else:
                logger.error(f"Failed to close position for {symbol}")
                return False
                
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {str(e)}")
            return False
    
    async def update_stop_loss(self, symbol: str, new_stop_loss: float) -> bool:
        """
        Update stop loss for a position.
        
        Args:
            symbol: Trading symbol
            new_stop_loss: New stop loss price
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.crypto_handler is None:
                logger.error("CryptoHandler not available")
                return False
            
            # Get current position
            position = await self.get_position_info(symbol)
            if not position:
                logger.warning(f"No open position found for {symbol}")
                return False
            
            # Update stop loss (this would depend on exchange API)
            # For now, we'll just log the update
            logger.info(f"Updated stop loss for {symbol} to {new_stop_loss}")
            
            # Update our tracking
            if symbol in self.active_trades:
                self.active_trades[symbol]['stop_loss'] = new_stop_loss
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating stop loss for {symbol}: {str(e)}")
            return False
    
    async def update_take_profit(self, symbol: str, new_take_profit: float) -> bool:
        """
        Update take profit for a position.
        
        Args:
            symbol: Trading symbol
            new_take_profit: New take profit price
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.crypto_handler is None:
                logger.error("CryptoHandler not available")
                return False
            
            # Get current position
            position = await self.get_position_info(symbol)
            if not position:
                logger.warning(f"No open position found for {symbol}")
                return False
            
            # Update take profit (this would depend on exchange API)
            # For now, we'll just log the update
            logger.info(f"Updated take profit for {symbol} to {new_take_profit}")
            
            # Update our tracking
            if symbol in self.active_trades:
                self.active_trades[symbol]['take_profit'] = new_take_profit
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating take profit for {symbol}: {str(e)}")
            return False
    
    async def check_trailing_stop(self, symbol: str, current_price: float) -> bool:
        """
        Check and update trailing stop for a position.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            True if position was closed, False otherwise
        """
        try:
            if not self.trailing_stop_enabled:
                return False
            
            if symbol not in self.trailing_stop_data:
                return False
            
            trailing_data = self.trailing_stop_data[symbol]
            position = await self.get_position_info(symbol)
            
            if not position:
                # Position no longer exists, clean up
                del self.trailing_stop_data[symbol]
                return False
            
            side = position.get('side', '').lower()
            entry_price = position.get('entry_price', 0)
            trailing_distance = trailing_data.get('distance', 0.01)  # 1% trailing distance
            
            if side == 'long':
                # For long positions, update trailing stop if price moves up
                if current_price > trailing_data.get('highest_price', entry_price):
                    new_stop_loss = current_price - (current_price * trailing_distance)
                    if new_stop_loss > trailing_data.get('stop_loss', 0):
                        await self.update_stop_loss(symbol, new_stop_loss)
                        self.trailing_stop_data[symbol]['stop_loss'] = new_stop_loss
                        self.trailing_stop_data[symbol]['highest_price'] = current_price
                        logger.info(f"Updated trailing stop for {symbol} to {new_stop_loss}")
                
                # Check if stop loss was hit
                if current_price <= trailing_data.get('stop_loss', 0):
                    await self.close_position(symbol, "Trailing stop hit")
                    return True
                    
            elif side == 'short':
                # For short positions, update trailing stop if price moves down
                if current_price < trailing_data.get('lowest_price', entry_price):
                    new_stop_loss = current_price + (current_price * trailing_distance)
                    if new_stop_loss < trailing_data.get('stop_loss', float('inf')):
                        await self.update_stop_loss(symbol, new_stop_loss)
                        self.trailing_stop_data[symbol]['stop_loss'] = new_stop_loss
                        self.trailing_stop_data[symbol]['lowest_price'] = current_price
                        logger.info(f"Updated trailing stop for {symbol} to {new_stop_loss}")
                
                # Check if stop loss was hit
                if current_price >= trailing_data.get('stop_loss', float('inf')):
                    await self.close_position(symbol, "Trailing stop hit")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking trailing stop for {symbol}: {str(e)}")
            return False
    
    async def setup_trailing_stop(self, symbol: str, distance: float = 0.01):
        """
        Setup trailing stop for a position.
        
        Args:
            symbol: Trading symbol
            distance: Trailing distance (percentage)
        """
        try:
            position = await self.get_position_info(symbol)
            if not position:
                logger.warning(f"No open position found for {symbol}")
                return
            
            entry_price = position.get('entry_price', 0)
            side = position.get('side', '').lower()
            
            # Initialize trailing stop data
            self.trailing_stop_data[symbol] = {
                'distance': distance,
                'entry_price': entry_price,
                'stop_loss': entry_price * (1 - distance) if side == 'long' else entry_price * (1 + distance),
                'highest_price': entry_price if side == 'long' else 0,
                'lowest_price': entry_price if side == 'short' else float('inf')
            }
            
            logger.info(f"Setup trailing stop for {symbol} with distance {distance}")
            
        except Exception as e:
            logger.error(f"Error setting up trailing stop for {symbol}: {str(e)}")
    
    async def check_scalping_exit(self, symbol: str, current_price: float) -> bool:
        """
        Check if scalping exit conditions are met.
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            True if position should be closed, False otherwise
        """
        try:
            if not self.scalping_enabled:
                return False
            
            position = await self.get_position_info(symbol)
            if not position:
                return False
            
            entry_price = position.get('entry_price', 0)
            side = position.get('side', '').lower()
            
            if side == 'long':
                # Check profit target
                profit_pct = (current_price - entry_price) / entry_price
                if profit_pct >= self.scalping_profit_target:
                    await self.close_position(symbol, "Scalping profit target reached")
                    return True
                
                # Check stop loss
                if profit_pct <= -self.scalping_stop_loss:
                    await self.close_position(symbol, "Scalping stop loss hit")
                    return True
                    
            elif side == 'short':
                # Check profit target
                profit_pct = (entry_price - current_price) / entry_price
                if profit_pct >= self.scalping_profit_target:
                    await self.close_position(symbol, "Scalping profit target reached")
                    return True
                
                # Check stop loss
                if profit_pct <= -self.scalping_stop_loss:
                    await self.close_position(symbol, "Scalping stop loss hit")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking scalping exit for {symbol}: {str(e)}")
            return False
    
    async def manage_positions(self) -> Dict[str, Any]:
        """
        Main position management loop.
        
        Returns:
            Management summary
        """
        try:
            managed_count = 0
            closed_count = 0
            
            # Get all open positions
            positions = await self.get_open_positions()
            
            for position in positions:
                symbol = position.get('symbol')
                if not symbol:
                    continue
                
                # Get current price (this would need to be implemented)
                current_price = position.get('mark_price', 0)
                
                # Check trailing stop
                if await self.check_trailing_stop(symbol, current_price):
                    closed_count += 1
                    continue
                
                # Check scalping exit
                if await self.check_scalping_exit(symbol, current_price):
                    closed_count += 1
                    continue
                
                # Check position timeout
                if self.position_timeout > 0:
                    position_time = position.get('timestamp', 0)
                    if time.time() - position_time > self.position_timeout:
                        await self.close_position(symbol, "Position timeout")
                        closed_count += 1
                        continue
                
                managed_count += 1
            
            return {
                "managed_positions": managed_count,
                "closed_positions": closed_count,
                "total_positions": len(positions)
            }
            
        except Exception as e:
            logger.error(f"Error in position management: {str(e)}")
            return {"error": str(e)}
    
    async def get_position_summary(self) -> Dict[str, Any]:
        """
        Get summary of all positions.
        
        Returns:
            Position summary
        """
        try:
            positions = await self.get_open_positions()
            
            summary = {
                "total_positions": len(positions),
                "positions": [],
                "total_pnl": 0.0,
                "total_volume": 0.0
            }
            
            for position in positions:
                pnl = position.get('pnl', 0)
                volume = position.get('size', 0) * position.get('entry_price', 0)
                
                summary["total_pnl"] += pnl
                summary["total_volume"] += volume
                
                summary["positions"].append({
                    "symbol": position.get('symbol'),
                    "side": position.get('side'),
                    "size": position.get('size'),
                    "entry_price": position.get('entry_price'),
                    "current_price": position.get('mark_price'),
                    "pnl": pnl,
                    "volume": volume
                })
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting position summary: {str(e)}")
            return {"error": str(e)}
    
    def set_crypto_handler(self, crypto_handler: CryptoHandler):
        """Set the crypto handler instance."""
        self.crypto_handler = crypto_handler
        logger.info("CryptoHandler set for CryptoPositionManager")
    
    def set_risk_manager(self, risk_manager: CryptoRiskManager):
        """Set the risk manager instance."""
        self.risk_manager = risk_manager
        logger.info("CryptoRiskManager set for CryptoPositionManager")
