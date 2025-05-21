
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.trend import EMAIndicator, MACD
import requests

st.set_page_config(layout="wide")
st.title("🚀 Day Trading Dashboard (MACD, EMA, VWAP, Volume + Support/Resistance + News)")

# Sidebar Inputs
ticker = st.sidebar.text_input("Ticker Symbol", value="AAPL")
interval = st.sidebar.selectbox("Interval", ["1m", "5m", "15m", "30m", "1h"], index=2)
period = st.sidebar.selectbox("Data Period", ["1d", "5d", "7d"], index=1)

# --- Fetch Data ---
df = yf.download(ticker, interval=interval, period=period)

# Flatten columns if needed
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df.dropna(inplace=True)
close = df["Close"]

# --- Indicators ---
df["EMA9"] = EMAIndicator(close=close, window=9).ema_indicator()
df["EMA21"] = EMAIndicator(close=close, window=21).ema_indicator()
macd_calc = MACD(close=close)
df["MACD"] = macd_calc.macd()
df["MACD_Signal"] = macd_calc.macd_signal()
df["VWAP"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum() / df["Volume"].cumsum()
df["Volume_SMA20"] = df["Volume"].rolling(window=20).mean()
df["Volume_Spike"] = df["Volume"] > (1.5 * df["Volume_SMA20"])

# --- Support & Resistance ---
def detect_levels(data, sensitivity=3):
    levels = []
    for i in range(sensitivity, len(data) - sensitivity):
        if data["Low"][i] < data["Low"][i - sensitivity:i].min() and data["Low"][i] < data["Low"][i + 1:i + sensitivity + 1].min():
            levels.append(("support", data.index[i], data["Low"][i]))
        if data["High"][i] > data["High"][i - sensitivity:i].max() and data["High"][i] > data["High"][i + 1:i + sensitivity + 1].max():
            levels.append(("resistance", data.index[i], data["High"][i]))
    return levels

levels = detect_levels(df)

# --- Signal Logic with Support/Resistance Filter ---
df.dropna(inplace=True)
df["Signal"] = ""

support_levels = [price for kind, _, price in levels if kind == "support"]
resistance_levels = [price for kind, _, price in levels if kind == "resistance"]

last_price = df["Close"].iloc[-1]
near_support = any(abs(last_price - lvl) / last_price < 0.01 for lvl in support_levels)
near_resistance = any(abs(last_price - lvl) / last_price < 0.01 for lvl in resistance_levels)

buy_condition = (
    (df["MACD"] > df["MACD_Signal"]) &
    (df["EMA9"] > df["EMA21"]) &
    (df["Close"] > df["VWAP"]) &
    (df["Volume_Spike"]) &
    near_support
)

sell_condition = (
    (df["MACD"] < df["MACD_Signal"]) &
    (df["EMA9"] < df["EMA21"]) &
    (df["Close"] < df["VWAP"]) &
    (df["Volume_Spike"]) &
    near_resistance
)

df.loc[buy_condition, "Signal"] = "BUY"
df.loc[sell_condition, "Signal"] = "SELL"

# --- News Headlines (via Yahoo Finance RSS) ---
st.sidebar.markdown("### 📰 Latest News")
news_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
try:
    import feedparser
    feed = feedparser.parse(news_url)
    for entry in feed.entries[:5]:
        st.sidebar.write(f"• [{entry.title}]({entry.link})")
except:
    st.sidebar.warning("Unable to fetch news.")

# --- Display Latest Signal ---
latest = df.iloc[-1]
st.subheader(f"📊 Latest Signal for {ticker}")
st.write(f"**MACD:** {latest['MACD']:.2f} | **MACD Signal:** {latest['MACD_Signal']:.2f}")
st.write(f"**EMA9:** {latest['EMA9']:.2f} | EMA21: {latest['EMA21']:.2f}")
st.write(f"**VWAP:** {latest['VWAP']:.2f}")
st.write(f"**Volume:** {int(latest['Volume'])} | Avg Volume: {int(latest['Volume_SMA20'])}")
st.write(f"**Near Support:** {near_support} | Near Resistance: {near_resistance}")
st.write(f"**Signal:** {'🟢 ' + latest['Signal'] if latest['Signal'] else 'No strong signal'}")

# --- Plot Chart ---
fig = go.Figure()
fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"],
                             low=df["Low"], close=df["Close"], name="Price"))
fig.add_trace(go.Scatter(x=df.index, y=df["EMA9"], name="EMA9", line=dict(width=1)))
fig.add_trace(go.Scatter(x=df.index, y=df["EMA21"], name="EMA21", line=dict(width=1)))
fig.add_trace(go.Scatter(x=df.index, y=df["VWAP"], name="VWAP", line=dict(width=1, dash="dot")))

for level_type, x, price in levels:
    fig.add_shape(type="line", x0=df.index[0], x1=df.index[-1], y0=price, y1=price,
                  line=dict(dash="dot", color="blue" if level_type == "support" else "red"),
                  name=level_type)

fig.add_trace(go.Scatter(x=df[df["Signal"] == "BUY"].index,
                         y=df[df["Signal"] == "BUY"]["Close"],
                         mode="markers", marker=dict(color="green", size=8),
                         name="BUY"))

fig.add_trace(go.Scatter(x=df[df["Signal"] == "SELL"].index,
                         y=df[df["Signal"] == "SELL"]["Close"],
                         mode="markers", marker=dict(color="red", size=8),
                         name="SELL"))

fig.update_layout(title=f"{ticker} Price + Signals + S/R Levels", xaxis_title="Time", yaxis_title="Price", height=600)
st.plotly_chart(fig, use_container_width=True)

# --- Volume Chart ---
vol_fig = go.Figure()
vol_fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume"))
vol_fig.add_trace(go.Scatter(x=df.index, y=df["Volume_SMA20"], name="Avg Volume", line=dict(color="orange")))
vol_fig.update_layout(title=f"{ticker} Volume with Spikes", height=300)
st.plotly_chart(vol_fig, use_container_width=True)
