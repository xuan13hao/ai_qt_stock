"""
Alpaca Quantitative Trading Platform
Simplified version - Only Alpaca US Stock Trading
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import time
import os
from us_stock_trading import USStockTradingInterface, USStockTradingSimulator
from config_manager import config_manager
from alpaca_ai_decision import AlpacaAIDecision
from alpaca_strategy_manager import AlpacaStrategyManager
from alpaca_auto_trader import get_auto_trader

# Page configuration
st.set_page_config(
    page_title="Quantitative Trading Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Styles - Clean Black & White Theme
st.markdown("""
<style>
    /* Global Styles */
    .main {
        background: #ffffff;
        background-attachment: fixed;
    }
    
    .stApp {
        background: #ffffff;
    }
    
    /* Main Container */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        background: #ffffff;
        border-radius: 10px;
        margin-top: 1rem;
    }
    
    /* Top Navigation Bar */
    .top-nav {
        background: #ffffff;
        padding: 1.5rem 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        border: 2px solid #000000;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .nav-title {
        font-size: 2rem;
        font-weight: 800;
        color: #000000;
        text-align: center;
        margin: 0;
        letter-spacing: 1px;
    }
    
    .nav-subtitle {
        text-align: center;
        color: #333333;
        font-size: 0.95rem;
        margin-top: 0.5rem;
        font-weight: 400;
    }
    
    /* Button Styling */
    .stButton>button {
        background: #ffffff !important;
        color: #000000 !important;
        border: 2px solid #000000 !important;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        background: #f5f5f5 !important;
        border-color: #000000 !important;
        color: #000000 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }
    
    /* Input Field Styling */
    .stTextInput>div>div>input {
        border-radius: 8px;
        border: 2px solid #d0d0d0;
        padding: 0.75rem;
        font-size: 1rem;
        transition: border-color 0.3s ease;
        background: #ffffff;
        color: #000000;
    }
    
    .stTextInput>div>div>input:focus {
        border-color: #000000;
        box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
    }
    
    /* Metric Cards */
    .metric-card {
        background: #ffffff;
        padding: 1.5rem;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
        text-align: center;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border-top: 3px solid #000000;
        border: 1px solid #e0e0e0;
    }
    
    /* Success/Error/Warning/Info Message Boxes */
    .stSuccess {
        border-radius: 8px;
        padding: 1rem;
        background-color: #ffffff;
        border-left: 4px solid #000000;
        border: 1px solid #e0e0e0;
        color: #000000;
    }
    
    .stError {
        border-radius: 8px;
        padding: 1rem;
        background-color: #ffffff;
        border-left: 4px solid #000000;
        border: 1px solid #e0e0e0;
        color: #000000;
    }
    
    .stWarning {
        border-radius: 8px;
        padding: 1rem;
        background-color: #ffffff;
        border-left: 4px solid #000000;
        border: 1px solid #e0e0e0;
        color: #000000;
    }
    
    .stInfo {
        border-radius: 8px;
        padding: 1rem;
        background-color: #ffffff;
        border-left: 4px solid #000000;
        border: 1px solid #e0e0e0;
        color: #000000;
    }
    
    /* Hide Streamlit Default Elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def get_trading_interface():
    """Get or initialize trading interface"""
    if 'trading_interface' not in st.session_state:
        # Read config
        config = config_manager.read_env()
        alpaca_enabled = config.get('ALPACA_ENABLED', 'false').lower() == 'true'
        alpaca_api_key = config.get('ALPACA_API_KEY', '')
        alpaca_api_secret = config.get('ALPACA_API_SECRET', '')
        alpaca_paper = config.get('ALPACA_PAPER', 'true').lower() == 'true'
        
        if alpaca_enabled and alpaca_api_key and alpaca_api_secret:
            st.session_state.trading_interface = USStockTradingInterface(
                api_key=alpaca_api_key,
                api_secret=alpaca_api_secret,
                paper=alpaca_paper
            )
            # Pass parameters to ensure reading from config, not environment variables
            st.session_state.trading_interface.connect(
                api_key=alpaca_api_key,
                api_secret=alpaca_api_secret,
                paper=alpaca_paper
            )
        else:
            st.session_state.trading_interface = USStockTradingSimulator()
            st.session_state.trading_interface.connect()
    
    return st.session_state.trading_interface


def display_account_info():
    """Display account information"""
    st.header("💰 Account Information")
    
    trading = get_trading_interface()
    account_info = trading.get_account_info()
    
    if not account_info.get('success', False):
        st.error(f"❌ Failed to get account info: {account_info.get('error', 'Unknown error')}")
        return
    
    # Account metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Portfolio Value", f"${account_info.get('portfolio_value', 0):,.2f}")
    
    with col2:
        st.metric("Buying Power", f"${account_info.get('buying_power', 0):,.2f}")
    
    with col3:
        st.metric("Cash", f"${account_info.get('cash', 0):,.2f}")
    
    with col4:
        st.metric("Equity", f"${account_info.get('equity', 0):,.2f}")
    
    # Account status
    st.markdown("### Account Status")
    status_col1, status_col2, status_col3 = st.columns(3)
    
    with status_col1:
        status = account_info.get('status', 'UNKNOWN')
        status_color = "🟢" if status == "ACTIVE" else "🔴"
        st.write(f"{status_color} **Status**: {status}")
        
        pattern_day_trader = account_info.get('pattern_day_trader', False)
        pdt_status = "⚠️ Yes" if pattern_day_trader else "✅ No"
        st.write(f"**Pattern Day Trader**: {pdt_status}")
    
    with status_col2:
        trading_blocked = account_info.get('trading_blocked', False)
        blocked_status = "🔴 Yes" if trading_blocked else "✅ No"
        st.write(f"**Trading Blocked**: {blocked_status}")
        
        account_blocked = account_info.get('account_blocked', False)
        acc_blocked_status = "🔴 Yes" if account_blocked else "✅ No"
        st.write(f"**Account Blocked**: {acc_blocked_status}")
    
    with status_col3:
        # Detect trading mode
        trading = get_trading_interface()
        is_simulator = isinstance(trading, USStockTradingSimulator)
        
        if is_simulator:
            trading_mode = "🎮 Local Simulator"
            mode_desc = "Local simulator (no API required)"
        else:
            is_paper = account_info.get('paper', True)
            if is_paper:
                trading_mode = "📝 Alpaca Paper Trading"
                mode_desc = "Alpaca paper trading API"
            else:
                trading_mode = "💵 Live Trading"
                mode_desc = "Live trading (real money)"
        
        st.write(f"**Trading Mode**: {trading_mode}")
        st.caption(mode_desc)
        
        multiplier = account_info.get('multiplier', 1)
        st.write(f"**Multiplier**: {multiplier}x")


def display_positions():
    """Display positions"""
    st.header("📊 Positions")
    
    trading = get_trading_interface()
    positions = trading.get_all_positions()
    
    if not positions:
        st.info("No current positions")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(positions)
    
    # Format columns
    display_df = pd.DataFrame({
        'Symbol': df['symbol'],
        'Quantity': df['quantity'],
        'Avg Entry Price': df['avg_entry_price'].apply(lambda x: f"${x:.2f}"),
        'Current Price': df['current_price'].apply(lambda x: f"${x:.2f}"),
        'Market Value': df['market_value'].apply(lambda x: f"${x:.2f}"),
        'Cost Basis': df['cost_basis'].apply(lambda x: f"${x:.2f}"),
        'Unrealized P&L': df['unrealized_pl'].apply(lambda x: f"${x:.2f}"),
        'Unrealized P&L %': df['unrealized_plpc'].apply(lambda x: f"{x:.2f}%"),
        'Side': df['side']
    })
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Calculate totals
    total_value = df['market_value'].sum()
    total_cost = df['cost_basis'].sum()
    total_pl = df['unrealized_pl'].sum()
    total_pl_pct = (total_pl / total_cost * 100) if total_cost > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Positions", len(positions))
    col2.metric("Total Market Value", f"${total_value:,.2f}")
    col3.metric("Total Cost Basis", f"${total_cost:,.2f}")
    col4.metric("Total Unrealized P&L", f"${total_pl:,.2f}", f"{total_pl_pct:.2f}%")


def display_trading_panel():
    """Display trading panel"""
    st.header("⚡ Trading")
    
    trading = get_trading_interface()
    
    # Trading tabs
    tab1, tab2, tab3 = st.tabs(["Buy", "Sell", "🤖 AI Decision"])
    
    with tab1:
        st.markdown("### 📈 Buy Order")
        
        col1, col2 = st.columns(2)
        
        with col1:
            symbol = st.text_input("Symbol", placeholder="AAPL", key="buy_symbol").upper()
            quantity = st.number_input("Quantity", min_value=1, value=1, key="buy_quantity")
            order_type = st.selectbox("Order Type", ["market", "limit", "stop", "stop_limit"], key="buy_order_type")
        
        with col2:
            limit_price = None
            stop_price = None
            
            if order_type in ["limit", "stop_limit"]:
                limit_price = st.number_input("Limit Price", min_value=0.01, value=0.01, step=0.01, key="buy_limit_price")
            
            if order_type in ["stop", "stop_limit"]:
                stop_price = st.number_input("Stop Price", min_value=0.01, value=0.01, step=0.01, key="buy_stop_price")
            
            time_in_force = st.selectbox("Time in Force", ["day", "gtc", "ioc", "fok"], key="buy_time_in_force")
        
        if st.button("Submit Buy Order", type="primary", key="submit_buy"):
            if not symbol:
                st.error("Please enter a symbol")
            else:
                with st.spinner("Submitting order..."):
                    result = trading.buy_stock(
                        symbol=symbol,
                        quantity=int(quantity),
                        order_type=order_type,
                        limit_price=limit_price if limit_price else None,
                        stop_price=stop_price if stop_price else None,
                        time_in_force=time_in_force
                    )
                    
                    if result.get('success'):
                        st.success(f"✅ Order submitted successfully! Order ID: {result.get('order_id')}")
                        st.json(result)
                    else:
                        st.error(f"❌ Order failed: {result.get('error', 'Unknown error')}")
    
    with tab2:
        st.markdown("### 📉 Sell Order")
        
        # Get current positions
        positions = trading.get_all_positions()
        
        if not positions:
            st.info("No positions to sell")
        else:
            position_symbols = [pos['symbol'] for pos in positions]
            
            col1, col2 = st.columns(2)
            
            with col1:
                symbol = st.selectbox("Symbol", position_symbols, key="sell_symbol")
                
                # Get position info
                position = trading.get_position(symbol)
                max_quantity = position['quantity'] if position else 0
                
                quantity = st.number_input("Quantity", min_value=1, max_value=max_quantity, value=1, key="sell_quantity")
                order_type = st.selectbox("Order Type", ["market", "limit", "stop", "stop_limit"], key="sell_order_type")
            
            with col2:
                limit_price = None
                stop_price = None
                
                if order_type in ["limit", "stop_limit"]:
                    limit_price = st.number_input("Limit Price", min_value=0.01, value=0.01, step=0.01, key="sell_limit_price")
                
                if order_type in ["stop", "stop_limit"]:
                    stop_price = st.number_input("Stop Price", min_value=0.01, value=0.01, step=0.01, key="sell_stop_price")
                
                time_in_force = st.selectbox("Time in Force", ["day", "gtc", "ioc", "fok"], key="sell_time_in_force")
            
            if st.button("Submit Sell Order", type="primary", key="submit_sell"):
                with st.spinner("Submitting order..."):
                    result = trading.sell_stock(
                        symbol=symbol,
                        quantity=int(quantity),
                        order_type=order_type,
                        limit_price=limit_price if limit_price else None,
                        stop_price=stop_price if stop_price else None,
                        time_in_force=time_in_force
                    )
                    
                    if result.get('success'):
                        st.success(f"✅ Order submitted successfully! Order ID: {result.get('order_id')}")
                        st.json(result)
                    else:
                        st.error(f"❌ Order failed: {result.get('error', 'Unknown error')}")
    
    with tab3:
        st.markdown("### 🤖 AI Trading Decision")
        st.markdown("Use DeepSeek AI to analyze stocks and get autonomous trading recommendations")
        
        # Check if DeepSeek is configured
        config = config_manager.read_env()
        deepseek_api_key = config.get('DEEPSEEK_API_KEY', '')
        
        if not deepseek_api_key:
            st.warning("⚠️ DeepSeek API Key not configured. Please configure it in the Configuration page.")
            st.info("💡 Go to ⚙️ Configuration → 🤖 LLM Configuration (DeepSeek) to set up your API key")
        else:
            # Symbol input
            symbol = st.text_input("Stock Symbol", placeholder="AAPL", key="ai_symbol").upper()
            
            # Check if has position
            positions = trading.get_all_positions()
            has_position = False
            position_cost = 0
            position_quantity = 0
            
            if symbol:
                for pos in positions:
                    if pos['symbol'].upper() == symbol.upper():
                        has_position = True
                        position_cost = pos.get('avg_entry_price', 0)
                        position_quantity = pos.get('quantity', 0)
                        break
            
            if has_position:
                st.info(f"📊 Current Position: {position_quantity} shares @ ${position_cost:.2f}")
            
            # Analyze button
            if st.button("🤖 Get AI Decision", type="primary", key="ai_analyze"):
                if not symbol:
                    st.error("Please enter a stock symbol")
                else:
                    with st.spinner("AI is analyzing..."):
                        try:
                            # Get account info
                            account_info = trading.get_account_info()
                            
                            # Initialize AI decision engine
                            ai_engine = AlpacaAIDecision(
                                api_key=deepseek_api_key,
                                base_url=config.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
                            )
                            
                            # Get AI decision
                            result = ai_engine.analyze_and_decide(
                                symbol=symbol,
                                account_info=account_info,
                                has_position=has_position,
                                position_cost=position_cost,
                                position_quantity=position_quantity
                            )
                            
                            if result.get('success'):
                                decision = result['decision']
                                market_data = result.get('market_data', {})
                                
                                # Display decision
                                st.markdown("---")
                                st.markdown("### 📊 AI Decision Result")
                                
                                # Decision action
                                action = decision.get('action', 'HOLD')
                                confidence = decision.get('confidence', 0)
                                
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    if action == "BUY":
                                        st.success(f"🟢 **Action: {action}**")
                                    elif action == "SELL":
                                        st.error(f"🔴 **Action: {action}**")
                                    else:
                                        st.info(f"🟡 **Action: {action}**")
                                
                                with col2:
                                    st.metric("Confidence", f"{confidence}%")
                                
                                with col3:
                                    risk_level = decision.get('risk_level', 'medium')
                                    risk_color = {"low": "🟢", "medium": "🟡", "high": "🔴"}
                                    st.write(f"**Risk Level**: {risk_color.get(risk_level, '🟡')} {risk_level.upper()}")
                                
                                # Reasoning
                                st.markdown("### 💭 Decision Reasoning")
                                st.write(decision.get('reasoning', 'No reasoning provided'))
                                
                                # Trading parameters
                                st.markdown("### 📋 Trading Parameters")
                                param_col1, param_col2, param_col3 = st.columns(3)
                                
                                with param_col1:
                                    st.metric("Position Size", f"{decision.get('position_size_pct', 0)}%")
                                
                                with param_col2:
                                    st.metric("Stop Loss", f"-{decision.get('stop_loss_pct', 0)}%")
                                
                                with param_col3:
                                    st.metric("Take Profit", f"+{decision.get('take_profit_pct', 0)}%")
                                
                                # Key price levels
                                price_levels = decision.get('key_price_levels', {})
                                if price_levels:
                                    st.markdown("### 🎯 Key Price Levels")
                                    level_col1, level_col2, level_col3 = st.columns(3)
                                    
                                    with level_col1:
                                        if 'support' in price_levels:
                                            st.metric("Support", f"${price_levels['support']:.2f}")
                                    
                                    with level_col2:
                                        if 'resistance' in price_levels:
                                            st.metric("Resistance", f"${price_levels['resistance']:.2f}")
                                    
                                    with level_col3:
                                        if 'stop_loss' in price_levels:
                                            st.metric("Stop Loss", f"${price_levels['stop_loss']:.2f}")
                                
                                # Market data summary
                                if market_data:
                                    st.markdown("### 📈 Market Data Summary")
                                    data_col1, data_col2, data_col3, data_col4 = st.columns(4)
                                    
                                    with data_col1:
                                        st.metric("Current Price", f"${market_data.get('current_price', 0):.2f}")
                                    
                                    with data_col2:
                                        st.metric("RSI", f"{market_data.get('rsi', 0):.1f}")
                                    
                                    with data_col3:
                                        st.metric("Trend", market_data.get('trend', 'N/A').upper())
                                    
                                    with data_col4:
                                        st.metric("Volume Ratio", f"{market_data.get('volume_ratio', 0):.2f}x")
                                
                                # Auto execute option
                                st.markdown("---")
                                auto_execute = st.checkbox("🚀 Auto Execute Trade", key="auto_execute")
                                
                                if auto_execute and action in ["BUY", "SELL"]:
                                    if st.button("Execute AI Decision", type="primary", key="execute_ai"):
                                        with st.spinner("Executing trade..."):
                                            account_info = trading.get_account_info()
                                            buying_power = account_info.get('buying_power', 0)
                                            
                                            if action == "BUY":
                                                # Calculate quantity based on position size
                                                position_size_pct = decision.get('position_size_pct', 20) / 100
                                                buy_amount = buying_power * position_size_pct
                                                current_price = market_data.get('current_price', 0)
                                                quantity = int(buy_amount / current_price) if current_price > 0 else 0
                                                
                                                if quantity > 0:
                                                    trade_result = trading.buy_stock(
                                                        symbol=symbol,
                                                        quantity=quantity,
                                                        order_type='market',
                                                        time_in_force='day'
                                                    )
                                                    
                                                    if trade_result.get('success'):
                                                        st.success(f"✅ AI Buy Order Executed! Order ID: {trade_result.get('order_id')}")
                                                    else:
                                                        st.error(f"❌ Execution failed: {trade_result.get('error')}")
                                                else:
                                                    st.error("Insufficient buying power")
                                            
                                            elif action == "SELL" and has_position:
                                                # Sell all or partial position
                                                sell_quantity = position_quantity  # Can modify to sell partial
                                                
                                                trade_result = trading.sell_stock(
                                                    symbol=symbol,
                                                    quantity=sell_quantity,
                                                    order_type='market',
                                                    time_in_force='day'
                                                )
                                                
                                                if trade_result.get('success'):
                                                    st.success(f"✅ AI Sell Order Executed! Order ID: {trade_result.get('order_id')}")
                                                else:
                                                    st.error(f"❌ Execution failed: {trade_result.get('error')}")
                            
                            else:
                                st.error(f"❌ AI Decision failed: {result.get('error', 'Unknown error')}")
                        
                        except Exception as e:
                            st.error(f"❌ Error: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())


def display_ai_decision():
    """Display AI Decision page"""
    st.header("🤖 AI Trading Decision")
    st.markdown("Use DeepSeek AI to analyze stocks and get autonomous trading recommendations")
    
    # Check if DeepSeek is configured
    config = config_manager.read_env()
    deepseek_api_key = config.get('DEEPSEEK_API_KEY', '')
    
    if not deepseek_api_key:
        st.warning("⚠️ DeepSeek API Key not configured. Please configure it in the Configuration page.")
        st.info("💡 Go to ⚙️ Configuration → 🤖 LLM Configuration (DeepSeek) to set up your API key")
        return
    
    trading = get_trading_interface()
    
    # Symbol input
    col1, col2 = st.columns([3, 1])
    with col1:
        symbol = st.text_input("Stock Symbol", placeholder="AAPL", key="ai_symbol").upper()
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
    
    if not symbol:
        st.info("💡 Enter a stock symbol to get AI trading decision")
        return
    
    # Check if has position
    positions = trading.get_all_positions()
    has_position = False
    position_cost = 0
    position_quantity = 0
    
    for pos in positions:
        if pos['symbol'].upper() == symbol.upper():
            has_position = True
            position_cost = pos.get('avg_entry_price', 0)
            position_quantity = pos.get('quantity', 0)
            break
    
    if has_position:
        current_price = pos.get('current_price', position_cost)
        profit_loss = (current_price - position_cost) * position_quantity
        profit_loss_pct = ((current_price - position_cost) / position_cost * 100) if position_cost > 0 else 0
        
        st.info(f"📊 **Current Position**: {position_quantity} shares @ ${position_cost:.2f} | "
                f"Current: ${current_price:.2f} | "
                f"P&L: ${profit_loss:,.2f} ({profit_loss_pct:+.2f}%)")
    
    # Analyze button
    if st.button("🤖 Get AI Decision", type="primary", key="ai_analyze", use_container_width=True):
        with st.spinner("AI is analyzing market data and making decision..."):
            try:
                # Get account info
                account_info = trading.get_account_info()
                
                if not account_info.get('success'):
                    st.error(f"Failed to get account info: {account_info.get('error')}")
                    return
                
                # Initialize AI decision engine
                ai_engine = AlpacaAIDecision(
                    api_key=deepseek_api_key,
                    base_url=config.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
                )
                
                # Get AI decision
                result = ai_engine.analyze_and_decide(
                    symbol=symbol,
                    account_info=account_info,
                    has_position=has_position,
                    position_cost=position_cost,
                    position_quantity=position_quantity
                )
                
                if result.get('success'):
                    decision = result['decision']
                    market_data = result.get('market_data', {})
                    
                    # Display decision
                    st.markdown("---")
                    st.markdown("### 📊 AI Decision Result")
                    
                    # Decision action
                    action = decision.get('action', 'HOLD')
                    confidence = decision.get('confidence', 0)
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        if action == "BUY":
                            st.success(f"🟢 **Action: {action}**")
                        elif action == "SELL":
                            st.error(f"🔴 **Action: {action}**")
                        else:
                            st.info(f"🟡 **Action: {action}**")
                    
                    with col2:
                        st.metric("Confidence", f"{confidence}%")
                    
                    with col3:
                        risk_level = decision.get('risk_level', 'medium')
                        risk_color = {"low": "🟢", "medium": "🟡", "high": "🔴"}
                        st.write(f"**Risk Level**: {risk_color.get(risk_level, '🟡')} {risk_level.upper()}")
                    
                    # Reasoning
                    st.markdown("### 💭 Decision Reasoning")
                    st.write(decision.get('reasoning', 'No reasoning provided'))
                    
                    # Trading parameters
                    st.markdown("### 📋 Trading Parameters")
                    param_col1, param_col2, param_col3 = st.columns(3)
                    
                    with param_col1:
                        st.metric("Position Size", f"{decision.get('position_size_pct', 0)}%")
                    
                    with param_col2:
                        st.metric("Stop Loss", f"-{decision.get('stop_loss_pct', 0)}%")
                    
                    with param_col3:
                        st.metric("Take Profit", f"+{decision.get('take_profit_pct', 0)}%")
                    
                    # Key price levels
                    price_levels = decision.get('key_price_levels', {})
                    if price_levels:
                        st.markdown("### 🎯 Key Price Levels")
                        level_col1, level_col2, level_col3 = st.columns(3)
                        
                        with level_col1:
                            if 'support' in price_levels:
                                st.metric("Support", f"${price_levels['support']:.2f}")
                        
                        with level_col2:
                            if 'resistance' in price_levels:
                                st.metric("Resistance", f"${price_levels['resistance']:.2f}")
                        
                        with level_col3:
                            if 'stop_loss' in price_levels:
                                st.metric("Stop Loss", f"${price_levels['stop_loss']:.2f}")
                    
                    # Market data summary
                    if market_data:
                        st.markdown("### 📈 Market Data Summary")
                        data_col1, data_col2, data_col3, data_col4 = st.columns(4)
                        
                        with data_col1:
                            st.metric("Current Price", f"${market_data.get('current_price', 0):.2f}")
                        
                        with data_col2:
                            st.metric("RSI", f"{market_data.get('rsi', 0):.1f}")
                        
                        with data_col3:
                            st.metric("Trend", market_data.get('trend', 'N/A').upper())
                        
                        with data_col4:
                            st.metric("Volume Ratio", f"{market_data.get('volume_ratio', 0):.2f}x")
                    
                    # Auto execute option
                    st.markdown("---")
                    st.markdown("### 🚀 Auto Execute Trade")
                    auto_execute = st.checkbox("Enable Auto Execute", key="auto_execute")
                    
                    if auto_execute and action in ["BUY", "SELL"]:
                        st.warning("⚠️ Auto execution will place real orders. Please confirm:")
                        
                        if action == "BUY":
                            # Calculate quantity based on position size
                            position_size_pct = decision.get('position_size_pct', 20) / 100
                            buying_power = account_info.get('buying_power', 0)
                            buy_amount = buying_power * position_size_pct
                            current_price = market_data.get('current_price', 0)
                            quantity = int(buy_amount / current_price) if current_price > 0 else 0
                            
                            st.info(f"Will buy {quantity} shares of {symbol} (${buy_amount:,.2f})")
                            
                            if st.button("Confirm Buy", type="primary", key="confirm_buy"):
                                with st.spinner("Executing buy order..."):
                                    trade_result = trading.buy_stock(
                                        symbol=symbol,
                                        quantity=quantity,
                                        order_type='market',
                                        time_in_force='day'
                                    )
                                    
                                    if trade_result.get('success'):
                                        st.success(f"✅ AI Buy Order Executed! Order ID: {trade_result.get('order_id')}")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Execution failed: {trade_result.get('error')}")
                        
                        elif action == "SELL" and has_position:
                            # Sell all position
                            st.info(f"Will sell {position_quantity} shares of {symbol}")
                            
                            if st.button("Confirm Sell", type="primary", key="confirm_sell"):
                                with st.spinner("Executing sell order..."):
                                    trade_result = trading.sell_stock(
                                        symbol=symbol,
                                        quantity=position_quantity,
                                        order_type='market',
                                        time_in_force='day'
                                    )
                                    
                                    if trade_result.get('success'):
                                        st.success(f"✅ AI Sell Order Executed! Order ID: {trade_result.get('order_id')}")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Execution failed: {trade_result.get('error')}")
                
                else:
                    st.error(f"❌ AI Decision failed: {result.get('error', 'Unknown error')}")
            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())


def display_orders():
    """Display orders"""
    st.header("📋 Orders")
    
    trading = get_trading_interface()
    
    # Order status filter
    status_filter = st.selectbox("Filter by Status", ["open", "closed", "all"], index=0)
    
    # Refresh button
    if st.button("🔄 Refresh Orders"):
        st.rerun()
    
    orders = trading.get_orders(status=status_filter, limit=50)
    
    if not orders:
        st.info("No orders found")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(orders)
    
    # Format columns
    display_df = pd.DataFrame({
        'Order ID': df['id'],
        'Symbol': df['symbol'],
        'Side': df['side'].str.upper(),
        'Quantity': df['quantity'],
        'Type': df['type'].str.upper(),
        'Status': df['status'].str.upper(),
        'Filled Qty': df['filled_qty'],
        'Filled Avg Price': df['filled_avg_price'].apply(lambda x: f"${x:.2f}" if x else "N/A"),
        'Limit Price': df['limit_price'].apply(lambda x: f"${x:.2f}" if x else "N/A"),
        'Stop Price': df['stop_price'].apply(lambda x: f"${x:.2f}" if x else "N/A"),
        'Time in Force': df['time_in_force'].str.upper(),
        'Submitted At': df['submitted_at']
    })
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Cancel order section
    st.markdown("### Cancel Order")
    open_orders = [o for o in orders if o['status'] == 'open']
    
    if open_orders:
        order_options = [f"{o['symbol']} - {o['side'].upper()} {o['quantity']} @ {o['type'].upper()} (ID: {o['id']})" 
                        for o in open_orders]
        selected_order = st.selectbox("Select Order to Cancel", order_options)
        
        if st.button("Cancel Order", type="primary"):
            order_id = open_orders[order_options.index(selected_order)]['id']
            with st.spinner("Canceling order..."):
                result = trading.cancel_order(order_id)
                if result.get('success'):
                    st.success(f"✅ Order {order_id} canceled successfully")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to cancel order: {result.get('error', 'Unknown error')}")
    else:
        st.info("No open orders to cancel")


def display_strategies():
    """Display strategies management page"""
    st.header("🎯 Trading Strategies")
    st.markdown("Manage trading strategies and automatic trading")
    
    trading = get_trading_interface()
    strategy_manager = AlpacaStrategyManager(trading)
    strategy_manager.set_trading_interface(trading)
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Strategy Tasks", 
        "🤖 AI Auto Trading", 
        "🛡️ Stop Loss/Take Profit",
        "📝 Trade Records",
        "📈 Trading Signals"
    ])
    
    with tab1:
        st.markdown("### Strategy Tasks Management")
        
        # Add new strategy task
        with st.expander("➕ Add New Strategy Task", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                strategy_name = st.selectbox(
                    "Strategy Type",
                    ["ai_decision", "low_price_bull", "custom"],
                    key="new_strategy_type"
                )
                symbol = st.text_input("Stock Symbol", placeholder="AAPL", key="new_strategy_symbol").upper()
            
            with col2:
                auto_trade = st.checkbox("Enable Auto Trading", key="new_auto_trade")
                check_interval = st.number_input("Check Interval (minutes)", min_value=1, value=5, key="new_check_interval")
            
            if st.button("Add Strategy Task", type="primary", key="add_strategy_task"):
                if not symbol:
                    st.error("Please enter a stock symbol")
                else:
                    config = {
                        'auto_trade': auto_trade,
                        'check_interval': check_interval
                    }
                    success, message = strategy_manager.add_strategy_task(
                        strategy_name=strategy_name,
                        symbol=symbol,
                        config=config
                    )
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
        
        # Display active tasks
        st.markdown("### Active Strategy Tasks")
        tasks = strategy_manager.get_active_tasks()
        
        if not tasks:
            st.info("No active strategy tasks")
        else:
            df = pd.DataFrame(tasks)
            display_df = pd.DataFrame({
                'Strategy': df['strategy_name'],
                'Symbol': df['symbol'],
                'Status': df['status'],
                'Created': pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')
            })
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Remove task
            if st.button("🗑️ Remove Selected Task", key="remove_task"):
                selected_idx = st.selectbox("Select Task to Remove", range(len(tasks)), 
                                          format_func=lambda x: f"{tasks[x]['strategy_name']} - {tasks[x]['symbol']}")
                if selected_idx is not None:
                    task = tasks[selected_idx]
                    success, message = strategy_manager.remove_strategy_task(
                        task['strategy_name'],
                        task['symbol']
                    )
                    if success:
                        st.success(f"✅ {message}")
                        st.rerun()
                    else:
                        st.error(f"❌ {message}")
    
    with tab2:
        st.markdown("### 🤖 AI Auto Trading")
        
        # Auto trader status
        auto_trader = get_auto_trader(trading)
        
        col1, col2 = st.columns(2)
        with col1:
            if auto_trader.running:
                st.success("🟢 Auto Trading: **Running**")
                if st.button("⏹️ Stop Auto Trading", type="primary"):
                    auto_trader.stop()
                    st.success("✅ Auto trading stopped")
                    st.rerun()
            else:
                st.info("⚪ Auto Trading: **Stopped**")
                if st.button("▶️ Start Auto Trading", type="primary"):
                    auto_trader.start()
                    st.success("✅ Auto trading started")
                    st.rerun()
        
        with col2:
            check_interval = st.number_input("Check Interval (seconds)", min_value=60, value=300, step=60)
            auto_trader.check_interval = check_interval
        
        st.markdown("---")
        st.markdown("### Manual AI Strategy Execution")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            symbol = st.text_input("Stock Symbol", placeholder="AAPL", key="manual_ai_symbol").upper()
        with col2:
            auto_execute = st.checkbox("Auto Execute", key="manual_ai_auto")
        
        if st.button("🤖 Execute AI Strategy", type="primary", key="execute_ai_strategy"):
            if not symbol:
                st.error("Please enter a stock symbol")
            else:
                with st.spinner("Executing AI strategy..."):
                    result = strategy_manager.execute_ai_strategy(
                        symbol=symbol,
                        auto_trade=auto_execute
                    )
                    
                    if result.get('success'):
                        decision = result.get('decision', {})
                        st.success(f"✅ AI Strategy executed successfully")
                        
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Action", decision.get('action', 'N/A'))
                        with col2:
                            st.metric("Confidence", f"{decision.get('confidence', 0)}%")
                        with col3:
                            st.metric("Risk Level", decision.get('risk_level', 'N/A').upper())
                        
                        st.markdown("**Reasoning:**")
                        st.write(decision.get('reasoning', 'No reasoning provided'))
                        
                        if auto_execute and result.get('execution_result'):
                            exec_result = result.get('execution_result')
                            if exec_result.get('success'):
                                st.success(f"✅ Trade executed: {exec_result.get('action')}")
                            else:
                                st.error(f"❌ Trade execution failed: {exec_result.get('error')}")
                    else:
                        st.error(f"❌ AI Strategy failed: {result.get('error')}")
    
    with tab3:
        st.markdown("### 🛡️ Stop Loss / Take Profit Monitoring")
        
        # Check stop loss/take profit
        if st.button("🔍 Check Stop Loss/Take Profit", type="primary"):
            with st.spinner("Checking positions..."):
                signals = strategy_manager.check_stop_loss_take_profit()
                
                if not signals:
                    st.success("✅ No stop loss or take profit signals triggered")
                else:
                    st.warning(f"⚠️ Found {len(signals)} signal(s)")
                    
                    for signal in signals:
                        with st.expander(f"{signal['symbol']} - {signal['action']}"):
                            st.write(f"**Reason:** {signal['reason']}")
                            st.write(f"**Current Price:** ${signal.get('current_price', 0):.2f}")
                            st.write(f"**Cost Price:** ${signal.get('cost_price', 0):.2f}")
                            st.write(f"**P&L:** {signal.get('profit_loss_pct', 0):+.2f}%")
                            
                            if st.button(f"Execute {signal['action']}", key=f"execute_{signal['symbol']}"):
                                positions = trading.get_all_positions()
                                position_quantity = 0
                                
                                for pos in positions:
                                    if pos['symbol'].upper() == signal['symbol'].upper():
                                        position_quantity = pos.get('quantity', 0)
                                        break
                                
                                if position_quantity > 0:
                                    result = trading.sell_stock(
                                        symbol=signal['symbol'],
                                        quantity=position_quantity,
                                        order_type='market',
                                        time_in_force='day'
                                    )
                                    
                                    if result.get('success'):
                                        st.success(f"✅ Sell order executed")
                                        st.rerun()
                                    else:
                                        st.error(f"❌ Sell failed: {result.get('error')}")
        
        # Display monitored positions
        st.markdown("### Monitored Positions")
        monitored_positions = strategy_manager.get_monitored_positions()
        
        if not monitored_positions:
            st.info("No monitored positions")
        else:
            df = pd.DataFrame(monitored_positions)
            display_df = pd.DataFrame({
                'Symbol': df['symbol'],
                'Quantity': df['quantity'],
                'Cost Price': df['cost_price'].apply(lambda x: f"${x:.2f}"),
                'Stop Loss': df['stop_loss_pct'].apply(lambda x: f"-{x}%"),
                'Take Profit': df['take_profit_pct'].apply(lambda x: f"+{x}%"),
                'Holding Days': df['holding_days'],
                'Strategy': df['strategy_name']
            })
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    with tab4:
        st.markdown("### 📝 Trade Records")
        
        # Filter
        col1, col2 = st.columns(2)
        with col1:
            filter_symbol = st.text_input("Filter by Symbol", key="filter_symbol").upper()
        with col2:
            limit = st.number_input("Limit", min_value=10, max_value=500, value=100, key="trade_limit")
        
        records = strategy_manager.get_trade_records(
            symbol=filter_symbol if filter_symbol else None,
            limit=limit
        )
        
        if not records:
            st.info("No trade records found")
        else:
            df = pd.DataFrame(records)
            display_df = pd.DataFrame({
                'Time': pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S'),
                'Symbol': df['symbol'],
                'Type': df['trade_type'],
                'Quantity': df['quantity'],
                'Price': df['price'].apply(lambda x: f"${x:.2f}"),
                'Amount': df['amount'].apply(lambda x: f"${x:,.2f}"),
                'Order ID': df['order_id'],
                'Strategy': df['strategy_name']
            })
            st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    with tab5:
        st.markdown("### 📈 Trading Signals")
        
        signals = strategy_manager.get_recent_signals(limit=50)
        
        if not signals:
            st.info("No trading signals found")
        else:
            df = pd.DataFrame(signals)
            display_df = pd.DataFrame({
                'Time': pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M:%S'),
                'Symbol': df['symbol'],
                'Type': df['signal_type'],
                'Action': df['action'],
                'Confidence': df['confidence'].apply(lambda x: f"{x}%" if pd.notna(x) else "N/A"),
                'Executed': df['executed'].apply(lambda x: "✅" if x else "⏳")
            })
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # View signal details
            selected_idx = st.selectbox("View Signal Details", range(len(signals)),
                                       format_func=lambda x: f"{signals[x]['symbol']} - {signals[x]['action']} - {signals[x]['created_at']}")
            if selected_idx is not None:
                signal = signals[selected_idx]
                st.json({
                    'Symbol': signal['symbol'],
                    'Type': signal['signal_type'],
                    'Action': signal['action'],
                    'Reason': signal.get('reason'),
                    'Confidence': signal.get('confidence'),
                    'Time': signal['created_at']
                })


def display_config():
    """Display configuration"""
    st.header("⚙️ Configuration")
    
    config_info = config_manager.get_config_info()
    
    # Use session_state to save temporary config
    if 'temp_config' not in st.session_state:
        st.session_state.temp_config = {key: info["value"] for key, info in config_info.items()}
    
    # Create tabs for different configurations
    tab1, tab2 = st.tabs(["🤖 LLM Configuration (DeepSeek)", "📈 Alpaca Trading Configuration"])
    
    # Tab 1: LLM Configuration
    with tab1:
        st.markdown("### 🤖 DeepSeek API Configuration")
        st.markdown("Configure DeepSeek API for AI features. Get API keys from https://platform.deepseek.com")
        
        # DeepSeek API Key
        deepseek_api_key_info = config_info.get("DEEPSEEK_API_KEY", {"description": "DeepSeek API Key", "value": ""})
        current_deepseek_api_key = st.session_state.temp_config.get("DEEPSEEK_API_KEY", "")
        
        new_deepseek_api_key = st.text_input(
            f"🔑 {deepseek_api_key_info['description']} {'*' if deepseek_api_key_info.get('required', False) else ''}",
            value=current_deepseek_api_key,
            type="password",
            help="Get API key from https://platform.deepseek.com",
            key="input_deepseek_api_key"
        )
        st.session_state.temp_config["DEEPSEEK_API_KEY"] = new_deepseek_api_key
        
        # Display current status
        if new_deepseek_api_key:
            masked_key = new_deepseek_api_key[:8] + "*" * (len(new_deepseek_api_key) - 12) + new_deepseek_api_key[-4:] if len(new_deepseek_api_key) > 12 else "***"
            st.success(f"✅ API key set: {masked_key}")
        else:
            st.warning("⚠️ API key not set")
        
        st.markdown("---")
        
        # DeepSeek Base URL
        deepseek_base_url_info = config_info.get("DEEPSEEK_BASE_URL", {"description": "DeepSeek API Base URL", "value": "https://api.deepseek.com/v1"})
        current_deepseek_base_url = st.session_state.temp_config.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        
        new_deepseek_base_url = st.text_input(
            f"🌐 {deepseek_base_url_info['description']}",
            value=current_deepseek_base_url,
            help="Default: https://api.deepseek.com/v1\n\nOther options:\n- SiliconFlow: https://api.siliconflow.cn/v1\n- Volcano Engine: https://ark.cn-beijing.volces.com/api/v3\n- Alibaba: https://dashscope.aliyuncs.com/compatible-mode/v1",
            key="input_deepseek_base_url"
        )
        st.session_state.temp_config["DEEPSEEK_BASE_URL"] = new_deepseek_base_url
        
        st.info("💡 How to get DeepSeek API key?\n\n1. Visit https://platform.deepseek.com\n2. Register/Login account\n3. Go to API key management page\n4. Create new API key\n5. Copy key and paste into input box above")
    
    # Tab 2: Alpaca Configuration
    with tab2:
        st.markdown("### 📈 Alpaca US Stock Trading Configuration")
        st.markdown("Configure Alpaca Markets API for US stock trading. Get API keys from https://alpaca.markets")
    
    # Enable switch
    alpaca_enabled_info = config_info.get("ALPACA_ENABLED", {"description": "Enable Alpaca US Stock Trading", "value": "false"})
    current_alpaca_enabled = st.session_state.temp_config.get("ALPACA_ENABLED", "false") == "true"
    
    new_alpaca_enabled = st.checkbox(
        "Enable Alpaca US Stock Trading",
        value=current_alpaca_enabled,
        help="When enabled, US stock trading features can be used",
        key="input_alpaca_enabled"
    )
    st.session_state.temp_config["ALPACA_ENABLED"] = "true" if new_alpaca_enabled else "false"
    
    # Paper trading switch
    alpaca_paper_info = config_info.get("ALPACA_PAPER", {"description": "Paper Trading Mode", "value": "true"})
    current_alpaca_paper = st.session_state.temp_config.get("ALPACA_PAPER", "true") == "true"
    
    new_alpaca_paper = st.checkbox(
        "Paper Trading (Recommended for Testing)",
        value=current_alpaca_paper,
        disabled=not new_alpaca_enabled,
        help="Paper trading uses virtual money for testing. Uncheck for live trading.",
        key="input_alpaca_paper"
    )
    st.session_state.temp_config["ALPACA_PAPER"] = "true" if new_alpaca_paper else "false"
    
    # API credentials
    col1, col2 = st.columns(2)
    
    with col1:
        alpaca_api_key_info = config_info.get("ALPACA_API_KEY", {"description": "Alpaca API Key", "value": ""})
        current_alpaca_api_key = st.session_state.temp_config.get("ALPACA_API_KEY", "")
        
        new_alpaca_api_key = st.text_input(
            f"🔑 {alpaca_api_key_info['description']}",
            value=current_alpaca_api_key,
            type="password",
            disabled=not new_alpaca_enabled,
            help="Get API key from https://alpaca.markets",
            key="input_alpaca_api_key"
        )
        st.session_state.temp_config["ALPACA_API_KEY"] = new_alpaca_api_key
    
    with col2:
        alpaca_api_secret_info = config_info.get("ALPACA_API_SECRET", {"description": "Alpaca API Secret", "value": ""})
        current_alpaca_api_secret = st.session_state.temp_config.get("ALPACA_API_SECRET", "")
        
        new_alpaca_api_secret = st.text_input(
            f"🔐 {alpaca_api_secret_info['description']}",
            value=current_alpaca_api_secret,
            type="password",
            disabled=not new_alpaca_enabled,
            help="Get API secret from https://alpaca.markets",
            key="input_alpaca_api_secret"
        )
        st.session_state.temp_config["ALPACA_API_SECRET"] = new_alpaca_api_secret
    
    if new_alpaca_enabled:
        if new_alpaca_api_key and new_alpaca_api_secret:
            trading_mode = "Paper Trading" if new_alpaca_paper else "Live Trading"
            st.success(f"✅ Alpaca Enabled - {trading_mode}")
        else:
            st.warning("⚠️ Please enter both API Key and API Secret")
    else:
        st.info("ℹ️ Alpaca Not Enabled - Using simulation mode")
    
    st.info("💡 How to get Alpaca API keys?\n\n1. Visit https://alpaca.markets\n2. Sign up for a free account\n3. Go to Dashboard > API Keys\n4. Create new API key\n5. Copy Key ID and Secret Key\n6. Paste into input boxes above")
    
    st.warning("⚠️ Warning: Live trading involves real money operations, please test with paper trading first!")
    
    # Save button (outside tabs, applies to all configs)
    st.markdown("---")
    if st.button("💾 Save All Configuration", type="primary"):
        try:
            # Read current config
            current_config = config_manager.read_env()
            
            # Update all configs from temp_config
            for key, value in st.session_state.temp_config.items():
                if key in ["DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", 
                          "ALPACA_ENABLED", "ALPACA_API_KEY", "ALPACA_API_SECRET", "ALPACA_PAPER"]:
                    current_config[key] = value
            
            # Save configuration
            config_manager.write_env(current_config)
            
            st.success("✅ Configuration saved successfully!")
            st.info("ℹ️ Please refresh the page or restart the application to apply changes")
            
            # Reset trading interface
            if 'trading_interface' in st.session_state:
                del st.session_state.trading_interface
            
            st.rerun()
        except Exception as e:
            st.error(f"❌ Failed to save configuration: {e}")


def main():
    # Top title bar
    st.markdown("""
    <div class="top-nav">
        <h1 class="nav-title"> Quantitative Trading Platform</h1>
    </div>
    """, unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("### 🔍 Navigation")
        
        page = st.radio(
            "Select Page",
            ["💰 Account", "📊 Positions", "⚡ Trading", "📋 Orders", "🤖 AI Decision", "🎯 Strategies", "⚙️ Configuration"],
            key="main_nav"
        )
        
        st.markdown("---")
        
        # Connection status and trading mode
        trading = get_trading_interface()
        if trading.connected:
            st.success("✅ Connected")
        else:
            st.warning("⚠️ Not Connected")
        
        # Trading mode detection
        account_info = trading.get_account_info()
        if account_info.get('success'):
            # Check if using simulator or Alpaca
            is_simulator = isinstance(trading, USStockTradingSimulator)
            
            if is_simulator:
                st.info("🎮 **Local Simulator Mode**\n\nNo API required, completely virtual trading\nInitial capital: $100,000")
            else:
                is_paper = account_info.get('paper', True)
                if is_paper:
                    st.info("📝 **Alpaca Paper Trading**\n\nUsing Alpaca Paper Trading API\nVirtual funds, risk-free")
                else:
                    st.warning("💵 **Live Trading Mode**\n\n⚠️ Using real money\nPlease operate with caution!")
        
        st.markdown("---")
        
        # Help
        with st.expander("💡 Usage Help"):
            st.markdown("""
            **Trading Modes**
            
            🎮 **Local Simulator** (Current Default)
            - No API configuration required, ready to use
            - Initial capital: $100,000
            - Completely virtual trading, risk-free
            - Perfect for learning and testing strategies
            
            📝 **Alpaca Paper Trading**
            - Requires Alpaca API key configuration
            - Uses Alpaca Paper Trading API
            - Closer to real market conditions
            - Enable in Configuration page
            
            **Symbol Format**
            - US stocks: Letter codes (e.g., AAPL, TSLA, MSFT)
            
            **Order Types**
            - **Market**: Execute immediately at current market price
            - **Limit**: Execute only at specified price or better
            - **Stop**: Trigger when price reaches stop price
            - **Stop-Limit**: Combination of stop and limit orders
            
            **Time in Force**
            - **Day**: Order expires at end of trading day
            - **GTC**: Good till canceled
            - **IOC**: Immediate or cancel
            - **FOK**: Fill or kill
            
            **Trading Hours**
            - Regular Market: 9:30 AM - 4:00 PM ET
            - Pre-Market: 4:00 AM - 9:30 AM ET
            - After-Hours: 4:00 PM - 8:00 PM ET
            """)
    
    # Main content
    if page == "💰 Account":
        display_account_info()
    elif page == "📊 Positions":
        display_positions()
    elif page == "⚡ Trading":
        display_trading_panel()
    elif page == "📋 Orders":
        display_orders()
    elif page == "🤖 AI Decision":
        display_ai_decision()
    elif page == "🎯 Strategies":
        display_strategies()
    elif page == "⚙️ Configuration":
        display_config()


if __name__ == "__main__":
    main()

