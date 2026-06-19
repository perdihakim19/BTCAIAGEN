#!/usr/bin/env python3
"""
Telegram Trading Signal Tracker Bot
- Listen to signal bot messages
- Calculate position size (2% risk)
- Track entry & exit
- Calculate PnL & stats
- Show equity curve
"""

import os
import json
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    ContextTypes, ConversationHandler, CallbackQueryHandler, filters
)
from telegram.constants import ParseMode
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# States untuk ConversationHandler
WAITING_ENTRY, WAITING_EXIT = range(2)

class TradingBot:
    def __init__(self):
        self.trades = {}  # Store trades by message_id
        self.capital = 100  # Starting capital
        self.risk_per_trade = 0.02  # 2% risk
        
    def parse_signal(self, text):
        """Parse signal from original bot message"""
        try:
            result = {}
            
            # Extract signal type (BUY/SELL)
            if "BUY" in text:
                result['signal'] = 'BUY'
            elif "SELL" in text:
                result['signal'] = 'SELL'
            else:
                return None
            
            # Extract confidence
            conf_match = re.search(r'CONFIDENCE[:\s]*([A-Z]+)\s*\((\d+\.?\d*)', text)
            if conf_match:
                result['confidence'] = conf_match.group(1)
                result['confidence_pct'] = float(conf_match.group(2))
            
            # Extract entry
            entry_match = re.search(r'Entry[:\s]*\$?([\d,]+\.?\d*)', text)
            if entry_match:
                result['entry'] = float(entry_match.group(1).replace(',', ''))
            
            # Extract SL
            sl_match = re.search(r'SL[:\s]*\$?([\d,]+\.?\d*)', text)
            if sl_match:
                result['sl'] = float(sl_match.group(1).replace(',', ''))
            
            # Extract TP
            tp_match = re.search(r'TP[:\s]*\$?([\d,]+\.?\d*)', text)
            if tp_match:
                result['tp'] = float(tp_match.group(1).replace(',', ''))
            
            # Extract trend
            trend_match = re.search(r'Trend[:\s]*([A-Z_]+)', text)
            if trend_match:
                result['trend'] = trend_match.group(1)
            
            # Extract change
            change_match = re.search(r'Change[:\s]*([-\d.]+)%', text)
            if change_match:
                result['change_2h'] = float(change_match.group(1))
            
            # Validate required fields
            required = ['signal', 'entry', 'sl', 'tp']
            if all(k in result for k in required):
                return result
            else:
                logger.warning(f"Missing fields: {required}")
                return None
                
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None
    
    def calculate_position(self, signal):
        """Calculate position size based on risk management"""
        try:
            entry = signal['entry']
            sl = signal['sl']
            signal_type = signal['signal']
            
            # Risk amount in dollars
            risk_dollars = self.capital * self.risk_per_trade
            
            # Risk amount in price
            if signal_type == 'BUY':
                risk_price = entry - sl  # SL is below
            else:
                risk_price = sl - entry  # SL is above
            
            # Position size
            if risk_price <= 0:
                return None
            
            position_size = risk_dollars / risk_price
            
            # Calculate TP profit
            tp = signal['tp']
            if signal_type == 'BUY':
                profit_price = tp - entry
            else:
                profit_price = entry - tp
            
            tp_dollars = position_size * profit_price if profit_price > 0 else 0
            
            # R/R ratio
            rr_ratio = profit_price / risk_price if risk_price > 0 else 0
            
            return {
                'position_size': position_size,
                'risk_dollars': risk_dollars,
                'profit_potential': tp_dollars,
                'rr_ratio': rr_ratio
            }
        except Exception as e:
            logger.error(f"Calculation error: {e}")
            return None
    
    def format_signal_message(self, signal, position, msg_id):
        """Format signal with trading calculations"""
        try:
            sig = signal['signal']
            emoji = "🟢" if sig == "BUY" else "🔴"
            
            entry = signal['entry']
            sl = signal['sl']
            tp = signal['tp']
            conf = signal.get('confidence', 'N/A')
            conf_pct = signal.get('confidence_pct', 0)
            
            risk_dollars = position['risk_dollars']
            position_size = position['position_size']
            rr_ratio = position['rr_ratio']
            profit_potential = position['profit_potential']
            
            trend = signal.get('trend', 'N/A')
            change = signal.get('change_2h', 0)
            
            message = f"""
<b>{emoji} BTC/USD SIGNAL RECEIVED</b>

<b>Signal:</b> {sig}
<b>Confidence:</b> {conf} ({conf_pct:.1f}%)
<b>Trend:</b> {trend} ({change:+.3f}%)

<b>📊 PRICE LEVELS:</b>
Entry: ${entry:,.2f}
SL: ${sl:,.2f}
TP: ${tp:,.2f}
R/R: 1:{rr_ratio:.2f}

<b>💰 POSITION SIZING (2% Risk):</b>
Capital: ${self.capital:.2f}
Risk Amount: ${risk_dollars:.2f}
Position Size: {position_size:.4f} BTC
Profit Potential: ${profit_potential:+,.2f}

<b>⏰ Action:</b>
Reply with exit price when position closes
Callback ID: {msg_id}
"""
            return message
        except Exception as e:
            logger.error(f"Format error: {e}")
            return None

