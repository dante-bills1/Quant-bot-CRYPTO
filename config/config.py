from pathlib import Path
from dotenv import load_dotenv
import os

# --- Load environment variables ---
load_dotenv()

# --- Base paths ---
BASE_DIR = Path(__file__).parent.parent

# ================= Crypto Configuration =================
CRYPTO_CONFIG = {
    "exchange": os.getenv("CRYPTO_EXCHANGE", "bybit"),  # bybit, binance
    "api_key": os.getenv("CRYPTO_API_KEY", ""),
    "api_secret": os.getenv("CRYPTO_API_SECRET", ""),
    "sandbox": os.getenv("CRYPTO_SANDBOX", "true").lower() == "true",
    "timeout": 10,
    "retry_attempts": 3,
    "rate_limit": True,
}

# ================= Trading Configuration =================
TRADING_CONFIG = {
    "account_type": "demo",  # "real" or "demo"
    "magic_number": 1235, # Unique identifier for this bot's trades
    "symbols": [
        "BTC/USDT:USDT",
        "ETH/USDT:USDT",
        "SOL/USDT:USDT",
        "ADA/USDT:USDT",
        "DOT/USDT:USDT",
        "XRP/USDT:USDT",
        "DOGE/USDT:USDT",
        "POL/USDT:USDT",
        "LINK/USDT:USDT",
    ],
    "max_daily_risk": 0.06,
    "risk_per_trade": 0.02,  # 2% risk per trade
    "min_position_size": 10.0,  # Minimum position size in USD
    "max_position_size": 1000.0,  # Maximum position size in USD
    "default_leverage": 5,  # Default leverage for positions
    "spread_factor": 1.5,
    "allow_position_additions": False,
    "position_addition_threshold": 0.5,

    # --- Execution Mode ---
    # 'bar' -> analyze on closed candles (recommended)
    # 'tick' -> analyze on new ticks (real-time)
    "execution_mode": os.getenv("EXECUTION_MODE", "bar"),

    # --- Enhanced Data Management ---

    "data_management": {
        "use_direct_fetch": True,
        "real_time_bars_count": 10,
        "price_tolerance": 0.0003,
        "validate_trades": True,
        "tick_delay_tolerance": 2.0,
    },

    "close_positions_on_shutdown": False,
    "signal_generators": [
        "VolumeMAOscillator",
        # "MeanReversionScalper",
        # "SuperT",
        # "GarbageAlgoStrategy",
        # "ExhaustionReversalStrategy",
        # "AlphaFusionScalper",
        # "AlphaFusionScalper2",
        # "AlphaQuantScalperV1",
    ],
}

# ================= Telegram Configuration =================
TELEGRAM_CONFIG = {
    "token": os.getenv("TELEGRAM_BOT_TOKEN"),
    "allowed_users": [int(id) for id in os.getenv("TELEGRAM_ALLOWED_USERS", "").split(",") if id.strip()],
    "enabled": True
}

# ================= Logging Configuration =================
LOG_CONFIG = {
    "use_file_logging": os.getenv("LOG_TO_FILE", "False").lower() == "true",
    "log_file_path": BASE_DIR / "logs/trading_bot.log",
    "level": "INFO", # DEBUG, INFO, TRACE
    "rotation": "10 MB",
    "retention": "10 days",
    "compression": "zip",
    "colorize": True,
    "backtrace": False,
    "diagnose": False,
    "format_console": "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    "format_file": "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
}

# ================= Risk Management Configuration =================
RISK_MANAGER_CONFIG = {
    'max_risk_per_trade': 0.001,  # Max 0.1% of account balance per trade
    'max_drawdown': 0.10,  # Max 10% drawdown for the entire account
    'min_risk_reward_ratio': 1.5,
    'stop_level_buffer_percent': 0.15,  # 15% buffer on min stop distance
    'max_daily_loss': 0.015,
    'min_risk_reward': 0.5,
    'max_concurrent_trades': 1000,
    'risk_per_trade': TRADING_CONFIG['risk_per_trade'],
    'min_position_size': TRADING_CONFIG['min_position_size'],
    'max_position_size': TRADING_CONFIG['max_position_size'],
    'default_leverage': TRADING_CONFIG['default_leverage'],
}

