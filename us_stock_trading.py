"""
US Stock Trading Interface
Supports Alpaca Markets API for US stock trading
"""

import logging
import os
from typing import Dict, List, Optional
from datetime import datetime
import time


class USStockTradingInterface:
    """US Stock Trading Interface using Alpaca Markets API"""
    
    def __init__(self, api_key: str = None, api_secret: str = None, base_url: str = None, paper: bool = True):
        """
        Initialize US Stock Trading Interface
        
        Args:
            api_key: Alpaca API Key (optional, read from config)
            api_secret: Alpaca API Secret (optional, read from config)
            base_url: Alpaca API Base URL (optional, defaults to paper trading URL)
            paper: Whether to use paper trading (default True)
        """
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key
        self.api_secret = api_secret
        self.paper = paper
        self.connected = False
        self.alpaca = None
        
        # Default URLs
        if base_url is None:
            if paper:
                self.base_url = "https://paper-api.alpaca.markets"  # Paper trading
            else:
                self.base_url = "https://api.alpaca.markets"  # Live trading
        else:
            self.base_url = base_url
        
        # Try to import alpaca-trade-api
        try:
            import alpaca_trade_api as tradeapi
            self.tradeapi = tradeapi
            self.logger.info("Alpaca Trade API module loaded successfully")
        except ImportError:
            self.logger.warning("alpaca-trade-api module not installed")
            self.logger.warning("Install with: pip install alpaca-trade-api")
            self.logger.warning("Will use simulation mode (no actual orders)")
            self.tradeapi = None
    
    def connect(self, api_key: str = None, api_secret: str = None, paper: bool = None) -> bool:
        """
        Connect to Alpaca API
        
        Args:
            api_key: Alpaca API Key (optional, read from config)
            api_secret: Alpaca API Secret (optional, read from config)
            paper: Whether to use paper trading (optional, read from config)
            
        Returns:
            Whether connection was successful
        """
        if not self.tradeapi:
            self.logger.warning("Alpaca Trade API not installed, using simulation mode")
            self.connected = False
            return False
        
        # Read from config if not provided
        if api_key is None:
            api_key = os.getenv('ALPACA_API_KEY', '')
        if api_secret is None:
            api_secret = os.getenv('ALPACA_API_SECRET', '')
        if paper is None:
            paper = os.getenv('ALPACA_PAPER', 'true').lower() == 'true'
        
        if not api_key or not api_secret:
            self.logger.error("Alpaca API credentials not configured. Please set ALPACA_API_KEY and ALPACA_API_SECRET in environment config")
            self.connected = False
            return False
        
        try:
            # Create Alpaca API client
            self.alpaca = self.tradeapi.REST(
                key_id=api_key,
                secret_key=api_secret,
                base_url=self.base_url,
                api_version='v2'
            )
            
            # Test connection by getting account info
            account = self.alpaca.get_account()
            if account:
                self.connected = True
                self.api_key = api_key
                self.api_secret = api_secret
                self.paper = paper
                trading_mode = "Paper Trading" if paper else "Live Trading"
                self.logger.info(f"Alpaca API connected successfully - {trading_mode}")
                self.logger.info(f"Account Status: {account.status}, Buying Power: ${float(account.buying_power):,.2f}")
                return True
            else:
                self.logger.error("Failed to get account info from Alpaca")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to Alpaca API: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from Alpaca API"""
        if self.alpaca:
            try:
                self.alpaca = None
                self.connected = False
                self.logger.info("Alpaca API disconnected")
            except Exception as e:
                self.logger.error(f"Error disconnecting: {e}")
    
    def get_account_info(self) -> Dict:
        """
        Get account information
        
        Returns:
            Account information dictionary
        """
        if not self.connected or not self.alpaca:
            return {
                'success': False,
                'error': 'Not connected to Alpaca API'
            }
        
        try:
            account = self.alpaca.get_account()
            return {
                'success': True,
                'account_number': account.account_number,
                'status': account.status,
                'currency': account.currency,
                'buying_power': float(account.buying_power),
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'equity': float(account.equity),
                'day_trading_buying_power': float(account.daytrading_buying_power),
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'transfers_blocked': account.transfers_blocked,
                'account_blocked': account.account_blocked,
                'created_at': account.created_at,
                'trade_suspended_by_user': account.trade_suspended_by_user,
                'multiplier': float(account.multiplier),
                'shorting_enabled': account.shorting_enabled,
                'long_market_value': float(account.long_market_value),
                'short_market_value': float(account.short_market_value),
                'day_trade_count': account.daytrade_count
            }
        except Exception as e:
            self.logger.error(f"Failed to get account info: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """
        Get position for a stock
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            Position dictionary or None if no position
        """
        if not self.connected or not self.alpaca:
            return None
        
        try:
            positions = self.alpaca.list_positions()
            for pos in positions:
                if pos.symbol.upper() == symbol.upper():
                    return {
                        'symbol': pos.symbol,
                        'quantity': int(pos.qty),
                        'avg_entry_price': float(pos.avg_entry_price),
                        'current_price': float(pos.current_price),
                        'market_value': float(pos.market_value),
                        'cost_basis': float(pos.cost_basis),
                        'unrealized_pl': float(pos.unrealized_pl),
                        'unrealized_plpc': float(pos.unrealized_plpc),
                        'side': pos.side,  # 'long' or 'short'
                        'can_sell': int(pos.qty)  # US stocks support T+0, can sell immediately
                    }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get position for {symbol}: {e}")
            return None
    
    def get_all_positions(self) -> List[Dict]:
        """
        Get all positions
        
        Returns:
            List of position dictionaries
        """
        if not self.connected or not self.alpaca:
            return []
        
        try:
            positions = self.alpaca.list_positions()
            result = []
            for pos in positions:
                result.append({
                    'symbol': pos.symbol,
                    'quantity': int(pos.qty),
                    'avg_entry_price': float(pos.avg_entry_price),
                    'current_price': float(pos.current_price),
                    'market_value': float(pos.market_value),
                    'cost_basis': float(pos.cost_basis),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc),
                    'side': pos.side,
                    'can_sell': int(pos.qty)
                })
            return result
        except Exception as e:
            self.logger.error(f"Failed to get all positions: {e}")
            return []
    
    def buy_stock(self, symbol: str, quantity: int, order_type: str = 'market', 
                  limit_price: float = None, stop_price: float = None, 
                  time_in_force: str = 'day') -> Dict:
        """
        Buy stock
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            quantity: Number of shares to buy
            order_type: Order type ('market', 'limit', 'stop', 'stop_limit')
            limit_price: Limit price (required for limit orders)
            stop_price: Stop price (required for stop orders)
            time_in_force: Time in force ('day', 'gtc', 'opg', 'cls', 'ioc', 'fok')
            
        Returns:
            Order result dictionary
        """
        if not self.connected or not self.alpaca:
            return {
                'success': False,
                'error': 'Not connected to Alpaca API'
            }
        
        try:
            # Submit order
            if order_type == 'market':
                order = self.alpaca.submit_order(
                    symbol=symbol.upper(),
                    qty=quantity,
                    side='buy',
                    type='market',
                    time_in_force=time_in_force
                )
            elif order_type == 'limit':
                if limit_price is None:
                    return {'success': False, 'error': 'Limit price required for limit orders'}
                order = self.alpaca.submit_order(
                    symbol=symbol.upper(),
                    qty=quantity,
                    side='buy',
                    type='limit',
                    time_in_force=time_in_force,
                    limit_price=limit_price
                )
            elif order_type == 'stop':
                if stop_price is None:
                    return {'success': False, 'error': 'Stop price required for stop orders'}
                order = self.alpaca.submit_order(
                    symbol=symbol.upper(),
                    qty=quantity,
                    side='buy',
                    type='stop',
                    time_in_force=time_in_force,
                    stop_price=stop_price
                )
            elif order_type == 'stop_limit':
                if limit_price is None or stop_price is None:
                    return {'success': False, 'error': 'Limit price and stop price required for stop_limit orders'}
                order = self.alpaca.submit_order(
                    symbol=symbol.upper(),
                    qty=quantity,
                    side='buy',
                    type='stop_limit',
                    time_in_force=time_in_force,
                    limit_price=limit_price,
                    stop_price=stop_price
                )
            else:
                return {'success': False, 'error': f'Unsupported order type: {order_type}'}
            
            return {
                'success': True,
                'order_id': order.id,
                'symbol': order.symbol,
                'quantity': int(order.qty),
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'filled_qty': int(order.filled_qty) if hasattr(order, 'filled_qty') and order.filled_qty is not None else 0,
                'filled_avg_price': float(order.filled_avg_price) if hasattr(order, 'filled_avg_price') and order.filled_avg_price is not None else None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to buy {symbol}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def sell_stock(self, symbol: str, quantity: int, order_type: str = 'market',
                   limit_price: float = None, stop_price: float = None,
                   time_in_force: str = 'day') -> Dict:
        """
        Sell stock
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            quantity: Number of shares to sell
            order_type: Order type ('market', 'limit', 'stop', 'stop_limit')
            limit_price: Limit price (required for limit orders)
            stop_price: Stop price (required for stop orders)
            time_in_force: Time in force ('day', 'gtc', 'opg', 'cls', 'ioc', 'fok')
            
        Returns:
            Order result dictionary
        """
        if not self.connected or not self.alpaca:
            return {
                'success': False,
                'error': 'Not connected to Alpaca API'
            }
        
        try:
            # Submit order
            if order_type == 'market':
                order = self.alpaca.submit_order(
                    symbol=symbol.upper(),
                    qty=quantity,
                    side='sell',
                    type='market',
                    time_in_force=time_in_force
                )
            elif order_type == 'limit':
                if limit_price is None:
                    return {'success': False, 'error': 'Limit price required for limit orders'}
                order = self.alpaca.submit_order(
                    symbol=symbol.upper(),
                    qty=quantity,
                    side='sell',
                    type='limit',
                    time_in_force=time_in_force,
                    limit_price=limit_price
                )
            elif order_type == 'stop':
                if stop_price is None:
                    return {'success': False, 'error': 'Stop price required for stop orders'}
                order = self.alpaca.submit_order(
                    symbol=symbol.upper(),
                    qty=quantity,
                    side='sell',
                    type='stop',
                    time_in_force=time_in_force,
                    stop_price=stop_price
                )
            elif order_type == 'stop_limit':
                if limit_price is None or stop_price is None:
                    return {'success': False, 'error': 'Limit price and stop price required for stop_limit orders'}
                order = self.alpaca.submit_order(
                    symbol=symbol.upper(),
                    qty=quantity,
                    side='sell',
                    type='stop_limit',
                    time_in_force=time_in_force,
                    limit_price=limit_price,
                    stop_price=stop_price
                )
            else:
                return {'success': False, 'error': f'Unsupported order type: {order_type}'}
            
            return {
                'success': True,
                'order_id': order.id,
                'symbol': order.symbol,
                'quantity': int(order.qty),
                'side': order.side,
                'type': order.type,
                'status': order.status,
                'filled_qty': int(order.filled_qty) if hasattr(order, 'filled_qty') and order.filled_qty is not None else 0,
                'filled_avg_price': float(order.filled_avg_price) if hasattr(order, 'filled_avg_price') and order.filled_avg_price is not None else None
            }
            
        except Exception as e:
            self.logger.error(f"Failed to sell {symbol}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cancel_order(self, order_id: str) -> Dict:
        """
        Cancel an order
        
        Args:
            order_id: Order ID to cancel
            
        Returns:
            Cancellation result dictionary
        """
        if not self.connected or not self.alpaca:
            return {
                'success': False,
                'error': 'Not connected to Alpaca API'
            }
        
        try:
            self.alpaca.cancel_order(order_id)
            return {
                'success': True,
                'order_id': order_id
            }
        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_orders(self, status: str = 'open', limit: int = 50) -> List[Dict]:
        """
        Get orders
        
        Args:
            status: Order status ('open', 'closed', 'all')
            limit: Maximum number of orders to return
            
        Returns:
            List of order dictionaries
        """
        if not self.connected or not self.alpaca:
            return []
        
        try:
            orders = self.alpaca.list_orders(status=status, limit=limit)
            result = []
            for order in orders:
                result.append({
                    'id': order.id,
                    'symbol': order.symbol,
                    'quantity': int(order.qty),
                    'side': order.side,
                    'type': order.type,
                    'status': order.status,
                    'time_in_force': order.time_in_force,
                    'filled_qty': int(order.filled_qty) if hasattr(order, 'filled_qty') and order.filled_qty is not None else 0,
                    'filled_avg_price': float(order.filled_avg_price) if hasattr(order, 'filled_avg_price') and order.filled_avg_price is not None else None,
                    'limit_price': float(order.limit_price) if hasattr(order, 'limit_price') and order.limit_price is not None else None,
                    'stop_price': float(order.stop_price) if hasattr(order, 'stop_price') and order.stop_price is not None else None,
                    'submitted_at': order.submitted_at,
                    'filled_at': order.filled_at if hasattr(order, 'filled_at') else None
                })
            return result
        except Exception as e:
            self.logger.error(f"Failed to get orders: {e}")
            return []
    
    def get_latest_bar(self, symbol: str) -> Optional[Dict]:
        """
        Get latest bar (price data) for a symbol
        
        Args:
            symbol: Stock symbol
            
        Returns:
            Latest bar data dictionary
        """
        if not self.connected or not self.alpaca:
            return None
        
        try:
            bars = self.alpaca.get_latest_bar(symbol.upper())
            if bars:
                return {
                    'symbol': symbol.upper(),
                    'timestamp': bars.t,
                    'open': float(bars.o),
                    'high': float(bars.h),
                    'low': float(bars.l),
                    'close': float(bars.c),
                    'volume': int(bars.v)
                }
            return None
        except Exception as e:
            self.logger.error(f"Failed to get latest bar for {symbol}: {e}")
            return None


class USStockTradingSimulator:
    """US Stock Trading Simulator (for testing without API)"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.connected = True
        self.positions = {}
        self.orders = []
        self.cash = 100000.0  # Starting cash: $100,000
        
    def connect(self, *args, **kwargs) -> bool:
        """Simulate connection"""
        self.logger.info("Using US Stock Trading Simulator (no actual orders)")
        return True
    
    def disconnect(self):
        """Simulate disconnection"""
        pass
    
    def get_account_info(self) -> Dict:
        """Get simulated account info"""
        total_value = self.cash
        for pos in self.positions.values():
            total_value += pos['quantity'] * pos['current_price']
        
        return {
            'success': True,
            'status': 'ACTIVE',
            'currency': 'USD',
            'buying_power': self.cash,
            'cash': self.cash,
            'portfolio_value': total_value,
            'equity': total_value,
            'paper': True
        }
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get simulated position"""
        return self.positions.get(symbol.upper())
    
    def get_all_positions(self) -> List[Dict]:
        """Get all simulated positions"""
        return list(self.positions.values())
    
    def buy_stock(self, symbol: str, quantity: int, order_type: str = 'market',
                  limit_price: float = None, **kwargs) -> Dict:
        """Simulate buying stock"""
        # Get current price (simulated)
        current_price = limit_price if limit_price else 100.0  # Default $100
        
        total_cost = quantity * current_price
        if total_cost > self.cash:
            return {'success': False, 'error': 'Insufficient buying power'}
        
        self.cash -= total_cost
        
        if symbol.upper() in self.positions:
            pos = self.positions[symbol.upper()]
            total_qty = pos['quantity'] + quantity
            avg_price = ((pos['quantity'] * pos['avg_entry_price']) + total_cost) / total_qty
            pos['quantity'] = total_qty
            pos['avg_entry_price'] = avg_price
        else:
            self.positions[symbol.upper()] = {
                'symbol': symbol.upper(),
                'quantity': quantity,
                'avg_entry_price': current_price,
                'current_price': current_price,
                'can_sell': quantity
            }
        
        order_id = f"SIM_{int(time.time())}"
        self.orders.append({
            'id': order_id,
            'symbol': symbol.upper(),
            'side': 'buy',
            'quantity': quantity,
            'status': 'filled'
        })
        
        return {
            'success': True,
            'order_id': order_id,
            'symbol': symbol.upper(),
            'quantity': quantity,
            'status': 'filled'
        }
    
    def sell_stock(self, symbol: str, quantity: int, order_type: str = 'market',
                   limit_price: float = None, **kwargs) -> Dict:
        """Simulate selling stock"""
        if symbol.upper() not in self.positions:
            return {'success': False, 'error': 'No position found'}
        
        pos = self.positions[symbol.upper()]
        if quantity > pos['quantity']:
            return {'success': False, 'error': 'Insufficient shares'}
        
        current_price = limit_price if limit_price else pos.get('current_price', 100.0)
        proceeds = quantity * current_price
        self.cash += proceeds
        
        pos['quantity'] -= quantity
        if pos['quantity'] == 0:
            del self.positions[symbol.upper()]
        
        order_id = f"SIM_{int(time.time())}"
        self.orders.append({
            'id': order_id,
            'symbol': symbol.upper(),
            'side': 'sell',
            'quantity': quantity,
            'status': 'filled'
        })
        
        return {
            'success': True,
            'order_id': order_id,
            'symbol': symbol.upper(),
            'quantity': quantity,
            'status': 'filled'
        }
    
    def cancel_order(self, order_id: str) -> Dict:
        """Simulate canceling order"""
        return {'success': True, 'order_id': order_id}
    
    def get_orders(self, status: str = 'open', limit: int = 50) -> List[Dict]:
        """Get simulated orders"""
        return self.orders[-limit:] if self.orders else []
    
    def get_latest_bar(self, symbol: str) -> Optional[Dict]:
        """Get simulated latest bar"""
        if symbol.upper() in self.positions:
            price = self.positions[symbol.upper()]['current_price']
        else:
            price = 100.0
        
        return {
            'symbol': symbol.upper(),
            'close': price,
            'open': price,
            'high': price * 1.01,
            'low': price * 0.99,
            'volume': 1000000
        }

