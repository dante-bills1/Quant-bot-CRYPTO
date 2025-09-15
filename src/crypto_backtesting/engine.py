"""
Crypto Backtesting Engine

This module provides backtesting functionality specifically designed for crypto trading,
replacing the MT5-based backtesting with crypto-specific trade simulation and performance metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import asyncio
from loguru import logger

from src.trading_bot import SignalGenerator

class CryptoBacktester:
    """
    Crypto backtesting engine for testing trading strategies.
    
    This class handles:
    - Strategy execution simulation
    - Trade tracking and management
    - Performance metrics calculation
    - Risk management simulation
    """
    
    def __init__(
        self,
        strategy: SignalGenerator,
        initial_balance: float = 10000,
        commission: float = 0.001,
        slippage: float = 0.0005,
        max_leverage: float = 10.0
    ):
        """
        Initialize the crypto backtester.
        
        Args:
            strategy: Strategy instance to test
            initial_balance: Starting balance in base currency
            commission: Commission rate (0.001 = 0.1%)
            slippage: Slippage rate (0.0005 = 0.05%)
            max_leverage: Maximum leverage allowed
        """
        self.strategy = strategy
        self.initial_balance = initial_balance
        self.commission = commission
        self.slippage = slippage
        self.max_leverage = max_leverage
        
        # State tracking
        self.balance = initial_balance
        self.equity = initial_balance
        self.positions = {}
        self.trades = []
        self.orders = []
        
        # Performance tracking
        self.peak_balance = initial_balance
        self.max_drawdown = 0.0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        self.total_loss = 0.0
        
        # Risk management
        self.max_position_size = 0.1  # 10% of balance per position
        self.stop_loss_pct = 0.02  # 2% stop loss
        self.take_profit_pct = 0.04  # 4% take profit
        
        logger.info(f"CryptoBacktester initialized with balance: ${initial_balance:,.2f}")
    
    async def run(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Run the backtest on the provided data.
        
        Args:
            data: DataFrame with OHLCV data
            
        Returns:
            Dictionary with backtest results
        """
        try:
            logger.info(f"Starting backtest with {len(data)} data points")
            
            # Initialize strategy
            await self.strategy.initialize()
            
            # Process each data point
            for i, (timestamp, row) in enumerate(data.iterrows()):
                current_data = {
                    'timestamp': timestamp,
                    'open': row['open'],
                    'high': row['high'],
                    'low': row['low'],
                    'close': row['close'],
                    'volume': row['volume']
                }
                
                # Update equity
                self._update_equity(current_data)
                
                # Check for stop loss and take profit
                await self._check_exit_conditions(current_data)
                
                # Generate signals
                signals = await self.strategy.generate_signals(current_data)
                
                # Process signals
                for signal in signals:
                    await self._process_signal(signal, current_data)
                
                # Update positions
                self._update_positions(current_data)
                
                # Log progress
                if i % 1000 == 0:
                    logger.info(f"Processed {i}/{len(data)} data points")
            
            # Close all remaining positions
            await self._close_all_positions(data.iloc[-1])
            
            # Calculate final results
            results = self._calculate_results()
            
            logger.info("Backtest completed successfully")
            return results
            
        except Exception as e:
            logger.error(f"Backtest failed: {str(e)}")
            raise
    
    async def _process_signal(self, signal: Dict[str, Any], current_data: Dict[str, Any]):
        """
        Process a trading signal.
        
        Args:
            signal: Signal dictionary
            current_data: Current market data
        """
        try:
            action = signal.get('action', '').lower()
            confidence = signal.get('confidence', 0)
            
            if action == 'hold' or confidence < 0.6:
                return
            
            symbol = signal.get('symbol', 'BTC/USDT:USDT')
            current_price = current_data['close']
            
            if action == 'buy':
                await self._open_long_position(symbol, current_price, signal)
            elif action == 'sell':
                await self._open_short_position(symbol, current_price, signal)
                
        except Exception as e:
            logger.error(f"Error processing signal: {str(e)}")
    
    async def _open_long_position(self, symbol: str, price: float, signal: Dict[str, Any]):
        """
        Open a long position.
        
        Args:
            symbol: Trading symbol
            price: Entry price
            signal: Signal dictionary
        """
        try:
            # Check if position already exists
            if symbol in self.positions:
                return
            
            # Calculate position size
            position_size = self._calculate_position_size(price)
            if position_size <= 0:
                return
            
            # Calculate costs
            cost = position_size * price
            commission_cost = cost * self.commission
            total_cost = cost + commission_cost
            
            # Check if we have enough balance
            if total_cost > self.balance:
                logger.warning(f"Insufficient balance for {symbol} long position")
                return
            
            # Create position
            position = {
                'symbol': symbol,
                'side': 'long',
                'size': position_size,
                'entry_price': price,
                'entry_time': signal.get('timestamp', datetime.now()),
                'stop_loss': price * (1 - self.stop_loss_pct),
                'take_profit': price * (1 + self.take_profit_pct),
                'unrealized_pnl': 0.0,
                'signal': signal
            }
            
            self.positions[symbol] = position
            self.balance -= total_cost
            
            # Create trade record
            trade = {
                'symbol': symbol,
                'side': 'long',
                'size': position_size,
                'entry_price': price,
                'entry_time': position['entry_time'],
                'commission': commission_cost,
                'signal': signal
            }
            
            self.trades.append(trade)
            self.total_trades += 1
            
            logger.debug(f"Opened long position: {symbol} {position_size} @ {price}")
            
        except Exception as e:
            logger.error(f"Error opening long position: {str(e)}")
    
    async def _open_short_position(self, symbol: str, price: float, signal: Dict[str, Any]):
        """
        Open a short position.
        
        Args:
            symbol: Trading symbol
            price: Entry price
            signal: Signal dictionary
        """
        try:
            # Check if position already exists
            if symbol in self.positions:
                return
            
            # Calculate position size
            position_size = self._calculate_position_size(price)
            if position_size <= 0:
                return
            
            # Calculate costs
            cost = position_size * price
            commission_cost = cost * self.commission
            total_cost = cost + commission_cost
            
            # Check if we have enough balance
            if total_cost > self.balance:
                logger.warning(f"Insufficient balance for {symbol} short position")
                return
            
            # Create position
            position = {
                'symbol': symbol,
                'side': 'short',
                'size': position_size,
                'entry_price': price,
                'entry_time': signal.get('timestamp', datetime.now()),
                'stop_loss': price * (1 + self.stop_loss_pct),
                'take_profit': price * (1 - self.take_profit_pct),
                'unrealized_pnl': 0.0,
                'signal': signal
            }
            
            self.positions[symbol] = position
            self.balance -= total_cost
            
            # Create trade record
            trade = {
                'symbol': symbol,
                'side': 'short',
                'size': position_size,
                'entry_price': price,
                'entry_time': position['entry_time'],
                'commission': commission_cost,
                'signal': signal
            }
            
            self.trades.append(trade)
            self.total_trades += 1
            
            logger.debug(f"Opened short position: {symbol} {position_size} @ {price}")
            
        except Exception as e:
            logger.error(f"Error opening short position: {str(e)}")
    
    def _calculate_position_size(self, price: float) -> float:
        """
        Calculate position size based on risk management rules.
        
        Args:
            price: Current price
            
        Returns:
            Position size
        """
        try:
            # Use a percentage of available balance
            max_cost = self.balance * self.max_position_size
            position_size = max_cost / price
            
            # Apply minimum position size
            min_size = 0.001
            if position_size < min_size:
                return 0.0
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0.0
    
    async def _check_exit_conditions(self, current_data: Dict[str, Any]):
        """
        Check for stop loss and take profit conditions.
        
        Args:
            current_data: Current market data
        """
        try:
            current_price = current_data['close']
            positions_to_close = []
            
            for symbol, position in self.positions.items():
                side = position['side']
                entry_price = position['entry_price']
                stop_loss = position['stop_loss']
                take_profit = position['take_profit']
                
                should_close = False
                close_reason = ""
                
                if side == 'long':
                    if current_price <= stop_loss:
                        should_close = True
                        close_reason = "Stop loss"
                    elif current_price >= take_profit:
                        should_close = True
                        close_reason = "Take profit"
                else:  # short
                    if current_price >= stop_loss:
                        should_close = True
                        close_reason = "Stop loss"
                    elif current_price <= take_profit:
                        should_close = True
                        close_reason = "Take profit"
                
                if should_close:
                    positions_to_close.append((symbol, close_reason))
            
            # Close positions
            for symbol, reason in positions_to_close:
                await self._close_position(symbol, current_price, reason)
                
        except Exception as e:
            logger.error(f"Error checking exit conditions: {str(e)}")
    
    async def _close_position(self, symbol: str, price: float, reason: str):
        """
        Close a position.
        
        Args:
            symbol: Trading symbol
            price: Exit price
            reason: Reason for closing
        """
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            side = position['side']
            size = position['size']
            entry_price = position['entry_price']
            
            # Calculate P&L
            if side == 'long':
                pnl = (price - entry_price) * size
            else:  # short
                pnl = (entry_price - price) * size
            
            # Calculate commission
            cost = size * price
            commission = cost * self.commission
            net_pnl = pnl - commission
            
            # Update balance
            self.balance += net_pnl
            
            # Update trade record
            trade = {
                'symbol': symbol,
                'side': side,
                'size': size,
                'entry_price': entry_price,
                'exit_price': price,
                'exit_time': datetime.now(),
                'pnl': net_pnl,
                'commission': commission,
                'reason': reason
            }
            
            self.trades.append(trade)
            
            # Update statistics
            if net_pnl > 0:
                self.winning_trades += 1
                self.total_profit += net_pnl
            else:
                self.losing_trades += 1
                self.total_loss += abs(net_pnl)
            
            # Remove position
            del self.positions[symbol]
            
            logger.debug(f"Closed {side} position: {symbol} @ {price} (P&L: ${net_pnl:.2f})")
            
        except Exception as e:
            logger.error(f"Error closing position: {str(e)}")
    
    async def _close_all_positions(self, last_data: pd.Series):
        """
        Close all remaining positions at the end of backtest.
        
        Args:
            last_data: Last data point
        """
        try:
            current_price = last_data['close']
            
            for symbol in list(self.positions.keys()):
                await self._close_position(symbol, current_price, "End of backtest")
                
        except Exception as e:
            logger.error(f"Error closing all positions: {str(e)}")
    
    def _update_equity(self, current_data: Dict[str, Any]):
        """
        Update equity based on current positions.
        
        Args:
            current_data: Current market data
        """
        try:
            current_price = current_data['close']
            unrealized_pnl = 0.0
            
            for symbol, position in self.positions.items():
                side = position['side']
                size = position['size']
                entry_price = position['entry_price']
                
                if side == 'long':
                    pnl = (current_price - entry_price) * size
                else:  # short
                    pnl = (entry_price - current_price) * size
                
                position['unrealized_pnl'] = pnl
                unrealized_pnl += pnl
            
            self.equity = self.balance + unrealized_pnl
            
            # Update peak balance and drawdown
            if self.equity > self.peak_balance:
                self.peak_balance = self.equity
            
            drawdown = (self.peak_balance - self.equity) / self.peak_balance
            if drawdown > self.max_drawdown:
                self.max_drawdown = drawdown
                
        except Exception as e:
            logger.error(f"Error updating equity: {str(e)}")
    
    def _update_positions(self, current_data: Dict[str, Any]):
        """
        Update position information.
        
        Args:
            current_data: Current market data
        """
        try:
            current_price = current_data['close']
            
            for symbol, position in self.positions.items():
                side = position['side']
                size = position['size']
                entry_price = position['entry_price']
                
                if side == 'long':
                    pnl = (current_price - entry_price) * size
                else:  # short
                    pnl = (entry_price - current_price) * size
                
                position['unrealized_pnl'] = pnl
                
        except Exception as e:
            logger.error(f"Error updating positions: {str(e)}")
    
    def _calculate_results(self) -> Dict[str, Any]:
        """
        Calculate backtest results and performance metrics.
        
        Returns:
            Dictionary with results
        """
        try:
            # Basic metrics
            final_balance = self.balance
            total_return = (final_balance - self.initial_balance) / self.initial_balance
            
            # Trade metrics
            total_trades = len([t for t in self.trades if 'exit_price' in t])
            winning_trades = self.winning_trades
            losing_trades = self.losing_trades
            
            win_rate = winning_trades / max(total_trades, 1)
            
            # Profit factor
            profit_factor = self.total_profit / max(self.total_loss, 0.01)
            
            # Sharpe ratio (simplified)
            if total_trades > 1:
                returns = [t.get('pnl', 0) for t in self.trades if 'pnl' in t]
                if returns:
                    mean_return = np.mean(returns)
                    std_return = np.std(returns)
                    sharpe_ratio = mean_return / max(std_return, 0.01) * np.sqrt(252)  # Annualized
                else:
                    sharpe_ratio = 0.0
            else:
                sharpe_ratio = 0.0
            
            # Average trade metrics
            avg_win = self.total_profit / max(winning_trades, 1)
            avg_loss = self.total_loss / max(losing_trades, 1)
            
            results = {
                'initial_balance': self.initial_balance,
                'final_balance': final_balance,
                'total_return': total_return,
                'max_drawdown': self.max_drawdown,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'sharpe_ratio': sharpe_ratio,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'total_profit': self.total_profit,
                'total_loss': self.total_loss,
                'trades': self.trades
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error calculating results: {str(e)}")
            return {}
