# BTC Trading Signal Bot

Simple bot yang monitor BTC price dan kirim update ke Telegram setiap 1 jam.

## Setup

1. **Rename files:**
   - `btc_bot_new.py` → `btc_bot.py`
   - `requirements_new.txt` → `requirements.txt`
   - `Procfile_new` → `Procfile`

2. **Upload ke GitHub**

3. **Deploy ke Railway**

## Features

- Fetch BTC price from CoinGecko (gratis, reliable)
- Send updates to Telegram every 1 hour
- Simple & no API complexity
- 24/7 running on Railway

## Running Locally

```bash
pip install -r requirements.txt
python btc_bot.py
```

## Telegram Setup

- Bot Token: `8761185264:AAGETqAfUwrOcwQSIOar48Ozq5BXiUtiN04`
- Chat ID: `5280470660`

Modify `btc_bot.py` if you want to use different credentials.
