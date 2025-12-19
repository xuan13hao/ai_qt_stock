"""
Alpaca Auto Trader
自动交易监控服务
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
    """Alpaca自动交易服务"""
    
    def __init__(self, trading_interface=None):
        """
        初始化自动交易服务
        
        Args:
            trading_interface: 交易接口
        """
        self.logger = logging.getLogger(__name__)
        self.trading = trading_interface
        self.strategy_manager = AlpacaStrategyManager(trading_interface)
        self.running = False
        self.thread = None
        self.check_interval = 300  # 5分钟检查一次（秒）
    
    def set_trading_interface(self, trading_interface):
        """设置交易接口"""
        self.trading = trading_interface
        self.strategy_manager.set_trading_interface(trading_interface)
    
    def start(self):
        """启动自动交易服务"""
        if self.running:
            self.logger.warning("自动交易服务已在运行")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.logger.info("自动交易服务已启动")
    
    def stop(self):
        """停止自动交易服务"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.logger.info("自动交易服务已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                # 1. 检查止损止盈
                self._check_stop_loss_take_profit()
                
                # 2. 执行活跃的策略任务
                self._execute_strategy_tasks()
                
                # 等待下次检查
                time.sleep(self.check_interval)
                
            except Exception as e:
                self.logger.error(f"监控循环错误: {e}")
                time.sleep(60)  # 错误后等待1分钟再重试
    
    def _check_stop_loss_take_profit(self):
        """检查止损止盈"""
        try:
            signals = self.strategy_manager.check_stop_loss_take_profit()
            
            for signal in signals:
                symbol = signal['symbol']
                action = signal['action']
                reason = signal['reason']
                
                self.logger.info(f"[{symbol}] 触发{action}信号: {reason}")
                
                if action == 'SELL':
                    # 获取持仓信息
                    positions = self.trading.get_all_positions()
                    position_quantity = 0
                    
                    for pos in positions:
                        if pos['symbol'].upper() == symbol.upper():
                            position_quantity = pos.get('quantity', 0)
                            break
                    
                    if position_quantity > 0:
                        # 执行卖出
                        result = self.trading.sell_stock(
                            symbol=symbol,
                            quantity=position_quantity,
                            order_type='market',
                            time_in_force='day'
                        )
                        
                        if result.get('success'):
                            self.logger.info(f"[{symbol}] 自动卖出成功: {position_quantity}股")
                            
                            # 保存交易记录
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
                            
                            # 更新持仓状态
                            self.strategy_manager._update_position_status(symbol, 'sold')
                        else:
                            self.logger.error(f"[{symbol}] 自动卖出失败: {result.get('error')}")
                
        except Exception as e:
            self.logger.error(f"检查止损止盈失败: {e}")
    
    def _execute_strategy_tasks(self):
        """执行活跃的策略任务"""
        try:
            # 获取所有活跃的AI决策任务
            ai_tasks = self.strategy_manager.get_active_tasks('ai_decision')
            
            for task in ai_tasks:
                symbol = task['symbol']
                
                try:
                    # 执行AI策略（自动交易）
                    result = self.strategy_manager.execute_ai_strategy(
                        symbol=symbol,
                        auto_trade=True  # 启用自动交易
                    )
                    
                    if result.get('success'):
                        decision = result.get('decision', {})
                        action = decision.get('action')
                        
                        if action in ['BUY', 'SELL']:
                            execution_result = result.get('execution_result', {})
                            if execution_result.get('success'):
                                self.logger.info(f"[{symbol}] AI策略执行成功: {action}")
                            else:
                                self.logger.warning(f"[{symbol}] AI策略执行失败: {execution_result.get('error')}")
                    
                except Exception as e:
                    self.logger.error(f"[{symbol}] 执行AI策略任务失败: {e}")
                
                # 避免请求过快
                time.sleep(2)
                
        except Exception as e:
            self.logger.error(f"执行策略任务失败: {e}")


# 全局自动交易服务实例
_auto_trader = None

def get_auto_trader(trading_interface=None) -> AlpacaAutoTrader:
    """获取自动交易服务实例"""
    global _auto_trader
    
    if _auto_trader is None:
        _auto_trader = AlpacaAutoTrader(trading_interface)
    elif trading_interface and _auto_trader.trading != trading_interface:
        _auto_trader.set_trading_interface(trading_interface)
    
    return _auto_trader

