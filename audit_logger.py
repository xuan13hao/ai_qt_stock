"""
Audit Logger Module
审计日志记录器，记录所有决策和执行过程
"""

import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from pathlib import Path
from indicator_snapshot import IndicatorSnapshot
from hard_decision_firewall import LLMProposal, FirewallResult


class AuditLogger:
    """审计日志记录器"""
    
    def __init__(self, log_dir: str = "audit_logs"):
        """
        初始化审计日志器
        
        Args:
            log_dir: 日志目录
        """
        self.logger = logging.getLogger(__name__)
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # 日志文件路径（按日期）
        self.log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    def log_decision(self, 
                     symbol: str,
                     snapshot: IndicatorSnapshot,
                     llm_prompt_version: str,
                     llm_output_raw: str,
                     parsed_proposal: LLMProposal,
                     firewall_result: FirewallResult,
                     order_request: Optional[Dict] = None,
                     order_fill: Optional[Dict] = None,
                     pnl_update: Optional[Dict] = None) -> str:
        """
        记录完整的决策流程
        
        Args:
            symbol: 股票代码
            snapshot: 指标快照
            llm_prompt_version: LLM prompt 版本
            llm_output_raw: LLM 原始输出
            parsed_proposal: 解析后的 LLM 建议
            firewall_result: 防火墙结果
            order_request: 订单请求（如果有）
            order_fill: 订单成交（如果有）
            pnl_update: 盈亏更新（如果有）
            
        Returns:
            日志条目 ID
        """
        entry_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # 构建日志条目
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "entry_id": entry_id,
            "symbol": symbol,
            "snapshot_hash": snapshot.get_hash(),
            "snapshot_fields": {
                "price": snapshot.price,
                "ma5": snapshot.ma5,
                "ma20": snapshot.ma20,
                "ma60": snapshot.ma60,
                "macd": snapshot.macd,
                "rsi": snapshot.rsi,
                "volume_ratio": snapshot.volume_ratio,
                "session": snapshot.session,
                "trend_ok": snapshot.trend_ok,
                "volume_ok": snapshot.volume_ok,
                "macd_ok": snapshot.macd_ok,
                "rsi_ok": snapshot.rsi_ok,
                "breakout_ok": snapshot.breakout_ok,
                "bb_ok": snapshot.bb_ok,
                "buy_rule_count": snapshot.buy_rule_count,
                "has_position": snapshot.has_position,
                "position_pnl_pct": snapshot.position_pnl_pct,
                "day_pnl_pct": snapshot.day_pnl_pct
            },
            "llm_prompt_version": llm_prompt_version,
            "llm_output_raw": llm_output_raw,
            "parsed_proposal": {
                "proposed_action": parsed_proposal.proposed_action,
                "confidence": parsed_proposal.confidence,
                "evidence": parsed_proposal.evidence,
                "params": parsed_proposal.params,
                "risk_level": parsed_proposal.risk_level,
                "warnings": parsed_proposal.warnings,
                "counter_evidence": parsed_proposal.counter_evidence,
                "notes": parsed_proposal.notes
            },
            "firewall_result": {
                "allowed": firewall_result.allowed,
                "final_action": firewall_result.final_action,
                "final_params": firewall_result.final_params,
                "reject_reasons": firewall_result.reject_reasons,
                "reason_codes": firewall_result.reason_codes,
                "normalized_confidence": firewall_result.normalized_confidence,
                "modifications": firewall_result.modifications or []
            },
            "order_request": order_request,
            "order_fill": order_fill,
            "pnl_update": pnl_update
        }
        
        # 写入 JSONL 文件
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            self.logger.error(f"写入审计日志失败: {e}")
        
        return entry_id
    
    def log_rejection(self, symbol: str, snapshot: IndicatorSnapshot,
                    reason: str, reason_code: str, proposal: Optional[LLMProposal] = None):
        """记录拒绝决策"""
        entry_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "entry_id": entry_id,
            "symbol": symbol,
            "snapshot_hash": snapshot.get_hash(),
            "action": "REJECTED",
            "reason": reason,
            "reason_code": reason_code,
            "proposal": {
                "proposed_action": proposal.proposed_action if proposal else None,
                "confidence": proposal.confidence if proposal else None
            } if proposal else None
        }
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
        except Exception as e:
            self.logger.error(f"写入拒绝日志失败: {e}")
        
        return entry_id
    
    def query_logs(self, symbol: Optional[str] = None, 
                  start_time: Optional[datetime] = None,
                  end_time: Optional[datetime] = None,
                  limit: int = 100) -> list:
        """
        查询日志
        
        Args:
            symbol: 股票代码（可选）
            start_time: 开始时间（可选）
            end_time: 结束时间（可选）
            limit: 返回条数限制
            
        Returns:
            日志条目列表
        """
        results = []
        
        # 读取今天的日志文件
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        entry = json.loads(line)
                        
                        # 过滤
                        if symbol and entry.get('symbol') != symbol.upper():
                            continue
                        
                        entry_time = datetime.fromisoformat(entry['timestamp'])
                        if start_time and entry_time < start_time:
                            continue
                        if end_time and entry_time > end_time:
                            continue
                        
                        results.append(entry)
                        
                        if len(results) >= limit:
                            break
                    except json.JSONDecodeError:
                        continue
        except FileNotFoundError:
            pass
        
        # 按时间倒序
        results.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return results
    
    def get_statistics(self, symbol: Optional[str] = None, days: int = 1) -> Dict:
        """
        获取统计信息
        
        Args:
            symbol: 股票代码（可选）
            days: 统计天数
            
        Returns:
            统计字典
        """
        from datetime import timedelta
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        
        logs = self.query_logs(symbol=symbol, start_time=start_time, end_time=end_time, limit=10000)
        
        stats = {
            "total_decisions": len(logs),
            "allowed": 0,
            "rejected": 0,
            "buy": 0,
            "sell": 0,
            "hold": 0,
            "reject_reasons": {},
            "avg_confidence": 0.0
        }
        
        total_confidence = 0
        confidence_count = 0
        
        for log in logs:
            firewall_result = log.get('firewall_result', {})
            final_action = firewall_result.get('final_action', 'HOLD')
            
            if firewall_result.get('allowed', False):
                stats["allowed"] += 1
                if final_action == "BUY":
                    stats["buy"] += 1
                elif final_action == "SELL":
                    stats["sell"] += 1
            else:
                stats["rejected"] += 1
                stats["hold"] += 1
            
            # 统计拒绝原因
            reason_codes = firewall_result.get('reason_codes', [])
            for code in reason_codes:
                stats["reject_reasons"][code] = stats["reject_reasons"].get(code, 0) + 1
            
            # 统计置信度
            confidence = firewall_result.get('normalized_confidence', 0)
            if confidence > 0:
                total_confidence += confidence
                confidence_count += 1
        
        if confidence_count > 0:
            stats["avg_confidence"] = total_confidence / confidence_count
        
        return stats

