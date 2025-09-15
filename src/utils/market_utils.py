from typing import Dict, Optional, Any, List, Tuple
from loguru import logger
import traceback
import pandas as pd
import numpy as np

def calculate_tick_value(symbol: str, symbol_info: Any = None, crypto_handler=None) -> float:
    """
    Calculate the tick value for a given crypto symbol.
    
    Args:
        symbol: The trading symbol (e.g., 'BTC/USDT:USDT')
        symbol_info: Exchange symbol_info object (optional)
        crypto_handler: CryptoHandler instance (optional, used if symbol_info is not provided)
        
    Returns:
        float: The tick value for the symbol
    """
    try:
        # Default tick value for crypto (typically 0.01 for most pairs)
        tick_value = 0.01
        
        # If symbol_info not provided and crypto_handler is available, get symbol info
        if symbol_info is None and crypto_handler is not None:
            symbol_info = crypto_handler.get_symbol_info(symbol)
        
        if symbol_info:
            # Get price precision from symbol info
            price_precision = symbol_info.get("price_precision", 2)
            
            # Calculate tick value based on precision
            if price_precision == 0:
                tick_value = 1.0  # For symbols with no decimal places
            elif price_precision == 1:
                tick_value = 0.1  # For symbols with 1 decimal place
            elif price_precision == 2:
                tick_value = 0.01  # For symbols with 2 decimal places
            elif price_precision == 3:
                tick_value = 0.001  # For symbols with 3 decimal places
            elif price_precision == 4:
                tick_value = 0.0001  # For symbols with 4 decimal places
            elif price_precision == 5:
                tick_value = 0.00001  # For symbols with 5 decimal places
            elif price_precision == 6:
                tick_value = 0.000001  # For symbols with 6 decimal places
            else:
                tick_value = 10 ** (-price_precision)  # General case
                
            logger.debug(f"Calculated tick value for {symbol}: precision={price_precision}, tick_value={tick_value}")
            return tick_value
        
        # Fallback to hard-coded values for common crypto pairs
        if "BTC" in symbol.upper():
            tick_value = 0.01  # Bitcoin typically has 2 decimal places
        elif "ETH" in symbol.upper():
            tick_value = 0.01  # Ethereum typically has 2 decimal places
        elif "USDT" in symbol.upper() and any(coin in symbol.upper() for coin in ["BTC", "ETH", "BNB", "ADA", "SOL"]):
            tick_value = 0.0001  # Major crypto/USDT pairs typically have 4 decimal places
        elif "USDC" in symbol.upper():
            tick_value = 0.0001  # USDC pairs typically have 4 decimal places
        
        logger.warning(f"Using fallback tick value for {symbol}: {tick_value}")
        return tick_value
        
    except Exception as e:
        logger.error(f"Error calculating tick value for {symbol}: {str(e)}")
        logger.error(traceback.format_exc())
        return 0.01  # Return default value in case of error
    
def convert_ticks_to_price(ticks: float, symbol: str, symbol_info: Any = None, crypto_handler=None) -> float:
    """
    Convert ticks to price value for a crypto symbol.
    
    Args:
        ticks: Number of ticks
        symbol: The trading symbol
        symbol_info: Exchange symbol_info object (optional)
        crypto_handler: CryptoHandler instance (optional, used if symbol_info is not provided)
        
    Returns:
        float: The price equivalent of the given ticks
    """
    tick_value = calculate_tick_value(symbol, symbol_info, crypto_handler)
    return ticks * tick_value

def convert_price_to_ticks(price_diff: float, symbol: str, symbol_info: Any = None, crypto_handler=None) -> float:
    """
    Convert price difference to ticks for a crypto symbol.
    
    Args:
        price_diff: Price difference
        symbol: The trading symbol
        symbol_info: Exchange symbol_info object (optional)
        crypto_handler: CryptoHandler instance (optional, used if symbol_info is not provided)
        
    Returns:
        float: The tick equivalent of the given price difference
    """
    tick_value = calculate_tick_value(symbol, symbol_info, crypto_handler)
    if tick_value == 0:
        return 0  # Avoid division by zero
    return price_diff / tick_value 

def adjust_trade_for_spread(
    symbol: str,
    order_type: str,
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    crypto_handler: Any  # CryptoHandler instance
) -> Tuple[float, float, float, float]:
    """
    Adjusts SL/TP based on the current spread to maintain intended risk/reward.

    Args:
        symbol (str): The trading symbol.
        order_type (str): 'BUY' or 'SELL'.
        entry_price (float): The signal's entry price.
        stop_loss (float): The signal's stop loss.
        take_profit (float): The signal's take profit.
        crypto_handler (Any): An instance of the CryptoHandler.

    Returns:
        Tuple[float, float, float, float]: A tuple containing the actual_entry_price, 
                                           adjusted_stop_loss, and adjusted_take_profit, spread.
    """
    try:
        tick_info = crypto_handler.get_last_tick(symbol)
        if not tick_info:
            logger.error(f"Could not retrieve tick info for {symbol} to adjust for spread.")
            return entry_price, stop_loss, take_profit, 0.0

        spread = tick_info['ask'] - tick_info['bid']
        
        if order_type.upper() == 'BUY':
            actual_entry_price = tick_info['ask']
            risk_ticks = entry_price - stop_loss
            reward_ticks = take_profit - entry_price
            
            new_stop_loss = actual_entry_price - risk_ticks
            new_take_profit = actual_entry_price + reward_ticks
            
        elif order_type.upper() == 'SELL':
            actual_entry_price = tick_info['bid']
            risk_ticks = stop_loss - entry_price
            reward_ticks = entry_price - take_profit

            new_stop_loss = actual_entry_price + risk_ticks
            new_take_profit = actual_entry_price - reward_ticks
        else:
            logger.warning(f"Unknown order type '{order_type}' for spread adjustment.")
            return entry_price, stop_loss, take_profit, 0.0

        logger.info(f"Spread Adjustment for {symbol} {order_type}:")
        logger.info(f"  - Original Signal: Entry={entry_price}, SL={stop_loss}, TP={take_profit}")
        logger.info(f"  - Market Prices: Bid={tick_info['bid']}, Ask={tick_info['ask']}, Spread={spread:.5f}")
        logger.info(f"  - Actual Entry: {actual_entry_price}")
        logger.info(f"  - Adjusted Trade: SL={new_stop_loss}, TP={new_take_profit}")

        return actual_entry_price, new_stop_loss, new_take_profit, spread

    except Exception as e:
        logger.error(f"Error adjusting trade for spread for {symbol}: {e}")
        logger.error(traceback.format_exc())
        return entry_price, stop_loss, take_profit, 0.0 