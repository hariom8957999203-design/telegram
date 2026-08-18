import time
import telebot
import os
import threading
from flask import Flask

app = Flask(__name__)

# Direct Token & Chat ID
API_TOKEN = "8723657210:AAHyasRlDYvtpTZ3_dEWBdCZokH_eDcRPZk"  # Double quotes ke andar exact token paste karein
CHAT_ID = "8723657210"

bot = telebot.TeleBot(API_TOKEN)
# =====================================================================
# 1. RENDER PORT BINDING ENGINE (24/7 Uptime)
# =====================================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "⚡ DUAL STRATEGY AUTOMATED SCANNER ENGINE IS RUNNING 24/7 ⚡"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# =====================================================================
# 2. CONFIGURATION & WATCHLIST
# =====================================================================

WATCHLIST = [
    "NBCC.NS", "UCOBANK.NS", "IDEA.NS", "IDBI.NS", "IFCI.NS",
    "IOB.NS", "PCJEWELLER.NS", "SEPC.NS", "GTLINFRA.NS", "JPPOWER.NS",
    "GMRINFRA.NS", "PNB.NS", "RTNPOWER.NS", "SOUTHBANK.NS", "CENTRALBK.NS",
    "PSB.NS", "NHPC.NS", "SUZLON.NS", "TRIDENT.NS", "IRB.NS"
]

API_TOKEN = "8723657210:AAHyasRlDYvtpTZ3_dEWBdCZokH_eDcRPZk"
CHAT_ID = "8723657210"

bot = telebot.TeleBot(API_TOKEN)
# Duplicate alert rokne ke liye alag-alag trackers
last_indicator_signals = {}
last_zone_signals = {}

# =====================================================================
# 3. REAL-TIME DATA & ALL INDICATORS ENGINE (PURANA + NAYA)
# =====================================================================
def get_realtime_df(symbol, period, interval):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True)
        if df.empty: return df

        try:
            live_price = ticker.fast_info.get('lastPrice') or ticker.fast_info.get('last_price')
            if live_price and not np.isnan(live_price):
                live_price = float(live_price)
                df.loc[df.index[-1], 'Close'] = live_price
                if live_price > df.loc[df.index[-1], 'High']: df.loc[df.index[-1], 'High'] = live_price
                if live_price < df.loc[df.index[-1], 'Low']: df.loc[df.index[-1], 'Low'] = live_price
        except Exception:
            pass

        return df
    except Exception:
        return pd.DataFrame()

def clean_and_flatten_df(df):
    if df.empty: return df
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0] for col in df.columns]
    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    cleaned_df = pd.DataFrame(index=df.index)
    for col in required_cols:
        if col in df.columns:
            cleaned_df[col] = pd.to_numeric(df[col].values.flatten(), errors='coerce')
    return cleaned_df.dropna(subset=['Close'])

