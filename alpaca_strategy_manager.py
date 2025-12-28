"""
Alpaca Trading Strategy Manager
Integrate all trading logic into Alpaca trading system
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import sqlite3
import pandas as pd
from us_stock_trading import USStockTradingInterface, USStockTradingSimulator
from alpaca_ai_decision import AlpacaAIDecision
from config_manager import config_manager
from indicator_snapshot import IndicatorSnapshot
from hard_decision_firewall import HardDecisionFirewall, LLMProposal, FirewallResult
from trade_state_machine import TradeStateMachine
from audit_logger import AuditLogger


class AlpacaStrategyManager:
    """Alpaca Trading Strategy Manager"""
    
    def __init__(self, trading_interface=None):
        """
        Initialize strategy manager
        
        Args:
            trading_interface: Trading interface (USStockTradingInterface or USStockTradingSimulator)
        """
        self.logger = logging.getLogger(__name__)
        self.trading = trading_interface
        self.db_path = "alpaca_strategies.db"
        self._init_database()
        
        # Initialize AI decision engine (if DeepSeek is configured)
        config = config_manager.read_env()
        deepseek_api_key = config.get('DEEPSEEK_API_KEY', '')
        self.ai_engine = None
        if deepseek_api_key:
            try:
                self.ai_engine = AlpacaAIDecision(
                    api_key=deepseek_api_key,
                    base_url=config.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
                )
                self.logger.info("AI decision engine initialized")
            except Exception as e:
                self.logger.warning(f"AI decision engine initialization failed: {e}")
        
        # Initialize hard risk control firewall
        firewall_config = {
            'enable_extended_hours': config.get('ENABLE_EXTENDED_HOURS', 'false').lower() == 'true',
            'max_spread': float(config.get('MAX_SPREAD', '0.5')),
            'min_liquidity_score': float(config.get('MIN_LIQUIDITY_SCORE', '50.0')),
            'min_buy_rule_count': int(config.get('MIN_BUY_RULE_COUNT', '3')),
            'max_position_size_pct': int(config.get('MAX_POSITION_SIZE_PCT', '40')),
            'max_position_size_pct_extended': int(config.get('MAX_POSITION_SIZE_PCT_EXTENDED', '20')),
            'min_confidence_buy': int(config.get('MIN_CONFIDENCE_BUY', '65')),
            'stop_loss_min': float(config.get('STOP_LOSS_MIN', '3.0')),
            'stop_loss_max': float(config.get('STOP_LOSS_MAX', '5.0')),
            'take_profit_min': float(config.get('TAKE_PROFIT_MIN', '5.0')),
            'take_profit_max': float(config.get('TAKE_PROFIT_MAX', '15.0')),
            'day_circuit_breaker_pct': float(config.get('DAY_CIRCUIT_BREAKER_PCT', '-2.0')),
            'cooldown_minutes': int(config.get('COOLDOWN_MINUTES', '30')),
            'min_trade_interval_minutes': int(config.get('MIN_TRADE_INTERVAL_MINUTES', '5')),
            'hard_stop_loss_pct': float(config.get('HARD_STOP_LOSS_PCT', '-5.0'))
        }
        self.firewall = HardDecisionFirewall(firewall_config)
        
        # Initialize state machine
        self.state_machine = TradeStateMachine(
            cooldown_minutes=firewall_config['cooldown_minutes']
        )
        
        # Initialize audit logger
        self.audit_logger = AuditLogger()
        
        # Risk state (obtained from database or memory)
        self.risk_state = {
            'day_pnl_pct': 0.0,
            'consecutive_losses': 0,
            'last_trade_time_by_symbol': {}
        }
    
    def _init_database(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Strategy tasks table
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
        
        # Monitored positions table
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
        
        # Trade records table
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
        
        # Trading signals table
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
        self.logger.info("Strategy database initialized")
    
    def set_trading_interface(self, trading_interface):
        """Set trading interface"""
        self.trading = trading_interface
    
    # ==================== Strategy Task Management ====================
    
    def add_strategy_task(self, strategy_name: str, symbol: str, config: Dict = None) -> Tuple[bool, str]:
        """
        Add strategy task
        
        Args:
            strategy_name: Strategy name (e.g., ai_decision, low_price_bull, etc.)
            symbol: Stock symbol
            config: Strategy configuration
            
        Returns:
            (success, message)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if already exists
            cursor.execute("""
                SELECT id FROM strategy_tasks 
                WHERE strategy_name = ? AND symbol = ? AND status = 'active'
            """, (strategy_name, symbol))
            
            if cursor.fetchone():
                conn.close()
                return False, f"Strategy task already exists: {strategy_name} - {symbol}"
            
            import json
            config_json = json.dumps(config) if config else '{}'
            
            cursor.execute("""
                INSERT INTO strategy_tasks 
                (strategy_name, symbol, status, config, created_at)
                VALUES (?, ?, 'active', ?, ?)
            """, (strategy_name, symbol, config_json, datetime.now().isoformat()))
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Added strategy task: {strategy_name} - {symbol}")
            return True, "Strategy task added successfully"
            
        except Exception as e:
            self.logger.error(f"Failed to add strategy task: {e}")
            return False, str(e)
    
    def remove_strategy_task(self, strategy_name: str, symbol: str) -> Tuple[bool, str]:
        """Remove strategy task"""
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
            
            return True, "Strategy task removed successfully"
            
        except Exception as e:
            return False, str(e)
    
    def get_active_tasks(self, strategy_name: str = None) -> List[Dict]:
        """Get active strategy tasks"""
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
            self.logger.error(f"Failed to get strategy tasks: {e}")
            return []
    
    # ==================== AI Decision Strategy ====================
    
    def execute_ai_strategy_v2(self, symbol: str, auto_trade: bool = False) -> Dict:
        """
        Execute AI decision strategy (new version, with hard risk control)
        
        Args:
            symbol: Stock symbol
            auto_trade: Whether to automatically execute trades
            
        Returns:
            Strategy execution result
        """
        if not self.ai_engine:
            return {
                'success': False,
                'error': 'AI decision engine not initialized, please configure DeepSeek API Key'
            }
        
        if not self.trading:
            return {
                'success': False,
                'error': 'Trading interface not set'
            }
        
        try:
            # 1. Get account information
            account_info = self.trading.get_account_info()
            if not account_info.get('success'):
                return {
                    'success': False,
                    'error': f"Failed to get account information: {account_info.get('error')}"
                }
            
            # 2. Get positions
            positions = self.trading.get_all_positions()
            
            # 3. Get market data and create snapshot
            market_data_result = self.ai_engine.get_market_data(symbol)
            if not market_data_result:
                return {
                    'success': False,
                    'error': 'Failed to get market data'
                }
            
            snapshot = IndicatorSnapshot.from_market_data(
                symbol=symbol,
                market_data=market_data_result,
                account_info=account_info,
                positions=positions,
                risk_state=self.risk_state
            )
            
            # 4. Call LLM to get decision recommendation
            llm_result = self.ai_engine.analyze_and_decide_v2(snapshot)
            if not llm_result.get('success'):
                return {
                    'success': False,
                    'error': llm_result.get('error', 'LLM decision failed'),
                    'snapshot': snapshot.to_dict()
                }
            
            proposal = llm_result['proposal']
            llm_output_raw = llm_result.get('raw_output', '')
            
            # 5. Validate through firewall
            firewall_result = self.firewall.check(proposal, snapshot, self.risk_state)
            
            # 6. State machine check
            final_action = firewall_result.final_action
            can_execute = False
            
            if final_action == "BUY":
                can_execute = self.state_machine.can_open_position(symbol)
                if not can_execute:
                    firewall_result.allowed = False
                    firewall_result.final_action = "HOLD"
                    firewall_result.reject_reasons.append("State machine does not allow opening position")
                    firewall_result.reason_codes.append("STATE_MACHINE_BLOCK")
            elif final_action == "SELL":
                can_execute = self.state_machine.can_close_position(symbol) or snapshot.has_position
                if not can_execute:
                    firewall_result.allowed = False
                    firewall_result.final_action = "HOLD"
                    firewall_result.reject_reasons.append("State machine does not allow closing position")
                    firewall_result.reason_codes.append("STATE_MACHINE_BLOCK")
            
            # 7. Record audit log
            order_request = None
            order_fill = None
            
            if firewall_result.allowed and auto_trade:
                # Prepare order request
                order_request = {
                    'action': final_action,
                    'params': firewall_result.final_params,
                    'symbol': symbol
                }
            
            entry_id = self.audit_logger.log_decision(
                symbol=symbol,
                snapshot=snapshot,
                llm_prompt_version="v2",
                llm_output_raw=llm_output_raw,
                parsed_proposal=proposal,
                firewall_result=firewall_result,
                order_request=order_request,
                order_fill=order_fill
            )
            
            # 8. Execute trade (if allowed)
            execution_result = None
            if firewall_result.allowed and auto_trade and can_execute:
                execution_result = self._execute_firewall_decision(
                    symbol=symbol,
                    firewall_result=firewall_result,
                    snapshot=snapshot,
                    market_data=market_data_result
                )
                
                # Update state machine
                self.state_machine.transition(
                    symbol=symbol,
                    action=final_action,
                    has_position=snapshot.has_position
                )
                
                # Update risk state
                if execution_result.get('success'):
                    self._update_risk_state(symbol, final_action, execution_result)
                
                # Update order fill information in audit log
                if execution_result.get('success'):
                    order_fill = {
                        'order_id': execution_result.get('order_id'),
                        'quantity': execution_result.get('quantity'),
                        'price': execution_result.get('filled_avg_price'),
                        'status': execution_result.get('status', 'filled')
                    }
                    # Can update audit log here, but for simplicity, we only record once
            
            # 9. Save trading signal (compatible with old system)
            self._save_trading_signal(
                symbol=symbol,
                signal_type='ai_decision_v2',
                action=firewall_result.final_action,
                reason=proposal.notes,
                confidence=firewall_result.normalized_confidence,
                market_data=market_data_result,
                decision_data={
                    'proposal': {
                        'proposed_action': proposal.proposed_action,
                        'confidence': proposal.confidence,
                        'evidence': proposal.evidence,
                        'params': proposal.params,
                        'risk_level': proposal.risk_level,
                        'warnings': proposal.warnings,
                        'counter_evidence': proposal.counter_evidence
                    },
                    'firewall_result': {
                        'allowed': firewall_result.allowed,
                        'final_action': firewall_result.final_action,
                        'reject_reasons': firewall_result.reject_reasons,
                        'reason_codes': firewall_result.reason_codes,
                        'normalized_confidence': firewall_result.normalized_confidence,
                        'modifications': firewall_result.modifications
                    }
                }
            )
            
            return {
                'success': True,
                'proposal': {
                    'proposed_action': proposal.proposed_action,
                    'confidence': proposal.confidence,
                    'evidence': proposal.evidence,
                    'params': proposal.params,
                    'risk_level': proposal.risk_level,
                    'warnings': proposal.warnings,
                    'counter_evidence': proposal.counter_evidence,
                    'notes': proposal.notes
                },
                'firewall_result': {
                    'allowed': firewall_result.allowed,
                    'final_action': firewall_result.final_action,
                    'final_params': firewall_result.final_params,
                    'reject_reasons': firewall_result.reject_reasons,
                    'reason_codes': firewall_result.reason_codes,
                    'normalized_confidence': firewall_result.normalized_confidence,
                    'modifications': firewall_result.modifications
                },
                'snapshot': snapshot.to_dict(),
                'execution_result': execution_result,
                'audit_entry_id': entry_id
            }
            
        except Exception as e:
            self.logger.error(f"Failed to execute AI strategy v2: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
    
    def execute_ai_strategy(self, symbol: str, auto_trade: bool = False) -> Dict:
        """
        Execute AI decision strategy
        
        Args:
            symbol: Stock symbol
            auto_trade: Whether to automatically execute trades
            
        Returns:
            Strategy execution result
        """
        if not self.ai_engine:
            return {
                'success': False,
                'error': 'AI decision engine not initialized, please configure DeepSeek API Key'
            }
        
        if not self.trading:
            return {
                'success': False,
                'error': 'Trading interface not set'
            }
        
        try:
            # Get account information
            account_info = self.trading.get_account_info()
            if not account_info.get('success'):
                return {
                    'success': False,
                    'error': f"Failed to get account information: {account_info.get('error')}"
                }
            
            # Check positions
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
            
            # Get AI decision
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
            
            # Save trading signal
            self._save_trading_signal(
                symbol=symbol,
                signal_type='ai_decision',
                action=decision.get('action'),
                reason=decision.get('reasoning'),
                confidence=decision.get('confidence'),
                market_data=market_data,
                decision_data=decision
            )
            
            # If auto trading is enabled, execute trade
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
            self.logger.error(f"Failed to execute AI strategy: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_firewall_decision(self, symbol: str, firewall_result: FirewallResult,
                                   snapshot: IndicatorSnapshot, market_data: Dict) -> Dict:
        """Execute firewall-approved decision"""
        action = firewall_result.final_action
        params = firewall_result.final_params
        
        try:
            if action == 'BUY' and not snapshot.has_position:
                # Build decision dictionary (compatible with old interface)
                decision = {
                    'action': 'BUY',
                    'position_size_pct': params.get('position_size_pct', 20),
                    'stop_loss_pct': params.get('stop_loss_pct', 5.0),
                    'take_profit_pct': params.get('take_profit_pct', 10.0),
                    'reasoning': f"Firewall approved: {firewall_result.normalized_confidence}% confidence"
                }
                return self._execute_buy(symbol, decision, market_data, 'ai_decision_v2')
            
            elif action == 'SELL' and snapshot.has_position:
                decision = {
                    'action': 'SELL',
                    'reasoning': f"Firewall approved: {firewall_result.normalized_confidence}% confidence"
                }
                return self._execute_sell(symbol, decision, market_data, snapshot.position_quantity, 'ai_decision_v2')
            
            else:
                return {
                    'success': False,
                    'error': f'Invalid action or state: {action}, has_position={snapshot.has_position}'
                }
                
        except Exception as e:
            self.logger.error(f"Failed to execute firewall decision: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _execute_ai_decision(self, symbol: str, decision: Dict, market_data: Dict,
                             has_position: bool, position_cost: float, 
                             position_quantity: int) -> Dict:
        """Execute AI decision (old version, kept for compatibility)"""
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
                    'message': 'AI recommends holding, no trade executed'
                }
            
            else:
                return {
                    'success': False,
                    'error': f'Invalid action: {action}'
                }
                
        except Exception as e:
            self.logger.error(f"Failed to execute AI decision: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _update_risk_state(self, symbol: str, action: str, execution_result: Dict):
        """Update risk state"""
        now = datetime.now()
        
        # Update last trade time
        if symbol not in self.risk_state['last_trade_time_by_symbol']:
            self.risk_state['last_trade_time_by_symbol'] = {}
        self.risk_state['last_trade_time_by_symbol'][symbol] = now.isoformat()
        
        # Update consecutive losses (simplified implementation)
        if action == 'SELL' and execution_result.get('success'):
            # Should calculate from actual P&L, simplified handling
            pass
    
    # ==================== Buy Logic ====================
    
    def _execute_buy(self, symbol: str, decision: Dict, market_data: Dict,
                    strategy_name: str = 'manual') -> Dict:
        """Execute buy"""
        try:
            if not self.trading:
                return {'success': False, 'error': 'Trading interface not set'}
            
            # Get account information
            account_info = self.trading.get_account_info()
            if not account_info.get('success'):
                return {'success': False, 'error': 'Failed to get account information'}
            
            # Calculate buy amount
            buying_power = account_info.get('buying_power', account_info.get('cash', 0))
            position_size_pct = decision.get('position_size_pct', 20)
            buy_amount = buying_power * (position_size_pct / 100)
            
            # Calculate quantity
            current_price = market_data.get('current_price', 0)
            if current_price <= 0:
                return {'success': False, 'error': 'Invalid price'}
            
            quantity = int(buy_amount / current_price)
            if quantity < 1:
                return {'success': False, 'error': f'Insufficient funds, need at least ${current_price:.2f}'}
            
            # Execute buy
            result = self.trading.buy_stock(
                symbol=symbol,
                quantity=quantity,
                order_type='market',
                time_in_force='day'
            )
            
            if result.get('success'):
                # Save trade record
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
                
                # Save monitored position
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
                
                self.logger.info(f"[{symbol}] Buy successful: {quantity} shares @ ${current_price:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"[{symbol}] Buy failed: {e}")
            return {'success': False, 'error': str(e)}
    
    # ==================== Sell Logic ====================
    
    def _execute_sell(self, symbol: str, decision: Dict, market_data: Dict,
                     position_quantity: int, strategy_name: str = 'manual') -> Dict:
        """Execute sell"""
        try:
            if not self.trading:
                return {'success': False, 'error': 'Trading interface not set'}
            
            # Execute sell (sell all positions)
            result = self.trading.sell_stock(
                symbol=symbol,
                quantity=position_quantity,
                order_type='market',
                time_in_force='day'
            )
            
            if result.get('success'):
                current_price = market_data.get('current_price', 0)
                
                # Save trade record
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
                
                # Update position status
                self._update_position_status(symbol, 'sold')
                
                self.logger.info(f"[{symbol}] Sell successful: {position_quantity} shares @ ${current_price:.2f}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"[{symbol}] Sell failed: {e}")
            return {'success': False, 'error': str(e)}
    
    # ==================== Position Monitoring ====================
    
    def _save_monitored_position(self, symbol: str, quantity: int, cost_price: float,
                                stop_loss_pct: float = 5.0, take_profit_pct: float = 10.0,
                                strategy_name: str = None):
        """Save monitored position"""
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
            self.logger.error(f"Failed to save monitored position: {e}")
    
    def get_monitored_positions(self) -> List[Dict]:
        """Get monitored positions"""
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
            self.logger.error(f"Failed to get monitored positions: {e}")
            return []
    
    def check_stop_loss_take_profit(self) -> List[Dict]:
        """
        Check stop loss/take profit
        
        Returns:
            List of trading signals that need to be executed
        """
        signals = []
        
        try:
            if not self.trading:
                return signals
            
            # Get all positions
            positions = self.trading.get_all_positions()
            monitored_positions = self.get_monitored_positions()
            
            # Create position dictionary
            position_dict = {pos['symbol'].upper(): pos for pos in positions}
            
            for mon_pos in monitored_positions:
                symbol = mon_pos['symbol'].upper()
                
                if symbol not in position_dict:
                    # Position no longer exists, update status
                    self._update_position_status(symbol, 'sold')
                    continue
                
                current_pos = position_dict[symbol]
                current_price = current_pos.get('current_price', current_pos.get('avg_entry_price', 0))
                cost_price = mon_pos['cost_price']
                
                # Calculate P&L
                profit_loss_pct = ((current_price - cost_price) / cost_price * 100) if cost_price > 0 else 0
                
                # Check stop loss
                stop_loss_pct = mon_pos.get('stop_loss_pct', 5.0)
                if profit_loss_pct <= -stop_loss_pct:
                    signals.append({
                        'symbol': symbol,
                        'action': 'SELL',
                        'reason': f'Stop loss triggered: loss {profit_loss_pct:.2f}% (threshold: -{stop_loss_pct}%)',
                        'current_price': current_price,
                        'cost_price': cost_price,
                        'profit_loss_pct': profit_loss_pct,
                        'strategy_name': mon_pos.get('strategy_name', 'stop_loss')
                    })
                
                # Check take profit
                take_profit_pct = mon_pos.get('take_profit_pct', 10.0)
                if profit_loss_pct >= take_profit_pct:
                    signals.append({
                        'symbol': symbol,
                        'action': 'SELL',
                        'reason': f'Take profit triggered: profit {profit_loss_pct:.2f}% (threshold: +{take_profit_pct}%)',
                        'current_price': current_price,
                        'cost_price': cost_price,
                        'profit_loss_pct': profit_loss_pct,
                        'strategy_name': mon_pos.get('strategy_name', 'take_profit')
                    })
            
            return signals
            
        except Exception as e:
            self.logger.error(f"Failed to check stop loss/take profit: {e}")
            return []
    
    def _update_position_status(self, symbol: str, status: str):
        """Update position status"""
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
            self.logger.error(f"Failed to update position status: {e}")
    
    # ==================== Trade Records ====================
    
    def _save_trade_record(self, symbol: str, trade_type: str, quantity: int,
                          price: float, amount: float, order_id: str = None,
                          strategy_name: str = None, decision_reason: str = None):
        """Save trade record"""
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
            self.logger.error(f"Failed to save trade record: {e}")
    
    def get_trade_records(self, symbol: str = None, limit: int = 100) -> List[Dict]:
        """Get trade records"""
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
            self.logger.error(f"Failed to get trade records: {e}")
            return []
    
    # ==================== Trading Signals ====================
    
    def _save_trading_signal(self, symbol: str, signal_type: str, action: str,
                            reason: str = None, confidence: float = None,
                            market_data: Dict = None, decision_data: Dict = None):
        """Save trading signal"""
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
            self.logger.error(f"Failed to save trading signal: {e}")
    
    def get_recent_signals(self, limit: int = 50) -> List[Dict]:
        """Get recent trading signals"""
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
            self.logger.error(f"Failed to get trading signals: {e}")
            return []

