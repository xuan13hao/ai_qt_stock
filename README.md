# Quantitative Trading Platform

An AI-powered quantitative trading platform for US stocks using Alpaca Markets API and DeepSeek LLM for intelligent trading decisions.

## 📹 Project Demo

Watch the demo video to see the platform in action:

[![Watch the demo](video/demo.png)](
https://youtu.be/-yE2kslwVh4)



## 🚀 Features

### Core Functionality

- **💰 Account Management** - Real-time account information, portfolio value, buying power, and equity tracking
- **📊 Position Management** - View all positions with real-time P&L, entry prices, and market values
- **⚡ Order Management** - Place buy/sell orders with multiple order types (market, limit, stop, stop-limit)
- **🤖 AI Trading Decisions** - DeepSeek LLM-powered analysis providing buy/sell/hold recommendations with confidence scores
- **🎯 Strategy Management** - Create, manage, and execute trading strategies with automated monitoring
- **🔄 Auto Trading** - Automated trading execution based on AI decisions and strategy rules
- **🛡️ Risk Management** - Stop loss and take profit monitoring with automatic alerts
- **📋 Trade Records** - Complete history of all trades and trading signals
- **⚙️ Configuration** - Easy web-based configuration for API keys and trading settings

### Trading Modes

1. **🎮 Local Simulator** (Default)
   - No API required, works out of the box
   - Initial capital: $100,000
   - Completely virtual, risk-free for testing
   - Perfect for learning and strategy development

2. **📝 Alpaca Paper Trading**
   - Uses Alpaca Paper Trading API
   - Virtual money, real market conditions
   - Test strategies with realistic market data
   - Requires Alpaca account (free)

3. **💵 Live Trading**
   - Real money, real orders
   - Full Alpaca Markets integration
   - Use with caution - real financial risk

## 📋 Requirements

- Python 3.8+ (recommended 3.12)
- Stable internet connection
- DeepSeek API Key (for AI features)
- Alpaca API Key (optional, for paper/live trading)

## 🔧 Installation

### 1. Clone the Repository

```bash
git clone https://github.com/xuan13hao/ai_qt_stock.git
cd ai_qt_stock
```

Edit `.env` file and configure your API keys:

```env
# DeepSeek API (Required for AI features)
DEEPSEEK_API_KEY=your_deepseek_api_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# Alpaca API (Optional, for paper/live trading)
ALPACA_ENABLED=false
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_API_SECRET=your_alpaca_api_secret_here
ALPACA_PAPER=true  # true for paper trading, false for live trading
```

### 2. Run the Application

```bash
# Using the run script
python run.py

# Or directly with Streamlit
streamlit run app.py --server.port 8503
```

## 🐳 Docker Deployment

### Using Docker Compose (Recommended)

```bash
docker-compose up -d
```

### Using Dockerfile

```bash
# Build the image
docker build -t alpaca-trading-platform .

# Run the container
docker run -d -p 8503:8501 \
  -v $(pwd)/.env:/app/.env \
  --name alpaca-trading \
  alpaca-trading-platform
```


## 📖 Usage Guide

### Getting Started

1. **Configure API Keys**
   - Navigate to "⚙️ Configuration" in the sidebar
   - Enter your API keys (see [Getting API Keys](#-getting-api-keys) section below)
   - Click "💾 Save All Configuration"

2. **View Account Information**
   - Click "💰 Account" in the sidebar
   - View your portfolio value, buying power, cash, and equity
   - Check account status and trading mode

3. **Place Orders**
   - Navigate to "⚡ Trading"
   - Choose Buy or Sell tab
   - Enter stock symbol (e.g., AAPL, TSLA, MSFT)
   - Select order type (market, limit, stop, stop-limit)
   - Enter quantity and submit order

### AI Trading Decisions

1. **Get AI Recommendation**
   - Navigate to "🤖 AI Decision" or use the "🤖 AI Decision" tab in Trading
   - Enter a stock symbol
   - Click "🤖 Get AI Decision"
   - Review the AI analysis:
     - Action (BUY/SELL/HOLD)
     - Confidence level
     - Risk assessment
     - Reasoning and analysis
     - Trading parameters (position size, stop loss, take profit)
     - Key price levels (support, resistance)

2. **Auto Execute Trade**
   - Enable "Auto Execute Trade" checkbox
   - Review the decision details
   - Click "Execute AI Decision" to place the order automatically

### Strategy Management

1. **Add Strategy Task**
   - Navigate to "🎯 Strategies"
   - Click "➕ Add New Strategy Task"
   - Select strategy type (ai_decision, low_price_bull, custom)
   - Enter stock symbol
   - Configure check interval and auto trading
   - Click "Add Strategy Task"

2. **Auto Trading**
   - Enable "AI Auto Trading" in the Strategies page
   - Start auto trading service
   - System will automatically check and execute trades based on strategies
   - Configure check interval (default: 300 seconds)

3. **Stop Loss / Take Profit**
   - Navigate to "🛡️ Stop Loss/Take Profit" tab
   - Click "🔍 Check Stop Loss/Take Profit"
   - System will check all positions and alert if triggers are hit
   - Manually execute sell orders from the alert list

### Order Types

- **Market Order** - Execute immediately at current market price
- **Limit Order** - Execute only at specified price or better
- **Stop Order** - Trigger when price reaches stop price
- **Stop-Limit Order** - Combination of stop and limit orders

### Time in Force Options

- **Day** - Order expires at end of trading day
- **GTC** - Good till canceled (remains active until filled or canceled)
- **IOC** - Immediate or cancel (fill immediately or cancel)
- **FOK** - Fill or kill (fill completely or cancel)

## 🔑 Getting API Keys

### DeepSeek API Key

1. Visit https://platform.deepseek.com
2. Register/Login to your account
3. Navigate to API key management
4. Create a new API key
5. Copy the key and paste it into the configuration

### Alpaca API Keys

1. Visit https://alpaca.markets
2. Sign up for a free account
3. Go to Dashboard → API Keys
4. Create new API key (for paper trading)
5. Copy Key ID and Secret Key
6. Paste into configuration

**Important**: Start with paper trading to test strategies before using live trading!

## 📁 Project Structure

```
aiagents-stock/
├── app.py                      # Main Streamlit application
├── us_stock_trading.py         # Alpaca trading interface
├── alpaca_ai_decision.py       # AI decision engine (DeepSeek)
├── alpaca_strategy_manager.py  # Strategy management
├── alpaca_auto_trader.py       # Auto trading service
├── config_manager.py           # Configuration management
├── run.py                      # Application launcher
├── requirements.txt            # Python dependencies
├── env_example.txt             # Environment configuration template
├── Dockerfile                  # Docker image definition
├── docker-compose.yml          # Docker Compose configuration
└── README.md                   # This file
```

## 🛠️ Technology Stack

- **Frontend**: Streamlit
- **Trading API**: Alpaca Markets API
- **AI/LLM**: DeepSeek API
- **Data Source**: Yahoo Finance (yfinance)
- **Technical Analysis**: TA-Lib (ta library)
- **Database**: SQLite
- **Language**: Python 3.8+

## ⚠️ Important Notes

### Risk Warning

- **Stock trading involves real financial risk**
- AI recommendations are for reference only, not investment advice
- Always test strategies with paper trading first
- Never invest more than you can afford to lose
- Use stop loss orders to manage risk
- Past performance does not guarantee future results

### Best Practices

1. **Start with Simulator** - Use the local simulator to learn the platform
2. **Test with Paper Trading** - Use Alpaca paper trading to test strategies
3. **Start Small** - Begin with small position sizes
4. **Monitor Positions** - Regularly check your positions and account
5. **Understand Orders** - Learn different order types before trading
6. **Keep Records** - Review trade history to improve strategies

## 📜 Trading Policy

### Risk Management Rules

1. **Maximum Position Size**
   - Single position should not exceed 20% of total account equity
   - Recommended position size: 5-10% of account equity per trade
   - For new traders, limit to 2-5% per position

2. **Portfolio Diversification**
   - Maintain at least 5-10 different positions when possible
   - Avoid over-concentration in a single sector or stock
   - Maximum 30% of portfolio in any single sector

3. **Maximum Daily Loss Limit**
   - Set a daily loss limit (recommended: 2-5% of account equity)
   - Stop trading for the day if daily loss limit is reached
   - Review and adjust strategy before resuming trading

4. **Maximum Drawdown Limit**
   - Set an account drawdown limit (recommended: 10-20% from peak equity)
   - Reduce position sizes or pause trading if drawdown limit is reached
   - Reassess trading strategy and risk parameters

### Stop Loss Requirements

1. **Mandatory Stop Loss**
   - All positions must have a stop loss order set
   - Stop loss should be set immediately after entering a position
   - Use the platform's Stop Loss/Take Profit monitoring feature

2. **Stop Loss Placement**
   - Stop loss should be based on technical analysis (support levels, ATR, etc.)
   - Typical stop loss: 2-5% below entry price for long positions
   - Adjust stop loss based on volatility and time frame

3. **Trailing Stop Loss**
   - Consider using trailing stop loss for profitable positions
   - Lock in profits while allowing for continued upside
   - Adjust trailing stop as position becomes more profitable

### Position Management

1. **Entry Rules**
   - Verify sufficient buying power before placing orders
   - Confirm order details (symbol, quantity, order type) before submission

2. **Exit Rules**
   - Exit positions that hit stop loss immediately
   - Take profits at predetermined levels (take profit orders)
   - Review and exit positions that no longer meet entry criteria

3. **Position Monitoring**
   - Check all positions at least once per trading day
   - Monitor positions for news or events that may affect price
   - Use the platform's position management features regularly

### AI Decision Usage Policy

1. **AI Recommendations**
   - AI recommendations are tools for analysis, not guaranteed outcomes
   - Always review AI analysis before executing trades
   - Consider AI confidence levels when making decisions
   - Combine AI recommendations with your own research

2. **Auto Execution**
   - Use auto-execution feature with caution
   - Review all AI decision details before enabling auto-execution
   - Start with manual execution to understand AI behavior
   - Monitor auto-executed trades closely

3. **AI Limitations**
   - AI cannot predict market movements with certainty
   - AI analysis is based on historical data and patterns
   - Market conditions can change rapidly, making AI recommendations outdated
   - Always use stop loss orders even with AI recommendations

### Auto Trading Policy

1. **Auto Trading Activation**
   - Only enable auto trading after thorough testing in simulator mode
   - Test strategies with paper trading for at least 2-4 weeks
   - Start with small position sizes when first enabling auto trading
   - Monitor auto trading activity daily

2. **Strategy Requirements**
   - All auto trading strategies must include stop loss rules
   - Set maximum position size limits for each strategy
   - Define clear entry and exit criteria
   - Review and update strategies regularly

3. **Auto Trading Monitoring**
   - Check auto trading logs and trade history regularly
   - Review strategy performance weekly
   - Disable auto trading if performance degrades significantly
   - Adjust strategy parameters based on market conditions

### Trading Hours Policy

1. **Regular Market Hours (Recommended)**
   - Primary trading should occur during regular market hours: 9:30 AM - 4:00 PM ET
   - Better liquidity and tighter spreads during regular hours
   - Most reliable execution during regular market hours

2. **Extended Hours Trading**
   - Pre-market (4:00 AM - 9:30 AM ET) and after-hours (4:00 PM - 8:00 PM ET) have:
     - Lower liquidity
     - Wider bid-ask spreads
     - Higher volatility
   - Use extended hours trading with caution and smaller position sizes
   - Consider using limit orders instead of market orders during extended hours

3. **Market Closures**
   - Do not place orders when markets are closed
   - Be aware of market holidays and early closures
   - GTC (Good Till Canceled) orders will execute when markets reopen

### Account Protection

1. **API Key Security**
   - Never share API keys or credentials
   - Use environment variables or secure configuration files
   - Regularly rotate API keys for security

2. **Account Monitoring**
   - Monitor account status and buying power daily
   - Check for any account restrictions or warnings
   - Verify all trades executed as intended
   - Review account statements regularly

3. **Capital Preservation**
   - Maintain a cash reserve (recommended: 20-30% of account)
   - Avoid using margin unless you understand the risks
   - Set account-level risk limits

### Compliance and Regulatory

1. **Regulatory Compliance**
   - Ensure compliance with all applicable securities regulations
   - Understand pattern day trader (PDT) rules if applicable
   - Comply with tax reporting requirements
   - Keep accurate records of all trades

2. **Record Keeping**
   - Maintain records of all trades and decisions
   - Document strategy changes and rationale
   - Keep logs of AI recommendations and executions
   - Review trade history regularly for learning

3. **Disclosure Requirements**
   - This platform is for educational and research purposes
   - Not registered as an investment advisor
   - Users are responsible for their own trading decisions

### Prohibited Practices

1. **Do Not:**
   - Ignore stop loss orders or risk management rules
   - Over-leverage your account
   - Trade based solely on AI recommendations without research
   - Disable risk management features
   - Trade during high volatility without understanding risks
   - Share API keys or account credentials

2. **Restrictions:**
   - No trading of securities you don't understand
   - No trading based on insider information
   - No manipulation of market prices
   - No violation of securities regulations

### Policy Updates

- Trading policies may be updated periodically
- Users are responsible for reviewing and understanding current policies
- Policy violations may result in account restrictions
- Contact maintainers for questions about trading policies

**Remember**: These policies are guidelines to help manage risk. Adapt them to your risk tolerance and trading experience. When in doubt, err on the side of caution.

## 🐛 Troubleshooting

### Common Issues

1. **API Key Errors**
   - Verify API keys are correct in configuration
   - Check API key has sufficient balance/permissions
   - Ensure `.env` file exists and is properly formatted

2. **Connection Issues**
   - Check internet connection
   - Verify Alpaca API is accessible
   - Check firewall settings

3. **Order Execution Failures**
   - Verify trading hours (see Trading Policy section)
   - Check account has sufficient buying power
   - Verify stock symbol is correct
   - Check account status is ACTIVE

4. **AI Decision Failures**
   - Verify DeepSeek API key is valid
   - Check API account has sufficient balance
   - Ensure network connection is stable

5. **Docker Issues**
   - Check Docker is running: `docker ps`
   - View logs: `docker-compose logs -f`
   - Verify `.env` file is mounted correctly
   - Check port 8503 is not in use

## 📝 License

MIT License

### Commercial Use

**⚠️ Important**: Commercial use of this project requires explicit permission from the author. If you intend to use this software for commercial purposes, please contact the author for authorization before proceeding.

For commercial licensing inquiries, please open an issue on GitHub or contact the maintainers.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## 📧 Support

For questions or issues, please open an issue on GitHub or contact the maintainers.

---

**Disclaimer**: This platform is for educational and research purposes only. Stock trading involves substantial risk of loss. AI recommendations should not be considered as investment advice. Always conduct your own research and consult with financial advisors before making investment decisions.
