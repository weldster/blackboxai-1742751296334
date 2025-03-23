import multiprocessing
import sys
from main import TradingBot
from dashboard.dashboard import run_dashboard
from logger_setup import get_logger

logger = get_logger('run')

def run_trading_bot():
    """Run the trading bot process."""
    try:
        bot = TradingBot()
        bot.start()
    except Exception as e:
        logger.error(f"Trading bot error: {e}")
        sys.exit(1)

def run_dashboard_server():
    """Run the dashboard process."""
    try:
        run_dashboard()
    except Exception as e:
        logger.error(f"Dashboard error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        # Create processes
        bot_process = multiprocessing.Process(target=run_trading_bot)
        dashboard_process = multiprocessing.Process(target=run_dashboard_server)

        # Start processes
        logger.info("Starting trading bot and dashboard...")
        bot_process.start()
        dashboard_process.start()

        # Wait for processes to complete
        bot_process.join()
        dashboard_process.join()

    except KeyboardInterrupt:
        logger.info("Shutting down...")
        bot_process.terminate()
        dashboard_process.terminate()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error running application: {e}")
        if 'bot_process' in locals():
            bot_process.terminate()
        if 'dashboard_process' in locals():
            dashboard_process.terminate()
        sys.exit(1)