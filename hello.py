
import telebot
import yfinance as yf
import pandas as pd
import numpy as np

# Telegram Configuration
API_TOKEN = '8993700626:AAHmYnFkc_5tFHGg-ksmkxalkp4iC_f28Pw'
bot = telebot.TeleBot(API_TOKEN)

def calculate_manual_indicators(df):
    """Bina kisi external library ke purely pandas aur math se indicators nikalna"""
    if df.empty or len(df) < 50:
        return None, "BEARISH"

    # Multi-index fix karein agar yfinance matrix bhej raha ho
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]

    # Data flat aur numeric karein
    close_prices = pd.to_numeric(df['Close'].values.flatten(), errors='coerce')
    high_prices = pd.to_numeric(df['High'].values.flatten(), errors='coerce')
    low_prices = pd.to_numeric(df['Low'].values.flatten(), errors='coerce')
    volume_data = pd.to_numeric(df['Volume'].values.flatten(), errors='coerce')

    df_clean = pd.DataFrame({
        'Close': close_prices,
        'High': high_prices,
        'Low': low_prices,
        'Volume': volume_data
    }, index=df.index)
    
    df_clean.dropna(subset=['Close'], inplace=True)

    # 1. EMA Calculation
    df_clean['EMA_9'] = df_clean['Close'].ewm(span=9, adjust=False).mean()
    df_clean['EMA_21'] = df_clean['Close'].ewm(span=21, adjust=False).mean()
    df_clean['EMA_200'] = df_clean['Close'].ewm(span=200, adjust=False).mean()

    # 2. RSI Calculation
    delta = df_clean['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-10)
    df_clean['RSI'] = 100 - (100 / (1 + rs))

    # 3. Simple Volume MA
    df_clean['VOL_MA'] = df_clean['Volume'].rolling(window=20).mean()

    # Default missing handling
    df_clean.ffill(inplace=True)
    df_clean.fillna(0.0, inplace=True)

    # Trend detection based on 200 EMA
    latest_trend = "BULLISH" if df_clean['Close'].iloc[-1] > df_clean['EMA_200'].iloc[-1] else "BEARISH"

    return df_clean, latest_trend

def generate_signals(df, htf_trend):
    if df is None or len(df) < 2:
        return "HOLD", 0.0

    p = df.iloc[-2] # Last closed candle
    
    close = float(p.get('Close', 0.0))
    ema9 = float(p.get('EMA_9', 0.0))
    ema21 = float(p.get('EMA_21', 0.0))
    rsi = float(p.get('RSI', 50.0))
    volume = float(p.get('Volume', 0.0))
    vol_ma = float(p.get('VOL_MA', 1.0))

    is_volume_confirmed = volume > (vol_ma * 1.1)

    # Simple No-Repaint Pure Trading Strategy
    if (ema9 > ema21) and (45.0 < rsi < 68.0) and htf_trend == "BULLISH" and is_volume_confirmed:
        return "BUY", close
    elif (ema9 < ema21) and (32.0 < rsi < 55.0) and htf_trend == "BEARISH" and is_volume_confirmed:
        return "SELL", close
    
    return "HOLD", close

@bot.message_handler(commands=['start', 'dashboard'])
def show_dashboard(message):
    help_text = (
        "📊 **QUANT ALGO DASHBOARD ACTIVE (CLOUD LIVE)** 📊\n\n"
        "Kisi bhi stock ka live mathematical signal check karne ke liye uska name bhejein:\n"
        "👉 Indian Stocks: `SBIN.NS`, `NBCC.NS`\n"
        "👉 US Stocks: `AAPL`, `TSLA`"
    )
    bot.reply_to(message, help_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def process_signal_request(message):
    symbol = message.text.upper().strip()
    if symbol.startswith('/'): return

    bot.reply_to(message, f"🔍 Running Math Calculations & Scanning for {symbol}...")

    try:
        df_curr = yf.download(symbol, period="1mo", interval="15m", auto_adjust=True)
        if df_curr.empty:
            bot.reply_to(message, f"❌ `{symbol}` ka valid data nahi mila. Sahi symbol type karein.")
            return

        df_analysed, trend_state = calculate_manual_indicators(df_curr)
        if df_analysed is None:
            bot.reply_to(message, "❌ Analysis ke liye data kam hai.")
            return

        signal, entry = generate_signals(df_analysed, trend_state)
        latest_data = df_analysed.iloc[-2]

        label = "🟡"
        if "BUY" in signal: label = "🟢"
        if "SELL" in signal: label = "🔴"

        # Safe dynamic Stoploss/Targets based on 1.5% fixed risk matrix
        risk_factor = entry * 0.015
        sl = round((entry - risk_factor) if "BUY" in signal else (entry + risk_factor), 2)
        t1 = round((entry + risk_factor * 1.5) if "BUY" in signal else (entry - risk_factor * 1.5), 2)

        dashboard = (
            f"{label} **SIGNAL ALERT: {symbol}** {label}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📢 **Action:** {signal}\n"
            f"💰 **Price:** ₹{round(entry, 2)}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🛡️ **DYNAMIC RISK TARGETS**\n"
            f"🛑 **Stop Loss (SL):** ₹{sl}\n"
            f"🎯 **Target (1:1.5):** ₹{t1}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📈 **MATH METRICS**\n"
            f"• Macro Trend State: {trend_state}\n"
            f"• Calculated RSI: {round(float(latest_data.get('RSI', 50)), 2)}\n"
            f"• Volume vs Average: {'🔥 High Vol' if float(latest_data.get('Volume', 0)) > float(latest_data.get('VOL_MA', 0)) else '💤 Normal'}"
        )
        bot.reply_to(message, dashboard, parse_mode="Markdown")

    except Exception as e:
        bot.reply_to(message, f"⚠️ Analysis scan down. Dobara type karke bhejein.")

print("🚀 Cloud Engine Started Successfully!")
bot.infinity_polling()