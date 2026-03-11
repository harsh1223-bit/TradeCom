import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import date
from sklearn.linear_model import LinearRegression

st.set_page_config(page_title="TRADECOM", layout="wide")

st.title("📊 TRADECOM — Stock Analytics Platform")

# ---------------- SIDEBAR ----------------

st.sidebar.header("Portfolio Controls")

stocks = [
"AAPL","MSFT","TSLA","NVDA","META","AMZN","GOOGL",
"AMD","INTC","NFLX","UBER","SHOP","COIN","PYPL",
"JPM","BAC","WMT","DIS","ORCL","ADBE","CRM",
"PEP","KO","NKE","COST","T","V","MA","GS","MS"
]

selected_stocks = st.sidebar.multiselect(
"Select Stocks",
stocks,
default=["AAPL","MSFT","TSLA"]
)

start_date = st.sidebar.date_input("Start Date", date(2020,1,1))
end_date = st.sidebar.date_input("End Date", date.today())

if len(selected_stocks) == 0:
    st.warning("Please select at least one stock")
    st.stop()

# ---------------- DATA ----------------

@st.cache_data
def load_data(tickers):
    return yf.download(tickers, start=start_date, end=end_date)["Close"]

data = load_data(selected_stocks)

if isinstance(data, pd.Series):
    data = data.to_frame()

returns = data.pct_change().dropna()

annual_return = returns.mean()*252
risk = returns.std()*np.sqrt(252)

# ---------------- TABS ----------------

tab1, tab2, tab3, tab4 = st.tabs([
"📊 Market Overview",
"📈 Portfolio Analytics",
"🤖 AI Prediction",
"📉 Stock Analysis"
])

# ================= MARKET OVERVIEW =================

with tab1:

    st.subheader("Stock Price Comparison")

    fig = go.Figure()

    for stock in data.columns:
        fig.add_trace(go.Scatter(
            x=data.index,
            y=data[stock],
            mode="lines",
            name=stock
        ))

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Correlation Heatmap")

    corr = returns.corr()

    fig_corr = px.imshow(
        corr,
        text_auto=True,
        color_continuous_scale="RdBu_r"
    )

    st.plotly_chart(fig_corr, use_container_width=True)

# ================= PORTFOLIO ANALYTICS =================

