"""
Crypto Data Loader

This module provides data loading functionality for crypto backtesting,
handling various data formats and sources for historical crypto data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger

def load_crypto_historical_data(file_path: Path) -> Optional[pd.DataFrame]:
    """
    Load historical crypto data from CSV file.
    
    Args:
        file_path: Path to the CSV file
        
    Returns:
        DataFrame with OHLCV data or None if failed
    """
    try:
        if not file_path.exists():
            logger.error(f"Data file not found: {file_path}")
            return None
        
        # Load CSV data
        df = pd.read_csv(file_path)
        
        # Validate required columns
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return None
        
        # Convert timestamp to datetime
        if df['timestamp'].dtype == 'int64':
            # Assume timestamp is in milliseconds
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        else:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Set timestamp as index
        df.set_index('timestamp', inplace=True)
        
        # Sort by timestamp
        df.sort_index(inplace=True)
        
        # Validate data
        if len(df) == 0:
            logger.error("No data loaded")
            return None
        
        # Check for missing values
        missing_values = df.isnull().sum()
        if missing_values.any():
            logger.warning(f"Missing values found: {missing_values[missing_values > 0].to_dict()}")
            # Fill missing values with forward fill
            df.fillna(method='ffill', inplace=True)
        
        # Validate OHLC data
        invalid_ohlc = (df['high'] < df['low']) | (df['high'] < df['open']) | (df['high'] < df['close']) | \
                      (df['low'] > df['open']) | (df['low'] > df['close'])
        
        if invalid_ohlc.any():
            logger.warning(f"Found {invalid_ohlc.sum()} invalid OHLC bars")
            # Fix invalid bars
            df.loc[invalid_ohlc, 'high'] = df.loc[invalid_ohlc, ['open', 'close']].max(axis=1)
            df.loc[invalid_ohlc, 'low'] = df.loc[invalid_ohlc, ['open', 'close']].min(axis=1)
        
        # Validate volume
        negative_volume = df['volume'] < 0
        if negative_volume.any():
            logger.warning(f"Found {negative_volume.sum()} negative volume values")
            df.loc[negative_volume, 'volume'] = 0
        
        logger.info(f"Loaded {len(df)} data points from {file_path}")
        logger.info(f"Date range: {df.index[0]} to {df.index[-1]}")
        
        return df
        
    except Exception as e:
        logger.error(f"Error loading data from {file_path}: {str(e)}")
        return None

def load_crypto_data_from_exchange(
    symbol: str,
    timeframe: str,
    start_date: datetime,
    end_date: datetime,
    exchange: str = "bybit"
) -> Optional[pd.DataFrame]:
    """
    Load historical data directly from crypto exchange.
    
    Args:
        symbol: Trading symbol
        timeframe: Timeframe (1m, 5m, 1h, 1d)
        start_date: Start date
        end_date: End date
        exchange: Exchange name
        
    Returns:
        DataFrame with OHLCV data or None if failed
    """
    try:
        from src.crypto_handler import CryptoHandler
        
        # Initialize crypto handler
        crypto_handler = CryptoHandler(exchange_name=exchange)
        
        if not crypto_handler.initialize():
            logger.error(f"Failed to initialize {exchange} handler")
            return None
        
        # Get historical data
        data = crypto_handler.get_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date
        )
        
        if data is None or len(data) == 0:
            logger.error("No data received from exchange")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        logger.info(f"Loaded {len(df)} data points from {exchange}")
        return df
        
    except Exception as e:
        logger.error(f"Error loading data from {exchange}: {str(e)}")
        return None

def resample_data(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    Resample data to different timeframe.
    
    Args:
        df: Input DataFrame
        timeframe: Target timeframe (1m, 5m, 15m, 1h, 4h, 1d)
        
    Returns:
        Resampled DataFrame
    """
    try:
        # Map timeframe to pandas frequency
        timeframe_map = {
            '1m': '1T',
            '5m': '5T',
            '15m': '15T',
            '30m': '30T',
            '1h': '1H',
            '4h': '4H',
            '1d': '1D'
        }
        
        if timeframe not in timeframe_map:
            logger.error(f"Unsupported timeframe: {timeframe}")
            return df
        
        frequency = timeframe_map[timeframe]
        
        # Resample data
        resampled = df.resample(frequency).agg({
            'open': 'first',
            'high': 'max',
            'low': 'min',
            'close': 'last',
            'volume': 'sum'
        })
        
        # Remove rows with all NaN values
        resampled.dropna(inplace=True)
        
        logger.info(f"Resampled data to {timeframe}: {len(resampled)} bars")
        return resampled
        
    except Exception as e:
        logger.error(f"Error resampling data: {str(e)}")
        return df

