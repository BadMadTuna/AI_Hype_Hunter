import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
import yfinance as yf
from dotenv import load_dotenv

# Import our custom modules
from src.discovery import DiscoveryEngine
from src.hype_scanner import HypeScanner
from src.sentiment import RedditScraper  # Hijacked for Short Squeeze Data
from src.ai_agent import HypeAgent
from src.database import get_portfolio_df, get_journal_df, init_cash
from src.portfolio import PortfolioManager

# Load environment variables
load_dotenv()

# Initialize engines
discovery = DiscoveryEngine()
scanner = HypeScanner()
reddit = RedditScraper()
agent = HypeAgent()
pm = PortfolioManager()

# Ensure DB is initialized on first run
init_cash(10000)

# Helper function for Tiingo News
def fetch_recent_news(ticker, api_key):
    try:
        url = f"https://api.tiingo.com/tiingo/news?tickers={ticker}&limit=5"
        headers = {'Authorization': f'Token {api_key}', 'Content-Type': 'application/json'}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return "\n".join([f"- {article['title']}" for article in data]) if data else "No news found."
        return f"⚠️ API Error {res.status_code}"
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# --- HEADER ---
st.set_page_config(page_title="Hype Hunter Pro", page_icon="🦅", layout="wide")
st.title("🦅 Hype Hunter: Institutional Momentum Terminal")

# --- TABS ---
tab_radar, tab_deep_dive, tab_risk, tab_port = st.tabs([
    "📡 Radar Scan", "🧠 VC Deep Dive", "🛡️ Risk Simulator", "💼 Portfolio Manager"
])

# ==========================================
# TAB 1: RADAR SCAN (Functional & Transparent)
# ==========================================
with tab_radar:
    st.header("Phase 1: Dynamic Discovery & RVOL Scan")
    if "hype_scan_results" not in st.session_state: st.session_state['hype_scan_results'] = None
    if "hype_scan_debug" not in st.session_state: st.session_state['hype_scan_debug'] = None
    
    col1, col2 = st.columns([1, 3])
    with col1:
        min_rvol = st.slider("Minimum RVOL", 1.0, 10.0, 2.0)
        show_debug = st.checkbox("Show Transparency Log", value=True)
        run_scan = st.button("🚀 Launch Scan", type="primary", use_container_width=True)
    
    if run_scan:
        with st.spinner("Hunting for anomalies..."):
            scan_list = list(set(discovery.get_live_market_movers()))
            results, rejected = [], []
            for t in scan_list:
                m = scanner.get_hype_metrics(t)
                if m and m['RVOL'] >= min_rvol:
                    results.append(m)
                elif m:
                    rejected.append({"Ticker": t, "RVOL": m['RVOL'], "Status": "❌ Low Vol"})
            
            st.session_state['hype_scan_results'] = pd.DataFrame(results).sort_values(by="RVOL", ascending=False)
            st.session_state['hype_scan_debug'] = pd.DataFrame(rejected)
            st.session_state['top_hype_tickers'] = st.session_state['hype_scan_results']['Ticker'].tolist() if results else []

    if st.session_state['hype_scan_results'] is not None:
        df = st.session_state['hype_scan_results']
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button("📥 Download Results (CSV)", df.to_csv(index=False), "scan.csv", "text/csv")
        
        if show_debug and st.session_state['hype_scan_debug'] is not None:
            with st.expander("🕵️ Transparency Log"):
                st.dataframe(st.session_state['hype_scan_debug'], use_container_width=True)

# ==========================================
# TAB 2: DEEP DIVE (AI & Short Data)
# ==========================================
with tab_deep_dive:
    st.header("Phase 2: Narrative Grading")
    if "dd_data" not in st.session_state: st.session_state['dd_data'] = None
    
    default_ticker = st.session_state.get('top_hype_tickers', ['SMCI'])[0]
    target_ticker = st.text_input("Ticker to Analyze", value=default_ticker).upper()
    
    if st.button("🧠 Grade Catalyst", type="primary"):
        with st.spinner("Analyzing Catalyst..."):
            metrics = scanner.get_hype_metrics(target_ticker)
            news = fetch_recent_news(target_ticker, os.getenv("TIINGO_API_KEY"))
            squeeze = reddit.get_ticker_sentiment(target_ticker) # Short Data
            verdict = agent.get_hype_verdict(target_ticker, metrics, news, squeeze)
            st.session_state['dd_data'] = {'metrics': metrics, 'news': news, 'squeeze': squeeze, 'verdict': verdict, 'ticker': target_ticker}

    if st.session_state['dd_data']:
        d = st.session_state['dd_data']
        v = d['verdict']
        st.metric("Frenzy Score", f"{v.get('hype_score')}/100")
        st.markdown(f"### VC Thesis\n{v.get('vc_thesis')}")
        # Add back the Memo Download
        memo = f"Ticker: {d['ticker']}\nScore: {v.get('hype_score')}\n\n{v.get('vc_thesis')}"
        st.download_button("📥 Download VC Memo", memo, f"{d['ticker']}_memo.txt")

# ==========================================
# TAB 3: RISK SIMULATOR & EXECUTION
# ==========================================
with tab_risk:
    st.header("Phase 3: ATR Risk & Execution")
    risk_ticker = st.text_input("Ticker to Size", value=st.session_state.get('dd_ticker', 'AAOI')).upper()
    
    if st.button("🛡️ Calculate ATR Risk"):
        with st.spinner("Calculating..."):
            stock = yf.Ticker(risk_ticker).history(period="1mo")
            price = stock['Close'].iloc[-1]
            atr = (stock['High'] - stock['Low']).mean()
            stop = price - (atr * 2)
            shares = int(100 / (price - stop)) if (price - stop) > 0 else 0
            st.session_state['last_calc'] = {"ticker": risk_ticker, "price": round(price,2), "shares": shares, "stop": round(stop,2), "atr": round(atr,2)}

    if "last_calc" in st.session_state:
        lc = st.session_state['last_calc']
        st.success(f"**Execution Plan for {lc['ticker']}**")
        st.write(f"Entry: ${lc['price']} | Stop: ${lc['stop']} | ATR: ${lc['atr']}")
        st.metric("Suggested Shares (Risk $100)", lc['shares'])
        
        if st.button(f"💳 Execute Buy Order"):
            if pm.execute_buy(lc['ticker'], lc['price'], lc['shares']):
                st.success("Order filled and logged to Portfolio.")
            else:
                st.error("Insufficient Cash.")

# ==========================================
# TAB 4: PORTFOLIO MANAGER
# ==========================================
with tab_port:
    st.header("Phase 4: Real-Time Portfolio")
    summary = pm.get_equity_summary()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Equity", f"${summary['total_equity']:,.2f}")
    c2.metric("Available Cash", f"${summary['cash']:,.2f}")
    c3.metric("Invested Capital", f"${summary['invested']:,.2f}")
    
    st.subheader("Open Positions")
    df_p = get_portfolio_df()
    if not df_p.empty:
        st.dataframe(df_p[df_p['Ticker'] != 'CASH'], use_container_width=True, hide_index=True)
    
    st.subheader("Trade Journal")
    st.dataframe(get_journal_df(), use_container_width=True, hide_index=True)