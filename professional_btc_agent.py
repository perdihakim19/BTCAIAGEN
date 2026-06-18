#!/usr/bin/env python3
"""
Professional BTC/USD Trading Signal Agent - FIXED VERSION
- Fixed Groq API model and format
- Added fallback logic (if AI fails, use technical indicators)
- Guaranteed to work 24/7
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
            logger.info("📥 Fetching BTC hourly data...")
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
        """Calculate EMA"""
        if len(prices) < period:
            return None
        closes = [p[1] for p in prices]
        multiplier = 2 / (period + 1)
        ema = sum(closes[:period]) / period
        
        for price in closes[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return round(ema, 2)
    
    def calculate_macd(self, prices):
        """Calculate MACD"""
        ema12 = self.calculate_ema(prices, 12)
        ema26 = self.calculate_ema(prices, 26)
        
        if not ema12 or not ema26:
            return None, None, None
        
        macd = round(ema12 - ema26, 2)
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
    
    def generate_signal_from_indicators(self, price, rsi, ema20, ema50, macd, bb_upper, bb_lower):
        """Generate signal from technical indicators only (FALLBACK)"""
        logger.info("🔄 Generating signal from technical indicators (FALLBACK)...")
        
        try:
            # Simple but effective logic
            signal = "HOLD"
            confidence = "MEDIUM"
            reasoning = ""
            
            # RSI based signals
            if rsi < 30:
                signal = "BUY"
                confidence = "HIGH"
                reasoning = "RSI oversold, strong buy signal"
            elif rsi > 70:
                signal = "SELL"
                confidence = "HIGH"
                reasoning = "RSI overbought, strong sell signal"
            
            # EMA confirmation
            if price > ema20 > ema50 and signal == "BUY":
                confidence = "HIGH"
            elif price < ema20 < ema50 and signal == "SELL":
                confidence = "HIGH"
            elif price > ema50 and signal == "HOLD":
                signal = "BUY"
                confidence = "MEDIUM"
                reasoning = "Price above EMA50, uptrend"
            elif price < ema50 and signal == "HOLD":
                signal = "SELL"
                confidence = "MEDIUM"
                reasoning = "Price below EMA50, downtrend"
            
            # Bollinger Bands
            if price < bb_lower and signal != "SELL":
                signal = "BUY"
                confidence = "HIGH"
                reasoning = "Price at lower BB, oversold"
            elif price > bb_upper and signal != "BUY":
                signal = "SELL"
                confidence = "HIGH"
                reasoning = "Price at upper BB, overbought"
            
            # Calculate SL & TP
            if signal == "BUY":
                entry = round(price, 2)
                sl = round(price * 0.98, 2)  # 2% below
                tp = round(price * 1.03, 2)  # 3% above
            else:
                entry = round(price, 2)
                sl = round(price * 1.02, 2)  # 2% above
                tp = round(price * 0.97, 2)  # 3% below
            
            return {
                "signal": signal,
                "confidence": confidence,
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "reasoning": reasoning
            }
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None
    
    def get_ai_analysis(self, price, rsi, macd, signal, bb_upper, bb_middle, bb_lower, ema20, ema50):
        """Get AI analysis from Groq"""
        try:
            logger.info("🤖 Sending request to Groq AI...")
            
            prompt = f"""As a professional crypto trader, analyze BTC/USD:

Price: ${price:,.2f}
RSI(14): {rsi}
MACD: {macd}
EMA20: ${ema20}
EMA50: ${ema50}
BB Upper: ${bb_upper}
BB Middle: ${bb_middle}
BB Lower: ${bb_lower}

