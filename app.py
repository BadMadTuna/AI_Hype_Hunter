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
from src.sentiment import RedditScraper 
from src.ai_agent import HypeAgent
from src.database import get_portfolio_df, get_journal_df, init_db
from src.portfolio import PortfolioManager

# Load environment variables
load_dotenv()

# Initialize engines
discovery = DiscoveryEngine()
scanner = HypeScanner()
reddit = RedditScraper()
agent = HypeAgent()
pm = PortfolioManager()

# Ensure DB is initialized
init_db()

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
st.set_page_config(page_title="Hype Hunter Terminal", page_icon="🦅", layout="wide")
st.title("🦅 Hype Hunter: Institutional Momentum Terminal")
st.markdown("---")

# --- TABS ---
tab_radar, tab_deep_dive, tab_risk, tab_port = st.tabs([
    "📡 Phase 1: Radar Scan", "🧠 Phase 2: VC Deep Dive", "🛡️ Phase 3: Risk Simulator", "💼 Phase 4: Portfolio"
])

# ==========================================
# TAB 1: RADAR SCAN
# ==========================================
with tab_radar:
    st.header("Radar Scan: Discovery & RVOL Analysis")
    if "hype_scan_results" not in st.session_state: st.session_state['hype_scan_results'] = None
    if "hype_scan_debug" not in st.session_state: st.session_state['hype_scan_debug'] = None
    
    col1, col2 = st.columns([1, 3])
    with col1:
        min_rvol = st.slider("Minimum RVOL", 1.0, 10.0, 2.0)
        show_debug = st.checkbox("Show Transparency Log", value=True)
        run_scan = st.button("🚀 Launch Dynamic Scan", type="primary", use_container_width=True)
    
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
        if not df.empty:
            st.success(f"🔥 Found {len(df)} High-Volume Anomalies.")
            st.dataframe(df.style.format({'Price': '${:.2f}', 'RVOL': '{:.2f}x', 'ROC_5_Days': '{:.2f}%'}), use_container_width=True, hide_index=True)
            st.download_button("📥 Download Scan (CSV)", df.to_csv(index=False), f"scan_{datetime.now().strftime('%Y%m%d')}.csv")
        
        if show_debug and st.session_state['hype_scan_debug'] is not None:
            with st.expander("🕵️ Transparency Log"):
                st.dataframe(st.session_state['hype_scan_debug'], use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: VC DEEP DIVE
# ==========================================
with tab_deep_dive:
    st.header("Phase 2: AI Narrative & Catalyst Grading")
    
    # Safely get the default ticker from the scan results
    ticker_list = st.session_state.get('top_hype_tickers', [])
    default_val = ticker_list[0] if ticker_list else "SMCI"
    target_ticker = st.text_input("Ticker to Analyze", value=default_val).upper()
    
    if st.button("🧠 Grade Narrative Catalyst", type="primary"):
        with st.spinner(f"AI Deep Dive: {target_ticker}..."):
            metrics = scanner.get_hype_metrics(target_ticker)
            news = fetch_recent_news(target_ticker, os.getenv("TIINGO_API_KEY"))
            squeeze = reddit.get_ticker_sentiment(target_ticker) 
            verdict = agent.get_hype_verdict(target_ticker, metrics, news, squeeze)
            
            # Save the full rich object to state
            st.session_state['dd_data'] = {
                'metrics': metrics, 
                'news': news, 
                'squeeze': squeeze, 
                'verdict': verdict, 
                'ticker': target_ticker
            }

    if st.session_state.get('dd_data'):
        d = st.session_state['dd_data']
        v = d['verdict']
        m = d['metrics']
        s = d['squeeze']
        
        # Metric Bar (Visual Output)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Price", f"${m['Price']}")
        c2.metric("RVOL", f"{m['RVOL']}x")
        c3.metric("5D Velocity", f"{m['ROC_5_Days']}%")
        c4.metric("Short Float", s['mention_count'])
        
        # Side-by-Side Expanders
        col_news, col_sqz = st.columns(2)
        with col_news:
            with st.expander("📰 Recent Headlines", expanded=True):
                st.text(d['news'])
        with col_sqz:
            with st.expander("🗜️ Short Squeeze Metrics", expanded=True):
                for post in s['top_posts']: st.write(post)
                
        # AI Verdict Section
        st.divider()
        st.subheader("🤖 AI Venture Capital Verdict")
        v_col1, v_col2 = st.columns([1, 2])
        with v_col1:
            st.metric("Frenzy Score", f"{v.get('hype_score')}/100")
            st.info(f"**Catalyst:** {v.get('catalyst_tier')}")
            st.success(f"**Action:** {v.get('verdict')}")
        with v_col2:
            st.markdown(f"### VC Thesis\n{v.get('vc_thesis')}")
            
        # The VC Memo Download (Fixed)
        memo_content = f"""# VC MEMO: {d['ticker']}
Generated: {datetime.now().strftime('%Y-%m-%d')}
SCORE: {v.get('hype_score')}/100
CATALYST: {v.get('catalyst_tier')}
VERDICT: {v.get('verdict')}

THESIS:
{v.get('vc_thesis')}

METRICS:
- Price: ${m['Price']}
- RVOL: {m['RVOL']}x
- 5D Momentum: {m['ROC_5_Days']}%
- Short Interest: {s['mention_count']}
"""
        st.download_button(
            label=f"📥 Download VC Memo for {d['ticker']}",
            data=memo_content,
            file_name=f"VC_Memo_{d['ticker']}.txt",
            use_container_width=True
        )

# ==========================================
# TAB 3: RISK SIMULATOR
# ==========================================
with tab_risk:
    st.header("ATR Risk Simulator & Execution")
    # Defensive check for ticker fallback
    dd_payload = st.session_state.get('dd_data')
    fallback_ticker = dd_payload.get('ticker', 'AAOI') if dd_payload else 'AAOI'
    
    risk_ticker = st.text_input("Ticker to Size", value=fallback_ticker).upper()
    
    col_input, col_output = st.columns([1, 2])
    with col_input:
        acc_size = st.number_input("Account Size", value=10000)
        risk_pct = st.slider("Risk % per Trade", 0.5, 5.0, 1.0)
        if st.button("🛡️ Calculate Exit & Sizing", type="primary", use_container_width=True):
            with st.spinner("Fetching Volatility..."):
                stock = yf.Ticker(risk_ticker).history(period="1mo")
                price = stock['Close'].iloc[-1]
                atr = (stock['High'] - stock['Low']).mean()
                stop = price - (atr * 2)
                max_loss = acc_size * (risk_pct/100)
                shares = int(max_loss / (price - stop)) if (price - stop) > 0 else 0
                st.session_state['last_calc'] = {"ticker": risk_ticker, "price": round(price,2), "shares": shares, "stop": round(stop,2), "atr": round(atr,2), "max_loss": max_loss}

    with col_output:
        if "last_calc" in st.session_state:
            lc = st.session_state['last_calc']
            st.success(f"**Execution Plan: {lc['ticker']}**")
            m1, m2, m3 = st.columns(3)
            m1.metric("Entry", f"${lc['price']}")
            m2.metric("Stop Loss", f"${lc['stop']}")
            m3.metric("Shares", lc['shares'])
            
            st.info(f"📋 **Strict Plan:** Buy {lc['shares']} shares. If stopped at ${lc['stop']}, you lose exactly ${lc['max_loss']}.")
            
            if st.button(f"💳 Execute Buy Order", use_container_width=True):
                if pm.execute_buy(lc['ticker'], lc['price'], lc['shares']):
                    st.success(f"Order Filled: {lc['shares']} shares of {lc['ticker']} logged to Fund.")
                else:
                    st.error("Trade Denied: Insufficient Cash.")

# ==========================================
# TAB 4: PORTFOLIO & MANAGEMENT
# ==========================================
with tab_port:
    st.header("Phase 4: Fund Management & Execution")
    summary = pm.get_equity_summary()

    # Top Level Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Total Equity", f"${summary['total_equity']:,.2f}")
    c2.metric("💵 Cash Balance", f"${summary['cash']:,.2f}")
    c3.metric("📈 Invested Capital", f"${summary['invested']:,.2f}")

    st.markdown("---")
    st.subheader("🛠️ Trade Execution & Portfolio Editing")
    m_col1, m_col2 = st.columns(2)

    with m_col1:
        with st.expander("➕ Add Single Position / Deposit Cash", expanded=False):
            with st.form("buy_form"):
                b_ticker = st.text_input("Ticker (Use 'USD' for Cash Deposit)", "AAPL").upper()
                b_price = st.number_input("Entry Price (1.0 for USD)", min_value=0.0, value=1.0)
                b_qty = st.number_input("Quantity", min_value=1.0, value=100.0)

                if st.form_submit_button("Execute Buy / Deposit"):
                    if b_ticker == 'USD':
                        # Bypass the purchase check and inject cash directly via SQLite
                        import sqlite3
                        import time
                        try:
                            conn = sqlite3.connect("data/hedgefund.db")
                            cursor = conn.cursor()
                            cursor.execute("SELECT id, quantity FROM portfolio WHERE ticker = 'USD'")
                            row = cursor.fetchone()
                            if row:
                                cursor.execute("UPDATE portfolio SET quantity = ? WHERE id = ?", (row[1] + b_qty, row[0]))
                            else:
                                date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                cursor.execute("INSERT INTO portfolio (ticker, cost, quantity, status, date_acquired) VALUES ('USD', 1.0, ?, 'Liquid', ?)", (b_qty, date_str))
                            conn.commit()
                            conn.close()
                            st.success(f"Deposited ${b_qty:,.2f} into cash reserves!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to deposit cash: {e}")
                    else:
                        # Standard stock purchase logic
                        if pm.execute_buy(b_ticker, b_price, b_qty, reason="Manual Entry"):
                            import time
                            st.success(f"Successfully bought {b_qty} of {b_ticker}!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Trade Failed. Check cash balance.")

    with m_col2:
        with st.expander("✂️ Sell / Trim Position", expanded=False):
            with st.form("sell_form"):
                s_ticker = st.text_input("Ticker to Sell").upper()
                s_price = st.number_input("Exit Price", min_value=0.0, value=150.0)
                s_qty = st.number_input("Quantity to Sell", min_value=1.0, value=10.0)

                if st.form_submit_button("Execute Sell / Trim"):
                    if pm.execute_sell(s_ticker, s_price, s_qty, reason="Manual Sell"):
                        import time
                        st.success(f"Successfully sold {s_qty} of {s_ticker}!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("Failed. Ensure you own enough shares of this stock.")

    st.markdown("---")
    
    # Holdings Display
    st.subheader("📂 Open Positions")
    df_p = get_portfolio_df()
    if not df_p.empty:
        # Filter out the cash row for the holdings table
        holdings = df_p[~df_p['ticker'].isin(['USD', 'CASH'])].copy()
        if not holdings.empty:
            st.dataframe(
                holdings.style.format({'cost': '${:.2f}', 'quantity': '{:.2f}', 'target': '${:.2f}'}),
                use_container_width=True, hide_index=True
            )
        else:
            st.info("No active stock positions. Your portfolio is 100% cash.")
    else:
        st.info("Portfolio is completely empty.")

    # Trade Journal
    st.subheader("📓 Trade Journal")
    df_j = get_journal_df()
    if not df_j.empty:
        st.dataframe(
            df_j.style.format({'entry': '${:.2f}', 'exit': '${:.2f}', 'pnl_abs': '${:.2f}', 'pnl_pct': '{:.2f}%'}),
            use_container_width=True, hide_index=True
        )
    else:
        st.info("No trades executed yet.")