# ================= Trade Exit Configuration =================
TRADE_EXIT_CONFIG = {
    'scalping': {
        'enabled': True,
        'profit_percentage': 0.6, # Close trade when 60% of TP is reached
        'strategy_names': [
            'AlphaFusionScalper',
            'AlphaFusionScalper2',
            'AlphaQuantScalperV1',
            'MeanReversionScalper'
        ]
    },
    'partial_tp_ratio': 0.5,
    'tp_levels': [
        {'ratio': 0.5, 'size': 0.4},
        {'ratio': 1.0, 'size': 0.3},
        {'ratio': 1.5, 'size': 0.3}
    ],
    'trailing_stop': {
        'enabled': False, # General enable/disable for trailing stops
        # --- Instrument Category Rules (processed in order, first match wins) ---
        'instrument_category_rules': [
            # Specific Symbols (highest priority)
            {'symbol_is': 'XAUUSD', 'category': 'metals_gold'},
            {'symbol_is': 'BTCUSD', 'category': 'crypto_btc'},

            # Crypto Exchange Based (crypto-specific categories)
            {'symbol_contains': ':USDT', 'category': 'crypto_stablecoin_pairs'}, # USDT pairs
            {'symbol_contains': ':USDC', 'category': 'crypto_stablecoin_pairs'}, # USDC pairs
            {'symbol_contains': ':BUSD', 'category': 'crypto_stablecoin_pairs'}, # BUSD pairs
            {'symbol_contains': 'BTC', 'category': 'crypto_bitcoin'}, # Bitcoin related
            {'symbol_contains': 'ETH', 'category': 'crypto_ethereum'}, # Ethereum related
            {'symbol_contains': 'SOL', 'category': 'crypto_solana'}, # Solana related
            {'symbol_contains': 'ADA', 'category': 'crypto_cardano'}, # Cardano related
            {'symbol_contains': 'DOT', 'category': 'crypto_polkadot'}, # Polkadot related
            {'symbol_contains': 'LINK', 'category': 'crypto_chainlink'}, # Chainlink related
            {'symbol_contains': 'UNI', 'category': 'crypto_uniswap'}, # Uniswap related
            {'symbol_contains': 'AAVE', 'category': 'crypto_aave'}, # Aave related

            # Fallback Regex/Symbol Name Contains (lower priority)
            {'symbol_contains': 'EUR', 'category': 'forex_eur_pairs'}, # Example for EUR specific
            {'symbol_contains': 'VOLATILITY', 'category': 'volatility_indices_fallback'}, # If path fails
            {'symbol_contains': 'CRASH', 'category': 'crash_boom_indices_fallback'},
            {'symbol_contains': 'BOOM', 'category': 'crash_boom_indices_fallback'},
            {'symbol_contains': 'JUMP', 'category': 'jump_indices_fallback'},
            {'symbol_contains': 'STEP', 'category': 'step_range_indices_fallback'},
            {'symbol_contains': 'RANGE BREAK', 'category': 'step_range_indices_fallback'},
        ],

        # --- Instrument Category Settings ---
        # These are the parameter sets. The 'default' is crucial.
        'instrument_category_settings': {
            'default': { # General fallback settings
                'mode': 'atr', # More robust default
                'trail_points': 20.0, # Pips, only if mode is 'pips'
                'atr_multiplier': 2.0,
                'atr_period': 14,
                'percent': 0.01, # Percentage, only if mode is 'percent'
                'break_even_enabled': True,
                'break_even_pips': 10,
                'break_even_buffer_pips': 1,
                'activation_ratio': 0.5, # When to start trailing (e.g., 0.5 = 50% of initial risk gained)
                'min_profit_activation': 0.2, # Alternative: min profit in R before activation
                'auto_sl_setup': True, # If position opened with no SL, set one automatically
                'auto_sl_percent': 0.02, # e.g. 2% of entry price
            },
            'forex_major': {
                'mode': 'pips',
                'trail_points': 15.0,
                'atr_multiplier': 1.8, # Keep for potential mode switch
                'percent': 0.005,    # Keep for potential mode switch
                'break_even_pips': 8,
                'activation_ratio': 0.6,
            },
            'forex_minor': {
                'mode': 'pips',
                'trail_points': 20.0,
                'atr_multiplier': 2.0,
                'percent': 0.007,
                'break_even_pips': 10,
            },
            'forex_exotic': {
                'mode': 'atr',
                'trail_points': 30.0,
                'atr_multiplier': 2.5,
                'percent': 0.012,
                'break_even_pips': 15,
            },
             'forex_eur_pairs': { # Example of a more specific regex/contains based category
                'mode': 'pips',
                'trail_points': 12.0, # Tighter for EUR pairs example
                'atr_multiplier': 1.5,
                'break_even_pips': 7,
            },
            'metals_gold': { # Specific for XAUUSD
                'mode': 'atr',
                'trail_points': 50.0, # Value in price points for XAUUSD
                'atr_multiplier': 2.0, # ATR multiplier
                'percent': 0.008,
                'break_even_pips': 20, # Value in price points
                'activation_ratio': 0.4,
            },
            'metals_other': {
                'mode': 'atr',
                'trail_points': 60.0,
                'atr_multiplier': 2.2,
                'percent': 0.01,
                'break_even_pips': 25,
            },
            'crypto_btc': { # Specific for BTCUSD
                'mode': 'percent',
                'trail_points': 100.0, # Basis points if mode was different, here it's just a placeholder
                'atr_multiplier': 2.5, # ATR for crypto can be large
                'percent': 0.015, # 1.5% trailing
                'break_even_pips': 50, # Price points
                'activation_ratio': 0.3,
            },
            'crypto_other': {
                'mode': 'percent',
                'trail_points': 150.0,
                'atr_multiplier': 3.0,
                'percent': 0.02, # 2% trailing
                'break_even_pips': 75,
            },
            'volatility_indices': {
                'mode': 'atr',
                'trail_points': 80.0, # Price points
                'atr_multiplier': 2.8,
                'percent': 0.012,
                'break_even_pips': 25, # Price points
            },
            'volatility_indices_fallback': { # If path fails, use symbol_contains
                'mode': 'atr',
                'trail_points': 85.0,
                'atr_multiplier': 3.0,
                'break_even_pips': 30,
            },
            'crash_boom_indices': {
                'mode': 'percent', # Often these move fast, percent might be better
                'trail_points': 150.0,
                'atr_multiplier': 3.5,
                'percent': 0.020, # 2%
                'break_even_pips': 40, # Price points
            },
            'crash_boom_indices_fallback': {
                'mode': 'percent',
                'trail_points': 160.0,
                'atr_multiplier': 3.7,
                'percent': 0.022,
                'break_even_pips': 45,
            },
            'jump_indices': {
                'mode': 'atr',
                'trail_points': 60.0,
                'atr_multiplier': 2.5,
                'percent': 0.010,
                'break_even_pips': 20,
            },
            'jump_indices_fallback': {
                'mode': 'atr',
                'trail_points': 65.0,
                'atr_multiplier': 2.6,
                'break_even_pips': 22,
            },
            'step_range_indices': {
                'mode': 'pips', # Or ATR depending on typical movement
                'trail_points': 40.0,
                'atr_multiplier': 2.0,
                'percent': 0.008,
                'break_even_pips': 15,
            },
            'step_range_indices_fallback': {
                'mode': 'pips',
                'trail_points': 45.0,
                'atr_multiplier': 2.2,
                'break_even_pips': 18,
            }
            # Add other categories as needed
        }
    }
}