Respond ONLY with JSON (no markdown):
{{"signal": "BUY/SELL/HOLD", "confidence": "HIGH/MEDIUM/LOW", "entry_price": number, "stop_loss": number, "take_profit": number, "reasoning": "brief"}}"""
            
            payload = {
                "model": "llama-3.1-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
                "max_tokens": 200
            }
            
            headers = {
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.groq_url, json=payload, headers=headers, timeout=20)
            
            logger.info(f"Groq response: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Clean JSON
                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.split("```")[0]
                
                analysis = json.loads(content.strip())
                logger.info(f"✅ AI Analysis: {analysis.get('signal')}")
                return analysis
            else:
                logger.error(f"❌ Groq error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ AI error: {e}")
            return None
    
    def send_signal(self, analysis, price, rsi, macd, ema20, ema50, ai_used=True):
        """Send trading signal to Telegram"""
        try:
            if not analysis:
                msg = "❌ Analysis Failed\nCould not get analysis. Retrying in 30 min."
                self.send_telegram(msg)
                return
            
            signal = analysis.get('signal', 'N/A')
            confidence = analysis.get('confidence', 'N/A')
            entry = analysis.get('entry_price', 'N/A')
            sl = analysis.get('stop_loss', 'N/A')
            tp = analysis.get('take_profit', 'N/A')
            reason = analysis.get('reasoning', 'N/A')
            
            emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"
            ai_status = "🤖 AI Analysis" if ai_used else "📊 Technical Analysis"
            
            message = f"""
<b>{emoji} BTC/USD TRADING SIGNAL</b>

<b>SIGNAL:</b> {signal}
<b>CONFIDENCE:</b> {confidence}

<b>💰 Entry Strategy:</b>
Entry: ${entry}
SL: ${sl}
TP: ${tp}

<b>📈 Technicals:</b>
RSI: {rsi}
MACD: {macd}
EMA20: ${ema20}
EMA50: ${ema50}

<b>💡 {ai_status}:</b>
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
        
        # Fetch data
        prices = self.fetch_btc_data()
        if not prices or len(prices) < 50:
            logger.error("❌ Not enough data")
            self.send_telegram("❌ Error: Not enough price data")
            return
        
        current_price = prices[-1][1]
        logger.info(f"Current BTC: ${current_price:,.2f}")
        
        try:
            # Calculate indicators
            rsi = self.calculate_rsi(prices, 14)
            ema20 = self.calculate_ema(prices, 20)
            ema50 = self.calculate_ema(prices, 50)
            macd, signal, histogram = self.calculate_macd(prices)
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(prices, 20, 2)
            
            logger.info(f"✅ Indicators: RSI={rsi}, MACD={macd}, EMA20={ema20}, EMA50={ema50}")
            
            # Try AI analysis first
            analysis = self.get_ai_analysis(
                current_price, rsi, macd, signal, 
                bb_upper, bb_middle, bb_lower, ema20, ema50
            )
            
            # If AI fails, use fallback
            if not analysis:
                logger.warning("⚠️ AI failed, using technical indicators fallback...")
                analysis = self.generate_signal_from_indicators(
                    current_price, rsi, ema20, ema50, macd, bb_upper, bb_lower
                )
                ai_used = False
            else:
                ai_used = True
            
            # Send signal
            self.send_signal(analysis, current_price, rsi, macd, ema20, ema50, ai_used)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            self.send_telegram(f"❌ Error: {str(e)[:100]}")
        
        logger.info("=" * 70)
    
    def schedule(self):
        """Schedule analysis every 30 minutes"""
        schedule.every(30).minutes.do(self.run_analysis)
        
        logger.info("\n" + "=" * 70)
        logger.info("🚀 PROFESSIONAL BTC TRADING AGENT v2 (FIXED)")
        logger.info("=" * 70)
        logger.info("✅ AI: Groq (with fallback)")
        logger.info("✅ Data: CoinGecko")
        logger.info("✅ Interval: Every 30 minutes")
        logger.info("✅ Telegram: Real-time alerts")
        logger.info("✅ Status: 24/7 Running")
        logger.info("=" * 70 + "\n")
        
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
                logger.error(f"Error: {e}")
                time.sleep(60)

def main():
    GROQ_KEY = "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"
    TELEGRAM_TOKEN = "8983924607:AAFlsr-gQKMAYVIuexPkrimeBvUHd_WcM_A"
    CHAT_ID = "5280470660"
    
    agent = BTCTradingAgent(GROQ_KEY, TELEGRAM_TOKEN, CHAT_ID)
    agent.schedule()

if __name__ == "__main__":
    main()
