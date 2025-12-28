"""
Alpaca Auto Trader
Auto Trading Monitoring Service
"""

import time
import threading
import logging
from datetime import datetime
from typing import Dict, List
from alpaca_strategy_manager import AlpacaStrategyManager
from us_stock_trading import USStockTradingInterface, USStockTradingSimulator
from config_manager import config_manager


class AlpacaAutoTrader:
    """Alpaca Auto Trading Service"""
    
    def __init__(self, trading_interface=None):
        """
        Initialize auto trading service
        
        Args:
            trading_interface: Trading interface
        """
        self.logger = logging.getLogger(__name__)
        self.trading = trading_interface
        self.strategy_manager = AlpacaStrategyManager(trading_interface)
        self.running = False
        self.thread = None
        self.check_interval = 300  # Check every 5 minutes (in seconds)
    
    def set_trading_interface(self, trading_interface):
        """Set trading interface"""
        self.trading = trading_interface
        self.strategy_manager.set_trading_interface(trading_interface)
    
    def start(self):
        """Start auto trading service"""
        if self.running:
            self.logger.warning("Auto trading service is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.logger.info("Auto trading service started")
    
    def stop(self):
        """Stop auto trading service"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("Auto trading service stopped")
    
    def _monitor_loop(self):
        """Monitoring loop"""
        while self.running:
            try:
                # 1. Check stop loss/take profit
                self._check_stop_loss_take_profit()
                
                # 2. Execute active strategy tasks
                self._execute_strategy_tasks()
                
                # Wait for next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                time.sleep(60)  # Wait 1 minute after error before retry
    
    def _check_stop_loss_take_profit(self):
        """Check stop loss/take profit"""
        try:
            signals = self.strategy_manager.check_stop_loss_take_profit()
            
            for signal in signals:
                symbol = signal['symbol']
                action = signal['action']
                reason = signal['reason']
                
                self.logger.info(f"[{symbol}] {action} signal triggered: {reason}")
                
                if action == 'SELL':
                    # Get position information
                    positions = self.trading.get_all_positions()
                    position_quantity = 0
                    
                    for pos in positions:
                        if pos['symbol'].upper() == symbol.upper():
                            position_quantity = pos.get('quantity', 0)
                            break
                    
                    if position_quantity > 0:
                        # Execute sell
                        result = self.trading.sell_stock(
                            symbol=symbol,
                            quantity=position_quantity,
                            order_type='market',
                            time_in_force='day'
                        )
                        
                        if result.get('success'):
                            self.logger.info(f"[{symbol}] Auto sell successful: {position_quantity} shares")
                            
                            # Save trade record
                            self.strategy_manager._save_trade_record(
                                symbol=symbol,
                                trade_type='SELL',
                                quantity=position_quantity,
                                price=signal.get('current_price', 0),
                                amount=position_quantity * signal.get('current_price', 0),
                                order_id=result.get('order_id'),
                                strategy_name=signal.get('strategy_name', 'auto_stop_loss_take_profit'),
                                decision_reason=reason
                            )
                            
                            # Update position status
                            self.strategy_manager._update_position_status(symbol, 'sold')
                        else:
                            self.logger.error(f"[{symbol}] Auto sell failed: {result.get('error')}")
                
        except Exception as e:
            self.logger.error(f"Check stop loss/take profit failed: {e}")
    
    def _execute_strategy_tasks(self):
        """Execute active strategy tasks"""
        try:
            # Get all active AI decision tasks
            ai_tasks = self.strategy_manager.get_active_tasks('ai_decision')
            
            for task in ai_tasks:
                symbol = task['symbol']
                
                try:
                    # Use new version of AI strategy (with hard risk control)
                    result = self.strategy_manager.execute_ai_strategy_v2(
                        symbol=symbol,
                        auto_trade=True  # Enable auto trading
                    )
                    
                    if result.get('success'):
                        firewall_result = result.get('firewall_result', {})
                        final_action = firewall_result.get('final_action', 'HOLD')
                        
                        if final_action in ['BUY', 'SELL']:
                            execution_result = result.get('execution_result', {})
                            if execution_result and execution_result.get('success'):
                                self.logger.info(f"[{symbol}] AI strategy executed successfully: {final_action}")
                                self.logger.info(f"[{symbol}] Order ID: {execution_result.get('order_id')}")
                            else:
                                error_msg = execution_result.get('error', 'Unknown error') if execution_result else 'No execution result'
                                self.logger.warning(f"[{symbol}] AI strategy execution failed: {error_msg}")
                        else:
                            # Rejected by firewall
                            reject_reasons = firewall_result.get('reject_reasons', [])
                            if reject_reasons:
                                self.logger.info(f"[{symbol}] Trade rejected: {', '.join(reject_reasons)}")
                    
                except Exception as e:
                    self.logger.error(f"[{symbol}] Execute AI strategy task failed: {e}", exc_info=True)
                
                # Avoid requests too fast
                time.sleep(2)
                
        except Exception as e:
            self.logger.error(f"Execute strategy tasks failed: {e}", exc_info=True)


# Global auto trading service instance
_auto_trader = None

def get_auto_trader(trading_interface=None) -> AlpacaAutoTrader:
    """Get auto trading service instance"""
    global _auto_trader
    
    if _auto_trader is None:
        _auto_trader = AlpacaAutoTrader(trading_interface)
    elif trading_interface and _auto_trader.trading != trading_interface:
        _auto_trader.set_trading_interface(trading_interface)
    
    return _auto_trader

