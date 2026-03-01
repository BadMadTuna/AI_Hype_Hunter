import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

# Import our custom modules
from src.discovery import DiscoveryEngine
from src.hype_scanner import HypeScanner
from src.sentiment import RedditScraper 
from src.ai_agent import HypeAgent
from src.database import get_portfolio_df, get_journal_df
from src.portfolio import PortfolioManager

# Load environment variables
load_dotenv()

# Initialize engines
discovery = DiscoveryEngine()
scanner = HypeScanner()
reddit = RedditScraper()
agent = HypeAgent()
pm = PortfolioManager()

# Helper function to fetch news
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
# TAB 1: RADAR SCAN
# ==========================================
with tab_radar:
    st.header("Phase 1: Dynamic RVOL Scan")
    if "hype_scan_results" not in st.session_state:
        st.session_state['hype_scan_results'] = None
    
    col1, col2 = st.columns([1, 3])
    with col1:
        min_rvol = st.slider("Min RVOL", 1.0, 10.0, 2.0)
        if st.button("🚀 Launch Scan", type="primary", use_container_width=True):
            with st.spinner("Hunting for anomalies..."):
                scan_list = list(set(discovery.get_live_market_movers()))
                results = [scanner.get_hype_metrics(t) for t in scan_list]
                results = [r for r in results if r and r['RVOL'] >= min_rvol]
                df = pd.DataFrame(results).sort_values(by="RVOL", ascending=False)
                st.session_state['hype_scan_results'] = df
                st.session_state['top_hype_tickers'] = df['Ticker'].tolist() if not df.empty else []

    if st.session_state['hype_scan_results'] is not None:
        st.dataframe(st.session_state['hype_scan_results'], use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: DEEP DIVE
# ==========================================
with tab_deep_dive:
    st.header("Phase 2: Narrative Grading")
    if "dd_data" not in st.session_state: st.session_state['dd_data'] = None
    
    target_ticker = st.text_input("Ticker to Analyze", 
                                  value=st.session_state.get('top_hype_tickers', ['SMCI'])[0]).upper()
    
    if st.button("🧠 Grade Catalyst", type="primary"):
        with st.spinner("Analyzing Short Squeeze & News..."):
            metrics = scanner.get_hype_metrics(target_ticker)
            news = fetch_recent_news(target_ticker, os.getenv("TIINGO_API_KEY"))
            squeeze = reddit.get_ticker_sentiment(target_ticker)
            verdict = agent.get_hype_verdict(target_ticker, metrics, news, squeeze)
            st.session_state['dd_data'] = {'metrics': metrics, 'news': news, 'squeeze': squeeze, 'verdict': verdict}
            st.session_state['dd_ticker'] = target_ticker

    if st.session_state['dd_data']:
        d = st.session_state['dd_data']
        v = d['verdict']
        col_v1, col_v2 = st.columns([1, 2])
        col_v1.metric("Frenzy Score", f"{v.get('hype_score')}/100")
        col_v1.write(f"**Action:** {v.get('verdict')}")
        col_v2.markdown(f"### VC Thesis\n{v.get('vc_thesis')}")

# ==========================================
# TAB 3: RISK SIMULATOR
# ==========================================
with tab_risk:
    st.header("Phase 3: Position Sizing & Execution")
    
    # Helper for ATR
    def get_atr(t):
        import yfinance as yf
        df = yf.Ticker(t).history(period="1mo")
        df['TR'] = df['High'] - df['Low']
        return round(df['TR'].mean(), 2), round(df['Close'].iloc[-1], 2)

    risk_ticker = st.text_input("Ticker", value=st.session_state.get('dd_ticker', 'AAOI')).upper()
    
    if st.button("🛡️ Calculate Risk"):
        atr, price = get_atr(risk_ticker)
        stop = price - (atr * 2)
        # Position Sizing: Risk 1% of $10k ($100) per trade
        shares = int(100 / (price - stop))
        
        st.session_state['last_calc'] = {"ticker": risk_ticker, "price": price, "shares": shares, "stop": stop}
        
    if "last_calc" in st.session_state:
        lc = st.session_state['last_calc']
        st.metric("Suggested Shares", lc['shares'], help=f"Entry: ${lc['price']} | Stop: ${lc['stop']:.2f}")
        
        if st.button(f"💳 Execute Buy: {lc['shares']} shares of {lc['ticker']}"):
            if pm.execute_buy(lc['ticker'], lc['price'], lc['shares']):
                st.success(f"Bought {lc['shares']} of {lc['ticker']}!")
            else:
                st.error("Insufficient Cash!")

# ==========================================
# TAB 4: PORTFOLIO MANAGER
# ==========================================
with tab_port:
    st.header("Phase 4: Fund Management")
    summary = pm.get_equity_summary()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Equity", f"${summary['total_equity']:,.2f}")
    c2.metric("Cash", f"${summary['cash']:,.2f}")
    c3.metric("Invested", f"${summary['invested']:,.2f}")
    
    st.subheader("Current Holdings")
    df_p = get_portfolio_df()
    if not df_p.empty:
        st.dataframe(df_p[df_p['ticker'] != 'CASH'], use_container_width=True, hide_index=True)
    else:
        st.info("No active positions.")
        
    st.subheader("Trade Journal")
    st.dataframe(get_journal_df(), use_container_width=True, hide_index=True)