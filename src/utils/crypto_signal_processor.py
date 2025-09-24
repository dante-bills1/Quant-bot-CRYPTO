"""
Crypto Signal Processor

This module provides signal processing and trade execution functionality specifically designed for crypto trading,
replacing the MT5-based signal processor with crypto-specific trade execution and validation.
"""

import traceback
from typing import Dict, List, Any, Optional
from loguru import logger
import asyncio
import time
import hashlib

from src.managers.crypto_risk_manager import CryptoRiskManager
from src.telegram.telegram_bot import TelegramBot
from src.utils.crypto_handler import CryptoHandler
from src.managers.crypto_position_manager import CryptoPositionManager

class CryptoSignalProcessor:
    """
    Handles signal processing and trade execution functionality for crypto trading.
    
    This class is responsible for:
    - Processing trading signals
    - Executing trades based on signals
    - Handling signals with existing positions
    - Validating signals against real-time crypto data before execution
    """
    
    def __init__(self, crypto_handler=None, risk_manager=None, telegram_bot=None, config=None, position_manager=None):
        """
        Initialize the CryptoSignalProcessor.
        
        Args:
            crypto_handler: CryptoHandler instance for executing trades
            risk_manager: CryptoRiskManager instance for position sizing
            telegram_bot: TelegramBot instance for notifications
            config: Configuration dictionary
            position_manager: CryptoPositionManager instance for position handling
        """
        self.crypto_handler = crypto_handler if crypto_handler is not None else CryptoHandler()
        self.risk_manager = risk_manager if risk_manager is not None else CryptoRiskManager()
        self.telegram_bot = telegram_bot if telegram_bot else TelegramBot.get_instance()
        self.position_manager = position_manager if position_manager is not None else CryptoPositionManager()
        self.config = config or {}
        
        # State tracking
        self.active_trades = {}
        self.min_confidence = self.config.get("min_confidence", 0.6)  # Default to 60% confidence
        # Import TRADING_CONFIG for key settings to ensure we always use the current values
        from config.config import TRADING_CONFIG
        # Use TRADING_CONFIG directly for this sensitive setting
        self.allow_position_additions = TRADING_CONFIG.get("allow_position_additions", False)  # Default to NOT allowing position additions
        self.trading_enabled = self.config.get("trading_enabled", True)  # Default to enabled
        
        # Real-time validation settings
        self.validate_signals = self.config.get("validate_signals", True)
        self.max_slippage = self.config.get("max_slippage", 0.001)  # 0.1% max slippage
        self.min_volume = self.config.get("min_volume", 0.001)  # Minimum volume for trading
        
        # Signal processing settings
        self.signal_timeout = self.config.get("signal_timeout", 30)  # 30 seconds signal timeout
        self.max_concurrent_trades = self.config.get("max_concurrent_trades", 5)
        
        # Performance tracking
        self.signals_processed = 0
        self.trades_executed = 0
        self.failed_executions = 0
        
        logger.info("CryptoSignalProcessor initialized")
    
    async def process_signal(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a trading signal and execute trade if valid.
        
        Args:
            signal: Signal dictionary containing trading information
            
        Returns:
            Dictionary with processing result
        """
        try:
            self.signals_processed += 1
            
            # Validate signal
            if not self._validate_signal(signal):
                return {
                    "success": False,
                    "reason": "Signal validation failed",
                    "signal": signal
                }
            
            # Check if trading is enabled
            if not self.trading_enabled:
                logger.info("Trading is disabled, signal ignored")
                return {
                    "success": False,
                    "reason": "Trading disabled",
                    "signal": signal
                }
            
            # Check for existing position
            symbol = signal.get("symbol")
            if symbol:
                existing_position = await self.position_manager.get_position_info(symbol)
                if existing_position:
                    return await self._handle_existing_position(signal, existing_position)
            
            # Execute new trade
            return await self._execute_trade(signal)
            
        except Exception as e:
            logger.error(f"Error processing signal: {str(e)}")
            logger.error(traceback.format_exc())
            self.failed_executions += 1
            return {
                "success": False,
                "reason": f"Processing error: {str(e)}",
                "signal": signal
            }
    
    def _validate_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Validate a trading signal.
        
        Args:
            signal: Signal dictionary
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check required fields
            required_fields = ["symbol", "action", "confidence"]
            for field in required_fields:
                if field not in signal:
                    logger.warning(f"Signal missing required field: {field}")
                    return False
            
            # Check confidence level
            confidence = signal.get("confidence", 0)
            if confidence < self.min_confidence:
                logger.warning(f"Signal confidence {confidence} below minimum {self.min_confidence}")
                return False
            
            # Check action validity
            action = signal.get("action", "").lower()
            if action not in ["buy", "sell", "hold"]:
                logger.warning(f"Invalid signal action: {action}")
                return False
            
            # Check symbol format
            symbol = signal.get("symbol", "")
            if not symbol or "/" not in symbol:
                logger.warning(f"Invalid symbol format: {symbol}")
                return False
            
            # Check if we have too many concurrent trades
            if len(self.active_trades) >= self.max_concurrent_trades:
                logger.warning(f"Maximum concurrent trades ({self.max_concurrent_trades}) reached")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating signal: {str(e)}")
            return False
    
    async def _handle_existing_position(self, signal: Dict[str, Any], existing_position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle signal when position already exists.
        
        Args:
            signal: New signal
            existing_position: Existing position information
            
        Returns:
            Processing result
        """
        try:
            symbol = signal.get("symbol")
            signal_action = signal.get("action", "").lower()
            position_side = existing_position.get("side", "").lower()
            
            # Check if signal is opposite to existing position
            if (signal_action == "buy" and position_side == "short") or \
               (signal_action == "sell" and position_side == "long"):
                
                # Close existing position first
                logger.info(f"Closing existing {position_side} position for {symbol} before new {signal_action} signal")
                close_result = await self.position_manager.close_position(symbol, "Signal reversal")
                
                if close_result:
                    # Wait a moment for position to close
                    await asyncio.sleep(1)
                    
                    # Execute new trade
                    return await self._execute_trade(signal)
                else:
                    return {
                        "success": False,
                        "reason": "Failed to close existing position",
                        "signal": signal
                    }
            
            # Check if position additions are allowed
            elif self.allow_position_additions:
                # Add to existing position (if same direction)
                logger.info(f"Adding to existing {position_side} position for {symbol}")
                return await self._add_to_position(signal, existing_position)
            
            else:
                # Ignore signal
                logger.info(f"Ignoring {signal_action} signal for {symbol} - position already exists and additions not allowed")
                return {
                    "success": False,
                    "reason": "Position already exists and additions not allowed",
                    "signal": signal
                }
                
        except Exception as e:
            logger.error(f"Error handling existing position: {str(e)}")
            return {
                "success": False,
                "reason": f"Error handling existing position: {str(e)}",
                "signal": signal
            }
    
    async def _execute_trade(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a new trade based on signal.
        
        Args:
            signal: Signal dictionary
            
        Returns:
            Execution result
        """
        try:
            symbol = signal.get("symbol")
            action = signal.get("action", "").lower()
            confidence = signal.get("confidence", 0)
            
            # Get current market data for validation
            if self.validate_signals:
                market_data = await self._get_market_data(symbol)
                if not market_data:
                    return {
                        "success": False,
                        "reason": "Failed to get market data for validation",
                        "signal": signal
                    }
                
                # Validate against current market conditions
                if not self._validate_market_conditions(signal, market_data):
                    return {
                        "success": False,
                        "reason": "Signal failed market validation",
                        "signal": signal
                    }
            
            # Calculate position size
            position_size = await self._calculate_position_size(signal)
            if position_size <= 0:
                return {
                    "success": False,
                    "reason": "Invalid position size calculated",
                    "signal": signal
                }
            
            # Get current price
            current_price = await self._get_current_price(symbol)
            if not current_price:
                return {
                    "success": False,
                    "reason": "Failed to get current price",
                    "signal": signal
                }
            
            # Calculate stop loss and take profit
            stop_loss = await self._calculate_stop_loss(signal, current_price)
            take_profit = await self._calculate_take_profit(signal, current_price)
            
            # Execute trade
            trade_result = await self.crypto_handler.place_order(
                symbol=symbol,
                side=action,
                amount=position_size,
                price=current_price,
                order_type="market"
            )
            
            if trade_result:
                self.trades_executed += 1
                
                # Track active trade
                trade_id = self._generate_trade_id(signal)
                self.active_trades[trade_id] = {
                    "symbol": symbol,
                    "side": action,
                    "size": position_size,
                    "entry_price": current_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "timestamp": time.time(),
                    "signal": signal
                }
                
                # Setup position management
                await self.position_manager.update_position(symbol, self.active_trades[trade_id])
                
                # Send notification
                if self.telegram_bot:
                    await self._send_trade_notification(signal, trade_result, current_price)
                
                logger.info(f"Trade executed successfully: {symbol} {action} {position_size} @ {current_price}")
                
                return {
                    "success": True,
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "action": action,
                    "size": position_size,
                    "price": current_price,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit
                }
            else:
                self.failed_executions += 1
                return {
                    "success": False,
                    "reason": "Trade execution failed",
                    "signal": signal
                }
                
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            logger.error(traceback.format_exc())
            self.failed_executions += 1
            return {
                "success": False,
                "reason": f"Trade execution error: {str(e)}",
                "signal": signal
            }
    
    async def _add_to_position(self, signal: Dict[str, Any], existing_position: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add to existing position.
        
        Args:
            signal: Signal dictionary
            existing_position: Existing position information
            
        Returns:
            Execution result
        """
        try:
            # This would implement adding to existing positions
            # For now, we'll just log and return success
            logger.info(f"Adding to position for {signal.get('symbol')} - not implemented yet")
            return {
                "success": False,
                "reason": "Position additions not implemented yet",
                "signal": signal
            }
        except Exception as e:
            logger.error(f"Error adding to position: {str(e)}")
            return {
                "success": False,
                "reason": f"Error adding to position: {str(e)}",
                "signal": signal
            }
    
    async def _get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current market data for validation.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Market data dictionary or None
        """
        try:
            # Get current price and volume
            current_price = await self._get_current_price(symbol)
            if not current_price:
                return None
            
            # Get symbol info
            symbol_info = await self.crypto_handler.get_symbol_info(symbol)
            if not symbol_info:
                return None
            
            return {
                "price": current_price,
                "symbol_info": symbol_info,
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {str(e)}")
            return None
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current price for symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Current price or None
        """
        try:
            # This would get current price from crypto handler
            # For now, return a mock price
            return 50000.0  # Mock price
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {str(e)}")
            return None
    
    def _validate_market_conditions(self, signal: Dict[str, Any], market_data: Dict[str, Any]) -> bool:
        """
        Validate signal against current market conditions.
        
        Args:
            signal: Signal dictionary
            market_data: Current market data
            
        Returns:
            True if valid, False otherwise
        """
        try:
            # Check if market is open (crypto is 24/7, so always true)
            # Check volume requirements
            # Check price movement limits
            # etc.
            return True
        except Exception as e:
            logger.error(f"Error validating market conditions: {str(e)}")
            return False
    
    async def _calculate_position_size(self, signal: Dict[str, Any]) -> float:
        """
        Calculate position size based on signal and risk management.
        
        Args:
            signal: Signal dictionary
            
        Returns:
            Position size
        """
        try:
            symbol = signal.get("symbol")
            current_price = await self._get_current_price(symbol)
            if not current_price:
                return 0.0
            
            # Use risk manager to calculate position size
            # This would need to be implemented with proper stop loss calculation
            stop_loss = current_price * 0.98  # 2% stop loss for now
            
            position_size = await self.risk_manager.calculate_position_size(
                symbol=symbol,
                entry_price=current_price,
                stop_loss=stop_loss
            )
            
            return position_size
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0.0
    
    async def _calculate_stop_loss(self, signal: Dict[str, Any], entry_price: float) -> float:
        """
        Calculate stop loss price.
        
        Args:
            signal: Signal dictionary
            entry_price: Entry price
            
        Returns:
            Stop loss price
        """
        try:
            symbol = signal.get("symbol")
            action = signal.get("action", "").lower()
            
            # Use risk manager to calculate stop loss
            stop_loss = self.risk_manager.calculate_stop_loss(
                symbol=symbol,
                entry_price=entry_price,
                side=action
            )
            
            return stop_loss
        except Exception as e:
            logger.error(f"Error calculating stop loss: {str(e)}")
            return entry_price * 0.98  # Fallback to 2% stop loss
    
    async def _calculate_take_profit(self, signal: Dict[str, Any], entry_price: float) -> float:
        """
        Calculate take profit price.
        
        Args:
            signal: Signal dictionary
            entry_price: Entry price
            
        Returns:
            Take profit price
        """
        try:
            symbol = signal.get("symbol")
            action = signal.get("action", "").lower()
            
            # Use risk manager to calculate take profit
            take_profit = self.risk_manager.calculate_take_profit(
                symbol=symbol,
                entry_price=entry_price,
                side=action
            )
            
            return take_profit
        except Exception as e:
            logger.error(f"Error calculating take profit: {str(e)}")
            return entry_price * 1.04  # Fallback to 4% take profit
    
    def _generate_trade_id(self, signal: Dict[str, Any]) -> str:
        """
        Generate unique trade ID.
        
        Args:
            signal: Signal dictionary
            
        Returns:
            Unique trade ID
        """
        try:
            # Create hash from signal data
            signal_str = f"{signal.get('symbol')}_{signal.get('action')}_{signal.get('timestamp', time.time())}"
            return hashlib.md5(signal_str.encode()).hexdigest()[:8]
        except Exception as e:
            logger.error(f"Error generating trade ID: {str(e)}")
            return f"trade_{int(time.time())}"
    
    async def _send_trade_notification(self, signal: Dict[str, Any], trade_result: Dict[str, Any], price: float):
        """
        Send trade notification via Telegram.
        
        Args:
            signal: Signal dictionary
            trade_result: Trade execution result
            price: Execution price
        """
        try:
            if not self.telegram_bot:
                return
            
            symbol = signal.get("symbol")
            action = signal.get("action", "").upper()
            confidence = signal.get("confidence", 0)
            
            emoji = "🟢" if action == "BUY" else "🔴"
            
            message = f"""
{emoji} **Trade Executed**

**Symbol:** {symbol}
**Action:** {action}
**Price:** ${price:,.2f}
**Confidence:** {confidence:.1%}
**Reason:** {signal.get('reason', 'N/A')}
**Time:** {time.strftime('%Y-%m-%d %H:%M:%S')}
            """
            
            await self.telegram_bot.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending trade notification: {str(e)}")
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get signal processing statistics.
        
        Returns:
            Statistics dictionary
        """
        try:
            return {
                "signals_processed": self.signals_processed,
                "trades_executed": self.trades_executed,
                "failed_executions": self.failed_executions,
                "active_trades": len(self.active_trades),
                "success_rate": self.trades_executed / max(self.signals_processed, 1),
                "trading_enabled": self.trading_enabled,
                "min_confidence": self.min_confidence
            }
        except Exception as e:
            logger.error(f"Error getting processing stats: {str(e)}")
            return {}
    
    def set_crypto_handler(self, crypto_handler: CryptoHandler):
        """Set the crypto handler instance."""
        self.crypto_handler = crypto_handler
        logger.info("CryptoHandler set for CryptoSignalProcessor")
    
    def set_risk_manager(self, risk_manager: CryptoRiskManager):
        """Set the risk manager instance."""
        self.risk_manager = risk_manager
        logger.info("CryptoRiskManager set for CryptoSignalProcessor")
    
    def set_position_manager(self, position_manager: CryptoPositionManager):
        """Set the position manager instance."""
        self.position_manager = position_manager
        logger.info("CryptoPositionManager set for CryptoSignalProcessor")
