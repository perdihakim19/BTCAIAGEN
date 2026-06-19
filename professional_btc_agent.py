#!/usr/bin/env python3
"""
Professional BTC Hourly Predictor v3
- Analyze past 1 hour (11:00-12:00)
- PREDICT next 1 hour (12:00-13:00) direction
- Generate BUY/SELL signals with tight SL/TP
- Signal every 1 hour
"""

import requests
import json
import time
from datetime import datetime, timedelta
import schedule
import logging
import math

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BTCHourlyPredictor:
    def __init__(self, groq_api_key, telegram_token, chat_id):
        self.groq_key = groq_api_key
        self.telegram_token = telegram_token
        self.chat_id = chat_id
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.coingecko_url = "https://api.coingecko.com/api/v3"
        
    def fetch_btc_data(self, days=1):
        """Fetch BTC 5-minute data for accurate hourly analysis"""
        try:
            logger.info("📥 Fetching BTC 5-minute data...")
            url = f"{self.coingecko_url}/coins/bitcoin/market_chart"
            params = {
                "vs_currency": "usd",
                "days": days,
                "interval": "5m"
            }
            response = requests.get(url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                prices = data.get('prices', [])
                logger.info(f"✅ Fetched {len(prices)} price points (5m interval)")
                return prices
            return None
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return None
    
    def get_last_hour_data(self, prices):
        """Extract last 1 hour of data"""
        if not prices or len(prices) < 12:  # 12 * 5min = 60min
            return None
        return prices[-12:]  # Last 12 candles (5min each)
    
    def analyze_hour_momentum(self, hour_prices):
        """Analyze momentum of past 1 hour"""
        if not hour_prices or len(hour_prices) < 2:
            return None
        
        closes = [p[1] for p in hour_prices]
        open_price = closes[0]
        close_price = closes[-1]
        high_price = max(closes)
        low_price = min(closes)
        
        # Calculate momentum
        change_pct = ((close_price - open_price) / open_price) * 100
        volatility = ((high_price - low_price) / open_price) * 100
        
        # Trend direction
        if change_pct > 0.1:
            trend = "UPTREND"
            strength = min(100, abs(change_pct) * 10)
        elif change_pct < -0.1:
            trend = "DOWNTREND"
            strength = min(100, abs(change_pct) * 10)
        else:
            trend = "SIDEWAYS"
            strength = 30
        
        return {
            "open": round(open_price, 2),
            "close": round(close_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "change_pct": round(change_pct, 3),
            "volatility": round(volatility, 3),
            "trend": trend,
            "strength": round(strength, 1)
        }
    
    def predict_next_hour(self, current_price, momentum_data):
        """Predict direction for next 1 hour using Groq"""
        try:
            logger.info("🤖 Predicting next 1 hour direction...")
            
            prompt = f"""You are a professional crypto trader. Based on past 1 hour momentum, predict BTC/USD direction for NEXT 1 HOUR.

PAST 1 HOUR DATA:
- Open: ${momentum_data['open']}
- Close: ${momentum_data['close']}
- High: ${momentum_data['high']}
- Low: ${momentum_data['low']}
- Change: {momentum_data['change_pct']}%
- Volatility: {momentum_data['volatility']}%
- Trend: {momentum_data['trend']}
- Strength: {momentum_data['strength']}/100

Current Price: ${current_price}

Based on MOMENTUM and TREND, predict:
1. Will price go UP or DOWN in next 1 hour?
2. How strong is this direction? (percentage)

Respond ONLY with JSON:
{{"direction": "UP/DOWN", "prediction_strength": number_0_to_100, "reasoning": "brief reason"}}"""
            
            payload = {
                "model": "llama-3.1-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 150
            }
            
            headers = {
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.groq_url, json=payload, headers=headers, timeout=20)
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                # Clean JSON
                if "```" in content:
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.split("```")[0]
                
                prediction = json.loads(content.strip())
                logger.info(f"✅ Prediction: {prediction.get('direction')}")
                return prediction
            else:
                logger.error(f"❌ Groq error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Prediction error: {e}")
            return None
    
    def generate_signal(self, current_price, momentum_data, prediction):
        """Generate trading signal with tight SL/TP"""
        try:
            if not prediction:
                return None
            
            direction = prediction.get('direction', 'DOWN')
            strength = prediction.get('prediction_strength', 50)
            reasoning = prediction.get('reasoning', '')
            
            # Confidence based on strength
            if strength > 70:
                confidence = "HIGH"
            elif strength > 50:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"
            
            # Generate signal
            if direction == "UP":
                signal = "BUY"
                entry = round(current_price, 2)
                # Tight SL: 0.5% below entry
                stop_loss = round(entry * 0.995, 2)
                # TP: 1% above entry (tight and achievable in 1 hour)
                take_profit = round(entry * 1.01, 2)
                pips_sl = round((entry - stop_loss) * 100, 2)
                pips_tp = round((take_profit - entry) * 100, 2)
            else:
                signal = "SELL"
                entry = round(current_price, 2)
                # Tight SL: 0.5% above entry
                stop_loss = round(entry * 1.005, 2)
                # TP: 1% below entry
                take_profit = round(entry * 0.99, 2)
                pips_sl = round((stop_loss - entry) * 100, 2)
                pips_tp = round((entry - take_profit) * 100, 2)
            
            return {
                "signal": signal,
                "confidence": confidence,
                "entry_price": entry,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "pips_sl": pips_sl,
                "pips_tp": pips_tp,
                "prediction_strength": strength,
                "reasoning": reasoning,
                "past_trend": momentum_data['trend'],
                "past_change": momentum_data['change_pct']
            }
        except Exception as e:
            logger.error(f"Signal error: {e}")
            return None
    
    def send_signal(self, signal, momentum_data):
        """Send signal to Telegram"""
        try:
            if not signal:
                self.send_telegram("❌ Could not generate signal. Retrying in 1 hour.")
                return
            
            sig = signal['signal']
            conf = signal['confidence']
            entry = signal['entry_price']
            sl = signal['stop_loss']
            tp = signal['take_profit']
            pips_sl = signal['pips_sl']
            pips_tp = signal['pips_tp']
            strength = signal['prediction_strength']
            reason = signal['reasoning']
            trend = signal['past_trend']
            change = signal['past_change']
            
            emoji = "🟢" if sig == "BUY" else "🔴"
            
            message = f"""
<b>{emoji} BTC/USD 1-HOUR PREDICTION</b>

<b>🎯 SIGNAL:</b> {sig}
<b>📊 CONFIDENCE:</b> {conf} ({strength}%)

<b>💰 TIGHT ENTRY STRATEGY:</b>
Entry: ${entry}
SL: ${sl} ({pips_sl} pips)
TP: ${tp} ({pips_tp} pips)
Risk/Reward: 1:{round(pips_tp/pips_sl, 2)}

<b>📈 Past 1 Hour Analysis:</b>
Trend: {trend}
Change: {change}%
Volatility: {momentum_data['volatility']}%

<b>🔮 Next 1 Hour Prediction:</b>
{reason}

<b>⏰ Timeline:</b>
Signal Time: {datetime.now().strftime('%H:%M UTC')}
Close Time: {(datetime.now() + timedelta(hours=1)).strftime('%H:%M UTC')}
(Position should be closed by next signal)

<i>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</i>
"""
            
            self.send_telegram(message)
            logger.info(f"✅ Signal sent: {sig}")
            
        except Exception as e:
            logger.error(f"Send signal error: {e}")
    
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
    
    def run_prediction(self):
        """Main prediction cycle"""
        logger.info("=" * 70)
        logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] HOURLY PREDICTION")
        logger.info("=" * 70)
        
        try:
            # Fetch data
            prices = self.fetch_btc_data(days=1)
            if not prices:
                self.send_telegram("❌ Error: Could not fetch BTC data")
                return
            
            # Get last hour
            hour_data = self.get_last_hour_data(prices)
            if not hour_data:
                self.send_telegram("❌ Error: Not enough data")
                return
            
            current_price = hour_data[-1][1]
            logger.info(f"Current BTC: ${current_price:,.2f}")
            
            # Analyze past 1 hour momentum
            momentum = self.analyze_hour_momentum(hour_data)
            if not momentum:
                self.send_telegram("❌ Error: Could not analyze momentum")
                return
            
            logger.info(f"✅ Past 1h: {momentum['trend']} ({momentum['change_pct']}%)")
            
            # Predict next 1 hour
            prediction = self.predict_next_hour(current_price, momentum)
            
            # Generate signal
            signal = self.generate_signal(current_price, momentum, prediction)
            
            # Send signal
            self.send_signal(signal, momentum)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            self.send_telegram(f"❌ Error: {str(e)[:100]}")
        
        logger.info("=" * 70)
    
    def schedule(self):
        """Schedule prediction every 1 hour"""
        schedule.every(1).hours.do(self.run_prediction)
        
        logger.info("\n" + "=" * 70)
        logger.info("🚀 BTC HOURLY PREDICTOR v3 - STARTED")
        logger.info("=" * 70)
        logger.info("📊 Analysis: Past 1 hour momentum")
        logger.info("🔮 Prediction: Next 1 hour direction")
        logger.info("💰 SL/TP: TIGHT (0.5% SL, 1% TP)")
        logger.info("⏰ Interval: Every 1 hour")
        logger.info("📱 Platform: Telegram")
        logger.info("🔄 Status: 24/7 Running")
        logger.info("=" * 70 + "\n")
        
        # Run first prediction immediately
        self.run_prediction()
        
        # Keep running
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info("\n🛑 Predictor stopped")
                break
            except Exception as e:
                logger.error(f"Error: {e}")
                time.sleep(60)

def main():
    GROQ_KEY = "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"
    TELEGRAM_TOKEN = "8983924607:AAFlsr-gQKMAYVIuexPkrimeBvUHd_WcM_A"
    CHAT_ID = "5280470660"
    
    predictor = BTCHourlyPredictor(GROQ_KEY, TELEGRAM_TOKEN, CHAT_ID)
    predictor.schedule()

if __name__ == "__main__":
    main()
