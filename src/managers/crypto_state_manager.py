"""
Crypto State Manager

This module provides state management functionality for the crypto trading bot,
implementing the JSON-based persistence and thread-safe state updates from the reference bot.
"""

import json
import os
import threading
import time
from typing import Dict, Any, Optional
from loguru import logger


class CryptoStateManager:
    """
    Manages trading bot state with JSON persistence and thread safety.

    Based on reference bot's state management patterns:
    - JSON-based persistence with atomic writes
    - Thread-safe state updates using locks
    - Position tracking and signal attempt prevention
    - Last bar tracking for proper timing
    """

    def __init__(self, state_file: str = "crypto_trading_state.json"):
        """
        Initialize the state manager.

        Args:
            state_file: Path to the state file
        """
        self.state_file = state_file
        self._state_lock = threading.Lock()
        self._state: Dict[str, Any] = {}
        self._initialize_state()

        logger.info(f"CryptoStateManager initialized with state file: {state_file}")

    def _initialize_state(self):
        """Initialize state with default values."""
        self._state = {
            "last_bar": None,
            "position": None,
            "last_signal_attempt": None,
            "active_trades": {},
            "daily_stats": {
                "trades": 0,
                "profit": 0.0,
                "loss": 0.0,
                "date": time.strftime("%Y-%m-%d")
            },
            "shutdown_requested": False,
            "last_updated": time.time()
        }

    def load_state(self) -> Dict[str, Any]:
        """
        Load state from file.

        Returns:
            Current state dictionary
        """
        try:
            if not os.path.exists(self.state_file):
                logger.info(f"State file {self.state_file} does not exist, using defaults")
                return self._state.copy()

            with open(self.state_file, "r", encoding="utf-8") as f:
                loaded_state = json.load(f)

            # Merge loaded state with defaults to handle missing keys
            merged_state = self._state.copy()
            merged_state.update(loaded_state)

            # Ensure last_signal_attempt is set (for backward compatibility)
            merged_state.setdefault("last_signal_attempt", None)
            merged_state.setdefault("active_trades", {})

            self._state = merged_state
            logger.info(f"State loaded from {self.state_file}")

            return self._state.copy()

        except Exception as e:
            logger.error(f"Failed to load state from {self.state_file}: {e}")
            return self._state.copy()

    def save_state(self):
        """Save current state to file with atomic write."""
        try:
            # Create temp file for atomic write
            temp_file = self.state_file + ".tmp"

            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, default=str)

            # Atomic move
            os.replace(temp_file, self.state_file)

            logger.debug(f"State saved to {self.state_file}")

        except Exception as e:
            logger.error(f"Failed to save state to {self.state_file}: {e}")

    def get_state(self, key: str = None) -> Any:
        """
        Get state value for a key.

        Args:
            key: State key to retrieve (None for entire state)

        Returns:
            State value or entire state dict
        """
        with self._state_lock:
            if key is None:
                return self._state.copy()
            return self._state.get(key)

    def set_state(self, key: str, value: Any):
        """
        Set state value for a key.

        Args:
            key: State key to set
            value: Value to set
        """
        with self._state_lock:
            self._state[key] = value
            self._state["last_updated"] = time.time()
            self.save_state()

    def update_state(self, updates: Dict[str, Any]):
        """
        Update multiple state values.

        Args:
            updates: Dictionary of state updates
        """
        with self._state_lock:
            self._state.update(updates)
            self._state["last_updated"] = time.time()
            self.save_state()

    def update_last_bar(self, symbol: str, timeframe: str, timestamp: int):
        """
        Update last bar timestamp for a symbol-timeframe pair.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe string
            timestamp: Bar timestamp
        """
        key = f"last_bar_{symbol}_{timeframe}"
        self.set_state(key, timestamp)

    def get_last_bar(self, symbol: str, timeframe: str) -> Optional[int]:
        """
        Get last bar timestamp for a symbol-timeframe pair.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe string

        Returns:
            Last bar timestamp or None
        """
        key = f"last_bar_{symbol}_{timeframe}"
        return self.get_state(key)

    def set_position(self, symbol: str, position_data: Dict[str, Any]):
        """
        Set position data for a symbol.

        Args:
            symbol: Trading symbol
            position_data: Position information
        """
        with self._state_lock:
            if "position" not in self._state:
                self._state["position"] = {}

            self._state["position"][symbol] = position_data
            self._state["last_updated"] = time.time()
            self.save_state()

            logger.debug(f"Position updated for {symbol}")

    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get position data for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Position data or None
        """
        positions = self.get_state("position") or {}
        return positions.get(symbol)

    def clear_position(self, symbol: str):
        """
        Clear position data for a symbol.

        Args:
            symbol: Trading symbol
        """
        with self._state_lock:
            if "position" in self._state and symbol in self._state["position"]:
                del self._state["position"][symbol]
                self._state["last_updated"] = time.time()
                self.save_state()

                logger.debug(f"Position cleared for {symbol}")

    def set_last_signal_attempt(self, signal_id: str, timestamp: int):
        """
        Set last signal attempt to prevent duplicate signals.

        Args:
            signal_id: Unique signal identifier
            timestamp: Signal timestamp
        """
        self.set_state("last_signal_attempt", {
            "signal_id": signal_id,
            "timestamp": timestamp
        })

    def get_last_signal_attempt(self) -> Optional[Dict[str, Any]]:
        """Get last signal attempt information."""
        return self.get_state("last_signal_attempt")

    def is_signal_already_attempted(self, signal_id: str, timestamp: int) -> bool:
        """
        Check if a signal was already attempted.

        Args:
            signal_id: Unique signal identifier
            timestamp: Signal timestamp

        Returns:
            True if signal was already attempted
        """
        last_attempt = self.get_last_signal_attempt()
        if not last_attempt:
            return False

        return (last_attempt.get("signal_id") == signal_id and
                last_attempt.get("timestamp") == timestamp)

    def add_active_trade(self, trade_id: str, trade_data: Dict[str, Any]):
        """
        Add an active trade to tracking.

        Args:
            trade_id: Unique trade identifier
            trade_data: Trade information
        """
        with self._state_lock:
            if "active_trades" not in self._state:
                self._state["active_trades"] = {}

            self._state["active_trades"][trade_id] = trade_data
            self._state["last_updated"] = time.time()
            self.save_state()

            logger.debug(f"Active trade added: {trade_id}")

    def remove_active_trade(self, trade_id: str):
        """
        Remove an active trade from tracking.

        Args:
            trade_id: Unique trade identifier
        """
        with self._state_lock:
            if "active_trades" in self._state and trade_id in self._state["active_trades"]:
                del self._state["active_trades"][trade_id]
                self._state["last_updated"] = time.time()
                self.save_state()

                logger.debug(f"Active trade removed: {trade_id}")

    def get_active_trades(self) -> Dict[str, Dict[str, Any]]:
        """Get all active trades."""
        return self.get_state("active_trades") or {}

    def update_daily_stats(self, pnl: float, trade_count: int = 1):
        """
        Update daily trading statistics.

        Args:
            pnl: Profit/Loss for the trade
            trade_count: Number of trades (default 1)
        """
        with self._state_lock:
            if "daily_stats" not in self._state:
                self._state["daily_stats"] = {
                    "trades": 0,
                    "profit": 0.0,
                    "loss": 0.0,
                    "date": time.strftime("%Y-%m-%d")
                }

            # Check if it's a new day
            current_date = time.strftime("%Y-%m-%d")
            if self._state["daily_stats"]["date"] != current_date:
                # Reset daily stats for new day
                self._state["daily_stats"] = {
                    "trades": 0,
                    "profit": 0.0,
                    "loss": 0.0,
                    "date": current_date
                }

            # Update stats
            self._state["daily_stats"]["trades"] += trade_count

            if pnl > 0:
                self._state["daily_stats"]["profit"] += pnl
            else:
                self._state["daily_stats"]["loss"] += abs(pnl)

            self._state["last_updated"] = time.time()
            self.save_state()

    def get_daily_stats(self) -> Dict[str, Any]:
        """Get daily trading statistics."""
        return self.get_state("daily_stats") or {}

    def set_shutdown_requested(self, requested: bool = True):
        """
        Set shutdown request flag.

        Args:
            requested: Whether shutdown is requested
        """
        self.set_state("shutdown_requested", requested)

    def is_shutdown_requested(self) -> bool:
        """Check if shutdown is requested."""
        return self.get_state("shutdown_requested") or False

    def reset_daily_stats(self):
        """Reset daily statistics."""
        with self._state_lock:
            self._state["daily_stats"] = {
                "trades": 0,
                "profit": 0.0,
                "loss": 0.0,
                "date": time.strftime("%Y-%m-%d")
            }
            self._state["last_updated"] = time.time()
            self.save_state()

            logger.info("Daily statistics reset")

    def get_state_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the current state.

        Returns:
            State summary dictionary
        """
        state = self.get_state()

        return {
            "positions_count": len(state.get("position", {})),
            "active_trades_count": len(state.get("active_trades", {})),
            "daily_trades": state.get("daily_stats", {}).get("trades", 0),
            "daily_pnl": state.get("daily_stats", {}).get("profit", 0) - state.get("daily_stats", {}).get("loss", 0),
            "shutdown_requested": state.get("shutdown_requested", False),
            "last_updated": state.get("last_updated", 0)
        }

    def cleanup_old_state(self, max_age_days: int = 30):
        """
        Clean up old state entries.

        Args:
            max_age_days: Maximum age in days for state entries
        """
        try:
            cutoff_time = time.time() - (max_age_days * 24 * 3600)

            with self._state_lock:
                # Clean up old last bar entries
                keys_to_remove = []
                for key, value in self._state.items():
                    if key.startswith("last_bar_") and isinstance(value, (int, float)):
                        if value < cutoff_time:
                            keys_to_remove.append(key)

                for key in keys_to_remove:
                    del self._state[key]

                if keys_to_remove:
                    self._state["last_updated"] = time.time()
                    self.save_state()
                    logger.info(f"Cleaned up {len(keys_to_remove)} old state entries")

        except Exception as e:
            logger.error(f"Error cleaning up old state: {e}")


# Global instance
_crypto_state_manager_instance = None


def get_crypto_state_manager(state_file: str = "crypto_trading_state.json") -> CryptoStateManager:
    """
    Get the global CryptoStateManager instance.

    Args:
        state_file: Path to the state file

    Returns:
        CryptoStateManager instance
    """
    global _crypto_state_manager_instance

    if _crypto_state_manager_instance is None:
        _crypto_state_manager_instance = CryptoStateManager(state_file)
        _crypto_state_manager_instance.load_state()

    return _crypto_state_manager_instance
