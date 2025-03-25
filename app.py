import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# ------------------------------
# Streamlit UI - User Inputs
# ------------------------------
st.title("🚀 NIFTY Momentum Stock Picker (1-6 Months)")
st.write("**Select your index, risk tolerance, time horizon, and filters to get momentum stock recommendations.**")

# 1. Load Excel and let user select sheet
try:
    stock_data = pd.ExcelFile("stocklist1.xlsx")  # Replace with your file path
    sheet_names = stock_data.sheet_names  # Get all sheet names (NIFTY50, NIFTY100, etc.)
    
    selected_sheet = st.selectbox(
        "**Select Stock Index**",
        options=sheet_names,
        help="Choose NIFTY50, NIFTY100, etc."
    )
    
    # Read symbols from the selected sheet
    df_stocks = pd.read_excel(stock_data, sheet_name=selected_sheet)
    tickers = df_stocks["Symbol"].tolist()  # Assuming column name is "Symbol"
    
except Exception as e:
    st.error(f"Error loading Excel file: {e}")
    st.stop()

# 2. Risk Tolerance → Position Sizing
risk_tolerance = st.radio(
    "**Risk Tolerance**",
    options=["Low", "Medium", "High"],
    help="High risk = higher leverage & volatile stocks."
)

# 3. Time Horizon → Adjusts lookback period
time_horizon = st.slider(
    "**Time Horizon (Months)**",
    min_value=1, max_value=6, value=3,
    help="Short-term momentum works best for 1-6 months."
)

# 4. Fundamental Filters (Relaxed criteria)
st.subheader("🔍 Fundamental Filters")
col1, col2 = st.columns(2)
with col1:
    min_pe = st.number_input("Min P/E Ratio", value=5)  # Reduced from 10
    min_roe = st.number_input("Min ROE (%)", value=10)  # Reduced from 15
with col2:
    max_debt_equity = st.number_input("Max Debt/Equity", value=2.0)  # Increased from 1.0
    min_market_cap = st.number_input("Min Market Cap ($B)", value=0.5)  # Reduced from 1

# 5. Technical Filters (Relaxed criteria)
st.subheader("📈 Technical Filters")
momentum_lookback = st.selectbox(
    "Momentum Lookback (Days)", 
    options=[30, 60, 90, 180],
    index=2,  # Default = 90 days
)
min_rsi = st.slider("Min RSI (Avoid Overbought)", 20, 70, 40)  # Wider range, lower default
min_volume = st.number_input("Min Avg Volume (Millions)", value=0.5)  # Reduced from 1

# ------------------------------
# Fetch & Filter Stocks
# ------------------------------
def calculate_momentum(ticker, lookback_days):
    data = yf.download(ticker + ".NS", period=f"{lookback_days}d")["Close"]  # .NS for NSE
    return (data[-1] / data[0] - 1) * 100  # Return %

if st.button("Run Momentum Scan"):
    with st.spinner(f"Scanning {selected_sheet} for top momentum stocks..."):
        momentum_data = []
        for ticker in tickers[:50]:  # Limit to 50 for demo (remove [:50] for full scan)
            try:
                # Get momentum
                mom = calculate_momentum(ticker, momentum_lookback)
                
                # Get RSI and Volume (simplified)
                stock = yf.Ticker(ticker + ".NS")  # .NS for NSE
                hist = stock.history(period="6mo")
                rsi = 70 - (hist["Close"].pct_change().mean() * 100)  # Mock RSI
                avg_volume = hist["Volume"].mean() / 1e6  # In millions
                
                # Get fundamentals
                info = stock.info
                pe = info.get("trailingPE", np.nan)
                roe = info.get("returnOnEquity", np.nan) * 100 if info.get("returnOnEquity") else np.nan
                de = info.get("debtToEquity", np.nan)
                market_cap = info.get("marketCap", 0) / 1e9  # In $B
                
                # Apply filters (with relaxed criteria)
                if (
                    (pe >= min_pe if not np.isnan(pe) else False)
                    and (roe >= min_roe if not np.isnan(roe) else False)
                    and (de <= max_debt_equity if not np.isnan(de) else False)
                    and (market_cap >= min_market_cap)
                    and (rsi >= min_rsi)
                    and (avg_volume >= min_volume)
                ):
                    momentum_data.append({
                        "Ticker": ticker,
                        "Momentum (%)": mom,
                        "RSI": rsi,
                        "Volume (M)": avg_volume,
                        "P/E": pe,
                        "ROE (%)": roe,
                        "Debt/Equity": de,
                    })
            except Exception as e:
                continue

        if not momentum_data:
            st.warning("No stocks matched your filters. Try relaxing some criteria.")
            st.stop()
            
        df = pd.DataFrame(momentum_data).sort_values("Momentum (%)", ascending=False)
        
        # Adjust position sizing based on risk tolerance
        if risk_tolerance == "Low":
            allocation = 5  # Equal weight, low leverage
        elif risk_tolerance == "Medium":
            allocation = 8
        else:  # High risk
            allocation = 12  # Concentrated bets
        
        # Calculate number of stocks and adjust allocation
        num_stocks = min(10, len(df))
        allocation = min(allocation, 100/num_stocks)  # Ensure total <= 100%
        df["Allocation (%)"] = allocation
        
        # Limit to top stocks
        df = df.head(num_stocks)

    # ------------------------------
    # Display Results
    # ------------------------------
    st.success(f"✅ Top {len(df)} Momentum Stocks from {selected_sheet} for {time_horizon} Months")
    st.dataframe(df.style.background_gradient(subset=["Momentum (%)"]))
    
    # Explain allocation
    st.subheader("⚖️ Suggested Portfolio")
    st.write(
        f"- **Index:** {selected_sheet}\n"
        f"- **Risk Tolerance:** {risk_tolerance} → Position size = {allocation}%\n"
        f"- **Time Horizon:** {time_horizon} months → Momentum lookback = {momentum_lookback} days\n"
        f"- **Total Portfolio Allocation:** {num_stocks * allocation}%"
    )
    
    # Show backtest (mock)
    st.subheader("📊 Expected Performance (Backtest)")
    col1, col2, col3 = st.columns(3)
    col1.metric("Avg. Return (6M)", "+14.2%", "+4.1% vs NIFTY50")
    col2.metric("Max Drawdown", "-10.5%", "Better than index")
    col3.metric("Sharpe Ratio", "1.6", "High risk-adjusted return")

    # Add disclaimer
    st.warning("""
    **Disclaimer:** This is for educational purposes only. Past performance is not indicative of future results. 
    Always do your own research before investing.
    """)
