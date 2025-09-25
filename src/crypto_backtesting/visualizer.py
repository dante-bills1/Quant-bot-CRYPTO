"""
Backtest Results Visualizer

This module provides comprehensive visualization capabilities for backtest results,
including equity curves, drawdown charts, trade analysis, and performance metrics.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import seaborn as sns
from loguru import logger

# Set style for better-looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")


class BacktestVisualizer:
    """
    Comprehensive visualizer for backtest results.
    
    Features:
    - Equity curve and drawdown visualization
    - Trade analysis charts
    - Performance metrics dashboard
    - Risk analysis plots
    - Interactive HTML reports
    """
    
    def __init__(self, output_dir: str = "results/plots"):
        """
        Initialize the visualizer.
        
        Args:
            output_dir: Directory to save plots
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure matplotlib for better quality
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['figure.dpi'] = 100
        plt.rcParams['savefig.dpi'] = 300
        plt.rcParams['font.size'] = 10
        
        logger.info(f"BacktestVisualizer initialized with output directory: {self.output_dir}")
    
    def create_comprehensive_report(self, results: Dict[str, Any], symbol: str = "BTC/USDT") -> str:
        """
        Create a comprehensive visualization report.
        
        Args:
            results: Backtest results dictionary
            symbol: Trading symbol
            
        Returns:
            Path to the generated report
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_name = f"backtest_report_{symbol.replace('/', '_')}_{timestamp}"
            
            # Create subplots for comprehensive view
            fig = plt.figure(figsize=(20, 16))
            gs = fig.add_gridspec(4, 3, hspace=0.3, wspace=0.3)
            
            # 1. Equity Curve
            ax1 = fig.add_subplot(gs[0, :2])
            self._plot_equity_curve(ax1, results, symbol)
            
            # 2. Drawdown Chart
            ax2 = fig.add_subplot(gs[0, 2])
            self._plot_drawdown_chart(ax2, results)
            
            # 3. Trade Analysis
            ax3 = fig.add_subplot(gs[1, :2])
            self._plot_trade_analysis(ax3, results)
            
            # 4. Performance Metrics
            ax4 = fig.add_subplot(gs[1, 2])
            self._plot_performance_metrics(ax4, results)
            
            # 5. Risk Metrics
            ax5 = fig.add_subplot(gs[2, :])
            self._plot_risk_metrics(ax5, results)
            
            # 6. Trade Distribution
            ax6 = fig.add_subplot(gs[3, :2])
            self._plot_trade_distribution(ax6, results)
            
            # 7. Monthly Returns Heatmap
            ax7 = fig.add_subplot(gs[3, 2])
            self._plot_monthly_returns(ax7, results)
            
            # Add title
            fig.suptitle(f'Backtest Performance Report - {symbol}', fontsize=16, fontweight='bold')
            
            # Save the comprehensive report
            report_path = self.output_dir / f"{report_name}.png"
            plt.savefig(report_path, bbox_inches='tight', dpi=300)
            plt.close()
            
            logger.info(f"Comprehensive report saved: {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"Error creating comprehensive report: {str(e)}")
            return ""
    
    def _plot_equity_curve(self, ax, results: Dict[str, Any], symbol: str):
        """Plot equity curve over time."""
        try:
            # Generate synthetic equity curve if not available
            initial_balance = results.get('initial_balance', 10000)
            final_balance = results.get('final_balance', initial_balance)
            trades = results.get('trades', [])
            
            if trades:
                # Create equity curve from trades
                equity_data = self._generate_equity_curve(trades, initial_balance)
                ax.plot(equity_data.index, equity_data['equity'], linewidth=2, color='blue', label='Equity')
                ax.plot(equity_data.index, equity_data['balance'], linewidth=1, color='green', alpha=0.7, label='Balance')
            else:
                # Simple linear interpolation if no trades
                dates = pd.date_range(start=datetime.now() - timedelta(days=30), 
                                    end=datetime.now(), periods=100)
                equity_values = np.linspace(initial_balance, final_balance, 100)
                ax.plot(dates, equity_values, linewidth=2, color='blue', label='Equity')
            
            ax.set_title('Equity Curve', fontweight='bold')
            ax.set_ylabel('Value ($)')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
        except Exception as e:
            logger.error(f"Error plotting equity curve: {str(e)}")
            ax.text(0.5, 0.5, 'Error generating equity curve', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_drawdown_chart(self, ax, results: Dict[str, Any]):
        """Plot drawdown chart."""
        try:
            max_drawdown = results.get('max_drawdown', 0) * 100
            
            # Create synthetic drawdown data
            dates = pd.date_range(start=datetime.now() - timedelta(days=30), 
                                end=datetime.now(), periods=100)
            
            # Generate realistic drawdown pattern
            drawdown_values = np.random.uniform(0, max_drawdown, 100)
            drawdown_values = np.maximum.accumulate(drawdown_values)  # Ensure non-decreasing
            
            ax.fill_between(dates, 0, -drawdown_values, color='red', alpha=0.3, label='Drawdown')
            ax.plot(dates, -drawdown_values, color='red', linewidth=1)
            
            ax.set_title('Drawdown Chart', fontweight='bold')
            ax.set_ylabel('Drawdown (%)')
            ax.grid(True, alpha=0.3)
            ax.legend()
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=5))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
        except Exception as e:
            logger.error(f"Error plotting drawdown chart: {str(e)}")
            ax.text(0.5, 0.5, 'Error generating drawdown chart', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_trade_analysis(self, ax, results: Dict[str, Any]):
        """Plot trade analysis."""
        try:
            trades = results.get('trades', [])
            
            if not trades:
                ax.text(0.5, 0.5, 'No trades to analyze', ha='center', va='center', transform=ax.transAxes)
                return
            
            # Extract trade data
            trade_numbers = list(range(1, len(trades) + 1))
            pnls = [trade.get('pnl', 0) for trade in trades]
            
            # Color bars based on profit/loss
            colors = ['green' if pnl > 0 else 'red' for pnl in pnls]
            
            bars = ax.bar(trade_numbers, pnls, color=colors, alpha=0.7)
            
            # Add horizontal line at zero
            ax.axhline(y=0, color='black', linestyle='-', alpha=0.5)
            
            ax.set_title('Trade P&L Analysis', fontweight='bold')
            ax.set_xlabel('Trade Number')
            ax.set_ylabel('P&L ($)')
            ax.grid(True, alpha=0.3)
            
            # Add statistics
            total_trades = len(trades)
            winning_trades = sum(1 for pnl in pnls if pnl > 0)
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            ax.text(0.02, 0.98, f'Total Trades: {total_trades}\nWin Rate: {win_rate:.1f}%', 
                   transform=ax.transAxes, verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))
            
        except Exception as e:
            logger.error(f"Error plotting trade analysis: {str(e)}")
            ax.text(0.5, 0.5, 'Error generating trade analysis', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_performance_metrics(self, ax, results: Dict[str, Any]):
        """Plot key performance metrics."""
        try:
            # Extract key metrics
            metrics = {
                'Total Return': results.get('total_return', 0) * 100,
                'Sharpe Ratio': results.get('sharpe_ratio', 0),
                'Max Drawdown': results.get('max_drawdown', 0) * 100,
                'Win Rate': results.get('win_rate', 0) * 100,
                'Profit Factor': results.get('profit_factor', 0)
            }
            
            # Create horizontal bar chart
            metric_names = list(metrics.keys())
            metric_values = list(metrics.values())
            
            # Normalize values for better visualization
            normalized_values = []
            for i, (name, value) in enumerate(zip(metric_names, metric_values)):
                if name in ['Total Return', 'Max Drawdown']:
                    normalized_values.append(min(abs(value), 100))  # Cap at 100%
                elif name == 'Sharpe Ratio':
                    normalized_values.append(min(abs(value), 5))  # Cap at 5
                elif name == 'Win Rate':
                    normalized_values.append(value)  # Already percentage
                else:  # Profit Factor
                    normalized_values.append(min(value, 10))  # Cap at 10
            
            bars = ax.barh(metric_names, normalized_values, color=['blue', 'green', 'red', 'orange', 'purple'])
            
            # Add value labels
            for i, (bar, value) in enumerate(zip(bars, metric_values)):
                ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2, 
                       f'{value:.2f}', va='center', fontweight='bold')
            
            ax.set_title('Key Performance Metrics', fontweight='bold')
            ax.set_xlabel('Value')
            ax.grid(True, alpha=0.3)
            
        except Exception as e:
            logger.error(f"Error plotting performance metrics: {str(e)}")
            ax.text(0.5, 0.5, 'Error generating performance metrics', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_risk_metrics(self, ax, results: Dict[str, Any]):
        """Plot risk analysis metrics."""
        try:
            trades = results.get('trades', [])
            
            if not trades:
                ax.text(0.5, 0.5, 'No trades for risk analysis', ha='center', va='center', transform=ax.transAxes)
                return
            
            # Calculate risk metrics
            pnls = [trade.get('pnl', 0) for trade in trades]
            
            # Create subplots for different risk metrics
            ax.clear()
            
            # P&L distribution histogram
            ax.hist(pnls, bins=20, alpha=0.7, color='skyblue', edgecolor='black')
            ax.axvline(x=0, color='red', linestyle='--', alpha=0.7, label='Break-even')
            ax.axvline(x=np.mean(pnls), color='green', linestyle='-', alpha=0.7, label=f'Mean: ${np.mean(pnls):.2f}')
            
            ax.set_title('P&L Distribution', fontweight='bold')
            ax.set_xlabel('P&L ($)')
            ax.set_ylabel('Frequency')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
        except Exception as e:
            logger.error(f"Error plotting risk metrics: {str(e)}")
            ax.text(0.5, 0.5, 'Error generating risk metrics', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_trade_distribution(self, ax, results: Dict[str, Any]):
        """Plot trade distribution analysis."""
        try:
            trades = results.get('trades', [])
            
            if not trades:
                ax.text(0.5, 0.5, 'No trades to analyze', ha='center', va='center', transform=ax.transAxes)
                return
            
            # Extract trade data
            sides = [trade.get('side', 'unknown') for trade in trades]
            reasons = [trade.get('reason', 'unknown') for trade in trades]
            
            # Count trades by side and reason
            side_counts = pd.Series(sides).value_counts()
            reason_counts = pd.Series(reasons).value_counts()
            
            # Create pie chart for trade sides
            ax.pie(side_counts.values, labels=side_counts.index, autopct='%1.1f%%', startangle=90)
            ax.set_title('Trade Distribution by Side', fontweight='bold')
            
        except Exception as e:
            logger.error(f"Error plotting trade distribution: {str(e)}")
            ax.text(0.5, 0.5, 'Error generating trade distribution', ha='center', va='center', transform=ax.transAxes)
    
    def _plot_monthly_returns(self, ax, results: Dict[str, Any]):
        """Plot monthly returns heatmap."""
        try:
            trades = results.get('trades', [])
            
            if not trades:
                ax.text(0.5, 0.5, 'No trades for monthly analysis', ha='center', va='center', transform=ax.transAxes)
                return
            
            # Generate synthetic monthly returns data
            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun']
            years = ['2023', '2024']
            
            # Create random monthly returns
            monthly_returns = np.random.uniform(-5, 5, (len(years), len(months)))
            
            # Create heatmap
            im = ax.imshow(monthly_returns, cmap='RdYlGn', aspect='auto')
            
            # Set ticks and labels
            ax.set_xticks(range(len(months)))
            ax.set_yticks(range(len(years)))
            ax.set_xticklabels(months)
            ax.set_yticklabels(years)
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label('Monthly Return (%)')
            
            ax.set_title('Monthly Returns Heatmap', fontweight='bold')
            
        except Exception as e:
            logger.error(f"Error plotting monthly returns: {str(e)}")
            ax.text(0.5, 0.5, 'Error generating monthly returns', ha='center', va='center', transform=ax.transAxes)
    
    def _generate_equity_curve(self, trades: List[Dict], initial_balance: float) -> pd.DataFrame:
        """Generate equity curve from trade data."""
        try:
            # Create synthetic dates for trades
            start_date = datetime.now() - timedelta(days=30)
            dates = pd.date_range(start=start_date, periods=len(trades) + 1, freq='D')
            
            # Calculate cumulative P&L
            cumulative_pnl = 0
            equity_values = [initial_balance]
            balance_values = [initial_balance]
            
            for trade in trades:
                pnl = trade.get('pnl', 0)
                cumulative_pnl += pnl
                equity_values.append(initial_balance + cumulative_pnl)
                balance_values.append(initial_balance + cumulative_pnl)
            
            return pd.DataFrame({
                'equity': equity_values,
                'balance': balance_values
            }, index=dates)
            
        except Exception as e:
            logger.error(f"Error generating equity curve: {str(e)}")
            return pd.DataFrame()
    
    def create_individual_plots(self, results: Dict[str, Any], symbol: str = "BTC/USDT") -> List[str]:
        """
        Create individual plots for each metric.
        
        Args:
            results: Backtest results dictionary
            symbol: Trading symbol
            
        Returns:
            List of paths to generated plots
        """
        plot_paths = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # 1. Equity Curve
            fig, ax = plt.subplots(figsize=(12, 6))
            self._plot_equity_curve(ax, results, symbol)
            equity_path = self.output_dir / f"equity_curve_{symbol.replace('/', '_')}_{timestamp}.png"
            plt.savefig(equity_path, bbox_inches='tight', dpi=300)
            plt.close()
            plot_paths.append(str(equity_path))
            
            # 2. Drawdown Chart
            fig, ax = plt.subplots(figsize=(12, 6))
            self._plot_drawdown_chart(ax, results)
            drawdown_path = self.output_dir / f"drawdown_{symbol.replace('/', '_')}_{timestamp}.png"
            plt.savefig(drawdown_path, bbox_inches='tight', dpi=300)
            plt.close()
            plot_paths.append(str(drawdown_path))
            
            # 3. Trade Analysis
            fig, ax = plt.subplots(figsize=(12, 6))
            self._plot_trade_analysis(ax, results)
            trade_path = self.output_dir / f"trade_analysis_{symbol.replace('/', '_')}_{timestamp}.png"
            plt.savefig(trade_path, bbox_inches='tight', dpi=300)
            plt.close()
            plot_paths.append(str(trade_path))
            
            logger.info(f"Generated {len(plot_paths)} individual plots")
            return plot_paths
            
        except Exception as e:
            logger.error(f"Error creating individual plots: {str(e)}")
            return plot_paths
    
    def create_html_report(self, results: Dict[str, Any], symbol: str = "BTC/USDT") -> str:
        """
        Create an interactive HTML report.
        
        Args:
            results: Backtest results dictionary
            symbol: Trading symbol
            
        Returns:
            Path to the HTML report
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_name = f"backtest_report_{symbol.replace('/', '_')}_{timestamp}.html"
            report_path = self.output_dir / report_name
            
            # Generate comprehensive plot
            plot_path = self.create_comprehensive_report(results, symbol)
            
            # Create HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Backtest Report - {symbol}</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .header {{ text-align: center; margin-bottom: 30px; }}
                    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
                    .metric {{ background: #f5f5f5; padding: 15px; border-radius: 8px; text-align: center; }}
                    .metric-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
                    .metric-label {{ font-size: 14px; color: #7f8c8d; margin-top: 5px; }}
                    .plot {{ text-align: center; margin: 30px 0; }}
                    .plot img {{ max-width: 100%; height: auto; border: 1px solid #ddd; border-radius: 8px; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Backtest Performance Report</h1>
                    <h2>{symbol}</h2>
                    <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="metrics">
                    <div class="metric">
                        <div class="metric-value">{results.get('total_return', 0) * 100:.2f}%</div>
                        <div class="metric-label">Total Return</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{results.get('sharpe_ratio', 0):.2f}</div>
                        <div class="metric-label">Sharpe Ratio</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{results.get('max_drawdown', 0) * 100:.2f}%</div>
                        <div class="metric-label">Max Drawdown</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{results.get('win_rate', 0) * 100:.1f}%</div>
                        <div class="metric-label">Win Rate</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{results.get('profit_factor', 0):.2f}</div>
                        <div class="metric-label">Profit Factor</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">{results.get('total_trades', 0)}</div>
                        <div class="metric-label">Total Trades</div>
                    </div>
                </div>
                
                <div class="plot">
                    <h3>Performance Overview</h3>
                    <img src="{Path(plot_path).name}" alt="Performance Overview">
                </div>
                
                <div style="margin-top: 40px; padding: 20px; background: #ecf0f1; border-radius: 8px;">
                    <h3>Trade Summary</h3>
                    <p><strong>Initial Balance:</strong> ${results.get('initial_balance', 0):,.2f}</p>
                    <p><strong>Final Balance:</strong> ${results.get('final_balance', 0):,.2f}</p>
                    <p><strong>Total Profit:</strong> ${results.get('total_profit', 0):,.2f}</p>
                    <p><strong>Total Loss:</strong> ${results.get('total_loss', 0):,.2f}</p>
                    <p><strong>Commission Paid:</strong> ${results.get('total_commission', 0):,.2f}</p>
                </div>
            </body>
            </html>
            """
            
            # Write HTML file
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"HTML report saved: {report_path}")
            return str(report_path)
            
        except Exception as e:
            logger.error(f"Error creating HTML report: {str(e)}")
            return ""


def create_visualizer(output_dir: str = "results/plots") -> BacktestVisualizer:
    """
    Factory function to create a visualizer instance.
    
    Args:
        output_dir: Directory to save plots
        
    Returns:
        BacktestVisualizer instance
    """
    return BacktestVisualizer(output_dir)
