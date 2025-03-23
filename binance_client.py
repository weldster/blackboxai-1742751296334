import hmac
import hashlib
import time
import requests
from urllib.parse import urlencode
from requests.exceptions import RequestException
from config import API_KEY, SECRET_KEY, REST_BASE_URL, TESTNET
from logger_setup import get_logger

logger = get_logger('binance_client')

class BinanceClient:
    def __init__(self):
        self.api_key = API_KEY
        self.api_secret = SECRET_KEY
        self.base_url = REST_BASE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': self.api_key
        })

    def _generate_signature(self, params):
        """Generate HMAC SHA256 signature for request authentication."""
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    def _make_request(self, method, endpoint, params=None, signed=False, retry_count=3):
        """Make an HTTP request to the Binance API with retry logic."""
        if params is None:
            params = {}

        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)

        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(retry_count):
            try:
                response = self.session.request(
                    method,
                    url,
                    params=params if method == 'GET' else None,
                    json=params if method == 'POST' else None
                )
                response.raise_for_status()
                return response.json()
            except RequestException as e:
                if attempt == retry_count - 1:
                    logger.error(f"Request failed after {retry_count} attempts: {e}")
                    raise
                wait_time = 2 ** attempt
                logger.warning(f"Request failed, retrying in {wait_time} seconds...")
                time.sleep(wait_time)

    def get_listen_key(self):
        """Create a listen key for user data stream."""
        try:
            endpoint = '/v3/userDataStream'
            response = self._make_request('POST', endpoint)
            listen_key = response.get('listenKey')
            if not listen_key:
                raise ValueError("No listen key in response")
            logger.info("Successfully obtained listen key")
            return listen_key
        except Exception as e:
            logger.error(f"Failed to get listen key: {e}")
            raise

    def keep_alive_listen_key(self, listen_key):
        """Keep the user data stream alive."""
        try:
            endpoint = '/v3/userDataStream'
            params = {'listenKey': listen_key}
            self._make_request('PUT', endpoint, params)
            logger.debug("Successfully renewed listen key")
            return True
        except Exception as e:
            logger.error(f"Failed to keep listen key alive: {e}")
            return False

    def get_account_info(self):
        """Get account information."""
        try:
            endpoint = '/v3/account'
            return self._make_request('GET', endpoint, signed=True)
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            raise

    def create_order(self, symbol, side, order_type, quantity=None, price=None):
        """Create a new order."""
        try:
            endpoint = '/v3/order'
            params = {
                'symbol': symbol,
                'side': side,
                'type': order_type,
            }

            if quantity:
                params['quantity'] = quantity
            if price and order_type != 'MARKET':
                params['price'] = price
            
            response = self._make_request('POST', endpoint, params, signed=True)
            logger.info(f"Successfully created {order_type} {side} order for {symbol}")
            return response
        except Exception as e:
            logger.error(f"Failed to create order: {e}")
            raise

    def get_order_status(self, symbol, order_id):
        """Get status of an order."""
        try:
            endpoint = '/v3/order'
            params = {
                'symbol': symbol,
                'orderId': order_id
            }
            return self._make_request('GET', endpoint, params, signed=True)
        except Exception as e:
            logger.error(f"Failed to get order status: {e}")
            raise

    def cancel_order(self, symbol, order_id):
        """Cancel an existing order."""
        try:
            endpoint = '/v3/order'
            params = {
                'symbol': symbol,
                'orderId': order_id
            }
            response = self._make_request('DELETE', endpoint, params, signed=True)
            logger.info(f"Successfully cancelled order {order_id} for {symbol}")
            return response
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            raise

    def get_symbol_price(self, symbol):
        """Get current price for a symbol."""
        try:
            endpoint = '/v3/ticker/price'
            params = {'symbol': symbol}
            return float(self._make_request('GET', endpoint, params)['price'])
        except Exception as e:
            logger.error(f"Failed to get price for {symbol}: {e}")
            raise

    def get_exchange_info(self):
        """Get exchange trading rules and symbol information."""
        try:
            endpoint = '/v3/exchangeInfo'
            return self._make_request('GET', endpoint)
        except Exception as e:
            logger.error(f"Failed to get exchange info: {e}")
            raise

    def get_klines(self, symbol, interval, limit=500):
        """Get kline/candlestick data."""
        try:
            endpoint = '/v3/klines'
            params = {
                'symbol': symbol,
                'interval': interval,
                'limit': limit
            }
            return self._make_request('GET', endpoint, params)
        except Exception as e:
            logger.error(f"Failed to get klines for {symbol}: {e}")
            raise