def calculate_indicators(df):
    df = clean_and_flatten_df(df)
    if len(df) < 50: return df

    # AAPKE PURANE CODE KE SARE INDICATORS
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()

    tp = (df['High'] + df['Low'] + df['Close']) / 3
    df['VWAP'] = (tp * df['Volume']).rolling(20).sum() / (df['Volume'].rolling(20).sum() + 1e-10)

    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / (loss + 1e-10)
    df['RSI'] = 100 - (100 / (1 + rs))

    df['VOL_MA'] = df['Volume'].rolling(20).mean()

    high, low, close_prev = df['High'], df['Low'], df['Close'].shift(1)
    tr = pd.concat([high - low, (high - close_prev).abs(), (low - close_prev).abs()], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()

    upmove = df['High'].diff()
    downmove = df['Low'].shift(1) - df['Low']
    plus_dm = np.where((upmove > downmove) & (upmove > 0), upmove, 0.0)
    minus_dm = np.where((downmove > upmove) & (downmove > 0), downmove, 0.0)
    tr_sum = tr.rolling(14).sum() + 1e-10
    plus_di = 100 * (pd.Series(plus_dm, index=df.index).rolling(14).sum() / tr_sum)
    minus_di = 100 * (pd.Series(minus_dm, index=df.index).rolling(14).sum() / tr_sum)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di + 1e-10)
    df['ADX'] = dx.rolling(14).mean()

    atr_multiplier = 2.0
    hl2 = (df['High'] + df['Low']) / 2
    df['UB'] = hl2 + (atr_multiplier * df['ATR'])
    df['LB'] = hl2 - (atr_multiplier * df['ATR'])
    df['ST_DIR'] = 1
    
    for i in range(1, len(df)):
        if df['Close'].iloc[i-1] > df['UB'].iloc[i-1]: df.loc[df.index[i], 'UB'] = min(df['UB'].iloc[i], df['UB'].iloc[i-1])
        if df['Close'].iloc[i-1] < df['LB'].iloc[i-1]: df.loc[df.index[i], 'LB'] = max(df['LB'].iloc[i], df['LB'].iloc[i-1])
        if df['Close'].iloc[i] > df['UB'].iloc[i-1]: df.loc[df.index[i], 'ST_DIR'] = 1
        elif df['Close'].iloc[i] < df['LB'].iloc[i-1]: df.loc[df.index[i], 'ST_DIR'] = -1
        else: df.loc[df.index[i], 'ST_DIR'] = df['ST_DIR'].iloc[i-1]

    df.ffill(inplace=True)
    df.fillna(0.0, inplace=True)
    return df

# =====================================================================
# 4. STRATEGY 1: PURANA INDICATOR SIGNAL ENGINE
# =====================================================================
def generate_indicator_signals(df_curr, df_macro):
    if len(df_curr) < 2 or len(df_macro) < 2:
        return "HOLD", 0.0, 1.0, "Data insufficient"

    m = df_macro.iloc[-1]
    macro_bullish = (m['Close'] > m['EMA_200']) or (m['ST_DIR'] == 1)
    macro_bearish = (m['Close'] < m['EMA_200']) or (m['ST_DIR'] == -1)

    p = df_curr.iloc[-1]
    close, ema9, ema21, vwap = float(p['Close']), float(p['EMA_9']), float(p['EMA_21']), float(p['VWAP'])
    rsi, adx, atr = float(p['RSI']), float(p['ADX']), float(p['ATR'])
    volume, vol_ma, st_dir = float(p['Volume']), float(p['VOL_MA']), p['ST_DIR']

    is_volume_confirmed = volume > (vol_ma * 0.85)
    is_trend_strong = adx > 15.0

    if (ema9 > ema21) and (close > vwap) and (st_dir == 1) and macro_bullish:
        if (40.0 <= rsi <= 75.0) and is_volume_confirmed and is_trend_strong:
            return "BUY", close, atr, "Live Breakout Confirmed (EMA + VWAP + SuperTrend)"

    elif (ema9 < ema21) and (close < vwap) and (st_dir == -1) and macro_bearish:
        if (25.0 <= rsi <= 60.0) and is_volume_confirmed and is_trend_strong:
            return "SELL", close, atr, "Live Breakdown Confirmed (EMA + VWAP + SuperTrend)"

    return "HOLD", close, atr, "No trade setup"

def calculate_risk(signal, entry, atr):
    risk = (atr * 1.5) if atr > 0 else (entry * 0.012)
    if "BUY" in signal:
        return round(entry - risk, 2), round(entry + (risk * 1.5), 2), round(entry + (risk * 3.0), 2)
    elif "SELL" in signal:
        return round(entry + risk, 2), round(entry - (risk * 1.5), 2), round(entry - (risk * 3.0), 2)
    return "N/A", "N/A", "N/A"

