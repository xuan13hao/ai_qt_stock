# Alpaca US Stock Trading Integration Guide

## 📖 Introduction

This guide explains how to configure and use Alpaca Markets API for US stock trading in the system.

## 🚀 Quick Start

### 1. Install Required Package

```bash
pip install alpaca-trade-api
```

### 2. Get Alpaca API Credentials

1. Visit [https://alpaca.markets](https://alpaca.markets)
2. Sign up for a free account
3. Go to Dashboard > API Keys
4. Create a new API key
5. Copy the **Key ID** and **Secret Key**

### 3. Configure Environment Variables

Add the following to your `.env` file:

```bash
# Alpaca US Stock Trading API Configuration
ALPACA_ENABLED=true
ALPACA_API_KEY=your_alpaca_api_key_here
ALPACA_API_SECRET=your_alpaca_api_secret_here
ALPACA_PAPER=true  # true for paper trading, false for live trading
```

### 4. Verify Configuration

1. Start the application
2. Go to **⚙️ Environment Config** > **🇺🇸 US Stock Trading (Alpaca)** tab
3. Enter your API credentials
4. Enable Alpaca trading
5. Save configuration

## 📊 Features

### Supported Operations

- ✅ **Buy Orders**: Market, Limit, Stop, Stop-Limit orders
- ✅ **Sell Orders**: Market, Limit, Stop, Stop-Limit orders
- ✅ **Position Management**: View all positions, get position details
- ✅ **Account Information**: Buying power, cash, portfolio value
- ✅ **Order Management**: View orders, cancel orders
- ✅ **Real-time Data**: Latest bar (price) data

### Trading Modes

#### Paper Trading (Recommended for Testing)
- Uses virtual money
- No real financial risk
- Perfect for testing strategies
- Set `ALPACA_PAPER=true`

#### Live Trading
- Uses real money
- Real financial risk
- Only enable after thorough testing
- Set `ALPACA_PAPER=false`

## 🔧 Configuration Details

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ALPACA_ENABLED` | Enable Alpaca trading | No | `false` |
| `ALPACA_API_KEY` | Alpaca API Key ID | Yes (if enabled) | - |
| `ALPACA_API_SECRET` | Alpaca API Secret Key | Yes (if enabled) | - |
| `ALPACA_PAPER` | Paper trading mode | No | `true` |
| `ALPACA_BASE_URL` | API base URL (optional) | No | Auto-selected |

### API Endpoints

- **Paper Trading**: `https://paper-api.alpaca.markets`
- **Live Trading**: `https://api.alpaca.markets`

## 💡 Usage Tips

### 1. Start with Paper Trading
Always test your strategies with paper trading first before switching to live trading.

### 2. Position Sizing
- US stocks support T+0 trading (can buy and sell on same day)
- No minimum lot size (can buy any number of shares)
- Recommended position size: ≤40% per stock

### 3. Order Types
- **Market Orders**: Execute immediately at current market price
- **Limit Orders**: Execute only at specified price or better
- **Stop Orders**: Trigger when price reaches stop price
- **Stop-Limit Orders**: Combination of stop and limit orders

### 4. Trading Hours
- Regular Market: 9:30 AM - 4:00 PM ET
- Pre-Market: 4:00 AM - 9:30 AM ET (limited liquidity)
- After-Hours: 4:00 PM - 8:00 PM ET (limited liquidity)

## ⚠️ Important Notes

1. **API Rate Limits**: Alpaca has rate limits. The system handles this automatically.

2. **Account Requirements**: 
   - Paper trading accounts are free
   - Live trading requires account verification

3. **Market Data**: 
   - Real-time data requires subscription for some symbols
   - Free tier includes delayed data (15 minutes)

4. **Pattern Day Trader**: 
   - Accounts with < $25,000 may be subject to PDT rules
   - System will show PDT status in account info

## 🔍 Troubleshooting

### Connection Failed
- Check API credentials are correct
- Verify internet connection
- Check if Alpaca service is available

### Orders Not Executing
- Check account has sufficient buying power
- Verify trading hours (regular market hours)
- Check if symbol is tradeable

### Import Error
If you see `alpaca-trade-api module not installed`:
```bash
pip install alpaca-trade-api
```

## 📚 Additional Resources

- [Alpaca Markets Documentation](https://alpaca.markets/docs/)
- [Alpaca API Reference](https://alpaca.markets/docs/api-documentation/)
- [Alpaca Python SDK](https://github.com/alpacahq/alpaca-trade-api-python)

## 🔐 Security

- Never commit API keys to version control
- Use environment variables or `.env` file (already in `.gitignore`)
- Rotate API keys regularly
- Use paper trading for testing

## ✅ Checklist

Before using live trading:
- [ ] Tested with paper trading
- [ ] Verified API credentials work
- [ ] Understood trading risks
- [ ] Set appropriate position sizes
- [ ] Configured stop losses
- [ ] Reviewed account status

