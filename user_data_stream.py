import json
import threading
import time
import websocket
from config import WS_BASE_URL
from logger_setup import get_logger

logger = get_logger('user_data_stream')

class UserDataStream:
    def __init__(self, binance_client, message_handler=None):
        """Initialize the user data stream.
        
        Args:
            binance_client: Instance of BinanceClient
            message_handler: Callback function for handling incoming messages
        """
        self.binance_client = binance_client
        self.message_handler = message_handler
        self.ws = None
        self.listen_key = None
        self.ws_url = WS_BASE_URL
        self.running = False
        self.reconnect_delay = 1  # Initial reconnect delay in seconds
        self.max_reconnect_delay = 300  # Maximum reconnect delay (5 minutes)
        self.keepalive_timer = None

    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages."""
        try:
            data = json.loads(message)
            logger.debug(f"Received message: {message}")
            
            if self.message_handler:
                self.message_handler(data)
            
            # Process different event types
            if 'e' in data:
                event_type = data['e']
                if event_type == 'outboundAccountPosition':
                    self._handle_account_update(data)
                elif event_type == 'executionReport':
                    self._handle_order_update(data)
                elif event_type == 'balanceUpdate':
                    self._handle_balance_update(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _on_error(self, ws, error):
        """Handle WebSocket errors."""
        logger.error(f"WebSocket error: {error}")
        self._schedule_reconnect()

    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close."""
        logger.warning(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        self._schedule_reconnect()

    def _on_open(self, ws):
        """Handle WebSocket connection open."""
        logger.info("WebSocket connection established")
        self.reconnect_delay = 1  # Reset reconnect delay on successful connection
        self._start_keepalive_timer()

    def _schedule_reconnect(self):
        """Schedule a reconnection attempt with exponential backoff."""
        if self.running:
            logger.info(f"Attempting to reconnect in {self.reconnect_delay} seconds...")
            time.sleep(self.reconnect_delay)
            self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
            self.connect()

    def _start_keepalive_timer(self):
        """Start the keepalive timer to maintain the listen key."""
        def keepalive_job():
            while self.running:
                try:
                    if self.listen_key:
                        success = self.binance_client.keep_alive_listen_key(self.listen_key)
                        if success:
                            logger.debug("Keepalive successful")
                        else:
                            logger.warning("Failed to send keepalive")
                            self._schedule_reconnect()
                    time.sleep(30 * 60)  # Send keepalive every 30 minutes
                except Exception as e:
                    logger.error(f"Keepalive error: {e}")
                    self._schedule_reconnect()
                    break

        self.keepalive_timer = threading.Thread(target=keepalive_job)
        self.keepalive_timer.daemon = True
        self.keepalive_timer.start()

    def _handle_account_update(self, data):
        """Handle account position updates."""
        logger.info(f"Account update received: {data['B']}")
        # Implement specific account update handling logic here

    def _handle_order_update(self, data):
        """Handle order execution updates."""
        logger.info(f"Order update received: {data['s']} - {data['X']}")
        # Implement specific order update handling logic here

    def _handle_balance_update(self, data):
        """Handle balance updates."""
        logger.info(f"Balance update received: {data['a']} - {data['d']}")
        # Implement specific balance update handling logic here

    def connect(self):
        """Establish WebSocket connection."""
        try:
            if not self.listen_key:
                self.listen_key = self.binance_client.get_listen_key()
            
            ws_url = f"{self.ws_url}/{self.listen_key}"
            
            websocket.enableTrace(True)
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
                on_open=self._on_open
            )
            
            self.running = True
            
            # Start WebSocket connection in a separate thread
            ws_thread = threading.Thread(target=self.ws.run_forever)
            ws_thread.daemon = True
            ws_thread.start()
            
            logger.info("WebSocket connection started")
            
        except Exception as e:
            logger.error(f"Failed to establish WebSocket connection: {e}")
            self._schedule_reconnect()

    def disconnect(self):
        """Close WebSocket connection."""
        self.running = False
        if self.ws:
            self.ws.close()
        if self.keepalive_timer:
            self.keepalive_timer.join(timeout=1)
        logger.info("WebSocket connection closed")

    def is_connected(self):
        """Check if WebSocket is connected."""
        return self.ws and self.ws.sock and self.ws.sock.connected