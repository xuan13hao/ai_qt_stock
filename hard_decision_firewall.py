"""
Hard Decision Firewall Module
Hard risk control firewall, non-bypassable trading validation
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from indicator_snapshot import IndicatorSnapshot


class ReasonCode(Enum):
    """Rejection reason codes"""
    ALLOWED = "ALLOWED"
    INVALID_SESSION = "INVALID_SESSION"  # Non-trading session
    LOW_LIQUIDITY = "LOW_LIQUIDITY"  # Insufficient liquidity
    HIGH_SPREAD = "HIGH_SPREAD"  # Spread too large
    INSUFFICIENT_BUY_SIGNALS = "INSUFFICIENT_BUY_SIGNALS"  # Insufficient buy signals
    POSITION_SIZE_EXCEEDED = "POSITION_SIZE_EXCEEDED"  # Position size exceeded
    PARAMS_CLAMPED = "PARAMS_CLAMPED"  # Parameters clamped
    DAY_CIRCUIT_BREAKER = "DAY_CIRCUIT_BREAKER"  # Daily circuit breaker
    COOLDOWN_ACTIVE = "COOLDOWN_ACTIVE"  # Cooldown period
    MIN_TRADE_INTERVAL = "MIN_TRADE_INTERVAL"  # Insufficient trade interval
    MISSING_DATA = "MISSING_DATA"  # Missing data
    LOW_CONFIDENCE = "LOW_CONFIDENCE"  # Low confidence
    SIGNAL_CONFLICT = "SIGNAL_CONFLICT"  # Signal conflict
    HARD_STOP_LOSS = "HARD_STOP_LOSS"  # Hard stop loss triggered (forced sell)


@dataclass
class LLMProposal:
    """LLM trading proposal"""
    symbol: str
    proposed_action: str  # "BUY" | "SELL" | "HOLD"
    confidence: int  # 0-100
    evidence: Dict
    params: Dict
    risk_level: str
    warnings: List[str]
    counter_evidence: List[str]
    notes: str


@dataclass
class FirewallResult:
    """Firewall validation result"""
    allowed: bool
    final_action: str  # "BUY" | "SELL" | "HOLD"
    final_params: Dict
    reject_reasons: List[str]
    reason_codes: List[str]
    normalized_confidence: int  # 0-100, confidence adjusted by firewall
    original_proposal: Optional[LLMProposal] = None
    modifications: List[str] = None  # Record all modifications


class HardDecisionFirewall:
    """Hard risk control firewall"""
    
    def __init__(self, config: Dict = None):
        """
        Initialize firewall
        
        Args:
            config: Configuration dictionary containing various thresholds
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Default configuration
        self.enable_extended_hours = self.config.get('enable_extended_hours', False)
        self.max_spread = self.config.get('max_spread', 0.5)  # Maximum spread 0.5%
        self.min_liquidity_score = self.config.get('min_liquidity_score', 50.0)
        self.min_buy_rule_count = self.config.get('min_buy_rule_count', 3)
        self.max_position_size_pct = self.config.get('max_position_size_pct', 40)
        self.max_position_size_pct_extended = self.config.get('max_position_size_pct_extended', 20)
        self.min_confidence_buy = self.config.get('min_confidence_buy', 65)
        self.stop_loss_min = self.config.get('stop_loss_min', 3.0)
        self.stop_loss_max = self.config.get('stop_loss_max', 5.0)
        self.take_profit_min = self.config.get('take_profit_min', 5.0)
        self.take_profit_max = self.config.get('take_profit_max', 15.0)
        self.day_circuit_breaker_pct = self.config.get('day_circuit_breaker_pct', -2.0)
        self.cooldown_minutes = self.config.get('cooldown_minutes', 30)
        self.min_trade_interval_minutes = self.config.get('min_trade_interval_minutes', 5)
        self.hard_stop_loss_pct = self.config.get('hard_stop_loss_pct', -5.0)
    
    def check(self, proposal: LLMProposal, snapshot: IndicatorSnapshot,
              risk_state: Dict = None) -> FirewallResult:
        """
        Check trading proposal
        
        Args:
            proposal: LLM trading proposal
            snapshot: Indicator snapshot
            risk_state: Risk state (optional)
            
        Returns:
            FirewallResult
        """
        risk_state = risk_state or {}
        reject_reasons = []
        reason_codes = []
        modifications = []
        final_action = proposal.proposed_action
        final_params = proposal.params.copy()
        normalized_confidence = proposal.confidence
        
        # ==================== 1. Data Integrity Check ====================
        if not snapshot.has_valid_price:
            reject_reasons.append("Invalid price data")
            reason_codes.append(ReasonCode.MISSING_DATA.value)
            return FirewallResult(
                allowed=False,
                final_action="HOLD",
                final_params={},
                reject_reasons=reject_reasons,
                reason_codes=reason_codes,
                normalized_confidence=0,
                original_proposal=proposal
            )
        
        if snapshot.missing_fields:
            if proposal.proposed_action == "BUY":
                reject_reasons.append(f"Critical indicators missing: {', '.join(snapshot.missing_fields)}")
                reason_codes.append(ReasonCode.MISSING_DATA.value)
                final_action = "HOLD"
                normalized_confidence = max(0, normalized_confidence - 20)
        
        # ==================== 2. Hard Stop Loss Check (Highest Priority) ====================
        if snapshot.has_position and snapshot.position_pnl_pct <= self.hard_stop_loss_pct:
            # Hard stop loss triggered, force sell
            return FirewallResult(
                allowed=True,
                final_action="SELL",
                final_params={
                    'position_size_pct': 100,  # Sell all
                    'stop_loss_pct': self.hard_stop_loss_pct,
                    'take_profit_pct': 0
                },
                reject_reasons=[],
                reason_codes=[ReasonCode.HARD_STOP_LOSS.value],
                normalized_confidence=100,  # Hard stop loss has highest confidence
                original_proposal=proposal,
                modifications=[f"Hard stop loss triggered ({snapshot.position_pnl_pct:.2f}% <= {self.hard_stop_loss_pct}%), forced sell"]
            )
        
        # ==================== 3. Trading Session Check ====================
        if snapshot.session == 'closed':
            reject_reasons.append("Market is closed")
            reason_codes.append(ReasonCode.INVALID_SESSION.value)
            final_action = "HOLD"
        
        elif snapshot.session != 'regular':
            if not self.enable_extended_hours:
                reject_reasons.append(f"Non-regular trading session ({snapshot.session}), extended hours trading not enabled")
                reason_codes.append(ReasonCode.INVALID_SESSION.value)
                final_action = "HOLD"
            else:
                # Extended hours trading, stricter limits
                if proposal.proposed_action == "BUY":
                    # Reduce position limit
                    if final_params.get('position_size_pct', 0) > self.max_position_size_pct_extended:
                        final_params['position_size_pct'] = self.max_position_size_pct_extended
                        modifications.append(f"Extended hours trading, position limit reduced to {self.max_position_size_pct_extended}%")
                    
                    # Increase risk level
                    if proposal.risk_level != 'high':
                        modifications.append(f"Extended hours trading, risk level raised to high")
                    
                    normalized_confidence = max(0, normalized_confidence - 10)
        
        # ==================== 4. Liquidity Check ====================
        if snapshot.spread is not None and snapshot.spread > self.max_spread:
            reject_reasons.append(f"Spread too large: {snapshot.spread:.2f}% > {self.max_spread}%")
            reason_codes.append(ReasonCode.HIGH_SPREAD.value)
            if proposal.proposed_action == "BUY":
                final_action = "HOLD"
        
        if snapshot.liquidity_score is not None and snapshot.liquidity_score < self.min_liquidity_score:
            reject_reasons.append(f"Insufficient liquidity: {snapshot.liquidity_score:.1f} < {self.min_liquidity_score}")
            reason_codes.append(ReasonCode.LOW_LIQUIDITY.value)
            if proposal.proposed_action == "BUY":
                final_action = "HOLD"
        
        # ==================== 5. Buy Signal Check ====================
        if proposal.proposed_action == "BUY":
            # Check buy rule count
            buy_rule_count = snapshot.buy_rule_count
            if buy_rule_count < self.min_buy_rule_count:
                reject_reasons.append(f"Insufficient buy signals: {buy_rule_count} < {self.min_buy_rule_count}")
                reason_codes.append(ReasonCode.INSUFFICIENT_BUY_SIGNALS.value)
                final_action = "HOLD"
                normalized_confidence = max(0, normalized_confidence - 30)
            
            # Check confidence
            if proposal.confidence < self.min_confidence_buy:
                reject_reasons.append(f"Insufficient confidence: {proposal.confidence} < {self.min_confidence_buy}")
                reason_codes.append(ReasonCode.LOW_CONFIDENCE.value)
                final_action = "HOLD"
            
            # Check signal conflict
            if self._has_signal_conflict(snapshot, proposal):
                reject_reasons.append("Signal conflict: Uptrend but technical indicators inconsistent")
                reason_codes.append(ReasonCode.SIGNAL_CONFLICT.value)
                final_action = "HOLD"
                normalized_confidence = max(0, normalized_confidence - 20)
            
            # Check counter_evidence
            if len(proposal.counter_evidence) < 2:
                modifications.append("LLM did not provide sufficient counter-evidence, reducing confidence")
                normalized_confidence = max(0, normalized_confidence - 10)
        
        # ==================== 6. Position Limit Check ====================
        if proposal.proposed_action == "BUY":
            max_size = self.max_position_size_pct_extended if snapshot.session != 'regular' else self.max_position_size_pct
            
            if final_params.get('position_size_pct', 0) > max_size:
                final_params['position_size_pct'] = max_size
                modifications.append(f"Position limit clamped to {max_size}%")
                reason_codes.append(ReasonCode.PARAMS_CLAMPED.value)
        
        # ==================== 7. Stop Loss/Take Profit Range Check ====================
        stop_loss_pct = final_params.get('stop_loss_pct', 5.0)
        take_profit_pct = final_params.get('take_profit_pct', 10.0)
        
        if stop_loss_pct < self.stop_loss_min or stop_loss_pct > self.stop_loss_max:
            original = stop_loss_pct
            stop_loss_pct = max(self.stop_loss_min, min(self.stop_loss_max, stop_loss_pct))
            final_params['stop_loss_pct'] = stop_loss_pct
            modifications.append(f"Stop loss clamped from {original:.2f}% to {stop_loss_pct:.2f}%")
            reason_codes.append(ReasonCode.PARAMS_CLAMPED.value)
        
        if take_profit_pct < self.take_profit_min or take_profit_pct > self.take_profit_max:
            original = take_profit_pct
            take_profit_pct = max(self.take_profit_min, min(self.take_profit_max, take_profit_pct))
            final_params['take_profit_pct'] = take_profit_pct
            modifications.append(f"Take profit clamped from {original:.2f}% to {take_profit_pct:.2f}%")
            reason_codes.append(ReasonCode.PARAMS_CLAMPED.value)
        
        # ==================== 8. Daily Circuit Breaker Check ====================
        if proposal.proposed_action == "BUY":
            if snapshot.day_pnl_pct <= self.day_circuit_breaker_pct:
                reject_reasons.append(f"Daily circuit breaker triggered: {snapshot.day_pnl_pct:.2f}% <= {self.day_circuit_breaker_pct}%")
                reason_codes.append(ReasonCode.DAY_CIRCUIT_BREAKER.value)
                final_action = "HOLD"
        
        # ==================== 9. Cooldown Check ====================
        if snapshot.last_trade_time_by_symbol:
            last_trade_time = snapshot.last_trade_time_by_symbol.get(snapshot.symbol)
            if last_trade_time:
                if isinstance(last_trade_time, str):
                    last_trade_time = datetime.fromisoformat(last_trade_time)
                
                time_since_last_trade = datetime.now() - last_trade_time
                cooldown_delta = timedelta(minutes=self.cooldown_minutes)
                
                # Check if in cooldown period (cannot buy back immediately after sell)
                if proposal.proposed_action == "BUY" and time_since_last_trade < cooldown_delta:
                    reject_reasons.append(f"Cooldown period not ended: {time_since_last_trade.seconds // 60} minutes < {self.cooldown_minutes} minutes")
                    reason_codes.append(ReasonCode.COOLDOWN_ACTIVE.value)
                    final_action = "HOLD"
                
                # Check minimum trade interval
                min_interval_delta = timedelta(minutes=self.min_trade_interval_minutes)
                if time_since_last_trade < min_interval_delta:
                    reject_reasons.append(f"Insufficient trade interval: {time_since_last_trade.seconds // 60} minutes < {self.min_trade_interval_minutes} minutes")
                    reason_codes.append(ReasonCode.MIN_TRADE_INTERVAL.value)
                    if proposal.proposed_action != "SELL":  # Sell not restricted by this
                        final_action = "HOLD"
        
        # ==================== 10. Final Decision ====================
        allowed = (final_action in ["BUY", "SELL"]) and len(reject_reasons) == 0
        
        # If rejected, ensure it's HOLD
        if not allowed:
            final_action = "HOLD"
        
        return FirewallResult(
            allowed=allowed,
            final_action=final_action,
            final_params=final_params,
            reject_reasons=reject_reasons,
            reason_codes=reason_codes,
            normalized_confidence=normalized_confidence,
            original_proposal=proposal,
            modifications=modifications
        )
    
    def _has_signal_conflict(self, snapshot: IndicatorSnapshot, proposal: LLMProposal) -> bool:
        """
        Check signal conflict
        
        Example: trend_ok=True but macd_ok=False and volume_ok=False
        """
        if snapshot.trend_ok:
            # Uptrend but technical indicators don't support it
            if not snapshot.macd_ok and not snapshot.volume_ok:
                return True
        
        # Check conflicts in evidence
        evidence = proposal.evidence
        if evidence.get('trend_ok') and not evidence.get('macd_ok') and not evidence.get('volume_ok'):
            return True
        
        return False

