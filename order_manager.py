from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from config import TRADING_PAIR, ORDER_SIZE
from logger_setup import get_logger
from trading_strategy import Signal

logger = get_logger('order_manager')

class OrderManager:
    def __init__(self, binance_client):
        self.client = binance_client
        self.trading_pair = TRADING_PAIR
        self.order_size = ORDER_SIZE
        self.active_orders = {}
        self.initialize_trading_rules()

    def initialize_trading_rules(self):
        """Initialize trading rules from exchange info."""
        try:
            exchange_info = self.client.get_exchange_info()
            symbol_info = next(
                (s for s in exchange_info['symbols'] if s['symbol'] == self.trading_pair),
                None
            )
            
            if not symbol_info:
                raise ValueError(f"Trading pair {self.trading_pair} not found in exchange info")
            
            # Extract lot size filter
            lot_size_filter = next(
                (f for f in symbol_info['filters'] if f['filterType'] == 'LOT_SIZE'),
                None
            )
            
            if lot_size_filter:
                self.min_qty = float(lot_size_filter['minQty'])
                self.max_qty = float(lot_size_filter['maxQty'])
                self.step_size = float(lot_size_filter['stepSize'])
            
            # Extract price filter
            price_filter = next(
                (f for f in symbol_info['filters'] if f['filterType'] == 'PRICE_FILTER'),
                None
            )
            
            if price_filter:
                self.tick_size = float(price_filter['tickSize'])
            
            logger.info(f"Trading rules initialized for {self.trading_pair}")
            
        except Exception as e:
            logger.error(f"Failed to initialize trading rules: {e}")
            raise

    def normalize_quantity(self, quantity):
        """Normalize the quantity according to the lot size rules."""
        step_size_str = f"{self.step_size:.8f}"
        precision = len(step_size_str.split('.')[-1].rstrip('0'))
        normalized = float(Decimal(str(quantity)).quantize(
            Decimal(str(self.step_size)),
            rounding=ROUND_DOWN
        ))
        return round(normalized, precision)

    def normalize_price(self, price):
        """Normalize the price according to the tick size rules."""
        tick_size_str = f"{self.tick_size:.8f}"
        precision = len(tick_size_str.split('.')[-1].rstrip('0'))
        normalized = float(Decimal(str(price)).quantize(
            Decimal(str(self.tick_size)),
            rounding=ROUND_DOWN
        ))
        return round(normalized, precision)

    def execute_order(self, signal, strategy):
        """Execute a trade based on the signal."""
        try:
            if signal == Signal.HOLD:
                return None

            current_price = self.client.get_symbol_price(self.trading_pair)
            
            if signal == Signal.BUY:
                return self._place_buy_order(current_price, strategy)
            elif signal == Signal.SELL:
                return self._place_sell_order(current_price, strategy)
            
        except Exception as e:
            logger.error(f"Failed to execute {signal.value} order: {e}")
            return None

    def _place_buy_order(self, price, strategy):
        """Place a buy order."""
        try:
            # Calculate and normalize quantity
            quantity = self.normalize_quantity(self.order_size)
            
            # Check minimum quantity
            if quantity < self.min_qty:
                logger.warning(f"Order quantity {quantity} is below minimum {self.min_qty}")
                return None
            
            # Place market buy order
            order = self.client.create_order(
                symbol=self.trading_pair,
                side='BUY',
                order_type='MARKET',
                quantity=quantity
            )
            
            if order:
                order_id = order['orderId']
                self.active_orders[order_id] = {
                    'symbol': self.trading_pair,
                    'side': 'BUY',
                    'quantity': quantity,
                    'price': price,
                    'timestamp': datetime.now()
                }
                
                # Update strategy position
                strategy.update_position(Signal.BUY, price)
                
                logger.info(f"Buy order placed successfully: {order_id}")
                return order
            
        except Exception as e:
            logger.error(f"Failed to place buy order: {e}")
            return None

    def _place_sell_order(self, price, strategy):
        """Place a sell order."""
        try:
            # Calculate and normalize quantity
            quantity = self.normalize_quantity(self.order_size)
            
            # Check minimum quantity
            if quantity < self.min_qty:
                logger.warning(f"Order quantity {quantity} is below minimum {self.min_qty}")
                return None
            
            # Place market sell order
            order = self.client.create_order(
                symbol=self.trading_pair,
                side='SELL',
                order_type='MARKET',
                quantity=quantity
            )
            
            if order:
                order_id = order['orderId']
                self.active_orders[order_id] = {
                    'symbol': self.trading_pair,
                    'side': 'SELL',
                    'quantity': quantity,
                    'price': price,
                    'timestamp': datetime.now()
                }
                
                # Update strategy position
                strategy.update_position(Signal.SELL)
                
                logger.info(f"Sell order placed successfully: {order_id}")
                return order
            
        except Exception as e:
            logger.error(f"Failed to place sell order: {e}")
            return None

    def cancel_order(self, order_id):
        """Cancel an active order."""
        try:
            if order_id in self.active_orders:
                order_info = self.active_orders[order_id]
                
                response = self.client.cancel_order(
                    symbol=order_info['symbol'],
                    order_id=order_id
                )
                
                if response:
                    del self.active_orders[order_id]
                    logger.info(f"Order {order_id} cancelled successfully")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False

    def get_order_status(self, order_id):
        """Get the current status of an order."""
        try:
            if order_id in self.active_orders:
                order_info = self.active_orders[order_id]
                
                status = self.client.get_order_status(
                    symbol=order_info['symbol'],
                    order_id=order_id
                )
                
                return status
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get status for order {order_id}: {e}")
            return None

    def get_active_orders(self):
        """Get all active orders."""
        return self.active_orders

    def update_order_status(self, order_update):
        """Update the status of an order based on WebSocket updates."""
        try:
            order_id = order_update['i']
            
            if order_id in self.active_orders:
                if order_update['X'] in ['FILLED', 'CANCELED', 'REJECTED', 'EXPIRED']:
                    del self.active_orders[order_id]
                    logger.info(f"Order {order_id} status updated to {order_update['X']}")
                
        except Exception as e:
            logger.error(f"Failed to update order status: {e}")