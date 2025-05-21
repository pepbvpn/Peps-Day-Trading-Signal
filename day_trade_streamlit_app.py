
import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator, MACD
import plotly.express as px

st.set_page_config(layout="wide")
st.title("📈 Day Trading Signal Dashboard")

# --- Sidebar Inputs ---
ticker = st.sidebar.text_input("Ticker Symbol", value="AAPL")
interval = st.sidebar.selectbox("Interval", ["5m", "15m", "30m", "1h", "1d"], index=1)
period = st.sidebar.selectbox("Data Period", ["1d", "5d", "7d", "1mo"], index=1)

# --- Fetch Data ---
df = yf.download(ticker, interval=interval, period=period)

# ✅ FLATTEN MULTI-LEVEL COLUMNS IF PRESENT
if isinstance(df.columns, pd.MultiIndex):
    df.columns = df.columns.get_level_values(0)

df.dropna(inplace=True)
close = df["Close"]

# --- Indicators ---
df["RSI"] = RSIIndicator(close=close).rsi()
df["EMA9"] = EMAIndicator(close=close, window=9).ema_indicator()
df["EMA21"] = EMAIndicator(close=close, window=21).ema_indicator()
macd = MACD(close=close)
df["MACD"] = macd.macd()
df["MACD_Signal"] = macd.macd_signal()

df.dropna(inplace=True)

# --- Buy/Sell Signal Logic ---
df["Signal"] = ""
df.loc[(df["RSI"] < 30) & (df["MACD"] > df["MACD_Signal"]) & (df["EMA9"] > df["EMA21"]), "Signal"] = "BUY"
df.loc[(df["RSI"] > 70) & (df["MACD"] < df["MACD_Signal"]) & (df["EMA9"] < df["EMA21"]), "Signal"] = "SELL"

# --- Display Latest Signal ---
latest = df.iloc[-1]
st.subheader(f"📊 Latest Signal for {ticker}")
st.write(f"**RSI:** {latest['RSI']:.2f}")
st.write(f"**MACD:** {latest['MACD']:.2f}")
st.write(f"**EMA9:** {latest['EMA9']:.2f}")
st.write(f"**EMA21:** {latest['EMA21']:.2f}")
st.write(f"**Signal:** {'🟢 ' + latest['Signal'] if latest['Signal'] else 'No strong signal'}")

# --- Candlestick + Signal Chart ---
fig = go.Figure()
fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"],
                             low=df["Low"], close=df["Close"], name="Price"))
fig.add_trace(go.Scatter(x=df.index, y=df["EMA9"], name="EMA9"))
fig.add_trace(go.Scatter(x=df.index, y=df["EMA21"], name="EMA21"))

fig.add_trace(go.Scatter(x=df[df["Signal"] == "BUY"].index,
                         y=df[df["Signal"] == "BUY"]["Close"],
                         mode="markers", marker=dict(color="green", size=8),
                         name="BUY"))
fig.add_trace(go.Scatter(x=df[df["Signal"] == "SELL"].index,
                         y=df[df["Signal"] == "SELL"]["Close"],
                         mode="markers", marker=dict(color="red", size=8),
                         name="SELL"))

fig.update_layout(title=f"{ticker} Price + Signals", xaxis_title="Time", yaxis_title="Price", height=600)
st.plotly_chart(fig, use_container_width=True)

# --- RSI Chart ---
fig_rsi = px.line(df, x=df.index, y="RSI", title=f"{ticker} RSI")
fig_rsi.update_traces(line_color="orange")
st.plotly_chart(fig_rsi, use_container_width=True)

# --- MACD Chart ---
fig_macd = go.Figure()
fig_macd.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD", line=dict(color="blue")))
fig_macd.add_trace(go.Scatter(x=df.index, y=df["MACD_Signal"], name="MACD Signal", line=dict(color="red")))
fig_macd.update_layout(title=f"{ticker} MACD", xaxis_title="Time", yaxis_title="MACD", height=400)
st.plotly_chart(fig_macd, use_container_width=True)
