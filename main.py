# ==============================================================================
#  🦅 UNIFIED TRADE HAWK & EAGLE EYE PRO — Advanced Trading Terminal
#  Deploy: https://share.streamlit.io  (Works on Mobile & Desktop)
#  Run local: streamlit run unified_trading_terminal.py
# ==============================================================================

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, time
import pytz
import requests
import re as _re
import logging

# Logger setup
_log = logging.getLogger("unified_terminal")
logging.basicConfig(level=logging.WARNING)
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

# ─── PAGE CONFIGURATION ───
st.set_page_config(
    page_title="Trade Hawk & Eagle Eye Terminal",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── CUSTOM CSS FOR IMMERSIVE DARK TRADING THEME ───
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Inter:wght@300;400;600;800&display=swap');
    
    /* Global Overrides */
    .stApp {
        background-color: #020b18;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    
    /* Top Header Styling */
    .terminal-header {
        background: linear-gradient(135deg, #05162e 0%, #020b18 100%);
        padding: 18px;
        border-radius: 8px;
        border-left: 5px solid #00d463;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0, 212, 99, 0.08);
    }
    
    /* Metrics and Indicators styling */
    .metric-card {
        background: #08182e;
        border: 1px solid #102a45;
        border-radius: 6px;
        padding: 12px 16px;
        text-align: center;
        box-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    .metric-val {
        font-family: 'Share Tech Mono', monospace;
        font-size: 20px;
        font-weight: bold;
    }
    
    /* Dynamic Signal Banners */
    .buy-zone {
        background: rgba(0, 212, 99, 0.1);
        border: 1px solid #00d463;
        border-radius: 6px;
        padding: 15px;
        color: #00d463;
        font-weight: bold;
        animation: pulse-green 2s infinite;
    }
    .sell-zone {
        background: rgba(255, 61, 61, 0.1);
        border: 1px solid #ff3d3d;
        border-radius: 6px;
        padding: 15px;
        color: #ff3d3d;
        font-weight: bold;
        animation: pulse-red 2s infinite;
    }
    
    @keyframes pulse-green {
        0% { box-shadow: 0 0 0 0 rgba(0, 212, 99, 0.4); }
        70% { box-shadow: 0 0 0 8px rgba(0, 212, 99, 0); }
        100% { box-shadow: 0 0 0 0 rgba(0, 212, 99, 0); }
    }
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(255, 61, 61, 0.4); }
        70% { box-shadow: 0 0 0 8px rgba(255, 61, 61, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 61, 61, 0); }
    }
</style>
""", unsafe_allow_html=True)

# ─── HELPER SCRIPT FOR WEB SPEECH API (AUDIO FEEDBACK) ───
def trigger_audio_alert(text):
    """Executes sound alerts directly through user's web browser with zero local packages"""
    js_code = f"""
    <script>
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel();
            var msg = new SpeechSynthesisUtterance('{text}');
            msg.rate = 1.0;
            msg.pitch = 1.1;
            window.speechSynthesis.speak(msg);
        }}
    </script>
    """
    st.components.v1.html(js_code, height=0, width=0)

# ─── DHAN API CREDENTIALS SANITIZATION & RETRIEVAL ───
def get_clean_dhan_credentials():
    """Extracts, cleans, and validates Dhan API credentials from Streamlit secrets"""
    try:
        if "dhan" in st.secrets:
            raw_token = st.secrets["dhan"].get("access_token", "")
            raw_client_id = st.secrets["dhan"].get("client_id", "")
            
            # Clean whitespaces and newlines
            clean_token = _re.sub(r'\s+', '', raw_token).strip()
            clean_client_id = _re.sub(r'\s+', '', str(raw_client_id)).strip()
            
            if clean_token and clean_client_id:
                return {"token": clean_token, "client_id": clean_client_id}
    except Exception as e:
         _log.warning(f"Dhan Secrets missing or inaccessible: {e}")
    return None

# ─── TECHNICAL ALGORITHMS ENGINE (TRADE HAWK SYSTEM) ───
def calculate_indicators(df):
    """Computes pure technical indicators used for Trend and Signal analysis"""
    if len(df) < 20:
        return df
        
    # EMAs
    df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
    
    # RSI
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    df['EMA_12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA_26'] = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    return df

def generate_signals(df):
    """Processes combination rules of Supertrend, EMA, and RSI to output exact signals"""
    if len(df) < 2 or 'EMA_9' not in df.columns:
        return "NEUTRAL", 0.0, 0.0, 0.0
        
    last_row = df.iloc[-1]
    prev_row = df.iloc[-2]
    
    close = last_row['Close']
    rsi = last_row['RSI']
    ema9 = last_row['EMA_9']
    ema21 = last_row['EMA_21']
    
    # Check crossover triggers
    bullish_crossover = (prev_row['EMA_9'] <= prev_row['EMA_21']) and (ema9 > ema21)
    bearish_crossover = (prev_row['EMA_9'] >= prev_row['EMA_21']) and (ema9 < ema21)
    
    # Strategy validation logic
    if bullish_crossover and rsi > 45:
        target = close + (close * 0.015)  # 1.5% target
        stoploss = close - (close * 0.007) # 0.7% stoploss
        return "STRONG BUY", round(target, 2), round(stoploss, 2), round(close, 2)
        
    elif bearish_crossover and rsi < 55:
        target = close - (close * 0.015)
        stoploss = close + (close * 0.007)
        return "STRONG SELL", round(target, 2), round(stoploss, 2), round(close, 2)
        
    return "HOLD / NEUTRAL", 0.0, 0.0, 0.0

# ─── DATA INGESTION ENGINE (HYBRID BACKUP INTERACTION) ───
@st.cache_data(ttl=10)
def fetch_market_data(symbol, interval="5m", period="5d"):
    """Fetches high-precision stock data using fallback paths for maximum availability"""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(interval=interval, period=period)
        if not df.empty:
            return df
    except Exception as ex:
        _log.error(f"yFinance default pipeline error: {ex}. Attempting fallback...")
        
    # Alternate direct HTTP Fallback implementation
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={interval}&range={period}"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=8)
        data = response.json()
        
        result = data['chart']['result'][0]
        timestamps = result['timestamp']
        indicators = result['indicators']['quote'][0]
        
        df_alt = pd.DataFrame({
            'Open': indicators['open'],
            'High': indicators['high'],
            'Low': indicators['low'],
            'Close': indicators['close'],
            'Volume': indicators['volume']
        }, index=pd.to_datetime(timestamps, unit='s'))
        
        df_alt.index = df_alt.index.tz_localize('UTC').tz_convert('Asia/Kolkata')
        return df_alt.dropna()
    except Exception as final_ex:
        st.error(f"Failed to fetch market data from both streams: {final_ex}")
        return pd.DataFrame()

# ─── TERMINAL HEADER ───
st.markdown("""
<div class="terminal-header">
    <h1 style="margin:0; font-family:'Inter'; font-weight:800; font-size:26px; color:#00d463; letter-spacing:0.5px;">
        🦅 UNIFIED TRADE HAWK & EAGLE EYE SYSTEM
    </h1>
    <p style="margin:5px 0 0 0; font-size:12px; color:#88ccaa; font-family:'Share Tech Mono';">
        INTEGRATED ALGORITHMIC SIGNAL GENERATOR & ADVANCED TERMINAL
    </p>
</div>
""", unsafe_allow_html=True)

# ─── SIDEBAR CONTROL PANEL ───
st.sidebar.markdown("### 🎛️ Terminal Controls")
symbol_input = st.sidebar.text_input("Enter Ticker Symbol (e.g. Reliance.NS, ^NSEI):", "^NSEI")
timeframe = st.sidebar.selectbox("Select Timeframe Interval:", ["1m", "5m", "15m", "1h", "1d"], index=1)
sound_enabled = st.sidebar.toggle("Enable Voice Alerts 🔊", value=True)

# Validate Dhan state
dhan_config = get_clean_dhan_credentials()
st.sidebar.markdown("---")
st.sidebar.markdown("### 🔌 Connection Status")
if dhan_config:
    st.sidebar.success(f"Dhan Status: CONNECTED (ID: {dhan_config['client_id']})")
else:
    st.sidebar.info("Dhan Connection: running local/unauthenticated mode.")

# ─── CORE PIPELINE RUNNER ───
if symbol_input:
    with st.spinner(f"Analyzing {symbol_input} ticker matrix..."):
        df = fetch_market_data(symbol_input, interval=timeframe)
        
    if not df.empty:
        # Calculate Indicators & Signals
        df = calculate_indicators(df)
        signal, target, stoploss, entry = generate_signals(df)
        
        last_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2] if len(df) > 1 else last_price
        price_change = last_price - prev_price
        pct_change = (price_change / prev_price) * 100
        
        # Audio alert trigger
        if sound_enabled and signal != "HOLD / NEUTRAL":
            trigger_audio_alert(f"Attention, New {signal} Signal triggered for {symbol_input} at {round(last_price, 1)}")
            
        # ─ Top Metrics Row ─
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            color = "#00d463" if price_change >= 0 else "#ff3d3d"
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size:11px; color:#88a2c4;">LAST TRADED PRICE</div>
                <div class="metric-val" style="color:{color};">{last_price:,.2f}</div>
                <div style="font-size:10px; color:{color};">{'▲' if price_change>=0 else '▼'} {price_change:+.2f} ({pct_change:+.2f}%)</div>
            </div>
            """, unsafe_allow_html=True)
        with m2:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size:11px; color:#88a2c4;">14-PERIOD RSI</div>
                <div class="metric-val" style="color:#ffd000;">{df['RSI'].iloc[-1]:.2f}</div>
                <div style="font-size:10px; color:#88ccaa;">Indicator Signal: {'Overbought' if df['RSI'].iloc[-1] > 70 else 'Oversold' if df['RSI'].iloc[-1] < 30 else 'Neutral'}</div>
            </div>
            """, unsafe_allow_html=True)
        with m3:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size:11px; color:#88a2c4;">EMA SPREAD (9/21)</div>
                <div class="metric-val" style="color:#00d4aa;">{(df['EMA_9'].iloc[-1] - df['EMA_21'].iloc[-1]):+.2f}</div>
                <div style="font-size:10px; color:#88ccaa;">EMA 9: {df['EMA_9'].iloc[-1]:.2f}</div>
            </div>
            """, unsafe_allow_html=True)
        with m4:
            st.markdown(f"""
            <div class="metric-card">
                <div style="font-size:11px; color:#88a2c4;">MACD HISTOGRAM</div>
                <div class="metric-val" style="color:#3d9be9;">{(df['MACD'].iloc[-1] - df['Signal_Line'].iloc[-1]):+.4f}</div>
                <div style="font-size:10px; color:#88ccaa;">Line: {df['MACD'].iloc[-1]:.4f}</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # ─ Main Workspace Layout (Signals Panel & Chart) ─
        col_left, col_right = st.columns([1, 2])
        
        with col_left:
            st.markdown("### 📊 Trade Signal Matrix")
            if signal == "STRONG BUY":
                st.markdown(f"""
                <div class="buy-zone">
                    <h3>🚀 HAWK BUY SIGNAL TRIGGERED</h3>
                    <p style="margin: 3px 0 10px 0;">Criteria matched for bullish momentum.</p>
                    <hr style="border-color:#00d463;">
                    <div style="font-family:'Share Tech Mono'; font-size:15px; line-height:2;">
                        Entry Price: <b>{entry}</b><br>
                        Calculated Target: <b style="color:#ffffff;">{target} (1.5%)</b><br>
                        Stoploss Limit: <b style="color:#ffaeae;">{stoploss} (0.7%)</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            elif signal == "STRONG SELL":
                st.markdown(f"""
                <div class="sell-zone">
                    <h3>📉 HAWK SELL SIGNAL TRIGGERED</h3>
                    <p style="margin: 3px 0 10px 0;">Criteria matched for bearish expansion.</p>
                    <hr style="border-color:#ff3d3d;">
                    <div style="font-family:'Share Tech Mono'; font-size:15px; line-height:2;">
                        Entry Price: <b>{entry}</b><br>
                        Calculated Target: <b style="color:#ffffff;">{target} (1.5%)</b><br>
                        Stoploss Limit: <b style="color:#ffaeae;">{stoploss} (0.7%)</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background:#08182e; border:1px solid #102a45; padding:15px; border-radius:6px; color:#a0aec0;">
                    <h3 style="color:#ffffff;">🔍 SCANNING CHANNELS</h3>
                    <p>Indicators are currently neutral. No breakout condition met.</p>
                    <hr style="border-color:#102a45;">
                    <p style="font-size:12px; font-family:'Share Tech Mono';">
                        Wait for active EMA 9/21 cross with support from corresponding RSI level.
                    </p>
                </div>
                """, unsafe_allow_html=True)
                
            # Risk Management Info
            st.markdown("<br>", unsafe_allow_html=True)
            with st.expander("🛡️ Advanced Position Sizing Helper"):
                st.write("Sizing calculated on safe risk threshold (1% total bankroll):")
                risk_amt = st.number_input("Account Balance (INR):", min_value=1000, max_value=10000000, value=50000, step=5000)
                risk_per_trade = risk_amt * 0.01
                sl_distance = abs(last_price - stoploss) if stoploss > 0 else (last_price * 0.007)
                quantity = int(risk_per_trade / sl_distance) if sl_distance > 0 else 0
                st.info(f"Recommended Quantity: **{quantity} Units** (Max risk: ₹{risk_per_trade:.2f})")

        with col_right:
            st.markdown("### 📈 Interactive Terminal Analytics Chart")
            
            # Interactive Chart Builder
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, row_width=[0.3, 0.7])
            
            # Candlesticks
            fig.add_trace(go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                name="Price Candles", legendgroup="1"
            ), row=1, col=1)
            
            # Overlay EMAs
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_9'], name="EMA 9 (Fast)", line=dict(color='#ff9f43', width=1.5), legendgroup="1"), row=1, col=1)
            fig.add_trace(go.Scatter(x=df.index, y=df['EMA_21'], name="EMA 21 (Slow)", line=dict(color='#3d9be9', width=1.5), legendgroup="1"), row=1, col=1)
            
            # Subplot: RSI Panel
            fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI (14)", line=dict(color='#ffd000', width=1.2), legendgroup="2"), row=2, col=1)
            fig.add_hline(y=70, line_dash="dash", line_color="#ff3d3d", line_width=1, row=2, col=1)
            fig.add_hline(y=30, line_dash="dash", line_color="#00d463", line_width=1, row=2, col=1)
            
            # Update Layout for Immersive Look
            fig.update_layout(
                paper_bgcolor="#020b18",
                plot_bgcolor="#020b18",
                font_color="#e2e8f0",
                xaxis_rangeslider_visible=False,
                margin=dict(t=10, b=10, l=10, r=10),
                height=500,
                showlegend=True,
                xaxis=dict(gridcolor="#08182e"),
                yaxis=dict(gridcolor="#08182e"),
                xaxis2=dict(gridcolor="#08182e"),
                yaxis2=dict(gridcolor="#08182e", range=[10, 90])
            )
            
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.error("Market data stream was empty. Please check the stock symbol or connection parameters.")
