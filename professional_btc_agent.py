#!/usr/bin/env python3
"""
BTC Hourly Predictor FIXED v4
- Uses hourly data (reliable from CoinGecko free tier)
- Analyze past 1-2 hours momentum
- PREDICT next 1 hour direction
- TIGHT SL/TP: 0.5% SL, 0.8-1% TP
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
        
    def fetch_btc_hourly(self):
        """Fetch BTC hourly data (RELIABLE)"""
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
                logger.info(f"✅ Fetched {len(prices)} hourly candles")
                return prices
            logger.error(f"API error: {response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            return None
    
    def analyze_momentum(self, prices):
        """Analyze past 2 hours momentum (last 2 candles)"""
        if not prices or len(prices) < 3:
            return None
        
        try:
            # Last 2 hourly candles
            candle_1 = prices[-2]  # 2 hours ago
            candle_2 = prices[-1]  # current
            
            price_2h_ago = candle_1[1]
            price_now = candle_2[1]
            
            # Get recent highs/lows for volatility
            recent_prices = [p[1] for p in prices[-5:]]
            high = max(recent_prices)
            low = min(recent_prices)
            
            # Calculate metrics
            change_2h = ((price_now - price_2h_ago) / price_2h_ago) * 100
            volatility = ((high - low) / price_now) * 100
            
            # Determine trend strength
            if change_2h > 0.15:
                trend = "STRONG_UP"
                strength = min(100, abs(change_2h) * 20)
            elif change_2h > 0.05:
                trend = "WEAK_UP"
                strength = 45
            elif change_2h < -0.15:
                trend = "STRONG_DOWN"
                strength = min(100, abs(change_2h) * 20)
            elif change_2h < -0.05:
                trend = "WEAK_DOWN"
                strength = 45
            else:
                trend = "SIDEWAYS"
                strength = 30
            
            return {
                "price_2h_ago": round(price_2h_ago, 2),
                "price_now": round(price_now, 2),
                "change_2h": round(change_2h, 3),
                "high_5h": round(high, 2),
                "low_5h": round(low, 2),
                "volatility": round(volatility, 3),
                "trend": trend,
                "strength": round(strength, 1)
            }
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return None
    
    def predict_next_hour(self, current_price, momentum):
        """Predict next 1 hour direction"""
        try:
            logger.info("🤖 Predicting next hour...")
            
            prompt = f"""You are a professional crypto trader. Based on PAST 2 HOURS momentum, predict BTC/USD for NEXT 1 HOUR.

PAST 2 HOURS:
- Price 2h ago: ${momentum['price_2h_ago']}
- Price now: ${momentum['price_now']}
- Change: {momentum['change_2h']}%
- Volatility: {momentum['volatility']}%
- Trend: {momentum['trend']}
- Strength: {momentum['strength']}/100

Current Price: ${current_price}

IMPORTANT: Predict if price will go UP or DOWN in the NEXT 1 HOUR based on momentum.

Respond ONLY with JSON:
{{"direction": "UP/DOWN", "strength": number_0_to_100, "reason": "brief"}}"""
            
            payload = {
                "model": "llama-3.1-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 100
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
                
                pred = json.loads(content.strip())
                logger.info(f"✅ Prediction: {pred.get('direction')}")
                return pred
            else:
                logger.error(f"Groq error: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return None
    
    def fallback_prediction(self, momentum):
        """Fallback prediction if AI fails"""
        try:
            logger.warning("⚠️ Using fallback prediction...")
            
            trend = momentum['trend']
            strength = momentum['strength']
            
            if "UP" in trend:
                direction = "UP"
            elif "DOWN" in trend:
                direction = "DOWN"
            else:
                direction = "DOWN"  # Default conservative
            
            return {
                "direction": direction,
                "strength": strength,
                "reason": f"Based on {trend} momentum"
            }
        except:
            return {
                "direction": "DOWN",
                "strength": 50,
                "reason": "Default conservative"
            }
    
    def generate_signal(self, current_price, momentum, prediction):
        """Generate TIGHT signal with tight SL/TP"""
        try:
            if not prediction:
                return None
            
            direction = prediction.get('direction', 'DOWN')
            pred_strength = prediction.get('strength', 50)
            reason = prediction.get('reason', '')
            
            # Confidence
            if pred_strength > 70:
                confidence = "HIGH"
            elif pred_strength > 50:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"
            
            # Generate signal with TIGHT SL/TP
            if direction == "UP":
                signal = "BUY"
                entry = round(current_price, 2)
                # 0.5% SL below
                sl = round(entry * 0.995, 2)
                # 0.8% TP above
                tp = round(entry * 1.008, 2)
            else:
                signal = "SELL"
                entry = round(current_price, 2)
                # 0.5% SL above
                sl = round(entry * 1.005, 2)
                # 0.8% TP below
                tp = round(entry * 0.992, 2)
            
            # Calculate pips (for reference, treating as if 1 pip = 0.01)
            pips_sl = abs(round((entry - sl) * 100, 1))
            pips_tp = abs(round((entry - tp) * 100, 1))
            
            return {
                "signal": signal,
                "confidence": confidence,
                "entry": entry,
                "sl": sl,
                "tp": tp,
                "pips_sl": pips_sl,
                "pips_tp": pips_tp,
                "pred_strength": pred_strength,
                "reason": reason,
                "trend": momentum['trend'],
                "change_2h": momentum['change_2h']
            }
        except Exception as e:
            logger.error(f"Signal error: {e}")
            return None
    
    def send_signal_telegram(self, signal, momentum):
        """Send signal to Telegram"""
        try:
            if not signal:
                self.send_telegram("❌ Could not generate signal. Next prediction in 1 hour.")
                return
            
            sig = signal['signal']
            conf = signal['confidence']
            entry = signal['entry']
            sl = signal['sl']
            tp = signal['tp']
            pips_sl = signal['pips_sl']
            pips_tp = signal['pips_tp']
            strength = signal['pred_strength']
            reason = signal['reason']
            trend = signal['trend']
            change = signal['change_2h']
            
            emoji = "🟢" if sig == "BUY" else "🔴"
            rr = round(pips_tp / pips_sl, 2) if pips_sl > 0 else 0
            
            now = datetime.now()
            next_hour = now + timedelta(hours=1)
            
            message = f"""
