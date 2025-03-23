import numpy as np
from datetime import datetime
from enum import Enum
from config import (
    TRADING_PAIR, RSI_PERIOD, RSI_OVERBOUGHT, RSI_OVERSOLD,
    MOVING_AVERAGE_PERIOD, STOP_LOSS_PERCENTAGE, TAKE_PROFIT_PERCENTAGE
)
from logger_setup import get_logger

logger = get_logger('trading_strategy')

class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class TradingStrategy:
    def __init__(self, binance_client):
        self.binance_client = binance_client
        self.trading_pair = TRADING_PAIR
        self.position = None
        self.entry_price = None
        self.last_signal = None
        self.trades_today = 0
        self.last_trade_date = None

    def calculate_rsi(self, prices, period=RSI_PERIOD):
        """Calculate Relative Strength Index."""
        try:
            if len(prices) < period + 1:
                return None

            # Calculate price changes
            deltas = np.diff(prices)
            
            # Calculate gains (positive changes) and losses (negative changes)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            # Calculate average gains and losses
            avg_gain = np.mean(gains[:period])
            avg_loss = np.mean(losses[:period])
            
            if avg_loss == 0:
                return 100
            
            # Calculate RS and RSI
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return None

    def calculate_moving_average(self, prices, period=MOVING_AVERAGE_PERIOD):
        """Calculate Simple Moving Average."""
        try:
            if len(prices) < period:
                return None
            return np.mean(prices[-period:])
        except Exception as e:
            logger.error(f"Error calculating MA: {e}")
            return None

    def should_reset_trade_count(self):
        """Check if trades count should be reset (new day)."""
        current_date = datetime.now().date()
        if self.last_trade_date != current_date:
            self.trades_today = 0
            self.last_trade_date = current_date
            return True
        return False

    def check_stop_loss(self, current_price):
        """Check if stop loss has been triggered."""
        if self.position and self.entry_price:
            loss_percentage = ((self.entry_price - current_price) / self.entry_price) * 100
            if loss_percentage >= STOP_LOSS_PERCENTAGE:
                logger.info(f"Stop loss triggered at {loss_percentage:.2f}%")
                return True
        return False

    def check_take_profit(self, current_price):
        """Check if take profit has been triggered."""
        if self.position and self.entry_price:
            profit_percentage = ((current_price - self.entry_price) / self.entry_price) * 100
            if profit_percentage >= TAKE_PROFIT_PERCENTAGE:
                logger.info(f"Take profit triggered at {profit_percentage:.2f}%")
                return True
        return False

    def generate_signal(self):
        """Generate trading signal based on technical indicators."""
        try:
            # Reset daily trade count if needed
            self.should_reset_trade_count()

            # Get historical klines data
            klines = self.binance_client.get_klines(
                self.trading_pair,
                interval='1h',
                limit=100
            )
            
            if not klines:
                logger.warning("No klines data available")
                return Signal.HOLD

            # Extract closing prices
            prices = np.array([float(k[4]) for k in klines])
            current_price = prices[-1]

            # Calculate indicators
            rsi = self.calculate_rsi(prices)
            ma = self.calculate_moving_average(prices)

            if rsi is None or ma is None:
                logger.warning("Unable to calculate indicators")
                return Signal.HOLD

            logger.info(f"Current RSI: {rsi:.2f}, MA: {ma:.2f}, Price: {current_price:.2f}")

            # Check stop loss and take profit if in position
            if self.position:
                if self.check_stop_loss(current_price) or self.check_take_profit(current_price):
                    self.last_signal = Signal.SELL
                    return Signal.SELL

            # Generate signals based on RSI and MA
            if rsi <= RSI_OVERSOLD and current_price > ma:
                if not self.position and self.trades_today < MAX_TRADES_PER_DAY:
                    self.last_signal = Signal.BUY
                    return Signal.BUY
                    
            elif rsi >= RSI_OVERBOUGHT and current_price < ma:
                if self.position:
                    self.last_signal = Signal.SELL
                    return Signal.SELL

            return Signal.HOLD

        except Exception as e:
            logger.error(f"Error generating trading signal: {e}")
            return Signal.HOLD

    def update_position(self, side, price=None):
        """Update the current position after order execution."""
        if side == Signal.BUY:
            self.position = True
            self.entry_price = price
            self.trades_today += 1
            self.last_trade_date = datetime.now().date()
        elif side == Signal.SELL:
            self.position = False
            self.entry_price = None

    def get_position_info(self):
        """Get current position information."""
        return {
            'in_position': bool(self.position),
            'entry_price': self.entry_price,
            'trades_today': self.trades_today,
            'last_trade_date': self.last_trade_date,
            'last_signal': self.last_signal.value if self.last_signal else None
        }