# =====================================================================
# 5. STRATEGY 2: NAYA DEMAND & SUPPLY ZONE ENGINE (GTF EYE STYLE)
# =====================================================================
def detect_demand_supply_zones(df, lookback=60):
    if len(df) < lookback: return None, None
    recent_df = df.tail(lookback).copy()
    atr = recent_df['ATR'].iloc[-1] if 'ATR' in recent_df.columns else (recent_df['High'] - recent_df['Low']).mean()

    demand_zones, supply_zones = [], []

    for i in range(2, len(recent_df) - 1):
        prev_candle, curr_candle = recent_df.iloc[i-1], recent_df.iloc[i]
        body_size = abs(curr_candle['Close'] - curr_candle['Open'])

        if curr_candle['Close'] > curr_candle['Open'] and body_size > (1.1 * atr):
            z_low = round(float(min(prev_candle['Low'], curr_candle['Low'])), 2)
            z_high = round(float(max(prev_candle['Open'], prev_candle['Close'])), 2)
            demand_zones.append({'low': z_low, 'high': z_high})

        elif curr_candle['Close'] < curr_candle['Open'] and body_size > (1.1 * atr):
            z_high = round(float(max(prev_candle['High'], curr_candle['High'])), 2)
            z_low = round(float(min(prev_candle['Open'], prev_candle['Close'])), 2)
            supply_zones.append({'low': z_low, 'high': z_high})

    return (demand_zones[-1] if demand_zones else None), (supply_zones[-1] if supply_zones else None)

def generate_zone_signals(df):
    if len(df) < 30:
        return "HOLD", 0.0, 0.0, 0.0, 0.0, None, "Insufficient Data"

    close = round(float(df['Close'].iloc[-1]), 2)
    atr = float(df['ATR'].iloc[-1]) if 'ATR' in df.columns else close * 0.01

    demand, supply = detect_demand_supply_zones(df)

    if demand and (demand['low'] * 0.998 <= close <= demand['high'] * 1.008):
        sl = round(demand['low'] - (0.3 * atr), 2)
        risk = max(close - sl, close * 0.01)
        return "BUY_DEMAND", close, sl, round(close + (1.5 * risk), 2), round(close + (3.0 * risk), 2), demand, "Stock Reached Demand Zone (Buy Zone Active)"

    elif supply and (supply['low'] * 0.992 <= close <= supply['high'] * 1.002):
        sl = round(supply['high'] + (0.3 * atr), 2)
        risk = max(sl - close, close * 0.01)
        return "SELL_SUPPLY", close, sl, round(close - (1.5 * risk), 2), round(close - (3.0 * risk), 2), supply, "Stock Reached Supply Zone (Sell Zone Active)"

    return "HOLD", close, 0.0, 0.0, 0.0, None, "No Zone Trigger"

