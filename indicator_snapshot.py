"""
Indicator Snapshot Module
只读结构体，包含所有技术指标和计算好的布尔条件
"""

from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime
import pytz
import hashlib
import json


@dataclass(frozen=True)
class IndicatorSnapshot:
    """
    只读指标快照，包含所有技术指标和预计算的布尔条件
    所有字段都是不可变的，确保数据一致性
    """
    
    # ==================== 基础信息 ====================
    symbol: str
    timestamp_utc: datetime
    timestamp_et: datetime
    
    # ==================== 价格数据 ====================
    price: float
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    # ==================== 移动平均线 ====================
    ma5: Optional[float] = None
    ma20: Optional[float] = None
    ma60: Optional[float] = None
    
    # ==================== MACD ====================
    macd: Optional[float] = None  # MACD 线
    macd_dif: Optional[float] = None  # DIF (等同于 macd)
    macd_dea: Optional[float] = None  # DEA (等同于 macd_signal)
    macd_hist: Optional[float] = None  # Histogram (DIF - DEA)
    macd_cross: Optional[str] = None  # 'golden' | 'death' | 'none'
    
    # ==================== RSI ====================
    rsi: Optional[float] = None
    
    # ==================== 布林带 ====================
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_position: Optional[str] = None  # 'upper' | 'middle' | 'lower'
    
    # ==================== 成交量 ====================
    avg_volume_5d: Optional[float] = None
    volume_ratio: Optional[float] = None  # volume / avg_volume_5d
    
    # ==================== 流动性指标 ====================
    spread: Optional[float] = None  # bid-ask spread (百分比)
    liquidity_score: Optional[float] = None  # 0-100, 越高流动性越好
    
    # ==================== 交易时段 ====================
    session: str = 'regular'  # 'regular' | 'premarket' | 'afterhours' | 'closed'
    
    # ==================== 支撑阻力 ====================
    support: Optional[float] = None
    resistance: Optional[float] = None
    
    # ==================== 账户信息 ====================
    account_equity: float = 0.0
    account_buying_power: float = 0.0
    
    # ==================== 持仓信息 ====================
    positions: Dict[str, Dict] = field(default_factory=dict)  # {symbol: {quantity, cost_price, ...}}
    has_position: bool = False
    position_cost: float = 0.0
    position_quantity: int = 0
    position_pnl_pct: float = 0.0  # 当前持仓盈亏百分比
    
    # ==================== 风险状态 ====================
    day_pnl_pct: float = 0.0  # 当日盈亏百分比
    consecutive_losses: int = 0  # 连续亏损次数
    last_trade_time_by_symbol: Dict[str, datetime] = field(default_factory=dict)  # {symbol: last_trade_time}
    
    # ==================== 预计算的布尔条件 ====================
    trend_ok: bool = False  # Price > MA5 > MA20 > MA60
    volume_ok: bool = False  # volume_ratio > 1.2
    macd_ok: bool = False  # MACD > 0 and golden cross
    rsi_ok: bool = False  # RSI in [50, 70]
    breakout_ok: bool = False  # 突破关键阻力位
    bb_ok: bool = False  # 价格在布林带中上轨附近，有向上空间
    buy_rule_count: int = 0  # 满足的买入规则数量 (0-6)
    
    # ==================== 数据完整性标志 ====================
    has_valid_price: bool = True
    has_valid_indicators: bool = True
    missing_fields: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """计算布尔条件和规则计数"""
        # 由于 dataclass 是 frozen，我们需要使用 object.__setattr__ 来修改字段
        object.__setattr__(self, '_computed', True)
    
    @classmethod
    def from_market_data(cls, symbol: str, market_data: Dict, account_info: Dict,
                        positions: List[Dict] = None, risk_state: Dict = None) -> 'IndicatorSnapshot':
        """
        从市场数据创建快照
        
        Args:
            symbol: 股票代码
            market_data: 市场数据字典（来自 AlpacaAIDecision.get_market_data）
            account_info: 账户信息
            positions: 持仓列表
            risk_state: 风险状态（可选）
        """
        # 获取当前时间
        now_utc = datetime.now(pytz.UTC)
        et_tz = pytz.timezone('America/New_York')
        now_et = now_utc.astimezone(et_tz)
        
        # 判断交易时段
        hour_et = now_et.hour
        minute_et = now_et.minute
        time_minutes = hour_et * 60 + minute_et
        
        if 570 <= time_minutes < 930:  # 4:30 AM - 9:30 AM ET
            session = 'premarket'
        elif 930 <= time_minutes < 960:  # 9:30 AM - 4:00 PM ET
            session = 'regular'
        elif 960 <= time_minutes < 1200:  # 4:00 PM - 8:00 PM ET
            session = 'afterhours'
        else:
            session = 'closed'
        
        # 提取价格数据
        price = market_data.get('current_price', 0.0)
        open_price = market_data.get('open', price)
        high = market_data.get('high', price)
        low = market_data.get('low', price)
        close = market_data.get('close', price)
        volume = market_data.get('volume', 0)
        
        # 提取技术指标
        ma5 = market_data.get('ma5')
        ma20 = market_data.get('ma20')
        ma60 = market_data.get('ma60')
        
        macd = market_data.get('macd')
        macd_signal = market_data.get('macd_signal')
        macd_hist = market_data.get('macd_hist')
        
        # 判断 MACD 交叉
        macd_cross = 'none'
        if macd is not None and macd_signal is not None:
            if macd_hist is not None:
                if macd_hist > 0 and macd > macd_signal:
                    macd_cross = 'golden'
                elif macd_hist < 0 and macd < macd_signal:
                    macd_cross = 'death'
        
        rsi = market_data.get('rsi')
        
        bb_upper = market_data.get('bb_upper')
        bb_middle = market_data.get('bb_middle')
        bb_lower = market_data.get('bb_lower')
        
        # 判断布林带位置
        bb_position = None
        if bb_upper and bb_middle and bb_lower and price:
            if price >= bb_upper * 0.98:
                bb_position = 'upper'
            elif price >= bb_middle:
                bb_position = 'middle'
            else:
                bb_position = 'lower'
        
        volume_ratio = market_data.get('volume_ratio')
        avg_volume_5d = None
        if volume_ratio and volume:
            avg_volume_5d = volume / volume_ratio
        
        # 计算支撑阻力（简化：使用最近的高低点）
        support = low * 0.98 if low else None  # 简化计算
        resistance = high * 1.02 if high else None  # 简化计算
        
        # 处理持仓信息
        positions_dict = {}
        has_position = False
        position_cost = 0.0
        position_quantity = 0
        position_pnl_pct = 0.0
        
        if positions:
            for pos in positions:
                pos_symbol = pos.get('symbol', '').upper()
                positions_dict[pos_symbol] = pos
                if pos_symbol == symbol.upper():
                    has_position = True
                    position_cost = pos.get('avg_entry_price', 0.0)
                    position_quantity = pos.get('quantity', 0)
                    current_price = pos.get('current_price', price)
                    if position_cost > 0:
                        position_pnl_pct = ((current_price - position_cost) / position_cost) * 100
        
        # 账户信息
        account_equity = account_info.get('equity', account_info.get('portfolio_value', 0.0))
        account_buying_power = account_info.get('buying_power', account_info.get('cash', 0.0))
        
        # 风险状态
        risk_state = risk_state or {}
        day_pnl_pct = risk_state.get('day_pnl_pct', 0.0)
        consecutive_losses = risk_state.get('consecutive_losses', 0)
        last_trade_time_by_symbol = risk_state.get('last_trade_time_by_symbol', {})
        
        # 计算布尔条件
        trend_ok = False
        if ma5 and ma20 and ma60 and price:
            trend_ok = (price > ma5 > ma20 > ma60)
        
        volume_ok = False
        if volume_ratio:
            volume_ok = (volume_ratio > 1.2)
        
        macd_ok = False
        if macd is not None and macd_signal is not None:
            macd_ok = (macd > 0 and macd > macd_signal and macd_cross == 'golden')
        
        rsi_ok = False
        if rsi:
            rsi_ok = (50 <= rsi <= 70)
        
        breakout_ok = False
        if resistance and price:
            # 简化：价格接近或突破阻力位
            breakout_ok = (price >= resistance * 0.99)
        
        bb_ok = False
        if bb_position and bb_middle and price:
            # 价格在中上轨附近，有向上空间
            bb_ok = (bb_position in ['middle', 'upper']) and (price >= bb_middle)
        
        # 计算买入规则计数
        buy_rule_count = sum([
            trend_ok,
            volume_ok,
            macd_ok,
            rsi_ok,
            breakout_ok,
            bb_ok
        ])
        
        # 检查数据完整性
        missing_fields = []
        has_valid_price = (price > 0)
        has_valid_indicators = True
        
        if not has_valid_price:
            missing_fields.append('price')
            has_valid_indicators = False
        
        if ma5 is None:
            missing_fields.append('ma5')
        if ma20 is None:
            missing_fields.append('ma20')
        if ma60 is None:
            missing_fields.append('ma60')
        if macd is None:
            missing_fields.append('macd')
        if rsi is None:
            missing_fields.append('rsi')
        
        # 流动性指标（默认值，实际应从市场数据获取）
        spread = market_data.get('spread', 0.1)  # 默认 0.1%
        liquidity_score = market_data.get('liquidity_score', 80.0)  # 默认 80
        
        # 创建快照
        snapshot = cls(
            symbol=symbol.upper(),
            timestamp_utc=now_utc,
            timestamp_et=now_et,
            price=price,
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
            ma5=ma5,
            ma20=ma20,
            ma60=ma60,
            macd=macd,
            macd_dif=macd,
            macd_dea=macd_signal,
            macd_hist=macd_hist,
            macd_cross=macd_cross,
            rsi=rsi,
            bb_upper=bb_upper,
            bb_middle=bb_middle,
            bb_lower=bb_lower,
            bb_position=bb_position,
            avg_volume_5d=avg_volume_5d,
            volume_ratio=volume_ratio,
            spread=spread,
            liquidity_score=liquidity_score,
            session=session,
            support=support,
            resistance=resistance,
            account_equity=account_equity,
            account_buying_power=account_buying_power,
            positions=positions_dict,
            has_position=has_position,
            position_cost=position_cost,
            position_quantity=position_quantity,
            position_pnl_pct=position_pnl_pct,
            day_pnl_pct=day_pnl_pct,
            consecutive_losses=consecutive_losses,
            last_trade_time_by_symbol=last_trade_time_by_symbol,
            trend_ok=trend_ok,
            volume_ok=volume_ok,
            macd_ok=macd_ok,
            rsi_ok=rsi_ok,
            breakout_ok=breakout_ok,
            bb_ok=bb_ok,
            buy_rule_count=buy_rule_count,
            has_valid_price=has_valid_price,
            has_valid_indicators=has_valid_indicators,
            missing_fields=missing_fields
        )
        
        return snapshot
    
    def to_dict(self) -> Dict:
        """转换为字典（用于序列化）"""
        result = {}
        for key, value in self.__dict__.items():
            if key == '_computed':
                continue
            if isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                # 处理嵌套字典，特别是 datetime 值
                result[key] = {
                    k: v.isoformat() if isinstance(v, datetime) else v
                    for k, v in value.items()
                }
            else:
                result[key] = value
        return result
    
    def get_hash(self) -> str:
        """获取快照的哈希值（用于审计）"""
        data = self.to_dict()
        # 移除时间戳，只对数据内容哈希
        data.pop('timestamp_utc', None)
        data.pop('timestamp_et', None)
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()[:16]

