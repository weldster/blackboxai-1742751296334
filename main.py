import signal
import sys
import time
from datetime import datetime
from config import TRADING_PAIR, MAX_TRADES_PER_DAY
from logger_setup import get_logger
from binance_client import BinanceClient
from user_data_stream import UserDataStream
from trading_strategy import TradingStrategy
from order_manager import OrderManager

logger = get_logger('main')

class TradingBot:
    def __init__(self):
        self.running = False
        self.binance_client = None
        self.user_stream = None
        self.strategy = None
        self.order_manager = None
        self.last_check_time = None
        self.check_interval = 60  # Time in seconds between trading checks

    def initialize(self):
        """Initialize all components of the trading bot."""
        try:
            logger.info("Initializing trading bot...")
            
            # Initialize Binance client
            self.binance_client = BinanceClient()
            logger.info("Binance client initialized")
            
            # Initialize trading strategy
            self.strategy = TradingStrategy(self.binance_client)
            logger.info("Trading strategy initialized")
            
            # Initialize order manager
            self.order_manager = OrderManager(self.binance_client)
            logger.info("Order manager initialized")
            
            # Initialize user data stream
            self.user_stream = UserDataStream(
                self.binance_client,
                message_handler=self.handle_user_data_message
            )
            logger.info("User data stream initialized")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize trading bot: {e}")
            return False

    def handle_user_data_message(self, message):
        """Handle incoming WebSocket messages."""
        try:
            if 'e' in message:  # Check if message has an event type
                event_type = message['e']
                
                if event_type == 'executionReport':
                    # Update order status
                    self.order_manager.update_order_status(message)
                    
                elif event_type == 'outboundAccountPosition':
                    # Handle account updates
                    logger.info("Account position update received")
                    
                elif event_type == 'balanceUpdate':
                    # Handle balance updates
                    logger.info("Balance update received")
                    
        except Exception as e:
            logger.error(f"Error handling user data message: {e}")

    def execute_trading_cycle(self):
        """Execute one trading cycle."""
        try:
            # Generate trading signal
            signal = self.strategy.generate_signal()
            logger.info(f"Generated signal: {signal}")
            
            # Execute order based on signal
            if signal != "HOLD":
                order = self.order_manager.execute_order(signal, self.strategy)
                if order:
                    logger.info(f"Order executed: {order}")
                    
            # Update last check time
            self.last_check_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Error in trading cycle: {e}")

    def start(self):
        """Start the trading bot."""
        try:
            if not self.initialize():
                logger.error("Failed to initialize trading bot")
                return
            
            self.running = True
            
            # Connect to user data stream
            self.user_stream.connect()
            
            logger.info(f"Trading bot started. Trading pair: {TRADING_PAIR}")
            logger.info(f"Maximum trades per day: {MAX_TRADES_PER_DAY}")
            
            # Main trading loop
            while self.running:
                current_time = datetime.now()
                
                # Check if it's time to execute trading cycle
                if (not self.last_check_time or 
                    (current_time - self.last_check_time).seconds >= self.check_interval):
                    self.execute_trading_cycle()
                
                # Sleep to prevent excessive CPU usage
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt")
            self.stop()
        except Exception as e:
            logger.error(f"Error in main trading loop: {e}")
            self.stop()

    def stop(self):
        """Stop the trading bot."""
        try:
            logger.info("Stopping trading bot...")
            self.running = False
            
            # Disconnect user data stream
            if self.user_stream:
                self.user_stream.disconnect()
            
            # Cancel any active orders
            active_orders = self.order_manager.get_active_orders()
            for order_id in active_orders:
                self.order_manager.cancel_order(order_id)
            
            logger.info("Trading bot stopped")
            
        except Exception as e:
            logger.error(f"Error stopping trading bot: {e}")

def signal_handler(signum, frame):
    """Handle system signals."""
    logger.info(f"Received signal {signum}")
    if trading_bot:
        trading_bot.stop()
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start trading bot
    trading_bot = TradingBot()
    trading_bot.start()