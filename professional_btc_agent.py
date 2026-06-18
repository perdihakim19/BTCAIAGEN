#!/usr/bin/env python3
"""
Professional BTC/USD Trading Signal Agent
- Monitor every 30 minutes
- Technical analysis: RSI, MACD, EMA, Bollinger Bands
- AI analysis with Groq
- Professional BUY/SELL signals with SL & TP
- 24/7 operation on Railway
"""

import requests
import json
import time
from datetime import datetime
import schedule
import logging
import math

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BTCTradingAgent:
    def __init__(self, groq_api_key, telegram_token, chat_id):
        self.groq_key = groq_api_key
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.coingecko_url = "https://api.coingecko.com/api/v3"
        
    def fetch_btc_data(self):
        """Fetch BTC hourly data from CoinGecko"""
        try:
            logger.info("Fetching BTC hourly data...")
            url = f"{self.coingecko_url}/coins/bitcoin/market_chart"
            params = {
                "vs_currency": "usd",
                "days": "7",
                "interval": "hourly"
            }
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                prices = data.get('prices', [])
                logger.info(f"✅ Fetched {len(prices)} price points")
                return prices
            return None
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None
    
    def calculate_rsi(self, prices, period=14):
        """Calculate RSI indicator"""
        if len(prices) < period + 1:
            return None
        closes = [p[1] for p in prices]
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)
    
    def calculate_ema(self, prices, period):
        """Calculate EMA (Exponential Moving Average)"""
        if len(prices) < period:
            return None
        closes = [p[1] for p in prices]
        multiplier = 2 / (period + 1)
        ema = sum(closes[:period]) / period
        
        for price in closes[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return round(ema, 2)
    
    def calculate_macd(self, prices):
        """Calculate MACD (Moving Average Convergence Divergence)"""
        ema12 = self.calculate_ema(prices, 12)
        ema26 = self.calculate_ema(prices, 26)
        
        if not ema12 or not ema26:
            return None, None, None
        
        macd = round(ema12 - ema26, 2)
        
        # Signal line (9-period EMA of MACD)
        # Simplified: use EMA12
        signal = round(ema12 * 0.9, 2)
        
        histogram = round(macd - signal, 2)
        
        return macd, signal, histogram
    
    def calculate_bollinger_bands(self, prices, period=20, std_dev=2):
        """Calculate Bollinger Bands"""
        if len(prices) < period:
            return None, None, None
        
        closes = [p[1] for p in prices[-period:]]
        sma = sum(closes) / len(closes)
        
        variance = sum((x - sma) ** 2 for x in closes) / len(closes)
        std = math.sqrt(variance)
        
        upper = round(sma + (std_dev * std), 2)
        middle = round(sma, 2)
        lower = round(sma - (std_dev * std), 2)
        
        return upper, middle, lower
    
    def get_ai_analysis(self, price, rsi, macd, signal, bb_upper, bb_middle, bb_lower, ema20, ema50):
        """Get AI analysis from Groq"""
        try:
            logger.info("Getting AI analysis from Groq...")
            
            prompt = f"""You are a professional crypto trader. Analyze BTC/USD with this data:

Current Price: ${price:,.2f}
RSI(14): {rsi}
MACD: {macd}
Signal: {signal}
Histogram: {macd - signal}
BB Upper: ${bb_upper}
BB Middle: ${bb_middle}
BB Lower: ${bb_lower}
EMA20: ${ema20}
EMA50: ${ema50}

Provide trading decision in JSON format ONLY (no markdown):
{{
  "signal": "BUY or SELL or HOLD",
  "confidence": "HIGH or MEDIUM or LOW",
  "entry_price": number,
  "stop_loss": number,
  "take_profit": number,
  "reasoning": "Brief analysis (1-2 sentences)"
}}"""
            
            payload = {
                "model": "mixtral-8x7b-32768",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
                "max_tokens": 300
            }
            
            headers = {
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.groq_url, json=payload, headers=headers, timeout=20)
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Parse JSON
                if "```" in content:
                    content = content.split("```")[1].split("```")[0]
                    if content.startswith("json"):
                        content = content[4:]
                
                analysis = json.loads(content.strip())
                logger.info(f"✅ AI Analysis: {analysis.get('signal')}")
                return analysis
            else:
                logger.error(f"Groq error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"AI analysis error: {e}")
            return None
    
    def send_signal(self, analysis, price, rsi, macd, ema20, ema50):
        """Send trading signal to Telegram"""
        try:
            if not analysis:
                msg = "❌ <b>Analysis Failed</b>\nCould not get AI analysis. Retry in 30 min."
                self.send_telegram(msg)
                return
            
            signal = analysis.get('signal', 'N/A')
            confidence = analysis.get('confidence', 'N/A')
            entry = analysis.get('entry_price', 'N/A')
            sl = analysis.get('stop_loss', 'N/A')
            tp = analysis.get('take_profit', 'N/A')
            reason = analysis.get('reasoning', 'N/A')
            
            emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"
            
            message = f"""
<b>{emoji} BTC/USD TRADING SIGNAL</b>

<b>SIGNAL:</b> {signal}
<b>CONFIDENCE:</b> {confidence}

<b>📊 Price Action:</b>
Current: ${price:,.2f}
Entry: ${entry}
SL: ${sl}
TP: ${tp}

<b>📈 Technical:</b>
RSI: {rsi}
MACD: {macd}
EMA20: ${ema20}
EMA50: ${ema50}

<b>💡 Analysis:</b>
{reason}

<i>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>
"""
            
            self.send_telegram(message)
            logger.info(f"✅ Signal sent: {signal}")
            
        except Exception as e:
            logger.error(f"Signal error: {e}")
    
    def send_telegram(self, message):
        """Send message to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                logger.info("✅ Telegram sent")
                return True
            return False
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    def run_analysis(self):
        """Main analysis cycle"""
        logger.info("=" * 70)
        logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] STARTING ANALYSIS")
        logger.info("=" * 70)
        
        # Step 1: Fetch data
        prices = self.fetch_btc_data()
        if not prices or len(prices) < 50:
            logger.error("❌ Not enough price data")
            self.send_telegram("❌ Error: Not enough price data")
            return
        
        current_price = prices[-1][1]
        logger.info(f"Current BTC Price: ${current_price:,.2f}")
        
        # Step 2: Calculate indicators
        try:
            rsi = self.calculate_rsi(prices, 14)
            ema20 = self.calculate_ema(prices, 20)
            ema50 = self.calculate_ema(prices, 50)
            macd, signal, histogram = self.calculate_macd(prices)
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(prices, 20, 2)
            
            logger.info(f"✅ Indicators - RSI:{rsi}, MACD:{macd}, EMA20:{ema20}, EMA50:{ema50}")
            
            # Step 3: Get AI analysis
            analysis = self.get_ai_analysis(
                current_price, rsi, macd, signal, 
                bb_upper, bb_middle, bb_lower, ema20, ema50
            )
            
            # Step 4: Send signal
            self.send_signal(analysis, current_price, rsi, macd, ema20, ema50)
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            self.send_telegram(f"❌ Error: {str(e)}")
        
        logger.info("=" * 70)
    
    def schedule(self):
        """Schedule analysis every 30 minutes"""
        schedule.every(30).minutes.do(self.run_analysis)
        
        logger.info("\n" + "=" * 70)
        logger.info("🤖 PROFESSIONAL BTC TRADING AGENT STARTED")
        logger.info("=" * 70)
        logger.info("📊 Monitoring: BTC/USD")
        logger.info("⏱️  Interval: Every 30 minutes")
        logger.info("🤖 AI: Groq (Professional Analysis)")
        logger.info("📱 Platform: Telegram")
        logger.info("🔄 Status: 24/7 Running")
        logger.info("Press Ctrl+C to stop\n")
        
        # Run first analysis immediately
        self.run_analysis()
        
        # Keep running
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info("\n🛑 Agent stopped")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)

def main():
    GROQ_KEY = "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"
    TELEGRAM_TOKEN = "8983924607:AAFlsr-gQKMAYVIuexPkrimeBvUHd_WcM_A"
    CHAT_ID = "5280470660"
    
    agent = BTCTradingAgent(GROQ_KEY, TELEGRAM_TOKEN, CHAT_ID)
    agent.schedule()

if __name__ == "__main__":
    main()