# =====================================================================
# 6. AUTOMATED WATCHLIST SCANNER (2 ALAG-ALAG TELEGRAM MESSAGES)
# =====================================================================
def auto_market_scanner():
    while True:
        try:
            for symbol in WATCHLIST:
                df_curr_raw = get_realtime_df(symbol, period="1mo", interval="15m")
                df_macro_raw = get_realtime_df(symbol, period="3mo", interval="1h")

                if df_curr_raw.empty or df_macro_raw.empty: continue

                df_curr = calculate_indicators(df_curr_raw)
                df_macro = calculate_indicators(df_macro_raw)

                # -------------------------------------------------------------
                # CODE 1 ANALYSIS: QUANT INDICATOR STRATEGY
                # -------------------------------------------------------------
                ind_signal, ind_entry, ind_atr, ind_reason = generate_indicator_signals(df_curr, df_macro)
                
                if ind_signal in ["BUY", "SELL"]:
                    if last_indicator_signals.get(symbol) != ind_signal:
                        last_indicator_signals[symbol] = ind_signal
                        sl, t1, t2 = calculate_risk(ind_signal, ind_entry, ind_atr)
                        label = "🟢 [QUANT BUY SIGNAL]" if ind_signal == "BUY" else "🔴 [QUANT SELL SIGNAL]"
                        
                        msg1 = (
                            f"{label}\n"
                            f"Stock: **{symbol}**\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"⚙️ **Strategy:** Indicator Breakout\n"
                            f"💰 **ENTRY PRICE:** ₹{round(ind_entry, 2)}\n"
                            f"🛑 **STOP LOSS:** ₹{sl}\n"
                            f"🎯 **TARGET 1:** ₹{t1}\n"
                            f"🎯 **TARGET 2:** ₹{t2}\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"📋 **REASON:** _{ind_reason}_"
                        )
                        if CHAT_ID: bot.send_message(CHAT_ID, msg1, parse_mode="Markdown")
                else:
                    last_indicator_signals[symbol] = "HOLD"

                # -------------------------------------------------------------
                # CODE 2 ANALYSIS: DEMAND & SUPPLY ZONE STRATEGY (GTF EYE STYLE)
                # -------------------------------------------------------------
                zone_signal, z_entry, z_sl, z_t1, z_t2, zone, z_reason = generate_zone_signals(df_curr)

                if zone_signal in ["BUY_DEMAND", "SELL_SUPPLY"]:
                    if last_zone_signals.get(symbol) != zone_signal:
                        last_zone_signals[symbol] = zone_signal
                        
                        label_z = "🟢 [DEMAND ZONE ALERT]" if zone_signal == "BUY_DEMAND" else "🔴 [SUPPLY ZONE ALERT]"
                        msg2 = (
                            f"{label_z}\n"
                            f"Stock: **{symbol}**\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"📍 **ZONE RANGE:** ₹{zone['low']} - ₹{zone['high']}\n"
                            f"💰 **ENTRY PRICE:** ₹{z_entry}\n"
                            f"🛑 **STOP LOSS:** ₹{z_sl}\n"
                            f"🎯 **TARGET 1:** ₹{z_t1}\n"
                            f"🎯 **TARGET 2:** ₹{z_t2}\n"
                            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"📋 **REASON:** _{z_reason}_"
                        )
                        if CHAT_ID: bot.send_message(CHAT_ID, msg2, parse_mode="Markdown")
                else:
                    last_zone_signals[symbol] = "HOLD"

                time.sleep(2)
        except Exception as e:
            print(f"Scanner Error: {e}")

        time.sleep(180) # Rescan every 3 minutes