with tab2:

    st.subheader("Portfolio Calculator")

    weights=[]

    for stock in selected_stocks:
        weight = st.slider(
            f"Weight for {stock}",
            0.0,1.0,
            1.0/len(selected_stocks)
        )
        weights.append(weight)

    weights=np.array(weights)
    weights=weights/weights.sum()

    portfolio_return=np.sum(annual_return*weights)

    portfolio_volatility=np.sqrt(
        np.dot(weights.T,np.dot(returns.cov()*252,weights))
    )

    sharpe_ratio=portfolio_return/portfolio_volatility

    col1,col2,col3,col4=st.columns(4)

    col1.metric("Selected Stocks", len(selected_stocks))
    col2.metric("Portfolio Return", f"{portfolio_return*100:.2f}%")
    col3.metric("Portfolio Risk", f"{portfolio_volatility*100:.2f}%")
    col4.metric("Sharpe Ratio", f"{sharpe_ratio:.2f}")

    # Risk vs Return

    risk_df = pd.DataFrame({
        "Stock":annual_return.index,
        "Return":annual_return.values,
        "Risk":risk.values
    })

    fig_rr = px.scatter(
        risk_df,
        x="Risk",
        y="Return",
        text="Stock",
        size="Return"
    )

    st.plotly_chart(fig_rr, use_container_width=True)

    # Portfolio allocation

    st.subheader("Portfolio Allocation")

    portfolio_df = pd.DataFrame({
        "Stock": selected_stocks,
        "Weight": weights
    })

    fig_pie = px.pie(
        portfolio_df,
        values="Weight",
        names="Stock",
        hole=0.4,
        template="plotly_dark"
    )

    st.plotly_chart(fig_pie, use_container_width=True)

    # ---------------- BACKTESTING ----------------

    st.subheader("Portfolio Backtesting")

    initial_investment = 10000

    normalized_prices = data / data.iloc[0]

    portfolio_values = normalized_prices.dot(weights)

    portfolio_values = portfolio_values * initial_investment

    final_value = portfolio_values.iloc[-1]

    total_return = ((final_value - initial_investment) / initial_investment) * 100

    col1, col2 = st.columns(2)

    col1.metric("Initial Investment", f"${initial_investment:,.0f}")
    col2.metric("Final Portfolio Value", f"${final_value:,.0f}")

    st.metric("Total Return", f"{total_return:.2f}%")

    fig_backtest = go.Figure()

    fig_backtest.add_trace(go.Scatter(
        x=portfolio_values.index,
        y=portfolio_values,
        mode="lines",
        name="Portfolio Value",
        line=dict(color="lime", width=3)
    ))

    fig_backtest.update_layout(
        template="plotly_dark",
        title="Portfolio Value Over Time"
    )

    st.plotly_chart(fig_backtest, use_container_width=True)

    # ---------------- MONTE CARLO ----------------

    num_portfolios = 3000
    results = np.zeros((3,num_portfolios))

    for i in range(num_portfolios):

        rand_weights = np.random.random(len(selected_stocks))
        rand_weights /= np.sum(rand_weights)

        ret = np.sum(annual_return * rand_weights)

        vol = np.sqrt(
            np.dot(rand_weights.T,
            np.dot(returns.cov()*252, rand_weights))
        )

        sharpe = ret/vol

        results[0,i] = vol
        results[1,i] = ret
        results[2,i] = sharpe

    sim_df = pd.DataFrame({
        "Volatility":results[0],
        "Return":results[1],
        "Sharpe":results[2]
    })

    st.subheader("Interactive Efficient Frontier")

    risk_tolerance = st.slider(
        "Select Risk Level",
        float(sim_df["Volatility"].min()),
        float(sim_df["Volatility"].max()),
        float(sim_df["Volatility"].mean())
    )

    optimal_idx = (sim_df["Volatility"] - risk_tolerance).abs().idxmin()

    optimal_vol = sim_df.loc[optimal_idx,"Volatility"]
    optimal_return = sim_df.loc[optimal_idx,"Return"]

    fig_opt = px.scatter(
        sim_df,
        x="Volatility",
        y="Return",
        color="Sharpe",
        template="plotly_dark"
    )

    fig_opt.add_trace(
        go.Scatter(
            x=[optimal_vol],
            y=[optimal_return],
            mode="markers",
            marker=dict(size=18,color="yellow"),
            name="Optimal Portfolio"
        )
    )

    st.plotly_chart(fig_opt, use_container_width=True)

# ================= AI PREDICTION =================

with tab3:

    st.subheader("AI Stock Trend Prediction")

    ticker = st.selectbox("Select Stock", stocks)

    candles = yf.Ticker(ticker).history(start=start_date,end=end_date)

    df = candles.reset_index()

    df["Day"] = np.arange(len(df))

    X = df[["Day"]]
    y = df["Close"]

    model = LinearRegression()
    model.fit(X,y)

    future_days = 60

    future_index = np.arange(len(df),len(df)+future_days).reshape(-1,1)

    predictions = model.predict(future_index)

    future_dates = pd.date_range(
        start=df["Date"].iloc[-1],
        periods=future_days+1
    )[1:]

    fig_pred = go.Figure()

    fig_pred.add_trace(go.Scatter(
        x=df["Date"],
        y=df["Close"],
        name="Actual Price"
    ))

    fig_pred.add_trace(go.Scatter(
        x=future_dates,
        y=predictions,
        name="Predicted Trend",
        line=dict(color="yellow",dash="dash",width=3)
    ))

    st.plotly_chart(fig_pred, use_container_width=True)

# ================= STOCK ANALYSIS =================

with tab4:

    ticker = st.text_input("Enter Stock Symbol","AAPL")

    stock = yf.Ticker(ticker)

    candles = stock.history(start=start_date,end=end_date)

    if not candles.empty:

        candles["MA50"] = candles["Close"].rolling(50).mean()
        candles["MA200"] = candles["Close"].rolling(200).mean()

        fig = go.Figure()

        fig.add_trace(go.Candlestick(
            x=candles.index,
            open=candles["Open"],
            high=candles["High"],
            low=candles["Low"],
            close=candles["Close"]
        ))

        fig.add_trace(go.Scatter(
            x=candles.index,
            y=candles["MA50"],
            name="MA50"
        ))

        fig.add_trace(go.Scatter(
            x=candles.index,
            y=candles["MA200"],
            name="MA200"
        ))

        st.plotly_chart(fig,use_container_width=True)

        st.subheader("Trading Volume")

        fig_vol = px.bar(
            candles,
            x=candles.index,
            y="Volume"
        )

        st.plotly_chart(fig_vol)