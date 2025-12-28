"""
Trade State Machine Module
交易状态机，管理交易状态转换
"""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field


class TradeState(Enum):
    """交易状态"""
    WAIT = "WAIT"  # 等待信号
    CANDIDATE = "CANDIDATE"  # 候选（有信号但未开仓）
    ENTERED = "ENTERED"  # 已开仓
    MANAGING = "MANAGING"  # 持仓管理中
    EXITED = "EXITED"  # 已平仓
    COOLDOWN = "COOLDOWN"  # 冷却期（卖出后）


@dataclass
class SymbolState:
    """单个标的的状态"""
    symbol: str
    state: TradeState
    entered_at: Optional[datetime] = None
    exited_at: Optional[datetime] = None
    last_action: Optional[str] = None  # "BUY" | "SELL" | "HOLD"
    last_action_time: Optional[datetime] = None
    consecutive_holds: int = 0  # 连续 HOLD 次数


class TradeStateMachine:
    """交易状态机"""
    
    def __init__(self, cooldown_minutes: int = 30):
        """
        初始化状态机
        
        Args:
            cooldown_minutes: 冷却期时长（分钟）
        """
        self.logger = logging.getLogger(__name__)
        self.cooldown_minutes = cooldown_minutes
        self.states: Dict[str, SymbolState] = {}  # {symbol: SymbolState}
    
    def get_state(self, symbol: str) -> TradeState:
        """获取标的的当前状态"""
        if symbol not in self.states:
            return TradeState.WAIT
        return self.states[symbol].state
    
    def can_open_position(self, symbol: str) -> bool:
        """检查是否可以开仓"""
        state = self.get_state(symbol)
        return state in [TradeState.WAIT, TradeState.CANDIDATE]
    
    def can_close_position(self, symbol: str) -> bool:
        """检查是否可以平仓"""
        state = self.get_state(symbol)
        return state in [TradeState.ENTERED, TradeState.MANAGING]
    
    def transition(self, symbol: str, action: str, has_position: bool) -> TradeState:
        """
        状态转换
        
        Args:
            symbol: 股票代码
            action: 动作 "BUY" | "SELL" | "HOLD"
            has_position: 是否有持仓
            
        Returns:
            新状态
        """
        if symbol not in self.states:
            self.states[symbol] = SymbolState(symbol=symbol, state=TradeState.WAIT)
        
        state_obj = self.states[symbol]
        current_state = state_obj.state
        now = datetime.now()
        
        # 状态转换逻辑
        if action == "BUY":
            if current_state in [TradeState.WAIT, TradeState.CANDIDATE]:
                if has_position:
                    state_obj.state = TradeState.ENTERED
                    state_obj.entered_at = now
                else:
                    # 没有持仓但建议买入，进入候选状态
                    state_obj.state = TradeState.CANDIDATE
            elif current_state == TradeState.COOLDOWN:
                # 检查冷却期是否结束
                if state_obj.exited_at:
                    time_since_exit = now - state_obj.exited_at
                    if time_since_exit >= timedelta(minutes=self.cooldown_minutes):
                        state_obj.state = TradeState.CANDIDATE
                    else:
                        # 仍在冷却期，保持 COOLDOWN
                        pass
            # 其他状态不允许买入
        
        elif action == "SELL":
            if current_state in [TradeState.ENTERED, TradeState.MANAGING]:
                state_obj.state = TradeState.EXITED
                state_obj.exited_at = now
                # 进入冷却期
                state_obj.state = TradeState.COOLDOWN
            # 其他状态不允许卖出
        
        elif action == "HOLD":
            if current_state == TradeState.ENTERED:
                state_obj.state = TradeState.MANAGING
            elif current_state == TradeState.CANDIDATE:
                # 连续 HOLD，可能回到 WAIT
                state_obj.consecutive_holds += 1
                if state_obj.consecutive_holds >= 3:
                    state_obj.state = TradeState.WAIT
                    state_obj.consecutive_holds = 0
            elif current_state == TradeState.COOLDOWN:
                # 检查冷却期是否结束
                if state_obj.exited_at:
                    time_since_exit = now - state_obj.exited_at
                    if time_since_exit >= timedelta(minutes=self.cooldown_minutes):
                        state_obj.state = TradeState.WAIT
            else:
                state_obj.consecutive_holds += 1
        
        # 更新最后动作
        state_obj.last_action = action
        state_obj.last_action_time = now
        
        return state_obj.state
    
    def force_state(self, symbol: str, state: TradeState):
        """强制设置状态（用于异常情况）"""
        if symbol not in self.states:
            self.states[symbol] = SymbolState(symbol=symbol, state=state)
        else:
            self.states[symbol].state = state
    
    def reset(self, symbol: str):
        """重置状态"""
        if symbol in self.states:
            self.states[symbol] = SymbolState(symbol=symbol, state=TradeState.WAIT)
    
    def get_state_info(self, symbol: str) -> Optional[SymbolState]:
        """获取状态信息"""
        return self.states.get(symbol)
    
    def cleanup_old_states(self, max_age_hours: int = 24):
        """清理旧状态（超过指定时间未交易）"""
        now = datetime.now()
        to_remove = []
        
        for symbol, state_obj in self.states.items():
            if state_obj.last_action_time:
                age = now - state_obj.last_action_time
                if age > timedelta(hours=max_age_hours):
                    # 如果不在持仓状态，可以清理
                    if state_obj.state not in [TradeState.ENTERED, TradeState.MANAGING]:
                        to_remove.append(symbol)
        
        for symbol in to_remove:
            del self.states[symbol]
            self.logger.debug(f"清理旧状态: {symbol}")

