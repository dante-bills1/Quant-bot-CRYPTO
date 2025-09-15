"""
Crypto Telegram Command Handler

This module provides Telegram command handling functionality specifically designed for crypto trading,
replacing the MT5-based telegram command handler with crypto-specific commands and data.
"""

import asyncio
import traceback
from typing import Dict, List, Any, Optional, TYPE_CHECKING
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd
import numpy as np

from src.telegram.telegram_bot import TelegramBot
from src.crypto_handler import CryptoHandler
from src.crypto_risk_manager import CryptoRiskManager
from src.crypto_position_manager import CryptoPositionManager

if TYPE_CHECKING:
    from src.trading_bot import TradingBot

class CryptoTelegramCommandHandler:
    """
    Handles Telegram bot commands for crypto trading bot.

    This class provides crypto-specific commands and data access,
    replacing MT5-based functionality with crypto exchange data.
    """

    def __init__(self, trading_bot: "TradingBot", crypto_handler: CryptoHandler):
        """
        Initialize the crypto telegram command handler.

        Args:
            trading_bot: Reference to the main trading bot
            crypto_handler: Crypto handler for exchange data access
        """
        self.trading_bot = trading_bot
        self.crypto_handler = crypto_handler
        self.risk_manager = CryptoRiskManager()
        self.position_manager = CryptoPositionManager()

        # Initialize telegram bot
        self.telegram_bot = TelegramBot.get_instance()

        # Command definitions
        self.commands = {
            'help': self._cmd_help,
            'status': self._cmd_status,
            'balance': self._cmd_balance,
            'positions': self._cmd_positions,
            'daily': self._cmd_daily_report,
            'performance': self._cmd_performance_summary,
            'metrics': self._cmd_trading_metrics,
            'symbols': self._cmd_symbols,
            'start': self._cmd_start_trading,
            'stop': self._cmd_stop_trading,
            'settings': self._cmd_settings,
            'trades': self._cmd_recent_trades
        }

        logger.info("CryptoTelegramCommandHandler initialized")

    def register_commands(self):
        """Register all commands with the telegram bot."""
        try:
            for command_name, command_func in self.commands.items():
                # Register command with telegram bot
                self.telegram_bot.register_command(command_name, command_func)
                logger.debug(f"Registered command: /{command_name}")
        except Exception as e:
            logger.error(f"Error registering commands: {str(e)}")

    async def _cmd_help(self, update: Dict[str, Any], context: Any) -> str:
        """
        Show help information for all available commands.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Help message
        """
        try:
            help_text = """
🤖 <b>Crypto Trading Bot Commands</b>

<b>📊 Information Commands:</b>
/help - Show this help message
/status - Show bot status and connection info
/balance - Show account balance
/positions - Show current open positions
/symbols - Show available trading symbols

<b>📈 Trading Commands:</b>
/start - Start automated trading
/stop - Stop automated trading

<b>📋 Reports & Analytics:</b>
/daily - Show daily trading report
/performance - Show performance summary
/metrics - Show trading metrics and statistics
/trades - Show recent trades

<b>⚙️ Settings:</b>
/settings - Show current bot settings

<b>💡 Tips:</b>
• All crypto trading is 24/7
• Use /status to check exchange connections
• Monitor /positions for active trades
• Check /daily for performance tracking

<i>For support or questions, contact the developer.</i>
            """
            return help_text

        except Exception as e:
            logger.error(f"Error in help command: {str(e)}")
            return f"❌ Error: {str(e)}"

    async def _cmd_status(self, update: Dict[str, Any], context: Any) -> str:
        """
        Show bot status and connection information.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Status message
        """
        try:
            # Check crypto handler status
            crypto_status = "✅ Connected" if self.crypto_handler and self.crypto_handler.connected else "❌ Disconnected"

            # Check trading bot status
            trading_status = "🟢 Running" if hasattr(self.trading_bot, 'is_running') and self.trading_bot.is_running else "🔴 Stopped"

            # Get exchange info
            exchange_info = "Unknown"
            if self.crypto_handler:
                exchange_info = f"{self.crypto_handler.exchange_name.title()}"

            # Get symbol info
            symbols_count = 0
            if hasattr(self.trading_bot, 'symbols'):
                symbols_count = len(self.trading_bot.symbols)

            status_text = f"""
🔍 <b>Bot Status</b>

<b>🤖 Trading Bot:</b> {trading_status}
<b>🌐 Exchange:</b> {exchange_info}
<b>🔗 Connection:</b> {crypto_status}
<b>📊 Symbols:</b> {symbols_count} configured

<b>⚙️ Current Settings:</b>
• Risk per trade: {self.risk_manager.max_risk_per_trade:.1%}
• Daily risk limit: {self.risk_manager.max_daily_risk:.1%}
• Max positions: {self.position_manager.max_positions}
• Trading enabled: {'Yes' if self.risk_manager.trading_enabled else 'No'}
            """

            return status_text

        except Exception as e:
            logger.error(f"Error in status command: {str(e)}")
            return f"❌ Error getting status: {str(e)}"

    async def _cmd_balance(self, update: Dict[str, Any], context: Any) -> str:
        """
        Show account balance information.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Balance message
        """
        try:
            if not self.crypto_handler:
                return "⚠️ <b>Balance Check</b>\n\nCrypto handler not available. Cannot retrieve balance."

            # Get account balance
            balance = await self.crypto_handler.get_balance()

            if not balance:
                return "⚠️ <b>Balance Check</b>\n\nUnable to retrieve account balance. Please check your connection."

            # Format balance information
            balance_text = "💰 <b>Account Balance</b>\n\n"

            # Show USDT balance prominently
            if 'USDT' in balance:
                usdt_balance = balance['USDT']
                balance_text += f"💵 <b>USDT:</b> {usdt_balance['free']:.2f} free / {usdt_balance['total']:.2f} total\n\n"

            # Show other currencies
            balance_text += "<b>Other Assets:</b>\n"
            for currency, bal in balance.items():
                if currency != 'USDT' and bal['total'] > 0:
                    balance_text += f"• {currency}: {bal['free']:.6f} free / {bal['total']:.6f} total\n"

            # Calculate total portfolio value (assuming USDT as base)
            total_value = 0.0
            for currency, bal in balance.items():
                if currency == 'USDT':
                    total_value += bal['total']
                else:
                    # Try to get current price for conversion (simplified)
                    total_value += bal['total']  # Placeholder - would need price conversion

            balance_text += f"\n<b>💎 Total Portfolio Value:</b> ≈${total_value:.2f} USDT"

            return balance_text

        except Exception as e:
            logger.error(f"Error in balance command: {str(e)}")
            return f"❌ Error retrieving balance: {str(e)}"

    async def _cmd_positions(self, update: Dict[str, Any], context: Any) -> str:
        """
        Show current open positions.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Positions message
        """
        try:
            if not self.position_manager:
                return "⚠️ <b>Open Positions</b>\n\nPosition manager not available."

            # Get position summary
            positions_summary = await self.position_manager.get_position_summary()

            if positions_summary.get('error'):
                return f"⚠️ <b>Open Positions</b>\n\nError: {positions_summary['error']}"

            positions = positions_summary.get('positions', [])
            total_pnl = positions_summary.get('total_pnl', 0)

            if not positions:
                return "📊 <b>Open Positions</b>\n\nNo open positions at this time."

            positions_text = f"""
📊 <b>Open Positions ({len(positions)})</b>

<b>Total P&L:</b> ${total_pnl:+.2f}
"""

            for pos in positions:
                pnl_color = "🟢" if pos['pnl'] >= 0 else "🔴"
                pnl_text = f"{pnl_color} ${pos['pnl']:+.2f}"

                positions_text += f"""
<b>{pos['symbol']}</b> - {pos['side'].upper()}
• Size: {pos['size']:.6f}
• Entry: ${pos['entry_price']:.2f}
• Current: ${pos['current_price']:.2f}
• P&L: {pnl_text}
• Volume: ${pos['volume']:.2f}
"""

            return positions_text

        except Exception as e:
            logger.error(f"Error in positions command: {str(e)}")
            return f"❌ Error retrieving positions: {str(e)}"

    async def _cmd_daily_report(self, update: Dict[str, Any], context: Any) -> str:
        """
        Show daily trading report.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Daily report message
        """
        try:
            # Get date range for today
            today = datetime.now()
            date_str = today.strftime('%Y-%m-%d')

            if not self.crypto_handler:
                return f"⚠️ <b>Daily Report ({date_str})</b>\n\nCrypto handler not available. Cannot retrieve trading history."

            # Get risk manager stats
            risk_summary = self.risk_manager.get_risk_summary()

            # Get position summary
            positions_summary = await self.position_manager.get_position_summary()

            # Format daily report
            report_text = f"""
📈 <b>Daily Report ({date_str})</b>

<b>💰 Risk Management:</b>
• Daily P&L: ${risk_summary.get('daily_pnl', 0):+.2f}
• Total P&L: ${risk_summary.get('total_pnl', 0):+.2f}
• Daily Trades: {risk_summary.get('daily_trades', 0)}
• Open Positions: {risk_summary.get('open_positions', 0)}

<b>📊 Portfolio:</b>
• Total Positions: {positions_summary.get('total_positions', 0)}
• Total P&L: ${positions_summary.get('total_pnl', 0):+.2f}
• Total Volume: ${positions_summary.get('total_volume', 0):+.2f}
"""

            # Add current positions summary
            positions = positions_summary.get('positions', [])
            if positions:
                report_text += "\n<b>📋 Current Positions:</b>\n"
                for pos in positions[:5]:  # Show top 5 positions
                    pnl_color = "🟢" if pos['pnl'] >= 0 else "🔴"
                    report_text += f"• {pos['symbol']}: {pnl_color} ${pos['pnl']:+.2f}\n"

                if len(positions) > 5:
                    report_text += f"• ... and {len(positions) - 5} more positions"

            return report_text

        except Exception as e:
            logger.error(f"Error in daily report command: {str(e)}")
            return f"❌ Error generating daily report: {str(e)}"

    async def _cmd_performance_summary(self, update: Dict[str, Any], context: Any) -> str:
        """
        Show performance summary.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Performance summary message
        """
        try:
            if not self.risk_manager:
                return "⚠️ <b>Performance Summary</b>\n\nRisk manager not available. Cannot retrieve performance data."

            # Get risk summary
            risk_summary = self.risk_manager.get_risk_summary()

            # Calculate additional metrics
            total_trades = risk_summary.get('daily_trades', 0)  # This should be total trades
            winning_trades = 0  # Would need to be tracked
            win_rate = (winning_trades / max(total_trades, 1)) * 100

            performance_text = f"""
📊 <b>Performance Summary</b>

<b>💵 Account Performance:</b>
• Total P&L: ${risk_summary.get('total_pnl', 0):+.2f}
• Daily P&L: ${risk_summary.get('daily_pnl', 0):+.2f}

<b>📈 Trading Statistics:</b>
• Total Trades: {total_trades}
• Win Rate: {win_rate:.1f}%
• Open Positions: {risk_summary.get('open_positions', 0)}

<b>⚠️ Risk Management:</b>
• Daily Risk Used: {risk_summary.get('daily_risk_used', 0):.1%}
• Total Risk Used: {risk_summary.get('total_risk_used', 0):.1%}
• Risk per Trade: {risk_summary.get('max_risk_per_trade', 0):.1%}
• Daily Risk Limit: {risk_summary.get('max_daily_risk', 0):.1%}
"""

            return performance_text

        except Exception as e:
            logger.error(f"Error in performance summary command: {str(e)}")
            return f"❌ Error generating performance summary: {str(e)}"

    async def _cmd_trading_metrics(self, update: Dict[str, Any], context: Any) -> str:
        """
        Show trading metrics and statistics.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Trading metrics message
        """
        try:
            # Get basic metrics from risk manager
            risk_summary = self.risk_manager.get_risk_summary()

            # Get signal processor stats if available
            signal_stats = {}
            if hasattr(self.trading_bot, 'signal_processor') and self.trading_bot.signal_processor:
                signal_stats = await self.trading_bot.signal_processor.get_processing_stats()

            metrics_text = f"""
📊 <b>Trading Metrics</b>

<b>🤖 Signal Processing:</b>
• Signals Processed: {signal_stats.get('signals_processed', 0)}
• Trades Executed: {signal_stats.get('trades_executed', 0)}
• Failed Executions: {signal_stats.get('failed_executions', 0)}
• Active Trades: {signal_stats.get('active_trades', 0)}
• Success Rate: {signal_stats.get('success_rate', 0):.1%}

<b>📋 Risk Metrics:</b>
• Max Risk per Trade: {risk_summary.get('max_risk_per_trade', 0):.1%}
• Max Daily Risk: {risk_summary.get('max_daily_risk', 0):.1%}
• Max Total Risk: {risk_summary.get('max_total_risk', 0):.1%}
• Stop Loss Multiplier: {risk_summary.get('stop_loss_atr_multiplier', 0):.1f}
• Take Profit Multiplier: {risk_summary.get('take_profit_atr_multiplier', 0):.1f}

<b>⚙️ System Settings:</b>
• Trading Enabled: {'Yes' if signal_stats.get('trading_enabled', False) else 'No'}
• Min Confidence: {signal_stats.get('min_confidence', 0):.1%}
"""

            return metrics_text

        except Exception as e:
            logger.error(f"Error in trading metrics command: {str(e)}")
            return f"❌ Error retrieving trading metrics: {str(e)}"

    async def _cmd_symbols(self, update: Dict[str, Any], context: Any) -> str:
        """
        Show available trading symbols.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Symbols message
        """
        try:
            if not hasattr(self.trading_bot, 'symbols'):
                return "⚠️ <b>Trading Symbols</b>\n\nNo symbols configured."

            symbols = self.trading_bot.symbols

            if not symbols:
                return "⚠️ <b>Trading Symbols</b>\n\nNo symbols available."

            symbols_text = f"""
🔤 <b>Trading Symbols ({len(symbols)})</b>

"""

            # Group symbols by base currency
            symbol_groups = {}
            for symbol in symbols:
                if '/' in symbol:
                    base = symbol.split('/')[0]
                    if base not in symbol_groups:
                        symbol_groups[base] = []
                    symbol_groups[base].append(symbol)

            # Display grouped symbols
            for base, group_symbols in symbol_groups.items():
                symbols_text += f"<b>{base} Pairs:</b>\n"
                for symbol in group_symbols[:5]:  # Show up to 5 per group
                    symbols_text += f"• {symbol}\n"
                if len(group_symbols) > 5:
                    symbols_text += f"• ... and {len(group_symbols) - 5} more\n"
                symbols_text += "\n"

            return symbols_text

        except Exception as e:
            logger.error(f"Error in symbols command: {str(e)}")
            return f"❌ Error retrieving symbols: {str(e)}"

    async def _cmd_start_trading(self, update: Dict[str, Any], context: Any) -> str:
        """
        Start automated trading.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Start trading message
        """
        try:
            # Enable trading in risk manager
            self.risk_manager.trading_enabled = True

            # Enable trading in signal processor if available
            if hasattr(self.trading_bot, 'signal_processor') and self.trading_bot.signal_processor:
                self.trading_bot.signal_processor.trading_enabled = True

            # Start trading bot if available
            if hasattr(self.trading_bot, 'start'):
                result = await self.trading_bot.start()
                if result:
                    return "✅ <b>Trading Started</b>\n\nAutomated trading has been enabled and bot is running."
                else:
                    return "⚠️ <b>Trading Partially Started</b>\n\nTrading enabled but bot start encountered issues."
            else:
                return "✅ <b>Trading Enabled</b>\n\nAutomated trading has been enabled."

        except Exception as e:
            logger.error(f"Error starting trading: {str(e)}")
            return f"❌ Error starting trading: {str(e)}"

    async def _cmd_stop_trading(self, update: Dict[str, Any], context: Any) -> str:
        """
        Stop automated trading.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Stop trading message
        """
        try:
            # Disable trading in risk manager
            self.risk_manager.trading_enabled = False

            # Disable trading in signal processor if available
            if hasattr(self.trading_bot, 'signal_processor') and self.trading_bot.signal_processor:
                self.trading_bot.signal_processor.trading_enabled = False

            # Stop trading bot if available
            if hasattr(self.trading_bot, 'stop'):
                result = await self.trading_bot.stop()
                if result:
                    return "🛑 <b>Trading Stopped</b>\n\nAutomated trading has been disabled and bot is stopped."
                else:
                    return "⚠️ <b>Trading Partially Stopped</b>\n\nTrading disabled but bot stop encountered issues."
            else:
                return "🛑 <b>Trading Disabled</b>\n\nAutomated trading has been disabled."

        except Exception as e:
            logger.error(f"Error stopping trading: {str(e)}")
            return f"❌ Error stopping trading: {str(e)}"

    async def _cmd_settings(self, update: Dict[str, Any], context: Any) -> str:
        """
        Show current bot settings.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Settings message
        """
        try:
            settings_text = """
⚙️ <b>Bot Settings</b>

<b>🤖 Trading Bot:</b>
• Status: """ + ("Running" if getattr(self.trading_bot, 'is_running', False) else "Stopped") + """
• Trading Enabled: """ + ("Yes" if getattr(self.risk_manager, 'trading_enabled', False) else "No") + """

<b>📊 Risk Management:</b>
• Max Risk per Trade: """ + f"{getattr(self.risk_manager, 'max_risk_per_trade', 0):.1%}" + """
• Max Daily Risk: """ + f"{getattr(self.risk_manager, 'max_daily_risk', 0):.1%}" + """
• Stop Loss ATR Multiplier: """ + f"{getattr(self.risk_manager, 'stop_loss_atr_multiplier', 0):.1f}" + """
• Take Profit ATR Multiplier: """ + f"{getattr(self.risk_manager, 'take_profit_atr_multiplier', 0):.1f}" + """

<b>📈 Position Management:</b>
• Max Positions: """ + f"{getattr(self.position_manager, 'max_positions', 10)}" + """
• Position Timeout: """ + f"{getattr(self.position_manager, 'position_timeout', 3600)}s" + """
• Trailing Stop Enabled: """ + ("Yes" if getattr(self.position_manager, 'trailing_stop_enabled', False) else "No") + """

<b>🌐 Exchange:</b>
• Exchange: """ + f"{getattr(self.crypto_handler, 'exchange_name', 'Unknown')}" + """
• Sandbox Mode: """ + ("Yes" if getattr(self.crypto_handler, 'sandbox', False) else "No") + """
• Connected: """ + ("Yes" if getattr(self.crypto_handler, 'connected', False) else "No") + """
"""

            return settings_text

        except Exception as e:
            logger.error(f"Error in settings command: {str(e)}")
            return f"❌ Error retrieving settings: {str(e)}"

    async def _cmd_recent_trades(self, update: Dict[str, Any], context: Any) -> str:
        """
        Show recent trades.

        Args:
            update: Telegram update object
            context: Telegram context object

        Returns:
            Recent trades message
        """
        try:
            # Get recent trades from signal processor if available
            if hasattr(self.trading_bot, 'signal_processor') and self.trading_bot.signal_processor:
                # This would need to be implemented in the signal processor
                # For now, show a placeholder
                return """
📋 <b>Recent Trades</b>

<i>Recent trade history would be displayed here.</i>

This feature requires trade history storage implementation.
                """

            return "⚠️ <b>Recent Trades</b>\n\nTrade history tracking not available yet."

        except Exception as e:
            logger.error(f"Error in recent trades command: {str(e)}")
            return f"❌ Error retrieving recent trades: {str(e)}"

    def set_crypto_handler(self, crypto_handler: CryptoHandler):
        """Set the crypto handler instance."""
        self.crypto_handler = crypto_handler
        logger.info("CryptoHandler set for CryptoTelegramCommandHandler")

    def set_risk_manager(self, risk_manager: CryptoRiskManager):
        """Set the risk manager instance."""
        self.risk_manager = risk_manager
        logger.info("CryptoRiskManager set for CryptoTelegramCommandHandler")

    def set_position_manager(self, position_manager: CryptoPositionManager):
        """Set the position manager instance."""
        self.position_manager = position_manager
        logger.info("CryptoPositionManager set for CryptoTelegramCommandHandler")
