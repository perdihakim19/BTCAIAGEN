# 🤖 BTC Trading System - Signal Generator + Tracker

Complete crypto trading system dengan 2 bot yang bekerja bersama:

**Bot 1 (Signal Generator):** Generate signal BTC/USD setiap 1 jam
**Bot 2 (Tracker):** Listen signal, calculate position size, track PnL

## Architecture 🏗️

```
┌─────────────────────────────────────────────┐
│  BOT 1: SIGNAL GENERATOR                    │
│  (professional_btc_agent.py)                │
│  ✅ Fetch BTC hourly data                   │
│  ✅ Analyze momentum (2 hours)              │
│  ✅ Predict next hour direction (AI)        │
│  ✅ Generate tight signal (0.5% SL, 0.8% TP)│
│  ✅ Send ke Telegram setiap 1 jam           │
└─────────────────────────────────────────────┘
              ⬇️ Signal Message
┌─────────────────────────────────────────────┐
│  BOT 2: TRACKER & RISK MANAGER              │
│  (telegram_trader_bot.py)                   │
│  ✅ Listen signal message                   │
│  ✅ Parse signal (entry, SL, TP)            │
│  ✅ Calculate position size (2% risk)       │
│  ✅ Show trading calculations               │
│  ✅ Track entry/exit & PnL                  │
│  ✅ Calculate stats (win rate, etc)         │
└─────────────────────────────────────────────┘
```

## Features ✨

### Bot 1 (Signal Generator)
- Hourly BTC/USD prediction
- 2-hour momentum analysis
- AI-powered direction prediction (Groq)
- Tight stop loss & take profit
- Indonesia timezone (WIB)

### Bot 2 (Tracker)
- Auto-parse signals
- Position sizing (2% risk management)
- PnL tracking
- Win rate & statistics
- Equity curve tracking

## Setup 🎯

### Step 1: Create Telegram Bot

1. **Create bot di @BotFather:**
   - Klik `/newbot`
   - Name: `BTC Trading System`
   - Username: `btc_trading_system_bot`
   - Copy TOKEN

2. **Get Chat ID:**
   - Search bot Anda di Telegram
   - Klik `/start`
   - Forward ke `@userinfobot`
   - Copy Chat ID

3. **Get Groq API Key:**
   - Buka https://console.groq.com/keys
   - Create API key
   - Copy key

### Step 2: Set Environment Variables

Copy `.env.example` → `.env` dan fill dengan:

```
GROQ_KEY=gsk_your_key_here
TELEGRAM_TOKEN=123456:ABC-DEF...
CHAT_ID=123456789
CAPITAL=100
RISK_PERCENT=2
```

### Step 3: Deploy ke Railway

1. Push files ke GitHub repo BTCAIAGEN
2. Buka https://railway.app
3. **New Project** → **Deploy from GitHub**
4. Select `BTCAIAGEN` repo
5. Railway auto-detect Procfile dengan 2 bots
6. Set environment variables
7. Deploy ✅

**Railway akan run 2 processes:**
- `signal-bot` - professional_btc_agent.py
- `tracker-bot` - telegram_trader_bot.py

## File Structure 📁

```
BTCAIAGEN/
├── professional_btc_agent.py    ← Bot 1 (Signal Generator)
├── telegram_trader_bot.py       ← Bot 2 (Tracker)
├── requirements.txt             ← Dependencies (both bots)
├── Procfile                     ← Railway config (2 workers)
├── .env.example                 ← Environment template
└── README.md                    ← This file
```

## How It Works 📱

### Setiap 1 jam:

**02:44 WIB - Bot 1 Generate Signal:**
```
🔴 BTC/USD 1-HOUR PREDICTION
SIGNAL: SELL
CONFIDENCE: LOW (3.1%)
Entry: $62,943.62
SL: $63,258.34
TP: $62,440.07
R/R: 1:1.6
```

**02:44 WIB - Bot 2 Listen & Track:**
```
📊 SIGNAL RECEIVED
Entry: $62,943.62
SL: $63,258.34
TP: $62,440.07

💰 POSITION SIZING:
Capital: $100.00
Risk: $2.00 (2%)
Position: 0.0032 BTC
Profit Potential: +$3.20

[Exit Button]
```

**03:44 WIB - User Exit:**
```
User: exit 62500
Bot: ✅ Trade closed
     PnL: +$1.41
     Win Rate: 55%
```

## Commands 🎮

```
/start           - Welcome message
/stats           - Trading statistics
/capital [X]     - Set capital (e.g., /capital 100)
/reset           - Reset all trades
```

## Environment Variables 🔐

```
GROQ_KEY          - Groq API key untuk AI prediction
TELEGRAM_TOKEN    - Bot token dari @BotFather
CHAT_ID          - Chat ID untuk telegram
CAPITAL          - Starting capital ($)
RISK_PERCENT     - Risk per trade (%)
```

## Deployment Checklist ✅

- [ ] Create bot di @BotFather (copy TOKEN)
- [ ] Get Chat ID dari @userinfobot
- [ ] Get Groq API key dari groq.com
- [ ] Update .env dengan semua values
- [ ] Push ke GitHub (BTCAIAGEN)
- [ ] Deploy di Railway
- [ ] Test signal generation
- [ ] Test tracker parsing
- [ ] Start trading!

## Troubleshooting 🔧

### Bot signal tidak kirim message?
- Check GROQ_KEY valid
- Check TELEGRAM_TOKEN valid
- Check CHAT_ID valid
- See logs di Railway

### Bot tracker tidak parse signal?
- Signal format harus sesuai
- Bot perlu restart setelah signal bot jalan
- Check message format di Telegram

### Equity tidak update?
- Format exit reply: `exit 62500` (no extra text)
- Bot perlu detect message contain "exit"

## Future Improvements 🚀

- [ ] Database untuk historical trades
- [ ] Dashboard visualization
- [ ] Multi-pair support (BTC, ETH, etc)
- [ ] OKX API integration untuk auto-trade
- [ ] Risk optimization
- [ ] Backtesting engine

## Support 💬

Issues? Check:
1. Railway logs
2. Telegram messages
3. Environment variables

---

**Happy trading! 📈**