def validate_data_quality(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate data quality and return statistics.
    
    Args:
        df: DataFrame to validate
        
    Returns:
        Dictionary with quality metrics
    """
    try:
        if df is None or len(df) == 0:
            return {"error": "No data to validate"}
        
        # Basic statistics
        total_bars = len(df)
        date_range = (df.index[-1] - df.index[0]).total_seconds() / 3600  # hours
        
        # Missing values
        missing_values = df.isnull().sum()
        
        # Price statistics
        price_stats = {
            'min_price': df[['open', 'high', 'low', 'close']].min().min(),
            'max_price': df[['open', 'high', 'low', 'close']].max().max(),
            'avg_price': df[['open', 'high', 'low', 'close']].mean().mean()
        }
        
        # Volume statistics
        volume_stats = {
            'min_volume': df['volume'].min(),
            'max_volume': df['volume'].max(),
            'avg_volume': df['volume'].mean(),
            'zero_volume_bars': (df['volume'] == 0).sum()
        }
        
        # OHLC validation
        invalid_ohlc = (df['high'] < df['low']) | (df['high'] < df['open']) | (df['high'] < df['close']) | \
                      (df['low'] > df['open']) | (df['low'] > df['close'])
        
        # Price gaps
        price_changes = df['close'].pct_change().abs()
        large_gaps = (price_changes > 0.1).sum()  # >10% price change
        
        quality_metrics = {
            'total_bars': total_bars,
            'date_range_hours': date_range,
            'missing_values': missing_values.to_dict(),
            'price_stats': price_stats,
            'volume_stats': volume_stats,
            'invalid_ohlc_bars': invalid_ohlc.sum(),
            'large_gaps': large_gaps,
            'data_quality_score': _calculate_quality_score(df)
        }
        
        return quality_metrics
        
    except Exception as e:
        logger.error(f"Error validating data quality: {str(e)}")
        return {"error": str(e)}

def _calculate_quality_score(df: pd.DataFrame) -> float:
    """
    Calculate a data quality score (0-100).
    
    Args:
        df: DataFrame to score
        
    Returns:
        Quality score (0-100)
    """
    try:
        score = 100.0
        
        # Deduct points for missing values
        missing_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
        score -= missing_ratio * 50
        
        # Deduct points for invalid OHLC
        invalid_ohlc = (df['high'] < df['low']) | (df['high'] < df['open']) | (df['high'] < df['close']) | \
                      (df['low'] > df['open']) | (df['low'] > df['close'])
        invalid_ratio = invalid_ohlc.sum() / len(df)
        score -= invalid_ratio * 30
        
        # Deduct points for zero volume
        zero_volume_ratio = (df['volume'] == 0).sum() / len(df)
        score -= zero_volume_ratio * 20
        
        # Deduct points for large price gaps
        price_changes = df['close'].pct_change().abs()
        large_gaps_ratio = (price_changes > 0.1).sum() / len(df)
        score -= large_gaps_ratio * 10
        
        return max(0.0, min(100.0, score))
        
    except Exception as e:
        logger.error(f"Error calculating quality score: {str(e)}")
        return 0.0
