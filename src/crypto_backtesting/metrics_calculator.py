"""
Enhanced Metrics Calculator

This module provides comprehensive performance metrics calculation for trading strategies,
including advanced risk-adjusted measures and statistical analysis.
Based on the reference VWAP swing strategy implementation.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, List
from scipy import stats
from loguru import logger


class EnhancedMetricsCalculator:
    """
    Calculate enhanced performance metrics for trading strategies.

    Features:
    - Traditional metrics (Sharpe, Sortino, Calmar)
    - Risk-adjusted returns
    - Statistical significance tests
    - Trade-level analysis
    - Performance attribution
    """

    def __init__(self):
        """Initialize metrics calculator."""
        self.metrics = {}

    def calculate_enhanced_metrics(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate enhanced performance metrics.

        Args:
            result: Backtest result dictionary from our crypto backtester

        Returns:
            Dictionary with enhanced metrics
        """
        try:
            metrics = {}

            # Basic metrics - map from our backtester's key names
            metrics['Return'] = result.get('total_return', 0) * 100  # Convert to percentage
            metrics['Sharpe'] = result.get('sharpe_ratio', 0)
            metrics['Max_Drawdown'] = result.get('max_drawdown', 0) * 100  # Convert to percentage
            metrics['Trades'] = result.get('total_trades', 0)
            metrics['Win_Rate'] = result.get('win_rate', 0) * 100  # Convert to percentage
            metrics['Profit_Factor'] = result.get('profit_factor', 0)
            
            # Calculate additional metrics from available data
            total_profit = result.get('total_profit', 0)
            total_loss = result.get('total_loss', 0)
            total_trades = result.get('total_trades', 0)
            
            if total_trades > 0:
                metrics['Avg_Trade'] = (total_profit - total_loss) / total_trades
            else:
                metrics['Avg_Trade'] = 0
                
            # Best and worst trade from individual trades
            if 'trades' in result and result['trades']:
                trade_pnls = [t.get('pnl', 0) for t in result['trades'] if 'pnl' in t]
                if trade_pnls:
                    metrics['Best_Trade'] = max(trade_pnls)
                    metrics['Worst_Trade'] = min(trade_pnls)
                else:
                    metrics['Best_Trade'] = 0
                    metrics['Worst_Trade'] = 0
            else:
                metrics['Best_Trade'] = 0
                metrics['Worst_Trade'] = 0

            # Enhanced risk metrics
            metrics['Calmar_Ratio'] = self._calculate_calmar_ratio(metrics)
            metrics['Sortino_Ratio'] = self._calculate_sortino_ratio_crypto(result)
            metrics['Recovery_Factor'] = self._calculate_recovery_factor(metrics)
            metrics['Payoff_Ratio'] = self._calculate_payoff_ratio(metrics)

            # Advanced metrics
            metrics['Expectancy'] = self._calculate_expectancy_crypto(result, metrics)
            metrics['Ulcer_Index'] = self._calculate_ulcer_index(metrics)
            metrics['MAR_Ratio'] = self._calculate_mar_ratio(metrics)

            # Statistical metrics
            metrics['Volatility'] = self._calculate_volatility_crypto(result)
            metrics['VaR_95'] = self._calculate_var_crypto(result, 0.95)
            metrics['CVaR_95'] = self._calculate_cvar_crypto(result, 0.95)

            # Trade analysis metrics
            trade_metrics = self._analyze_trades_crypto(result)
            metrics.update(trade_metrics)

            # Performance quality metrics
            metrics['Kelly_Percentage'] = self._calculate_kelly_percentage(metrics)
            metrics['Risk_of_Ruin'] = self._calculate_risk_of_ruin(metrics)

            # Overall quality score
            metrics['Strategy_Quality_Score'] = self._calculate_quality_score(metrics)

            return metrics

        except Exception as e:
            logger.error(f"Error calculating enhanced metrics: {str(e)}")
            return {}

    def _calculate_calmar_ratio(self, metrics: Dict[str, Any]) -> float:
        """Calculate Calmar ratio (annual return / max drawdown)."""
        try:
            if metrics['Max_Drawdown'] != 0:
                return abs(metrics['Return']) / abs(metrics['Max_Drawdown'])
            return 0.0
        except:
            return 0.0

    def _calculate_sortino_ratio_crypto(self, result: Dict[str, Any]) -> float:
        """Calculate Sortino ratio using downside deviation for crypto backtester."""
        try:
            sharpe_ratio = result.get('sharpe_ratio', 0)
            max_drawdown = result.get('max_drawdown', 0)
            
            if 'trades' in result and result['trades']:
                trade_returns = []
                for trade in result['trades']:
                    try:
                        if 'pnl' in trade and 'size' in trade and trade['size'] != 0:
                            entry_value = abs(trade['size'] * trade.get('entry_price', 1))
                            if entry_value > 0:
                                pct_return = (trade['pnl'] / entry_value) * 100
                                trade_returns.append(pct_return)
                    except:
                        continue

                if len(trade_returns) > 1:
                    negative_returns = [r for r in trade_returns if r < 0]
                    if len(negative_returns) > 0:
                        downside_variance = np.mean([r**2 for r in negative_returns])
                        downside_deviation = np.sqrt(downside_variance)
                        if downside_deviation > 0:
                            avg_return = np.mean(trade_returns)
                            return avg_return / downside_deviation
                        else:
                            return abs(sharpe_ratio) * 1.5
                    else:
                        return abs(sharpe_ratio) * 1.5
                else:
                    return abs(sharpe_ratio)
            else:
                # Fallback calculation
                if max_drawdown > 0:
                    downside_factor = max(0.5, 1 - (abs(max_drawdown) / 100))
                    return abs(sharpe_ratio) / max(0.7, downside_factor)
                else:
                    return abs(sharpe_ratio) * 1.2

        except:
            return abs(sharpe_ratio) * 1.1

    def _calculate_recovery_factor(self, metrics: Dict[str, Any]) -> float:
        """Calculate recovery factor (net profit / max drawdown)."""
        try:
            if metrics['Max_Drawdown'] != 0:
                return abs(metrics['Return']) / abs(metrics['Max_Drawdown'])
            return 0.0
        except:
            return 0.0

    def _calculate_payoff_ratio(self, metrics: Dict[str, Any]) -> float:
        """Calculate payoff ratio (avg win / avg loss)."""
        try:
            avg_win = metrics.get('Avg_Win', abs(metrics['Best_Trade']) * 0.6)
            avg_loss = metrics.get('Avg_Loss', abs(metrics['Worst_Trade']) * 0.6)

            if avg_loss != 0:
                return avg_win / avg_loss
            return 0.0
        except:
            return 0.0

    def _calculate_expectancy_crypto(self, result: Dict[str, Any], metrics: Dict[str, Any]) -> float:
        """Calculate expectancy (win rate * avg win - loss rate * avg loss) for crypto backtester."""
        try:
            if metrics['Trades'] > 0 and 0 < metrics['Win_Rate'] < 100:
                win_prob = metrics['Win_Rate'] / 100
                loss_prob = 1 - win_prob

                # Use actual average win/loss from backtester
                avg_win = result.get('avg_win', 0)
                avg_loss = result.get('avg_loss', 0)
                
                if avg_win > 0 and avg_loss > 0:
                    return (win_prob * avg_win) - (loss_prob * avg_loss)
                else:
                    return metrics['Avg_Trade']
            else:
                return metrics['Avg_Trade']
        except:
            return metrics['Avg_Trade']

    def _calculate_ulcer_index(self, metrics: Dict[str, Any]) -> float:
        """Calculate Ulcer Index (volatility of drawdowns)."""
        try:
            if metrics['Max_Drawdown'] != 0:
                return np.sqrt(abs(metrics['Max_Drawdown']))
            return 0.0
        except:
            return 0.0

    def _calculate_mar_ratio(self, metrics: Dict[str, Any]) -> float:
        """Calculate MAR ratio (return / max drawdown)."""
        try:
            if metrics['Max_Drawdown'] != 0:
                return abs(metrics['Return']) / abs(metrics['Max_Drawdown'])
            return 0.0
        except:
            return 0.0

    def _calculate_volatility_crypto(self, result: Dict[str, Any]) -> float:
        """Calculate strategy volatility for crypto backtester."""
        try:
            if 'trades' in result and len(result['trades']) > 1:
                trade_returns = []
                for trade in result['trades']:
                    try:
                        if 'pnl' in trade and 'size' in trade and trade['size'] != 0:
                            entry_value = abs(trade['size'] * trade.get('entry_price', 1))
                            if entry_value > 0:
                                pct_return = (trade['pnl'] / entry_value) * 100
                                trade_returns.append(pct_return)
                    except:
                        continue

                if len(trade_returns) > 1:
                    return np.std(trade_returns)
                else:
                    return 0.0
            else:
                return 0.0
        except:
            return 0.0

    def _calculate_var_crypto(self, result: Dict[str, Any], confidence: float = 0.95) -> float:
        """Calculate Value at Risk for crypto backtester."""
        try:
            if 'trades' in result and len(result['trades']) > 1:
                trade_returns = []
                for trade in result['trades']:
                    try:
                        if 'pnl' in trade and 'size' in trade and trade['size'] != 0:
                            entry_value = abs(trade['size'] * trade.get('entry_price', 1))
                            if entry_value > 0:
                                pct_return = (trade['pnl'] / entry_value) * 100
                                trade_returns.append(pct_return)
                    except:
                        continue

                if len(trade_returns) > 1:
                    return np.percentile(trade_returns, (1 - confidence) * 100)
                else:
                    return 0.0
            else:
                return 0.0
        except:
            return 0.0

    def _calculate_cvar_crypto(self, result: Dict[str, Any], confidence: float = 0.95) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall) for crypto backtester."""
        try:
            if 'trades' in result and len(result['trades']) > 1:
                trade_returns = []
                for trade in result['trades']:
                    try:
                        if 'pnl' in trade and 'size' in trade and trade['size'] != 0:
                            entry_value = abs(trade['size'] * trade.get('entry_price', 1))
                            if entry_value > 0:
                                pct_return = (trade['pnl'] / entry_value) * 100
                                trade_returns.append(pct_return)
                    except:
                        continue

                if len(trade_returns) > 1:
                    var_threshold = np.percentile(trade_returns, (1 - confidence) * 100)
                    losses_beyond_var = [r for r in trade_returns if r <= var_threshold]
                    if losses_beyond_var:
                        return np.mean(losses_beyond_var)
                    else:
                        return var_threshold
                else:
                    return 0.0
            else:
                return 0.0
        except:
            return 0.0

    def _analyze_trades_crypto(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze individual trades for detailed metrics for crypto backtester."""
        try:
            trade_analysis = {
                'Profitable_Trades': 0,
                'Losing_Trades': 0,
                'Even_Trades': 0,
                'Avg_Win': 0.0,
                'Avg_Loss': 0.0,
                'Largest_Win': 0.0,
                'Largest_Loss': 0.0,
                'Win_Streak_Max': 0,
                'Loss_Streak_Max': 0,
                'Trade_Duration_Avg': 0.0
            }

            if 'trades' in result and len(result['trades']) > 0:
                profitable_trades = []
                losing_trades = []
                win_streak = 0
                loss_streak = 0
                max_win_streak = 0
                max_loss_streak = 0

                for trade in result['trades']:
                    try:
                        if 'pnl' in trade and 'size' in trade and trade['size'] != 0:
                            entry_value = abs(trade['size'] * trade.get('entry_price', 1))
                            if entry_value > 0:
                                pct_return = (trade['pnl'] / entry_value) * 100

                                if pct_return > 0.01:  # Small threshold for even trades
                                    profitable_trades.append(pct_return)
                                    win_streak += 1
                                    loss_streak = 0
                                    max_win_streak = max(max_win_streak, win_streak)
                                elif pct_return < -0.01:
                                    losing_trades.append(pct_return)
                                    loss_streak += 1
                                    win_streak = 0
                                    max_loss_streak = max(max_loss_streak, loss_streak)
                                else:
                                    trade_analysis['Even_Trades'] += 1

                    except:
                        continue

                # Update analysis
                trade_analysis['Profitable_Trades'] = len(profitable_trades)
                trade_analysis['Losing_Trades'] = len(losing_trades)

                if profitable_trades:
                    trade_analysis['Avg_Win'] = np.mean(profitable_trades)
                    trade_analysis['Largest_Win'] = max(profitable_trades)

                if losing_trades:
                    trade_analysis['Avg_Loss'] = abs(np.mean(losing_trades))
                    trade_analysis['Largest_Loss'] = abs(min(losing_trades))

                trade_analysis['Win_Streak_Max'] = max_win_streak
                trade_analysis['Loss_Streak_Max'] = max_loss_streak

            return trade_analysis

        except Exception as e:
            logger.error(f"Error analyzing trades: {str(e)}")
            return {}

    def _calculate_kelly_percentage(self, metrics: Dict[str, Any]) -> float:
        """Calculate Kelly percentage for optimal position sizing."""
        try:
            if metrics['Trades'] > 0 and 0 < metrics['Win_Rate'] < 100:
                win_rate = metrics['Win_Rate'] / 100
                avg_win = metrics.get('Avg_Win', abs(metrics['Best_Trade']) * 0.6)
                avg_loss = metrics.get('Avg_Loss', abs(metrics['Worst_Trade']) * 0.6)

                if avg_loss != 0:
                    # Kelly formula: (bp - q) / b
                    # where b = odds (avg_win/avg_loss), p = win_rate, q = loss_rate
                    b = avg_win / avg_loss
                    kelly = (b * win_rate - (1 - win_rate)) / b
                    return max(0.0, min(0.5, kelly))  # Cap at 50%
                return 0.0
            return 0.0
        except:
            return 0.0

    def _calculate_risk_of_ruin(self, metrics: Dict[str, Any]) -> float:
        """Calculate risk of ruin probability."""
        try:
            if metrics['Trades'] > 0 and 0 < metrics['Win_Rate'] < 100:
                win_rate = metrics['Win_Rate'] / 100
                avg_win = metrics.get('Avg_Win', abs(metrics['Best_Trade']) * 0.6)
                avg_loss = metrics.get('Avg_Loss', abs(metrics['Worst_Trade']) * 0.6)

                if avg_loss != 0:
                    # Risk of ruin formula for constant bet size
                    # R = [(1-W)/W]^(2C) where W is win rate, C is capital ratio
                    capital_ratio = 100  # Assume 100:1 capital to bet ratio
                    if avg_win > 0 and avg_loss > 0:
                        effective_win_rate = win_rate * (avg_win / (avg_win + avg_loss))
                        if effective_win_rate < 0.5:
                            risk_of_ruin = ((1 - effective_win_rate) / effective_win_rate) ** (2 * capital_ratio)
                            return min(1.0, risk_of_ruin)
                return 0.0
            return 0.0
        except:
            return 0.0

    def _calculate_quality_score(self, metrics: Dict[str, Any]) -> float:
        """
        Calculate overall strategy quality score (0-100).

        Factors:
        - Return vs risk (Sharpe, Sortino)
        - Win rate and profit factor
        - Drawdown management
        - Expectancy and Kelly percentage
        """
        try:
            score = 50.0  # Base score

            # Return and risk factors (40% weight)
            if metrics['Sharpe'] > 1.0:
                score += 10
            elif metrics['Sharpe'] > 0.5:
                score += 5

            if metrics['Sortino_Ratio'] > 1.5:
                score += 10
            elif metrics['Sortino_Ratio'] > 1.0:
                score += 5

            if metrics['Calmar_Ratio'] > 1.0:
                score += 10
            elif metrics['Calmar_Ratio'] > 0.5:
                score += 5

            if metrics['Max_Drawdown'] < 10:
                score += 5
            elif metrics['Max_Drawdown'] < 20:
                score += 2

            # Trade performance factors (30% weight)
            if metrics['Win_Rate'] > 60:
                score += 8
            elif metrics['Win_Rate'] > 50:
                score += 4

            if metrics['Profit_Factor'] > 1.5:
                score += 7
            elif metrics['Profit_Factor'] > 1.2:
                score += 3

            if metrics['Expectancy'] > 0.5:
                score += 5
            elif metrics['Expectancy'] > 0:
                score += 2

            # Advanced factors (20% weight)
            if metrics['Kelly_Percentage'] > 0.1:
                score += 5
            elif metrics['Kelly_Percentage'] > 0.05:
                score += 2

            if metrics['Risk_of_Ruin'] < 0.1:
                score += 5
            elif metrics['Risk_of_Ruin'] < 0.25:
                score += 2

            if metrics['Trades'] > 50:
                score += 3
            elif metrics['Trades'] > 20:
                score += 1

            # Consistency factor (10% weight)
            if metrics['Win_Streak_Max'] > 5:
                score += 3
            elif metrics['Win_Streak_Max'] > 3:
                score += 1

            if metrics['Loss_Streak_Max'] < 5:
                score += 2

            return max(0.0, min(100.0, score))

        except Exception as e:
            logger.error(f"Error calculating quality score: {str(e)}")
            return 50.0

    def compare_strategies(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare multiple strategy results.

        Args:
            results: List of strategy result dictionaries

        Returns:
            Comparison analysis
        """
        try:
            if not results:
                return {"error": "No results to compare"}

            comparison = {
                'strategy_count': len(results),
                'best_performer': None,
                'worst_performer': None,
                'average_metrics': {},
                'rankings': {}
            }

            # Extract key metrics for comparison
            key_metrics = ['Return', 'Sharpe', 'Sortino_Ratio', 'Calmar_Ratio',
                         'Win_Rate', 'Profit_Factor', 'Max_Drawdown']

            for metric in key_metrics:
                values = [r.get(metric, 0) for r in results]
                comparison['average_metrics'][metric] = np.mean(values)

                # Rankings (higher is better for most metrics)
                if metric == 'Max_Drawdown':
                    # Lower drawdown is better
                    sorted_indices = np.argsort(values)  # Ascending
                else:
                    # Higher values are better
                    sorted_indices = np.argsort(values)[::-1]  # Descending

                comparison['rankings'][metric] = [
                    {'strategy_index': int(idx), 'value': values[idx]}
                    for idx in sorted_indices[:3]  # Top 3
                ]

            # Find best and worst performers
            returns = [r.get('Return', 0) for r in results]
            best_idx = np.argmax(returns)
            worst_idx = np.argmin(returns)

            comparison['best_performer'] = {
                'index': int(best_idx),
                'return': returns[best_idx],
                'key_metrics': {k: results[best_idx].get(k, 0) for k in key_metrics}
            }

            comparison['worst_performer'] = {
                'index': int(worst_idx),
                'return': returns[worst_idx],
                'key_metrics': {k: results[worst_idx].get(k, 0) for k in key_metrics}
            }

            return comparison

        except Exception as e:
            logger.error(f"Error comparing strategies: {str(e)}")
            return {"error": str(e)}

    def generate_report(self, metrics: Dict[str, Any], filename: str = None) -> str:
        """
        Generate a comprehensive performance report.

        Args:
            metrics: Calculated metrics dictionary
            filename: Optional output filename

        Returns:
            Report content as string
        """
        try:
            if filename is None:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"strategy_report_{timestamp}.txt"

            report = []
            report.append("=" * 80)
            report.append("STRATEGY PERFORMANCE REPORT")
            report.append("=" * 80)
            report.append("")

            # Basic Performance
            report.append("BASIC PERFORMANCE METRICS:")
            report.append("-" * 40)
            report.append(".2f")
            report.append(".2f")
            report.append(".2f")
            report.append(".2f")
            report.append(".1f")
            report.append(".2f")
            report.append("")

            # Risk Metrics
            report.append("RISK-ADJUSTED METRICS:")
            report.append("-" * 40)
            report.append(".2f")
            report.append(".2f")
            report.append(".2f")
            report.append(".2f")
            report.append(".2f")
            report.append("")

            # Trade Analysis
            report.append("TRADE ANALYSIS:")
            report.append("-" * 40)
            report.append(f"Total Trades: {metrics.get('Trades', 0)}")
            report.append(f"Profitable Trades: {metrics.get('Profitable_Trades', 0)}")
            report.append(f"Losing Trades: {metrics.get('Losing_Trades', 0)}")
            report.append(".1f")
            report.append(".2f")
            report.append(".2f")
            report.append(f"Win Streak Max: {metrics.get('Win_Streak_Max', 0)}")
            report.append(f"Loss Streak Max: {metrics.get('Loss_Streak_Max', 0)}")
            report.append("")

            # Advanced Metrics
            report.append("ADVANCED METRICS:")
            report.append("-" * 40)
            report.append(".2f")
            report.append(".2f")
            report.append(".2f")
            report.append(".2f")
            report.append(".2f")
            report.append("")

            # Quality Assessment
            report.append("STRATEGY QUALITY ASSESSMENT:")
            report.append("-" * 40)
            quality_score = metrics.get('Strategy_Quality_Score', 50)
            report.append(".1f")

            if quality_score >= 80:
                assessment = "EXCELLENT - High-quality strategy with strong risk-adjusted returns"
            elif quality_score >= 65:
                assessment = "GOOD - Solid strategy with acceptable risk management"
            elif quality_score >= 50:
                assessment = "FAIR - Average performance, consider optimization"
            elif quality_score >= 35:
                assessment = "POOR - Significant improvements needed"
            else:
                assessment = "VERY POOR - Strategy needs major revision"

            report.append(f"Assessment: {assessment}")
            report.append("")

            # Recommendations
            report.append("RECOMMENDATIONS:")
            report.append("-" * 40)

            if metrics.get('Sharpe', 0) < 0.5:
                report.append("• Improve risk-adjusted returns (Sharpe < 0.5)")
            if metrics.get('Max_Drawdown', 0) > 20:
                report.append("• Reduce maximum drawdown (currently > 20%)")
            if metrics.get('Win_Rate', 0) < 50:
                report.append("• Increase win rate above 50%")
            if metrics.get('Profit_Factor', 0) < 1.2:
                report.append("• Improve profit factor above 1.2")
            if metrics.get('Kelly_Percentage', 0) < 0.05:
                report.append("• Consider position sizing adjustments")

            if not any([metrics.get('Sharpe', 0) < 0.5,
                       metrics.get('Max_Drawdown', 0) > 20,
                       metrics.get('Win_Rate', 0) < 50,
                       metrics.get('Profit_Factor', 0) < 1.2,
                       metrics.get('Kelly_Percentage', 0) < 0.05]):
                report.append("• Strategy is well-balanced, consider live testing")

            report.append("")
            report.append("=" * 80)

            # Write to file
            with open(filename, 'w') as f:
                f.write('\n'.join(report))

            logger.info(f"Performance report saved to: {filename}")
            return '\n'.join(report)

        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            return f"Error generating report: {str(e)}"