<b>{emoji} BTC/USD 1-HOUR PREDICTION</b>

<b>🎯 SIGNAL:</b> {sig}
<b>📊 CONFIDENCE:</b> {conf} ({strength}%)

<b>💰 ENTRY SETUP (TIGHT):</b>
Entry: ${entry}
SL: ${sl} ({pips_sl} pips)
TP: ${tp} ({pips_tp} pips)
R/R: 1:{rr}

<b>📈 Past 2 Hours:</b>
Trend: {trend}
Change: {change}%
Volatility: {momentum['volatility']}%

<b>🔮 Next 1 Hour Prediction:</b>
{reason}

<b>⏰ Timeline:</b>
Signal: {now.strftime('%H:%M UTC')}
Close: {next_hour.strftime('%H:%M UTC')}
(Position closes before next signal)

<i>{now.strftime('%Y-%m-%d %H:%M:%S')} UTC</i>
"""
            
            self.send_telegram(message)
            logger.info(f"✅ Signal {sig} sent to Telegram")
            
        except Exception as e:
            logger.error(f"Send error: {e}")
    
    def send_telegram(self, message):
        """Send to Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    def run(self):
        """Main cycle"""
        logger.info("=" * 70)
        logger.info(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] HOURLY PREDICTION")
        logger.info("=" * 70)
        
        try:
            # Fetch hourly data
            prices = self.fetch_btc_hourly()
            if not prices or len(prices) < 3:
                logger.error("❌ Not enough data")
                self.send_telegram("❌ Error: Not enough price data")
                return
            
            current_price = prices[-1][1]
            logger.info(f"Current BTC: ${current_price:,.2f}")
            
            # Analyze momentum
            momentum = self.analyze_momentum(prices)
            if not momentum:
                logger.error("❌ Could not analyze")
                self.send_telegram("❌ Error: Could not analyze momentum")
                return
            
            logger.info(f"✅ Momentum: {momentum['trend']} ({momentum['change_2h']}%)")
            
            # Predict next hour
            prediction = self.predict_next_hour(current_price, momentum)
            
            # Fallback if prediction fails
            if not prediction:
                logger.warning("⚠️ Using fallback")
                prediction = self.fallback_prediction(momentum)
            
            # Generate signal
            signal = self.generate_signal(current_price, momentum, prediction)
            
            # Send signal
            self.send_signal_telegram(signal, momentum)
            
        except Exception as e:
            logger.error(f"Error: {e}")
            self.send_telegram(f"❌ Error: {str(e)[:80]}")
        
        logger.info("=" * 70)
    
    def schedule(self):
        """Schedule every 1 hour"""
        schedule.every(1).hours.do(self.run)
        
        logger.info("\n" + "=" * 70)
        logger.info("🚀 BTC HOURLY PREDICTOR v4 (FIXED)")
        logger.info("=" * 70)
        logger.info("✅ Data: Hourly (CoinGecko - reliable)")
        logger.info("✅ Analysis: Past 2 hours momentum")
        logger.info("✅ Prediction: Next 1 hour direction")
        logger.info("✅ SL/TP: TIGHT (0.5% SL, 0.8% TP)")
        logger.info("✅ Interval: Every 1 hour")
        logger.info("✅ Status: 24/7 Running")
        logger.info("=" * 70 + "\n")
        
        # Run first immediately
        self.run()
        
        # Keep running
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except KeyboardInterrupt:
                logger.info("\n🛑 Stopped")
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
