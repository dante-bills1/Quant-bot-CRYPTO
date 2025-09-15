from typing import Any
from loguru import logger
import traceback

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