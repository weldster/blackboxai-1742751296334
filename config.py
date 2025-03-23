import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Configuration
API_KEY = os.getenv('BINANCE_API_KEY')
SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
TESTNET = os.getenv('TESTNET', 'True').lower() == 'true'

# API Endpoints
if TESTNET:
    REST_BASE_URL = 'https://testnet.binance.vision/api'
    WS_BASE_URL = 'wss://testnet.binance.vision/ws'
else:
    REST_BASE_URL = 'https://api.binance.us/api'
    WS_BASE_URL = 'wss://stream.binance.us:9443/ws'

# Trading Parameters
TRADING_PAIR = 'BTCUSDT'  # Default trading pair
ORDER_SIZE = 0.001  # Default order size in BTC
MAX_TRADES_PER_DAY = 10
STOP_LOSS_PERCENTAGE = 2.0  # 2% stop loss
TAKE_PROFIT_PERCENTAGE = 3.0  # 3% take profit

# Strategy Parameters
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MOVING_AVERAGE_PERIOD = 20

# Validate required configuration
if not API_KEY or not SECRET_KEY:
    raise ValueError("API_KEY and SECRET_KEY must be set in .env file")

# Application Settings
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = 'trading_bot.log'

# Dashboard Settings
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 8000