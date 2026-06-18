#!/usr/bin/env python3
"""
BTC Trading Signal Bot - STEP 1
Simple bot to fetch BTC data from CoinGecko and send to Telegram
"""

import requests
import json
import time
from datetime import datetime
import schedule
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BTCBot:
    def __init__(self, telegram_token, chat_id):
        self.token = telegram_token
        self.chat_id = chat_id
        
    def get_btc_price(self):
        """Get current BTC price from CoinGecko"""
        try:
            logger.info("Fetching BTC price...")
            
            url = "https://api.coingecko.com/api/v3/simple/price"
            params = {
                "ids": "bitcoin",
                "vs_currencies": "usd",
                "include_market_cap": "true",
                "include_24hr_vol": "true",
                "include_24hr_change": "true"
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                btc_data = data.get('bitcoin', {})
                
                price = btc_data.get('usd')
                change_24h = btc_data.get('usd_24h_change')
                market_cap = btc_data.get('usd_market_cap')
                volume_24h = btc_data.get('usd_24h_vol')
                
                logger.info(f"✅ BTC Price: ${price}")
                
                return {
                    "price": price,
                    "change_24h": change_24h,
                    "market_cap": market_cap,
                    "volume_24h": volume_24h
                }
            else:
                logger.error(f"API error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None
    
    def send_telegram(self, message):
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Message sent to Telegram")
                return True
            else:
                logger.error(f"Telegram error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    def run(self):
        """Main function"""
        logger.info("=" * 60)
        logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Bot running...")
        logger.info("=" * 60)
        
        # Get BTC data
        btc_data = self.get_btc_price()
        
        if btc_data:
            # Format message
            price = btc_data['price']
            change = btc_data['change_24h']
            
            # Determine emoji
            emoji = "🟢" if change > 0 else "🔴"
            
            message = f"""
<b>📊 BTC Price Update</b>

{emoji} <b>Price:</b> ${price:,.2f}
<b>24h Change:</b> {change:.2f}%

<i>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>
"""
            
            logger.info("Message ready to send")
            self.send_telegram(message)
            logger.info("✅✅✅ SUCCESS ✅✅✅")
        else:
            logger.error("❌ Failed to get BTC data")
            self.send_telegram("❌ Bot Error: Failed to fetch BTC data")
        
        logger.info("=" * 60)
    
    def schedule(self):
        """Schedule bot to run every 1 hour"""
        schedule.every(1).hours.do(self.run)
        
        logger.info("\n🚀 BTC Bot Started!")
        logger.info("📅 Running every 1 hour")
        logger.info("Press Ctrl+C to stop\n")
        
        # Run first time immediately
        self.run()
        
        # Keep running
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info("\n🛑 Bot stopped")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(60)

def main():
    # Your Telegram credentials
    TOKEN = "8761185264:AAGETqAfUwrOcwQSIOar48Ozq5BXiUtiN04"
    CHAT_ID = "5280470660"
    
    bot = BTCBot(TOKEN, CHAT_ID)
    bot.schedule()

if __name__ == "__main__":
    main()