# =====================================================================
# 7. TELEGRAM COMMAND HANDLERS (ALAG-ALAG MESSAGES IN BOT CHAT)
# =====================================================================
@bot.message_handler(commands=['start', 'status'])
def show_status(message):
    bot.reply_to(message, "📡 Running Dual-Engine Analysis across 20 Watchlist Stocks...")
    summary = "📊 **DUAL STRATEGY WATCHLIST STATUS** 📊\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    for symbol in WATCHLIST:
        try:
            df_curr_raw = get_realtime_df(symbol, period="1mo", interval="15m")
            df_macro_raw = get_realtime_df(symbol, period="3mo", interval="1h")
            if df_curr_raw.empty: continue
            
            df_curr = calculate_indicators(df_curr_raw)
            df_macro = calculate_indicators(df_macro_raw)
            
            ind_signal, entry, _, _ = generate_indicator_signals(df_curr, df_macro)
            zone_signal, _, _, _, _, _, _ = generate_zone_signals(df_curr)

            icon1 = "🟢" if ind_signal == "BUY" else ("🔴" if ind_signal == "SELL" else "🟡")
            icon2 = "🟢" if zone_signal == "BUY_DEMAND" else ("🔴" if zone_signal == "SELL_SUPPLY" else "⚪")

            summary += f"{symbol} @ ₹{round(entry,2)} -> Quant: {icon1} `{ind_signal}` | Zone: {icon2} `{zone_signal}`\n"
        except Exception:
            summary += f"⚠️ **{symbol}**: Data Error\n"
            
    bot.reply_to(message, summary, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
@bot.message_handler(func=lambda message: True)
def process_manual_request(message):
    print("🔥 TELEGRAM REQUEST RECEIVED")
    print("👤 CHAT ID:", message.chat.id)
    print("📝 USER MESSAGE:", message.text)

    try:
        bot.reply_to(
            message,
            "🚀 Analyzing your stock signal..."
        )

        # User message ko symbol maan rahe hain
        symbol = message.text.strip().upper()

        if not symbol:
            bot.reply_to(message, "⚠️ Stock symbol bhejo. Example: RELIANCE")
            return

        print("📊 ANALYZING SYMBOL:", symbol)

        # Yahan tumhara existing analysis code chalega
        # ------------------------------------------------
        # Existing analysis code yahan rakho
        # ------------------------------------------------

    except Exception as e:
        import traceback

        print("❌ SIGNAL ERROR:", repr(e))
        traceback.print_exc()

        bot.reply_to(
            message,
            f"⚠️ Signal error: {str(e)[:300]}"
        )
    try:
        df_curr_raw = get_realtime_df(symbol, period="1mo", interval="15m")
        df_macro_raw = get_realtime_df(symbol, period="3mo", interval="1h")

        if df_curr_raw.empty or df_macro_raw.empty:
            bot.reply_to(message, f"❌ `{symbol}` invalid symbol. Put .NS for NSE stocks (e.g. RELIANCE.NS).")
            return

        df_curr = calculate_indicators(df_curr_raw)
        df_macro = calculate_indicators(df_macro_raw)

        # 1. MESSAGE 1: QUANT INDICATOR STRATEGY
        ind_signal, entry, atr, log_reason = generate_indicator_signals(df_curr, df_macro)
        sl, t1, t2 = calculate_risk(ind_signal, entry, atr)
        
        msg1 = (
            f"📊 **[STRATEGY 1: QUANT BREAKOUT]**\n"
            f"Asset: **{symbol}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 **ACTION:** `{ind_signal}`\n"
            f"💰 **LIVE PRICE:** ₹{round(entry, 2)}\n"
            f"🛑 **SL:** ₹{sl} | 🎯 **T1:** ₹{t1} | 🎯 **T2:** ₹{t2}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 **NOTE:** _{log_reason}_"
        )
        bot.send_message(message.chat.id, msg1, parse_mode="Markdown")

        # 2. MESSAGE 2: DEMAND & SUPPLY ZONE STRATEGY
        z_signal, z_entry, z_sl, z_t1, z_t2, zone, z_reason = generate_zone_signals(df_curr)
        demand, supply = detect_demand_supply_zones(df_curr)

        demand_info = f"₹{demand['low']} - ₹{demand['high']}" if demand else "None"
        supply_info = f"₹{supply['low']} - ₹{supply['high']}" if supply else "None"

        msg2 = (
            f"📍 **[STRATEGY 2: DEMAND & SUPPLY ZONES]**\n"
            f"Asset: **{symbol}**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🟢 **NEAREST DEMAND ZONE:** `{demand_info}`\n"
            f"🔴 **NEAREST SUPPLY ZONE:** `{supply_info}`\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📢 **ACTION:** `{z_signal}`\n"
            f"🛑 **SL:** ₹{z_sl} | 🎯 **T1:** ₹{z_t1} | 🎯 **T2:** ₹{z_t2}\n"
            f"📋 **NOTE:** _{z_reason}_"
        )
except Exception as e:
        print("❌ SIGNAL ERROR:", repr(e))
        traceback.print_exc()
        try:
            bot.reply_to(
                message,
                f"⚠️ Signal error:\n{str(e)[:500]}"
            )
        except Exception:
            pass
    except Exception as send_error:
        print("❌ TELEGRAM SEND ERROR:", repr(send_error))

# ============================================================
# 8. MAIN EXECUTION ENGINE
# ============================================================

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=auto_market_scanner, daemon=True).start()

    print("🚀 Dual Strategy Quantum Bot active.")

    # Force reset old sessions
    try:
        print("🔄 Starting bot polling...")

        bot.infinity_polling(
            timeout=20,
            long_polling_timeout=10,
            skip_pending=True
        )

    except Exception as e:
        print(f"❌ Bot polling error: {e}")