# Create bot instance
trading_bot = TradingBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    welcome = """
<b>🤖 Crypto Trading Signal Tracker</b>

I track BTC/USD signals and calculate:
✅ Position size (2% risk management)
✅ Entry/Exit levels
✅ PnL tracking
✅ Win rate & stats

<b>How to use:</b>
1. Let the signal bot (@BTCAIAGEN) send signals
2. I'll auto-parse and show calculations
3. Reply with exit price when ready
4. I'll calculate PnL

<b>Commands:</b>
/stats - Show performance stats
/reset - Reset all trades
/capital - Set trading capital
"""
    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show trading statistics"""
    try:
        if not trading_bot.trades:
            await update.message.reply_text("No trades yet. Waiting for signals...")
            return
        
        closed_trades = [t for t in trading_bot.trades.values() if t.get('pnl') is not None]
        if not closed_trades:
            await update.message.reply_text(f"Open trades: {len(trading_bot.trades)}\nNo closed trades yet.")
            return
        
        wins = [t for t in closed_trades if t['pnl'] > 0]
        losses = [t for t in closed_trades if t['pnl'] <= 0]
        
        total_pnl = sum(t['pnl'] for t in closed_trades)
        win_rate = (len(wins) / len(closed_trades) * 100) if closed_trades else 0
        
        avg_win = sum(t['pnl'] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t['pnl'] for t in losses) / len(losses) if losses else 0
        
        profit_factor = abs(sum(t['pnl'] for t in wins)) / abs(sum(t['pnl'] for t in losses)) if losses else 0
        
        equity = trading_bot.capital + total_pnl
        
        stats_msg = f"""
<b>📊 TRADING STATS</b>

<b>Total Trades:</b> {len(closed_trades)}
<b>Wins:</b> {len(wins)} ({win_rate:.1f}%)
<b>Losses:</b> {len(losses)}

<b>Total PnL:</b> ${total_pnl:+,.2f}
<b>Equity:</b> ${equity:,.2f}
<b>Return:</b> {(total_pnl/trading_bot.capital)*100:+.1f}%

<b>Average Win:</b> ${avg_win:+,.2f}
<b>Average Loss:</b> ${avg_loss:+,.2f}
<b>Profit Factor:</b> {profit_factor:.2f}x

Capital: ${trading_bot.capital:.2f}
"""
        await update.message.reply_text(stats_msg, parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        await update.message.reply_text(f"Error: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all messages - try to parse signals"""
    try:
        text = update.message.text
        
        # Try to parse signal
        signal = trading_bot.parse_signal(text)
        if not signal:
            return
        
        # Calculate position
        position = trading_bot.calculate_position(signal)
        if not position:
            await update.message.reply_text("❌ Could not calculate position size")
            return
        
        # Format and send
        msg_id = update.message.message_id
        formatted = trading_bot.format_signal_message(signal, position, msg_id)
        
        # Store trade
        trading_bot.trades[msg_id] = {
            'signal': signal,
            'position': position,
            'timestamp': datetime.now().isoformat(),
            'pnl': None
        }
        
        # Create keyboard for exit
        keyboard = [
            [InlineKeyboardButton("Exit", callback_data=f"exit_{msg_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            formatted, 
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
        logger.info(f"✅ Signal parsed and sent (ID: {msg_id})")
        
    except Exception as e:
        logger.error(f"Message handler error: {e}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks"""
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("exit_"):
            msg_id = int(query.data.split("_")[1])
            
            if msg_id not in trading_bot.trades:
                await query.edit_message_text("Trade not found")
                return
            
            # Ask for exit price
            context.user_data['exit_trade_id'] = msg_id
            
            await query.edit_message_text(
                "Send exit price (e.g., 62500):",
                reply_markup=None
            )
            
    except Exception as e:
        logger.error(f"Button callback error: {e}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset all trades"""
    trading_bot.trades = {}
    await update.message.reply_text("✅ All trades reset")

async def set_capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set trading capital"""
    try:
        if not context.args:
            await update.message.reply_text(f"Current capital: ${trading_bot.capital:.2f}\n\nUsage: /capital 100")
            return
        
        amount = float(context.args[0])
        trading_bot.capital = amount
        await update.message.reply_text(f"✅ Capital set to ${amount:.2f}")
    except ValueError:
        await update.message.reply_text("Invalid amount")

def main():
    """Main function"""
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN not set")
        return
    
    app = Application.builder().token(token).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("capital", set_capital))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("🤖 Trading Signal Tracker started")
    app.run_polling()

if __name__ == "__main__":
    main()
