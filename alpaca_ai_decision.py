"""
Alpaca AI Decision Module
DeepSeek LLM powered autonomous trading decision for US stocks
"""

import logging
import requests
import json
from typing import Dict, Optional
from datetime import datetime
import pytz
import yfinance as yf
import pandas as pd
import ta


class AlpacaAIDecision:
    """Alpaca AI Decision Engine using DeepSeek LLM"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com/v1"):
        """
        Initialize AI Decision Engine
        
        Args:
            api_key: DeepSeek API key
            base_url: DeepSeek API base URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.logger = logging.getLogger(__name__)
    
    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """
        Get US stock market data and technical indicators
        
        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            
        Returns:
            Market data dictionary with technical indicators
        """
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="3mo", interval="1d")
            
            if df.empty:
                return None
            
            # Calculate technical indicators
            df['MA5'] = ta.trend.sma_indicator(df['Close'], window=5)
            df['MA20'] = ta.trend.sma_indicator(df['Close'], window=20)
            df['MA60'] = ta.trend.sma_indicator(df['Close'], window=60)
            
            macd = ta.trend.MACD(df['Close'])
            df['MACD'] = macd.macd()
            df['MACD_signal'] = macd.macd_signal()
            df['MACD_hist'] = macd.macd_diff()
            
            df['RSI'] = ta.momentum.rsi(df['Close'], window=14)
            
            bollinger = ta.volatility.BollingerBands(df['Close'])
            df['BB_upper'] = bollinger.bollinger_hband()
            df['BB_middle'] = bollinger.bollinger_mavg()
            df['BB_lower'] = bollinger.bollinger_lband()
            
            df['Volume_MA5'] = ta.trend.sma_indicator(df['Volume'], window=5)
            df['Volume_ratio'] = df['Volume'] / df['Volume_MA5']
            
            # Get latest data
            latest = df.iloc[-1]
            info = ticker.info
            
            market_data = {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'current_price': float(latest['Close']),
                'open': float(latest['Open']),
                'high': float(latest['High']),
                'low': float(latest['Low']),
                'volume': int(latest['Volume']),
                'change_pct': ((latest['Close'] - df.iloc[-2]['Close']) / df.iloc[-2]['Close'] * 100) if len(df) > 1 else 0,
                'ma5': float(latest['MA5']),
                'ma20': float(latest['MA20']),
                'ma60': float(latest['MA60']),
                'macd': float(latest['MACD']),
                'macd_signal': float(latest['MACD_signal']),
                'macd_hist': float(latest['MACD_hist']),
                'rsi': float(latest['RSI']),
                'bb_upper': float(latest['BB_upper']),
                'bb_middle': float(latest['BB_middle']),
                'bb_lower': float(latest['BB_lower']),
                'volume_ratio': float(latest['Volume_ratio']),
                'trend': 'up' if latest['MA5'] > latest['MA20'] > latest['MA60'] else 'down' if latest['MA5'] < latest['MA20'] < latest['MA60'] else 'sideways'
            }
            
            return market_data
            
        except Exception as e:
            self.logger.error(f"Failed to get market data for {symbol}: {e}")
            return None
    
    def analyze_and_decide(self, symbol: str, account_info: Dict, 
                          has_position: bool = False, position_cost: float = 0,
                          position_quantity: int = 0) -> Dict:
        """
        Analyze stock and make trading decision using DeepSeek AI
        
        Args:
            symbol: Stock symbol
            account_info: Account information
            has_position: Whether currently holding the stock
            position_cost: Position cost price
            position_quantity: Position quantity
            
        Returns:
            Decision dictionary
        """
        # Get market data
        market_data = self.get_market_data(symbol)
        if not market_data:
            return {
                'success': False,
                'error': 'Failed to get market data'
            }
        
        # Build prompt
        prompt = self._build_prompt(market_data, account_info, has_position, 
                                   position_cost, position_quantity)
        
        # Call DeepSeek API
        try:
            response = self._call_deepseek(prompt)
            decision = self._parse_decision(response)
            
            return {
                'success': True,
                'decision': decision,
                'market_data': market_data
            }
        except Exception as e:
            self.logger.error(f"AI decision failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def analyze_and_decide_v2(self, snapshot) -> Dict:
        """
        New version: Decision based on IndicatorSnapshot
        
        Args:
            snapshot: IndicatorSnapshot object
            
        Returns:
            Decision dictionary with LLM proposal
        """
        # Check data integrity
        if not snapshot.has_valid_price:
            return {
                'success': False,
                'error': 'Invalid price data',
                'proposal': None
            }
        
        # Build prompt (using snapshot data)
        prompt = self._build_prompt_v2(snapshot)
        
        # Call LLM
        try:
            response = self._call_deepseek(prompt)
            proposal = self._parse_proposal_v2(response, snapshot)
            
            return {
                'success': True,
                'proposal': proposal,
                'raw_output': response
            }
        except Exception as e:
            self.logger.error(f"AI decision v2 failed: {e}")
            # Return conservative decision
            from hard_decision_firewall import LLMProposal
            return {
                'success': False,
                'error': str(e),
                'proposal': LLMProposal(
                    symbol=snapshot.symbol,
                    proposed_action="HOLD",
                    confidence=0,
                    evidence={},
                    params={},
                    risk_level="high",
                    warnings=[f"AI decision failed: {str(e)}"],
                    counter_evidence=[],
                    notes="Data error or LLM call failed"
                )
            }
    
    def _build_prompt(self, market_data: Dict, account_info: Dict,
                     has_position: bool, position_cost: float, 
                     position_quantity: int) -> str:
        """Build analysis prompt"""
        
        prompt = f"""
You are an experienced US stock quantitative trading expert with 15 years of experience.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ US Stock Trading Rules
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[CRITICAL] T+0 Trading:
- Stocks bought today CAN be sold today (same-day trading allowed)
- No holding period restrictions
- More flexible than A-shares

[CRITICAL] Trading Hours:
- Regular Market: 9:30 AM - 4:00 PM ET
- Pre-Market: 4:00 AM - 9:30 AM ET (limited liquidity)
- After-Hours: 4:00 PM - 8:00 PM ET (limited liquidity)

[CRITICAL] No Circuit Breakers:
- US stocks have no daily price limits (unlike A-shares)
- Can move freely, but also more volatile

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 Your Trading Philosophy (T+0 Adapted)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**With T+0 flexibility, you can be more aggressive but still disciplined!**

1. **Buy with Confidence**:
   - Can exit quickly if trade goes wrong (T+0 advantage)
   - Still need strong technical signals
   - Can use smaller position sizes for testing

2. **Stop Loss is Easier**:
   - Can exit immediately if loss exceeds threshold
   - Recommended stop loss: -3% to -5% (tighter than A-shares)
   - Can take profits more flexibly: +5% to +15%

3. **Technical Analysis**:
   - Daily trend confirmation
   - Support/resistance levels
   - Volume confirmation
   - Price-volume relationship

4. **Risk Control**:
   - Single stock position ≤ 40% (can be higher than A-shares due to T+0)
   - Stop loss: -3% to -5% (tighter due to T+0 flexibility)
   - Take profit: +5% to +15% (can take profits more flexibly)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Available Trading Actions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

**If no position**:
- action = "BUY" - Must ensure strong technical signals, upward trend
- action = "HOLD" - Signals unclear, wait for better entry

**If has position**:
- action = "SELL" - Stop loss/take profit triggered, or technical weakness
- action = "HOLD" - Trend unchanged, continue holding
- ✅ Note: With T+0, can sell immediately if needed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📈 Buy Signals (at least 3 must be met)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ✅ Upward Trend: Price > MA5 > MA20 > MA60 (bullish alignment)
2. ✅ Volume-Price Coordination: Volume > 120% of 5-day average
3. ✅ MACD Golden Cross: MACD > 0 and DIF crosses above DEA
4. ✅ Healthy RSI: RSI in 50-70 range (not overbought/oversold)
5. ✅ Key Level Breakthrough: Breakthrough of previous high or resistance
6. ✅ Bollinger Band Position: Price near upper middle band, upward space

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📉 Sell Signals (any one triggers immediate sell)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. 🔴 Stop Loss Triggered: Loss ≥ -5% (sell immediately)
2. 🟢 Take Profit Triggered: Profit ≥ +10% (lock in gains)
3. 🔴 Trend Weakens: Falls below MA20/MA60, MACD death cross
4. 🔴 Volume Decline: Volume increases but price falls
5. 🔴 Technical Breakdown: Falls below important support level

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 Return Format (must be strict JSON)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
    "action": "BUY" | "SELL" | "HOLD",
    "confidence": 0-100,
    "reasoning": "Detailed decision reasoning, including technical analysis, risk assessment, 200-300 words",
    "position_size_pct": 10-40,
    "stop_loss_pct": 3.0-5.0,
    "take_profit_pct": 5.0-15.0,
    "risk_level": "low" | "medium" | "high",
    "key_price_levels": {{
        "support": support_price,
        "resistance": resistance_price,
        "stop_loss": stop_loss_price
    }}
}}
"""

        # Add market data
        prompt += f"""

[STOCK] Stock Information
═══════════════════════════════════════════════════════════
Symbol: {market_data['symbol']}
Name: {market_data['name']}
Current Price: ${market_data['current_price']:.2f}
Change: {market_data['change_pct']:+.2f}%
High: ${market_data['high']:.2f}
Low: ${market_data['low']:.2f}
Open: ${market_data['open']:.2f}
Volume: {market_data['volume']:,}

[TECHNICAL] Technical Indicators
═══════════════════════════════════════════════════════════
MA5: ${market_data['ma5']:.2f}
MA20: ${market_data['ma20']:.2f}
MA60: ${market_data['ma60']:.2f}
Trend: {market_data['trend'].upper()}

MACD: {market_data['macd']:.4f}
MACD Signal: {market_data['macd_signal']:.4f}
MACD Hist: {market_data['macd_hist']:.4f} ({'Bullish' if market_data['macd_hist'] > 0 else 'Bearish'})

RSI: {market_data['rsi']:.2f} {'[Overbought]' if market_data['rsi'] > 70 else '[Oversold]' if market_data['rsi'] < 30 else '[Normal]'}

Bollinger Bands:
  Upper: ${market_data['bb_upper']:.2f}
  Middle: ${market_data['bb_middle']:.2f}
  Lower: ${market_data['bb_lower']:.2f}
  Position: {'Near Upper' if market_data['current_price'] > market_data['bb_middle'] else 'Near Lower'}

Volume Ratio: {market_data['volume_ratio']:.2f} ({'High Volume' if market_data['volume_ratio'] > 1.2 else 'Low Volume' if market_data['volume_ratio'] < 0.8 else 'Normal'})

[ACCOUNT] Account Status
═══════════════════════════════════════════════════════════
Buying Power: ${account_info.get('buying_power', 0):,.2f}
Cash: ${account_info.get('cash', 0):,.2f}
Portfolio Value: ${account_info.get('portfolio_value', 0):,.2f}
Equity: ${account_info.get('equity', 0):,.2f}
"""

        if has_position and position_cost > 0 and position_quantity > 0:
            current_price = market_data['current_price']
            cost_total = position_cost * position_quantity
            current_total = current_price * position_quantity
            profit_loss = current_total - cost_total
            profit_loss_pct = (profit_loss / cost_total * 100) if cost_total > 0 else 0
            
            prompt += f"""
[POSITION] Current Position ({market_data['symbol']}) ⭐ Important
═══════════════════════════════════════════════════════════
Quantity: {position_quantity} shares
Cost Price: ${position_cost:.2f}
Current Price: ${current_price:.2f}
Position Value: ${current_total:,.2f}
Unrealized P&L: ${profit_loss:,.2f} ({profit_loss_pct:+.2f}%)

✅ T+0 Trading: This stock can be sold immediately (no holding period restriction)

💡 Decision Recommendations:
- If profitable and technical indicators weaken → Consider taking profits
- If loss exceeds stop loss (typically -3% to -5%) → Execute stop loss immediately
- If technical indicators strong and haven't reached profit target → Consider holding
- If profitable and bullish on outlook → Can consider adding position (but watch position sizing)
"""
        else:
            prompt += """
[POSITION] Currently No Position
═══════════════════════════════════════════════════════════
Can consider buying, but must ensure:
1. Strong technical signals (meet at least 3 buy signals)
2. Sufficient safety margin
3. With T+0 flexibility, can exit quickly if needed
4. Control position size, recommend single stock position ≤40%
"""

        prompt += "\nPlease provide trading decision in JSON format based on the above data."
        
        return prompt
    
    def _build_prompt_v2(self, snapshot) -> str:
        """Build new version of prompt (based on IndicatorSnapshot)"""
        # Format values first to avoid format specifier errors
        ma5_str = f"${snapshot.ma5:.2f}" if snapshot.ma5 else "None"
        ma20_str = f"${snapshot.ma20:.2f}" if snapshot.ma20 else "None"
        ma60_str = f"${snapshot.ma60:.2f}" if snapshot.ma60 else "None"
        macd_str = f"{snapshot.macd:.4f}" if snapshot.macd else "None"
        macd_dea_str = f"{snapshot.macd_dea:.4f}" if snapshot.macd_dea else "None"
        macd_hist_str = f"{snapshot.macd_hist:.4f}" if snapshot.macd_hist else "None"
        rsi_str = f"{snapshot.rsi:.2f}" if snapshot.rsi else "None"
        bb_upper_str = f"${snapshot.bb_upper:.2f}" if snapshot.bb_upper else "None"
        bb_middle_str = f"${snapshot.bb_middle:.2f}" if snapshot.bb_middle else "None"
        bb_lower_str = f"${snapshot.bb_lower:.2f}" if snapshot.bb_lower else "None"
        volume_ratio_str = f"{snapshot.volume_ratio:.2f}" if snapshot.volume_ratio else "None"
        
        prompt = f"""
You are an experienced US stock quantitative trading expert with 15 years of experience.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ CRITICAL: You MUST use ONLY the provided data fields. DO NOT invent or assume any values.
⚠️ LANGUAGE: ALL output must be in ENGLISH. Do not use Chinese or any other language.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[STOCK DATA] - Use ONLY these values:
═══════════════════════════════════════════════════════════
Symbol: {snapshot.symbol}
Price: ${snapshot.price:.2f} {'[INVALID]' if not snapshot.has_valid_price else ''}
Open: ${snapshot.open:.2f}
High: ${snapshot.high:.2f}
Low: ${snapshot.low:.2f}
Volume: {snapshot.volume:,}

[INDICATORS] - Use ONLY these values (None means missing):
═══════════════════════════════════════════════════════════
MA5: {ma5_str}
MA20: {ma20_str}
MA60: {ma60_str}

MACD: {macd_str}
MACD Signal: {macd_dea_str}
MACD Hist: {macd_hist_str}
MACD Cross: {snapshot.macd_cross or 'None'}

RSI: {rsi_str}

Bollinger Bands:
  Upper: {bb_upper_str}
  Middle: {bb_middle_str}
  Lower: {bb_lower_str}
  Position: {snapshot.bb_position or 'None'}

Volume Ratio: {volume_ratio_str}

[PRE-COMPUTED CONDITIONS] - These are already calculated:
═══════════════════════════════════════════════════════════
trend_ok: {snapshot.trend_ok} (Price > MA5 > MA20 > MA60)
volume_ok: {snapshot.volume_ok} (Volume ratio > 1.2)
macd_ok: {snapshot.macd_ok} (MACD > 0 and golden cross)
rsi_ok: {snapshot.rsi_ok} (RSI in 50-70)
breakout_ok: {snapshot.breakout_ok} (Breakthrough resistance)
bb_ok: {snapshot.bb_ok} (Price near upper/middle band)
buy_rule_count: {snapshot.buy_rule_count} / 6

[TRADING SESSION]
═══════════════════════════════════════════════════════════
Session: {snapshot.session}
Time ET: {snapshot.timestamp_et.strftime('%Y-%m-%d %H:%M:%S')}

[POSITION]
═══════════════════════════════════════════════════════════
Has Position: {snapshot.has_position}
Position Cost: ${snapshot.position_cost:.2f}
Position Quantity: {snapshot.position_quantity}
Position P&L: {snapshot.position_pnl_pct:+.2f}%

[ACCOUNT]
═══════════════════════════════════════════════════════════
Equity: ${snapshot.account_equity:,.2f}
Buying Power: ${snapshot.account_buying_power:,.2f}
Day P&L: {snapshot.day_pnl_pct:+.2f}%

[RISK STATE]
═══════════════════════════════════════════════════════════
Consecutive Losses: {snapshot.consecutive_losses}

[MISSING FIELDS] - Be cautious if these are missing:
═══════════════════════════════════════════════════════════
{', '.join(snapshot.missing_fields) if snapshot.missing_fields else 'None'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 REQUIRED OUTPUT FORMAT (strict JSON):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{{
    "symbol": "{snapshot.symbol}",
    "proposed_action": "BUY" | "SELL" | "HOLD",
    "confidence": 0-100,
    "evidence": {{
        "trend_ok": true/false,
        "volume_ok": true/false,
        "macd_ok": true/false,
        "rsi_ok": true/false,
        "breakout_ok": true/false,
        "bb_ok": true/false,
        "buy_rule_count": 0-6
    }},
    "params": {{
        "position_size_pct": 10-40,
        "stop_loss_pct": 3.0-5.0,
        "take_profit_pct": 5.0-15.0
    }},
    "risk_level": "low" | "medium" | "high",
    "warnings": ["string", ...],
    "counter_evidence": ["string", ...],  // MUST provide at least 2 items
    "notes": "200-300 word explanation in ENGLISH ONLY, must reference input fields. Use English language only."
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ CRITICAL RULES:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. If ANY critical field is None/missing → proposed_action MUST be "HOLD" and add warning
2. If buy_rule_count < 3 → proposed_action should be "HOLD" (unless strong counter-signals)
3. MUST provide at least 2 counter_evidence items (risks, concerns, negative signals)
4. If session != "regular" → risk_level should be "high" and be more conservative
5. If confidence < 65 → proposed_action should NOT be "BUY"
6. If signal conflict (e.g., trend_ok=true but macd_ok=false and volume_ok=false) → "HOLD"
7. MUST reference actual input values in notes (e.g., "MA5={ma5_str}, RSI={rsi_str}")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌐 LANGUAGE REQUIREMENT:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️ ALL OUTPUT MUST BE IN ENGLISH:
- All "notes" field content must be in English
- All "warnings" must be in English  
- All "counter_evidence" must be in English
- Do NOT use Chinese, Japanese, or any other language
- Use English only for all text fields

Now provide your decision in strict JSON format (ALL TEXT IN ENGLISH):
"""
        return prompt
    
    def _call_deepseek(self, prompt: str) -> str:
        """Call DeepSeek API"""
        system_prompt = "You are an experienced US stock quantitative trading expert. Provide clear, actionable trading decisions in JSON format."
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            self.logger.error(f"DeepSeek API call failed: {e}")
            raise
    
    def _parse_decision(self, ai_response: str) -> Dict:
        """Parse AI decision response"""
        try:
            # Extract JSON from response
            if "```json" in ai_response.lower():
                json_start = ai_response.lower().find("```json") + 7
                json_end = ai_response.find("```", json_start)
                json_str = ai_response[json_start:json_end].strip()
            elif "```" in ai_response:
                first_tick = ai_response.find("```")
                json_start = ai_response.find("\n", first_tick) + 1
                json_end = ai_response.find("```", json_start)
                json_str = ai_response[json_start:json_end].strip()
            elif "{" in ai_response and "}" in ai_response:
                start_idx = ai_response.find('{')
                end_idx = ai_response.rfind('}') + 1
                json_str = ai_response[start_idx:end_idx]
            else:
                json_str = ai_response
            
            decision = json.loads(json_str)
            
            # Validate required fields
            required_fields = ['action', 'confidence', 'reasoning']
            for field in required_fields:
                if field not in decision:
                    raise ValueError(f"Missing required field: {field}")
            
            # Set defaults
            decision.setdefault('position_size_pct', 20)
            decision.setdefault('stop_loss_pct', 5.0)
            decision.setdefault('take_profit_pct', 10.0)
            decision.setdefault('risk_level', 'medium')
            decision.setdefault('key_price_levels', {})
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Failed to parse AI decision: {e}")
            # Return conservative decision
            return {
                'action': 'HOLD',
                'confidence': 0,
                'reasoning': f'AI response parsing failed: {str(e)}',
                'position_size_pct': 0,
                'stop_loss_pct': 5.0,
                'take_profit_pct': 10.0,
                'risk_level': 'high',
                'key_price_levels': {}
            }
    
    def _parse_proposal_v2(self, ai_response: str, snapshot) -> 'LLMProposal':
        """Parse new version of LLM output as LLMProposal"""
        from hard_decision_firewall import LLMProposal
        
        try:
            # Extract JSON
            if "```json" in ai_response.lower():
                json_start = ai_response.lower().find("```json") + 7
                json_end = ai_response.find("```", json_start)
                json_str = ai_response[json_start:json_end].strip()
            elif "```" in ai_response:
                first_tick = ai_response.find("```")
                json_start = ai_response.find("\n", first_tick) + 1
                json_end = ai_response.find("```", json_start)
                json_str = ai_response[json_start:json_end].strip()
            elif "{" in ai_response and "}" in ai_response:
                start_idx = ai_response.find('{')
                end_idx = ai_response.rfind('}') + 1
                json_str = ai_response[start_idx:end_idx]
            else:
                json_str = ai_response
            
            data = json.loads(json_str)
            
            # Validate required fields
            if 'proposed_action' not in data:
                raise ValueError("Missing 'proposed_action' field")
            if 'confidence' not in data:
                raise ValueError("Missing 'confidence' field")
            
            # Build LLMProposal
            proposal = LLMProposal(
                symbol=data.get('symbol', snapshot.symbol),
                proposed_action=data.get('proposed_action', 'HOLD'),
                confidence=int(data.get('confidence', 0)),
                evidence=data.get('evidence', {}),
                params=data.get('params', {
                    'position_size_pct': 20,
                    'stop_loss_pct': 5.0,
                    'take_profit_pct': 10.0
                }),
                risk_level=data.get('risk_level', 'medium'),
                warnings=data.get('warnings', []),
                counter_evidence=data.get('counter_evidence', []),
                notes=data.get('notes', '')
            )
            
            # Data integrity check: If there are missing fields, force HOLD
            if snapshot.missing_fields and proposal.proposed_action == "BUY":
                proposal.proposed_action = "HOLD"
                proposal.warnings.append(f"Critical indicators missing: {', '.join(snapshot.missing_fields)}")
                proposal.confidence = max(0, proposal.confidence - 20)
            
            return proposal
            
        except Exception as e:
            self.logger.error(f"Failed to parse LLM proposal: {e}")
            # Return conservative decision
            return LLMProposal(
                symbol=snapshot.symbol,
                proposed_action="HOLD",
                confidence=0,
                evidence={},
                params={},
                risk_level="high",
                warnings=[f"Parse failed: {str(e)}"],
                counter_evidence=["Data parsing error", "Unable to generate valid decision"],
                notes="LLM output parsing failed, using conservative strategy"
            )

