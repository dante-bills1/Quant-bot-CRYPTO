"""
Crypto Data Fetcher

This module provides data fetching functionality from various crypto exchanges,
specifically designed for backtesting with rate limiting and error handling.
Based on the VWAP swing strategy reference implementation.
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path
import time
import warnings
warnings.filterwarnings('ignore')

from loguru import logger


class CryptoDataFetcher:
    """
    Crypto data fetcher with Binance API integration.

    Features:
    - Rate limiting to avoid API restrictions
    - Automatic retry logic
    - Multi-timeframe support
    - Data validation and cleaning
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None):
        """
        Initialize the data fetcher.

        Args:
            api_key: Binance API key (optional for public endpoints)
            api_secret: Binance API secret (optional for public endpoints)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.binance.com/api/v3"
        self.session = requests.Session()

        # Rate limiting
        self.request_count = 0
        self.last_request_time = 0
        self.min_request_interval = 0.1  # 100ms between requests

        # Request limits (Binance limits)
        self.max_requests_per_minute = 1200
        self.max_requests_per_second = 50

        logger.info("CryptoDataFetcher initialized")

    def _rate_limit_wait(self):
        """Apply rate limiting to avoid API restrictions."""
        current_time = time.time()

        # Reset counter every minute
        if current_time - self.last_request_time > 60:
            self.request_count = 0

        # Check if we need to wait
        if self.request_count >= self.max_requests_per_second:
            wait_time = 1.0 - (current_time - self.last_request_time)
            if wait_time > 0:
                time.sleep(wait_time)
                self.request_count = 0
        elif self.request_count > 0:
            # Minimum interval between requests
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.min_request_interval:
                time.sleep(self.min_request_interval - time_since_last)

        self.last_request_time = time.time()
        self.request_count += 1

    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Make a request to Binance API with rate limiting and error handling.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            JSON response or None if failed
        """
        self._rate_limit_wait()

        url = f"{self.base_url}{endpoint}"
        headers = {'Accept': 'application/json'}

        try:
            response = self.session.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()
            return data

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {endpoint}: {e}")
            return None
        except ValueError as e:
            logger.error(f"JSON parsing failed for {endpoint}: {e}")
            return None

    def fetch_ohlcv(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV data from Binance.

        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            interval: Timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            start_time: Start time for data
            end_time: End time for data
            limit: Maximum number of candles to fetch

        Returns:
            DataFrame with OHLCV data or None if failed
        """
        logger.info(f"Fetching {symbol} {interval} data from Binance")

        all_data = []
        current_start = start_time

        # If no start time provided, get recent data
        if current_start is None:
            current_start = datetime.now() - timedelta(days=30)  # Default to last 30 days

        while True:
            params = {
                'symbol': symbol,
                'interval': interval,
                'startTime': int(current_start.timestamp() * 1000),
                'limit': min(limit, 1000)  # Binance max limit is 1000
            }

            if end_time:
                params['endTime'] = int(end_time.timestamp() * 1000)

            try:
                data = self._make_request("/klines", params)

                if not data:
                    break

                all_data.extend(data)

                # Update start time for next batch
                last_timestamp = data[-1][0] / 1000
                if end_time and last_timestamp >= end_time.timestamp():
                    break
                current_start = datetime.fromtimestamp(last_timestamp + 1)

                # Break if we got less than limit (no more data)
                if len(data) < params['limit']:
                    break

                # Add delay between batches
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error fetching data for {symbol} {interval}: {e}")
                break

        if not all_data:
            logger.warning(f"No data received for {symbol} {interval}")
            return None

        # Convert to DataFrame
        df = self._convert_to_dataframe(all_data)

        if df is not None and not df.empty:
            logger.info(f"Fetched {len(df)} candles for {symbol} {interval}")
            logger.info(f"Date range: {df.index[0]} to {df.index[-1]}")

        return df

    def _convert_to_dataframe(self, raw_data: List[List]) -> Optional[pd.DataFrame]:
        """
        Convert raw Binance klines data to DataFrame.

        Args:
            raw_data: Raw kline data from Binance

        Returns:
            DataFrame with OHLCV data
        """
        try:
            if not raw_data:
                return None

            # Create DataFrame with Binance kline format
            df = pd.DataFrame(raw_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])

            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
            df.set_index('timestamp', inplace=True)

            # Convert OHLCV columns to numeric
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')

            # Drop rows with NaN values in essential columns
            df = df.dropna(subset=['open', 'high', 'low', 'close'])

            # Ensure volume is non-negative
            df['volume'] = df['volume'].clip(lower=0)

            # Sort by timestamp
            df.sort_index(inplace=True)

            return df[['open', 'high', 'low', 'close', 'volume']]

        except Exception as e:
            logger.error(f"Error converting raw data to DataFrame: {e}")
            return None

    def get_available_symbols(self) -> List[str]:
        """
        Get list of available trading symbols from Binance.

        Returns:
            List of trading symbols
        """
        try:
            data = self._make_request("/exchangeInfo")

            if not data or 'symbols' not in data:
                logger.error("Failed to get exchange info")
                return []

            symbols = []
            for symbol_info in data['symbols']:
                if symbol_info.get('status') == 'TRADING':
                    symbols.append(symbol_info['symbol'])

            logger.info(f"Found {len(symbols)} active trading symbols")
            return symbols

        except Exception as e:
            logger.error(f"Error getting available symbols: {e}")
            return []

    def validate_data_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate data quality and return metrics.

        Args:
            df: DataFrame to validate

        Returns:
            Dictionary with quality metrics
        """
        if df is None or df.empty:
            return {"error": "No data to validate"}

        try:
            metrics = {
                'total_bars': len(df),
                'date_range': f"{df.index[0]} to {df.index[-1]}",
                'missing_values': df.isnull().sum().to_dict(),
                'price_range': {
                    'min': df[['open', 'high', 'low', 'close']].min().min(),
                    'max': df[['open', 'high', 'low', 'close']].max().max()
                },
                'volume_stats': {
                    'min': df['volume'].min(),
                    'max': df['volume'].max(),
                    'avg': df['volume'].mean(),
                    'zero_volume_bars': (df['volume'] == 0).sum()
                }
            }

            # OHLC validation
            invalid_ohlc = (df['high'] < df['low']) | (df['high'] < df['open']) | (df['high'] < df['close']) | \
                          (df['low'] > df['open']) | (df['low'] > df['close'])
            metrics['invalid_ohlc_bars'] = invalid_ohlc.sum()

            # Calculate quality score
            quality_score = 100.0

            # Deduct for missing values
            missing_ratio = df.isnull().sum().sum() / (len(df) * len(df.columns))
            quality_score -= missing_ratio * 50

            # Deduct for invalid OHLC
            invalid_ratio = invalid_ohlc.sum() / len(df)
            quality_score -= invalid_ratio * 30

            # Deduct for zero volume
            zero_volume_ratio = (df['volume'] == 0).sum() / len(df)
            quality_score -= zero_volume_ratio * 20

            metrics['quality_score'] = max(0.0, min(100.0, quality_score))

            return metrics

        except Exception as e:
            logger.error(f"Error validating data quality: {e}")
            return {"error": str(e)}

    def save_data(self, df: pd.DataFrame, filepath: Path, format: str = 'csv'):
        """
        Save data to file.

        Args:
            df: DataFrame to save
            filepath: File path
            format: File format ('csv', 'json', 'parquet')
        """
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)

            if format == 'csv':
                df.to_csv(filepath)
            elif format == 'json':
                df.to_json(filepath, orient='index', date_format='iso')
            elif format == 'parquet':
                df.to_parquet(filepath)
            else:
                raise ValueError(f"Unsupported format: {format}")

            logger.info(f"Data saved to {filepath} in {format} format")

        except Exception as e:
            logger.error(f"Error saving data to {filepath}: {e}")

    def load_data(self, filepath: Path, format: str = 'csv') -> Optional[pd.DataFrame]:
        """
        Load data from file.

        Args:
            filepath: File path
            format: File format ('csv', 'json', 'parquet')

        Returns:
            DataFrame or None if failed
        """
        try:
            if not filepath.exists():
                logger.error(f"File not found: {filepath}")
                return None

            if format == 'csv':
                df = pd.read_csv(filepath, index_col=0, parse_dates=True)
            elif format == 'json':
                df = pd.read_json(filepath, orient='index')
                df.index = pd.to_datetime(df.index, utc=True)
            elif format == 'parquet':
                df = pd.read_parquet(filepath)
            else:
                raise ValueError(f"Unsupported format: {format}")

            logger.info(f"Data loaded from {filepath}")
            return df

        except Exception as e:
            logger.error(f"Error loading data from {filepath}: {e}")
            return None


def create_data_fetcher(api_key: Optional[str] = None, api_secret: Optional[str] = None) -> CryptoDataFetcher:
    """
    Factory function to create a data fetcher instance.

    Args:
        api_key: Binance API key
        api_secret: Binance API secret

    Returns:
        CryptoDataFetcher instance
    """
    return CryptoDataFetcher(api_key, api_secret)
