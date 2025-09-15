"""
Crypto Performance Tracker

Handles performance tracking and metrics for the crypto trading bot.
This replaces the MT5-based performance tracker with crypto-specific metrics.
"""

import traceback
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd
import numpy as np

class CryptoPerformanceTracker:
    """
    Handles performance tracking and metrics for the crypto trading bot.

    This class is responsible for:
    - Tracking trade performance metrics
    - Calculating win/loss ratios, drawdowns, etc.
    - Generating performance reports for crypto trading
    """

    def __init__(self, crypto_handler=None, config=None):
        """
        Initialize the CryptoPerformanceTracker.

        Args:
            crypto_handler: CryptoHandler instance for accessing trade data
            config: Configuration dictionary
        """
        self.crypto_handler = crypto_handler
        self.config = config or {}

        # Performance metrics tracking
        self.metrics = {
            "Global": self._initialize_metrics()
        }

        # Trade history storage
        self.trade_history = []
        self.daily_stats = {}
        self.monthly_stats = {}

        # Risk metrics
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        self.peak_balance = 0.0

        logger.info("CryptoPerformanceTracker initialized")

    def _initialize_metrics(self) -> Dict[str, Any]:
        """Initialize metrics dictionary for a strategy."""
        return {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
            "total_profit": 0.0,
            "total_loss": 0.0,
            "net_profit": 0.0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "profit_factor": 0.0,
            "sharpe_ratio": 0.0,
            "max_consecutive_wins": 0,
            "max_consecutive_losses": 0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "avg_trade_duration": 0.0,
            "best_day": 0.0,
            "worst_day": 0.0,
            "total_fees": 0.0,
            "total_volume": 0.0,
            "last_updated": datetime.now()
        }

    def set_crypto_handler(self, crypto_handler):
        """Set the crypto handler instance."""
        self.crypto_handler = crypto_handler
        logger.info("CryptoHandler set for CryptoPerformanceTracker")

    async def update_performance_metrics(self, strategy_name: str = "Global"):
        """
        Update performance metrics for a strategy.

        Args:
            strategy_name: Name of the strategy to update
        """
        try:
            if strategy_name not in self.metrics:
                self.metrics[strategy_name] = self._initialize_metrics()

            # Get trade history (this would need to be implemented)
            trades = await self._get_trade_history(strategy_name)

            if not trades:
                logger.debug(f"No trades found for {strategy_name}")
                return

            # Calculate metrics
            metrics = self._calculate_metrics(trades)
            self.metrics[strategy_name].update(metrics)
            self.metrics[strategy_name]["last_updated"] = datetime.now()

            logger.debug(f"Updated performance metrics for {strategy_name}")

        except Exception as e:
            logger.error(f"Error updating performance metrics for {strategy_name}: {str(e)}")

    async def _get_trade_history(self, strategy_name: str) -> List[Dict[str, Any]]:
        """
        Get trade history for a strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            List of trade dictionaries
        """
        try:
            # This would integrate with the crypto trading system to get trade history
            # For now, return mock data or integrate with database
            return self.trade_history

        except Exception as e:
            logger.error(f"Error getting trade history for {strategy_name}: {str(e)}")
            return []

    def _calculate_metrics(self, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate performance metrics from trades.

        Args:
            trades: List of trade dictionaries

        Returns:
            Dictionary of calculated metrics
        """
        try:
            if not trades:
                return self._initialize_metrics()

            # Basic trade counts
            total_trades = len(trades)
            profits = [trade.get('pnl', 0) for trade in trades]
            winning_trades = sum(1 for p in profits if p > 0)
            losing_trades = sum(1 for p in profits if p < 0)

            # Financial metrics
            total_profit = sum(p for p in profits if p > 0)
            total_loss = abs(sum(p for p in profits if p < 0))
            net_profit = sum(profits)

            # Ratios and averages
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            avg_win = total_profit / winning_trades if winning_trades > 0 else 0
            avg_loss = total_loss / losing_trades if losing_trades > 0 else 0
            profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

            # Extreme values
            largest_win = max(profits) if profits else 0
            largest_loss = min(profits) if profits else 0

            # Sharpe ratio (simplified)
            if len(profits) > 1:
                returns = np.array(profits)
                sharpe_ratio = returns.mean() / returns.std() * np.sqrt(365) if returns.std() > 0 else 0
            else:
                sharpe_ratio = 0

            # Consecutive trades
            consecutive_wins = 0
            consecutive_losses = 0
            max_consecutive_wins = 0
            max_consecutive_losses = 0

            for pnl in profits:
                if pnl > 0:
                    consecutive_wins += 1
                    consecutive_losses = 0
                    max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
                elif pnl < 0:
                    consecutive_losses += 1
                    consecutive_wins = 0
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

            return {
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
                "win_rate": win_rate,
                "total_profit": total_profit,
                "total_loss": total_loss,
                "net_profit": net_profit,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
                "sharpe_ratio": sharpe_ratio,
                "max_consecutive_wins": max_consecutive_wins,
                "max_consecutive_losses": max_consecutive_losses,
                "largest_win": largest_win,
                "largest_loss": largest_loss,
                "total_fees": sum(trade.get('fee', 0) for trade in trades),
                "total_volume": sum(trade.get('volume', 0) for trade in trades)
            }

        except Exception as e:
            logger.error(f"Error calculating metrics: {str(e)}")
            return self._initialize_metrics()

    def add_trade(self, trade: Dict[str, Any], strategy_name: str = "Global"):
        """
        Add a trade to the performance tracking.

        Args:
            trade: Trade dictionary
            strategy_name: Name of the strategy
        """
        try:
            # Add strategy name to trade
            trade['strategy'] = strategy_name
            trade['timestamp'] = datetime.now()

            # Add to trade history
            self.trade_history.append(trade)

            # Update metrics
            asyncio.create_task(self.update_performance_metrics(strategy_name))

            logger.debug(f"Added trade to {strategy_name} performance tracking")

        except Exception as e:
            logger.error(f"Error adding trade: {str(e)}")

    def get_performance_report(self, strategy_name: str = "Global") -> Dict[str, Any]:
        """
        Get performance report for a strategy.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Performance report dictionary
        """
        try:
            if strategy_name not in self.metrics:
                return {"error": f"Strategy {strategy_name} not found"}

            metrics = self.metrics[strategy_name]

            return {
                "strategy": strategy_name,
                "metrics": metrics,
                "summary": {
                    "total_return": metrics["net_profit"],
                    "win_rate_percent": metrics["win_rate"] * 100,
                    "profit_factor": metrics["profit_factor"],
                    "sharpe_ratio": metrics["sharpe_ratio"],
                    "total_trades": metrics["total_trades"],
                    "avg_trade_pnl": metrics["net_profit"] / metrics["total_trades"] if metrics["total_trades"] > 0 else 0
                }
            }

        except Exception as e:
            logger.error(f"Error generating performance report: {str(e)}")
            return {"error": str(e)}

    def get_all_strategies_report(self) -> Dict[str, Any]:
        """
        Get performance report for all strategies.

        Returns:
            Combined performance report
        """
        try:
            strategies_report = {}
            total_metrics = self._initialize_metrics()

            for strategy_name, metrics in self.metrics.items():
                strategies_report[strategy_name] = self.get_performance_report(strategy_name)

                # Aggregate totals
                for key in total_metrics:
                    if key in metrics and isinstance(metrics[key], (int, float)):
                        total_metrics[key] += metrics[key]

            return {
                "strategies": strategies_report,
                "total": total_metrics,
                "summary": f"Tracking {len(self.metrics)} strategies with {total_metrics['total_trades']} total trades"
            }

        except Exception as e:
            logger.error(f"Error generating all strategies report: {str(e)}")
            return {"error": str(e)}

    def reset_metrics(self, strategy_name: str = "Global"):
        """Reset metrics for a strategy."""
        try:
            if strategy_name in self.metrics:
                self.metrics[strategy_name] = self._initialize_metrics()
                logger.info(f"Reset metrics for {strategy_name}")
        except Exception as e:
            logger.error(f"Error resetting metrics for {strategy_name}: {str(e)}")

    def export_to_csv(self, filename: str, strategy_name: str = "Global"):
        """
        Export trade history to CSV.

        Args:
            filename: Output filename
            strategy_name: Name of the strategy to export
        """
        try:
            if strategy_name == "Global":
                trades = self.trade_history
            else:
                trades = [t for t in self.trade_history if t.get('strategy') == strategy_name]

            if trades:
                df = pd.DataFrame(trades)
                df.to_csv(filename, index=False)
                logger.info(f"Exported {len(trades)} trades to {filename}")
            else:
                logger.warning(f"No trades to export for {strategy_name}")

        except Exception as e:
            logger.error(f"Error exporting to CSV: {str(e)}")
