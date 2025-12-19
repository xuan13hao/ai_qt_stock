"""
Alpaca Trading Strategy Manager
整合所有交易逻辑到Alpaca交易系统
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import sqlite3
import pandas as pd
from us_stock_trading import USStockTradingInterface, USStockTradingSimulator
from alpaca_ai_decision import AlpacaAIDecision
from config_manager import config_manager


class AlpacaStrategyManager:
    """Alpaca交易策略管理器"""
    
    def __init__(self, trading_interface=None):
        """
        初始化策略管理器
        
        Args:
            trading_interface: 交易接口（USStockTradingInterface或USStockTradingSimulator）
        """
        self.logger = logging.getLogger(__name__)
        self.trading = trading_interface
        self.db_path = "alpaca_strategies.db"
        self._init_database()
        
        # 初始化AI决策引擎（如果配置了DeepSeek）
        config = config_manager.read_env()
        deepseek_api_key = config.get('DEEPSEEK_API_KEY', '')
        self.ai_engine = None
        if deepseek_api_key:
            try:
                self.ai_engine = AlpacaAIDecision(
                    api_key=deepseek_api_key,
                    base_url=config.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
                )
                self.logger.info("AI决策引擎已初始化")
            except Exception as e:
                self.logger.warning(f"AI决策引擎初始化失败: {e}")
    
    def _init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 策略任务表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategy_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                config TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                UNIQUE(strategy_name, symbol, status)
            )
        """)
        
        # 持仓监控表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS monitored_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                cost_price REAL NOT NULL,
                buy_date TEXT NOT NULL,
                stop_loss_price REAL,
                take_profit_price REAL,
                stop_loss_pct REAL DEFAULT 5.0,
                take_profit_pct REAL DEFAULT 10.0,
                holding_days INTEGER DEFAULT 0,
                status TEXT DEFAULT 'holding',
                strategy_name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )
        """)
        
        # 交易记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                amount REAL NOT NULL,
                order_id TEXT,
                strategy_name TEXT,
                decision_reason TEXT,
                created_at TEXT NOT NULL
            )
        """)
        
        # 交易信号表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trading_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                action TEXT NOT NULL,
                reason TEXT,
                confidence REAL,
                market_data TEXT,
                decision_data TEXT,
                created_at TEXT NOT NULL,
                executed INTEGER DEFAULT 0
            )
        """)
        
        conn.commit()
        conn.close()
        self.logger.info("策略数据库初始化完成")
    
    def set_trading_interface(self, trading_interface):
        """设置交易接口"""
        self.trading = trading_interface
    
    # ==================== 策略任务管理 ====================
    
    def add_strategy_task(self, strategy_name: str, symbol: str, config: Dict = None) -> Tuple[bool, str]:
        """
        添加策略任务
        
        Args:
            strategy_name: 策略名称（如：ai_decision, low_price_bull, etc.）
            symbol: 股票代码
            config: 策略配置
            
        Returns:
            (是否成功, 消息)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 检查是否已存在
            cursor.execute("""
                SELECT id FROM strategy_tasks 
                WHERE strategy_name = ? AND symbol = ? AND status = 'active'
            """, (strategy_name, symbol))
            
            if cursor.fetchone():
                conn.close()
                return False, f"策略任务已存在: {strategy_name} - {symbol}"
            
            import json
            config_json = json.dumps(config) if config else '{}'
            
            cursor.execute("""
                INSERT INTO strategy_tasks 
                (strategy_name, symbol, status, config, created_at)
                VALUES (?, ?, 'active', ?, ?)
            """, (strategy_name, symbol, config_json, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"添加策略任务: {strategy_name} - {symbol}")
            return True, "策略任务添加成功"
            
        except Exception as e:
            self.logger.error(f"添加策略任务失败: {e}")
            return False, str(e)
    
    def remove_strategy_task(self, strategy_name: str, symbol: str) -> Tuple[bool, str]:
        """移除策略任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE strategy_tasks 
                SET status = 'inactive', updated_at = ?
                WHERE strategy_name = ? AND symbol = ? AND status = 'active'
            """, (datetime.now().isoformat(), strategy_name, symbol))
            
            conn.commit()
            conn.close()
            
            return True, "策略任务移除成功"
            
        except Exception as e:
            return False, str(e)
    
    def get_active_tasks(self, strategy_name: str = None) -> List[Dict]:
        """获取活跃的策略任务"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            if strategy_name:
                query = "SELECT * FROM strategy_tasks WHERE status = 'active' AND strategy_name = ?"
                df = pd.read_sql_query(query, conn, params=(strategy_name,))
            else:
                query = "SELECT * FROM strategy_tasks WHERE status = 'active'"
                df = pd.read_sql_query(query, conn)
            
            conn.close()
            return df.to_dict('records') if not df.empty else []
            
        except Exception as e:
            self.logger.error(f"获取策略任务失败: {e}")
            return []
    
    # ==================== AI决策策略 ====================
    
    def execute_ai_strategy(self, symbol: str, auto_trade: bool = False) -> Dict:
        """
        执行AI决策策略
        
        Args:
            symbol: 股票代码
            auto_trade: 是否自动执行交易
            
        Returns:
            策略执行结果
        """
        if not self.ai_engine:
            return {
                'success': False,
                'error': 'AI决策引擎未初始化，请配置DeepSeek API Key'
            }
        
        if not self.trading:
            return {
                'success': False,
                'error': '交易接口未设置'
            }
        
        try:
            # 获取账户信息
            account_info = self.trading.get_account_info()
            if not account_info.get('success'):
                return {
                    'success': False,
                    'error': f"获取账户信息失败: {account_info.get('error')}"
                }
            
            # 检查持仓
            positions = self.trading.get_all_positions()
            has_position = False
            position_cost = 0
            position_quantity = 0
            
            for pos in positions:
                if pos['symbol'].upper() == symbol.upper():
                    has_position = True
                    position_cost = pos.get('avg_entry_price', 0)
                    position_quantity = pos.get('quantity', 0)
                    break
            
            # 获取AI决策
            result = self.ai_engine.analyze_and_decide(
                symbol=symbol,
                account_info=account_info,
                has_position=has_position,
                position_cost=position_cost,
                position_quantity=position_quantity
            )
            
            if not result.get('success'):
                return result
            
            decision = result['decision']
            market_data = result.get('market_data', {})
            
            # 保存交易信号
            self._save_trading_signal(
                symbol=symbol,
                signal_type='ai_decision',
                action=decision.get('action'),
                reason=decision.get('reasoning'),
                confidence=decision.get('confidence'),
                market_data=market_data,
                decision_data=decision
            )
            
            # 如果启用自动交易，执行交易
            if auto_trade:
                execution_result = self._execute_ai_decision(
                    symbol=symbol,
                    decision=decision,
                    market_data=market_data,
                    has_position=has_position,
                    position_cost=position_cost,
                    position_quantity=position_quantity
                )
                
                result['execution_result'] = execution_result
            
            return result
            
        except Exception as e:
            self.logger.error(f"执行AI策略失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_ai_decision(self, symbol: str, decision: Dict, market_data: Dict,
                             has_position: bool, position_cost: float, 
                             position_quantity: int) -> Dict:
        """执行AI决策"""
        action = decision.get('action')
        
        try:
            if action == 'BUY' and not has_position:
                return self._execute_buy(symbol, decision, market_data, 'ai_decision')
            
            elif action == 'SELL' and has_position:
                return self._execute_sell(symbol, decision, market_data, position_quantity, 'ai_decision')
            
            elif action == 'HOLD':
                return {
                    'success': True,
                    'action': 'HOLD',
                    'message': 'AI建议持有，未执行交易'
                }
            
            else:
                return {
                    'success': False,
                    'error': f'无效操作: {action}'
                }
                
        except Exception as e:
            self.logger.error(f"执行AI决策失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    # ==================== 买入逻辑 ====================
    
    def _execute_buy(self, symbol: str, decision: Dict, market_data: Dict,
                    strategy_name: str = 'manual') -> Dict:
        """执行买入"""
        try:
            if not self.trading:
                return {'success': False, 'error': '交易接口未设置'}
            
            # 获取账户信息
            account_info = self.trading.get_account_info()
            if not account_info.get('success'):
                return {'success': False, 'error': '获取账户信息失败'}
            
            # 计算买入金额
            buying_power = account_info.get('buying_power', account_info.get('cash', 0))
            position_size_pct = decision.get('position_size_pct', 20)
            buy_amount = buying_power * (position_size_pct / 100)
            
            # 计算数量
            current_price = market_data.get('current_price', 0)
            if current_price <= 0:
                return {'success': False, 'error': '无效的价格'}
            
            quantity = int(buy_amount / current_price)
            if quantity < 1:
                return {'success': False, 'error': f'资金不足，至少需要${current_price:.2f}'}
            
            # 执行买入
            result = self.trading.buy_stock(
                symbol=symbol,
                quantity=quantity,
                order_type='market',
                time_in_force='day'
            )
            
            if result.get('success'):
                # 保存交易记录
                self._save_trade_record(
                    symbol=symbol,
                    trade_type='BUY',
                    quantity=quantity,
                    price=current_price,
                    amount=quantity * current_price,
                    order_id=result.get('order_id'),
                    strategy_name=strategy_name,
                    decision_reason=decision.get('reasoning', '')
                )
                
                # 保存持仓监控
                stop_loss_pct = decision.get('stop_loss_pct', 5.0)
                take_profit_pct = decision.get('take_profit_pct', 10.0)
                
                self._save_monitored_position(
                    symbol=symbol,
                    quantity=quantity,
                    cost_price=current_price,
                    stop_loss_pct=stop_loss_pct,
                    take_profit_pct=take_profit_pct,
                    strategy_name=strategy_name
                )
                
                self.logger.info(f"[{symbol}] 买入成功: {quantity}股 @ ${current_price:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"[{symbol}] 买入失败: {e}")
            return {'success': False, 'error': str(e)}
    
    # ==================== 卖出逻辑 ====================
    
    def _execute_sell(self, symbol: str, decision: Dict, market_data: Dict,
                     position_quantity: int, strategy_name: str = 'manual') -> Dict:
        """执行卖出"""
        try:
            if not self.trading:
                return {'success': False, 'error': '交易接口未设置'}
            
            # 执行卖出（全部卖出）
            result = self.trading.sell_stock(
                symbol=symbol,
                quantity=position_quantity,
                order_type='market',
                time_in_force='day'
            )
            
            if result.get('success'):
                current_price = market_data.get('current_price', 0)
                
                # 保存交易记录
                self._save_trade_record(
                    symbol=symbol,
                    trade_type='SELL',
                    quantity=position_quantity,
                    price=current_price,
                    amount=position_quantity * current_price,
                    order_id=result.get('order_id'),
                    strategy_name=strategy_name,
                    decision_reason=decision.get('reasoning', '')
                )
                
                # 更新持仓状态
                self._update_position_status(symbol, 'sold')
                
                self.logger.info(f"[{symbol}] 卖出成功: {position_quantity}股 @ ${current_price:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"[{symbol}] 卖出失败: {e}")
            return {'success': False, 'error': str(e)}
    
    # ==================== 持仓监控 ====================
    
    def _save_monitored_position(self, symbol: str, quantity: int, cost_price: float,
                                stop_loss_pct: float = 5.0, take_profit_pct: float = 10.0,
                                strategy_name: str = None):
        """保存持仓监控"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            stop_loss_price = cost_price * (1 - stop_loss_pct / 100)
            take_profit_price = cost_price * (1 + take_profit_pct / 100)
            
            cursor.execute("""
                INSERT INTO monitored_positions 
                (symbol, quantity, cost_price, buy_date, stop_loss_price, take_profit_price,
                 stop_loss_pct, take_profit_pct, strategy_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, quantity, cost_price, datetime.now().strftime('%Y-%m-%d'),
                  stop_loss_price, take_profit_price, stop_loss_pct, take_profit_pct,
                  strategy_name, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"保存持仓监控失败: {e}")
    
    def get_monitored_positions(self) -> List[Dict]:
        """获取监控的持仓"""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("""
                SELECT * FROM monitored_positions 
                WHERE status = 'holding'
                ORDER BY created_at DESC
            """, conn)
            conn.close()
            return df.to_dict('records') if not df.empty else []
        except Exception as e:
            self.logger.error(f"获取监控持仓失败: {e}")
            return []
    
    def check_stop_loss_take_profit(self) -> List[Dict]:
        """
        检查止损止盈
        
        Returns:
            需要执行的交易信号列表
        """
        signals = []
        
        try:
            if not self.trading:
                return signals
            
            # 获取所有持仓
            positions = self.trading.get_all_positions()
            monitored_positions = self.get_monitored_positions()
            
            # 创建持仓字典
            position_dict = {pos['symbol'].upper(): pos for pos in positions}
            
            for mon_pos in monitored_positions:
                symbol = mon_pos['symbol'].upper()
                
                if symbol not in position_dict:
                    # 持仓已不存在，更新状态
                    self._update_position_status(symbol, 'sold')
                    continue
                
                current_pos = position_dict[symbol]
                current_price = current_pos.get('current_price', current_pos.get('avg_entry_price', 0))
                cost_price = mon_pos['cost_price']
                
                # 计算盈亏
                profit_loss_pct = ((current_price - cost_price) / cost_price * 100) if cost_price > 0 else 0
                
                # 检查止损
                stop_loss_pct = mon_pos.get('stop_loss_pct', 5.0)
                if profit_loss_pct <= -stop_loss_pct:
                    signals.append({
                        'symbol': symbol,
                        'action': 'SELL',
                        'reason': f'止损触发: 亏损{profit_loss_pct:.2f}% (阈值: -{stop_loss_pct}%)',
                        'current_price': current_price,
                        'cost_price': cost_price,
                        'profit_loss_pct': profit_loss_pct,
                        'strategy_name': mon_pos.get('strategy_name', 'stop_loss')
                    })
                
                # 检查止盈
                take_profit_pct = mon_pos.get('take_profit_pct', 10.0)
                if profit_loss_pct >= take_profit_pct:
                    signals.append({
                        'symbol': symbol,
                        'action': 'SELL',
                        'reason': f'止盈触发: 盈利{profit_loss_pct:.2f}% (阈值: +{take_profit_pct}%)',
                        'current_price': current_price,
                        'cost_price': cost_price,
                        'profit_loss_pct': profit_loss_pct,
                        'strategy_name': mon_pos.get('strategy_name', 'take_profit')
                    })
            
            return signals
            
        except Exception as e:
            self.logger.error(f"检查止损止盈失败: {e}")
            return []
    
    def _update_position_status(self, symbol: str, status: str):
        """更新持仓状态"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE monitored_positions 
                SET status = ?, updated_at = ?
                WHERE symbol = ? AND status = 'holding'
            """, (status, datetime.now().isoformat(), symbol))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"更新持仓状态失败: {e}")
    
    # ==================== 交易记录 ====================
    
    def _save_trade_record(self, symbol: str, trade_type: str, quantity: int,
                          price: float, amount: float, order_id: str = None,
                          strategy_name: str = None, decision_reason: str = None):
        """保存交易记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO trade_records 
                (symbol, trade_type, quantity, price, amount, order_id, 
                 strategy_name, decision_reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, trade_type, quantity, price, amount, order_id,
                  strategy_name, decision_reason, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"保存交易记录失败: {e}")
    
    def get_trade_records(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """获取交易记录"""
        try:
            conn = sqlite3.connect(self.db_path)
            
            if symbol:
                query = """
                    SELECT * FROM trade_records 
                    WHERE symbol = ? 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """
                df = pd.read_sql_query(query, conn, params=(symbol, limit))
            else:
                query = """
                    SELECT * FROM trade_records 
                    ORDER BY created_at DESC 
                    LIMIT ?
                """
                df = pd.read_sql_query(query, conn, params=(limit,))
            
            conn.close()
            return df.to_dict('records') if not df.empty else []
            
        except Exception as e:
            self.logger.error(f"获取交易记录失败: {e}")
            return []
    
    # ==================== 交易信号 ====================
    
    def _save_trading_signal(self, symbol: str, signal_type: str, action: str,
                            reason: str = None, confidence: float = None,
                            market_data: Dict = None, decision_data: Dict = None):
        """保存交易信号"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            import json
            market_data_json = json.dumps(market_data) if market_data else None
            decision_data_json = json.dumps(decision_data) if decision_data else None
            
            cursor.execute("""
                INSERT INTO trading_signals 
                (symbol, signal_type, action, reason, confidence, market_data, 
                 decision_data, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, signal_type, action, reason, confidence,
                  market_data_json, decision_data_json, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"保存交易信号失败: {e}")
    
    def get_recent_signals(self, limit: int = 50) -> List[Dict]:
        """获取最近的交易信号"""
        try:
            conn = sqlite3.connect(self.db_path)
            df = pd.read_sql_query("""
                SELECT * FROM trading_signals 
                ORDER BY created_at DESC 
                LIMIT ?
            """, conn, params=(limit,))
            conn.close()
            return df.to_dict('records') if not df.empty else []
        except Exception as e:
            self.logger.error(f"获取交易信号失败: {e}")
            return []

