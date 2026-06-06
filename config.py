DRY_RUN = True

WALLET_USAGE_PERCENT = 0.0  # must be between 0.0 and 100.0

MAXIMUM_NUMBER_OF_API_CALL_TRIES = 5
BINANCE_API_TIMEOUT = 60

TELEGRAM_USER_ID_LIST = []
SEND_TELEGRAM_MESSAGE = False

ACTIVE_TRADING_SYMBOLS = [
    {"symbol": "ETH", "weight": 1},
]

# Symbols allowed for analytical Telegram/social scanner.
# WATCHLIST is wider than ACTIVE_TRADING_SYMBOLS.
# Telegram/social signals are NOT trading permissions.
WATCHLIST = [
    "BTC",
    "ETH",
    "SOL",
    "TON",
    "LINK",
    "AVAX",
    "NEAR",
    "SUI",
    "ARB",
    "OP",
    "APT",
    "INJ",
    "SEI",
    "DOT",
    "ATOM",
    "XRP",
    "ADA",
    "FET",
    "RNDR",
]

TRADING_INTERVAL = "4h"

MIN_AI_CONFIDENCE = 0.60
MAX_TRADE_USDT = 10.0
MAX_DAILY_TRADES = 20

ALLOW_BEARISH_REVERSAL_BUY = False
