from flask import Flask, render_template, jsonify
from datetime import datetime
import os
import sys

# Add parent directory to path to import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import FLASK_HOST, FLASK_PORT, TRADING_PAIR
from logger_setup import get_logger
from binance_client import BinanceClient
from trading_strategy import TradingStrategy
from order_manager import OrderManager

logger = get_logger('dashboard')

app = Flask(__name__)
binance_client = BinanceClient()
trading_strategy = TradingStrategy(binance_client)
order_manager = OrderManager(binance_client)

@app.route('/')
def index():
    """Render the main dashboard page."""
    return render_template('index.html', trading_pair=TRADING_PAIR)

@app.route('/api/market_data')
def get_market_data():
    """Get current market data."""
    try:
        current_price = binance_client.get_symbol_price(TRADING_PAIR)
        
        # Get recent klines for chart
        klines = binance_client.get_klines(
            TRADING_PAIR,
            interval='1h',
            limit=24
        )
        
        chart_data = [{
            'time': datetime.fromtimestamp(k[0] / 1000).strftime('%Y-%m-%d %H:%M'),
            'price': float(k[4])  # closing price
        } for k in klines]
        
        return jsonify({
            'success': True,
            'current_price': current_price,
            'chart_data': chart_data
        })
    except Exception as e:
        logger.error(f"Error fetching market data: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/trading_status')
def get_trading_status():
    """Get current trading status."""
    try:
        position_info = trading_strategy.get_position_info()
        active_orders = order_manager.get_active_orders()
        
        return jsonify({
            'success': True,
            'position': position_info,
            'active_orders': active_orders,
            'trading_pair': TRADING_PAIR
        })
    except Exception as e:
        logger.error(f"Error fetching trading status: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/account_info')
def get_account_info():
    """Get account information."""
    try:
        account_info = binance_client.get_account_info()
        
        # Filter and format balances
        balances = [{
            'asset': balance['asset'],
            'free': float(balance['free']),
            'locked': float(balance['locked'])
        } for balance in account_info['balances']
        if float(balance['free']) > 0 or float(balance['locked']) > 0]
        
        return jsonify({
            'success': True,
            'balances': balances
        })
    except Exception as e:
        logger.error(f"Error fetching account info: {e}")
        return jsonify({'success': False, 'error': str(e)})

def run_dashboard():
    """Run the Flask dashboard application."""
    try:
        app.run(
            host=FLASK_HOST,
            port=FLASK_PORT,
            debug=False  # Set to False in production
        )
    except Exception as e:
        logger.error(f"Error running dashboard: {e}")
        raise

if __name__ == '__main__':
    run_dashboard()