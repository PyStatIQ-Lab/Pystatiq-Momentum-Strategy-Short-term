import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# ------------------------------
# Streamlit UI - User Inputs
# ------------------------------
st.title("🚀 NIFTY Momentum Stock Picker")
st.write("**Select your risk tolerance and time horizon for momentum stock recommendations.**")

# 1. Load Excel and let user select sheet
try:
    stock_data = pd.ExcelFile("stocklist.xlsx")  # Replace with your file path
    sheet_names = stock_data.sheet_names  # Get all sheet names (NIFTY50, NIFTY100, etc.)
    
    selected_sheet = st.selectbox(
        "**Select Stock Index**",
        options=sheet_names,
        help="Choose NIFTY50, NIFTY100, etc."
    )
    
    # Read symbols from the selected sheet
    df_stocks = pd.read_excel(stock_data, sheet_name=selected_sheet)
    # Clean ticker symbols - remove .NS if already present
    tickers = df_stocks["Symbol"].str.replace('.NS', '').tolist()
    
except Exception as e:
    st.error(f"Error loading Excel file: {e}")
    st.stop()

# 2. Risk Tolerance → Position Sizing
risk_tolerance = st.radio(
    "**Risk Tolerance**",
    options=["Low", "Medium", "High"],
    help="High risk = higher position sizing"
)

# 3. Time Horizon → Adjusts lookback period
time_horizon = st.slider(
    "**Time Horizon (Months)**",
    min_value=1, max_value=6, value=3,
    help="Short-term momentum works best for 1-6 months."
)

# Convert months to days for lookback period
lookback_days = time_horizon * 30  # Approximate 30 days per month

# ------------------------------
# Fetch & Calculate Momentum
# ------------------------------
def calculate_momentum(ticker, days):
    try:
        yf_ticker = f"{ticker}.NS"
        data = yf.download(yf_ticker, period=f"{days}d", progress=False)["Close"]
        if len(data) == 0:
            return np.nan
        return (data[-1] / data[0] - 1) * 100  # Return %
    except:
        return np.nan

if st.button("Get Momentum Stocks"):
    with st.spinner(f"Scanning {selected_sheet} for top momentum stocks..."):
        momentum_data = []
        problematic_tickers = []
        
        for ticker in tickers[:50]:  # Limit to 50 for demo (remove [:50] for full scan)
            mom = calculate_momentum(ticker, lookback_days)
            if not np.isnan(mom):
                momentum_data.append({
                    "Ticker": ticker,
                    "Momentum (%)": mom,
                    "Current Price": yf.Ticker(f"{ticker}.NS").history(period="1d")["Close"].iloc[-1]
                })
            else:
                problematic_tickers.append(ticker)

        if problematic_tickers:
            st.warning(f"Could not fetch data for these tickers: {', '.join(problematic_tickers)}")

        if not momentum_data:
            st.error("No stocks could be analyzed. Please try again later.")
            st.stop()
            
        df = pd.DataFrame(momentum_data).sort_values("Momentum (%)", ascending=False)
        
        # Adjust position sizing based on risk tolerance
        if risk_tolerance == "Low":
            allocation = 5  # Equal weight, low leverage
            num_stocks = min(20, len(df))  # More diversified
        elif risk_tolerance == "Medium":
            allocation = 8
            num_stocks = min(12, len(df))
        else:  # High risk
            allocation = 12  # Concentrated bets
            num_stocks = min(8, len(df))
        
        allocation = min(allocation, 100/num_stocks)  # Ensure total <= 100%
        df["Allocation (%)"] = allocation
        
        # Limit to top stocks
        df = df.head(num_stocks)

    # ------------------------------
    # Display Results
    # ------------------------------
    st.success(f"✅ Top {len(df)} Momentum Stocks from {selected_sheet}")
    
    # Format the dataframe
    formatted_df = df.copy()
    formatted_df["Momentum (%)"] = formatted_df["Momentum (%)"].round(2)
    formatted_df["Current Price"] = formatted_df["Current Price"].round(2)
    formatted_df["Allocation (%)"] = formatted_df["Allocation (%)"].round(1)
    
    st.dataframe(
        formatted_df.style.background_gradient(
            subset=["Momentum (%)"],
            cmap='RdYlGn'  # Red-Yellow-Green color scale
        )
    )
    
    # Explain strategy
    st.subheader("⚖️ Suggested Portfolio Strategy")
    st.write(
        f"- **Risk Tolerance:** {risk_tolerance}\n"
        f"  - Position size: {allocation}% per stock\n"
        f"  - Number of stocks: {num_stocks}\n"
        f"- **Time Horizon:** {time_horizon} months\n"
        f"  - Lookback period: {lookback_days} days\n"
        f"- **Total Portfolio Allocation:** {num_stocks * allocation}%"
    )
    
    # Add disclaimer
    st.warning("""
    **Disclaimer:** This is for educational purposes only. Past performance is not indicative of future results. 
    Always do your own research before investing.
    """)
