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
    
@st.cache_data(ttl=3600) # Cache for 1 hour to save API calls
def get_fx_rate(api_key):
    """Fetches real-time USD to EUR conversion rate via Tiingo."""
    try:
        url = "https://api.tiingo.com/tiingo/fx/top"
        res = requests.get(url, params={'tickers': 'eurusd', 'token': api_key}, timeout=5)
        if res.status_code == 200:
            return 1.0 / res.json()[0]['midPrice']
    except Exception:
        pass
    return 0.92 # Fallback rate

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
            total_tickers = len(scan_list)
            
            st.info(f"📡 API Connection Established. Scanning {total_tickers} dynamic targets...")
            
            # --- PROGRESS BAR RESTORED ---
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, t in enumerate(scan_list):
                # Update the live text
                status_text.text(f"Analyzing {t} ({i+1}/{total_tickers})...")
                
                # Fetch metrics
                m = scanner.get_hype_metrics(t)
                if m and m['RVOL'] >= min_rvol:
                    results.append(m)
                elif m:
                    rejected.append({"Ticker": t, "RVOL": m['RVOL'], "Status": "❌ Low Vol"})
                
                # Tick the progress bar forward
                progress_bar.progress((i + 1) / total_tickers)
            
            # Clear the status text when finished
            status_text.empty()
            # -----------------------------
            
            # Save to session state
            st.session_state['hype_scan_results'] = pd.DataFrame(results).sort_values(by="RVOL", ascending=False)
            st.session_state['hype_scan_debug'] = pd.DataFrame(rejected)
            st.session_state['top_hype_tickers'] = st.session_state['hype_scan_results']['Ticker'].tolist() if results else []

    if st.session_state['hype_scan_results'] is not None:
        df = st.session_state['hype_scan_results']
        if not df.empty:
            st.success(f"🔥 Found {len(df)} High-Volume Anomalies.")
            
            # Restoring the visual heat map for RVOL
            def highlight_rvol(val):
                if val >= 4.0: return 'background-color: #7f1d1d; color: white; font-weight: bold;' 
                if val >= 2.5: return 'background-color: #9a3412; color: white; font-weight: bold;' 
                return ''
                
            styled_df = df.style.format({
                'Price': '${:.2f}', 'RVOL': '{:.2f}x', 'Gap_Pct': '{:.2f}%', 'ROC_5_Days': '{:.2f}%'
            }).map(highlight_rvol, subset=['RVOL'])
            
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
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
                for post in s['top_posts']: 
                    # Hide the secret AI prompt from the human UI
                    if "SYSTEM OVERRIDE" not in post:
                        st.write(post)
                
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
# TAB 3: RISK SIMULATOR (EUR NATIVE)
# ==========================================
with tab_risk:
    st.header("Phase 3: ATR Risk & Execution (EUR)")
    risk_ticker = st.text_input("Ticker to Size", value=st.session_state.get('dd_data', {}).get('ticker', 'AAOI')).upper()
    
    col_input, col_output = st.columns([1, 2])
    with col_input:
        acc_size = st.number_input("Account Size (€)", value=10000)
        risk_pct = st.slider("Risk % per Trade", 0.5, 5.0, 1.0)
        
        if st.button("🛡️ Calculate Exit & Sizing", type="primary", use_container_width=True):
            with st.spinner("Fetching Volatility & FX Rates..."):
                fx_rate = get_fx_rate(os.getenv("TIINGO_API_KEY"))
                stock = yf.Ticker(risk_ticker).history(period="1mo")
                price_usd = stock['Close'].iloc[-1]
                atr_usd = (stock['High'] - stock['Low']).mean()
                
                # Convert to EUR
                price_eur = price_usd * fx_rate
                atr_eur = atr_usd * fx_rate
                stop_eur = price_eur - (atr_eur * 2)
                
                max_loss_eur = acc_size * (risk_pct/100)
                shares = int(max_loss_eur / (price_eur - stop_eur)) if (price_eur - stop_eur) > 0 else 0
                
                st.session_state['last_calc'] = {
                    "ticker": risk_ticker, "price_eur": round(price_eur, 2), 
                    "shares": shares, "stop_eur": round(stop_eur, 2), 
                    "max_loss": max_loss_eur, "fx_rate": fx_rate, "price_usd": round(price_usd, 2)
                }

    with col_output:
        if "last_calc" in st.session_state:
            lc = st.session_state['last_calc']
            st.success(f"**Execution Plan: {lc['ticker']}** (USD/EUR Rate: {lc['fx_rate']:.4f})")
            m1, m2, m3 = st.columns(3)
            m1.metric("Entry (€)", f"€{lc['price_eur']}")
            m2.metric("Stop Loss (€)", f"€{lc['stop_eur']}")
            m3.metric("Shares", lc['shares'])
            
            st.info(f"📋 **Strict Plan:** Buy {lc['shares']} shares. If stopped at €{lc['stop_eur']}, you lose exactly €{lc['max_loss']}.")
            st.caption(f"*Note: Actual US Market Price is ${lc['price_usd']}*")
            
            if st.button(f"💳 Execute Buy Order (€{lc['price_eur'] * lc['shares']:.2f})", use_container_width=True):
                # We execute the buy using the EUR cost basis so it deducts correctly from EUR cash
                if pm.execute_buy(lc['ticker'], lc['price_eur'], lc['shares']):
                    st.success(f"Order Filled: {lc['shares']} shares of {lc['ticker']} logged to Fund.")
                else:
                    st.error("Trade Denied: Insufficient Cash.")

# ==========================================
# TAB 4: PORTFOLIO & MANAGEMENT (LIVE MTM)
# ==========================================
with tab_port:
    st.header("Phase 4: Fund Management & Execution")
    
    # 1. Fetch raw portfolio data from the database
    df_port = get_portfolio_df()
    
    # 2. Initialize Session State for Live Tracking
    if "live_port_df" not in st.session_state:
        st.session_state.live_port_df = None
        st.session_state.current_fx_rate = 1.0

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        refresh_clicked = st.button("🔄 Refresh Live Prices & PnL", type="primary", use_container_width=True)

    # 3. Live Price Fetching Logic 
    if refresh_clicked and not df_port.empty:
        with st.spinner("Fetching real-time US market prices & FX rates..."):
            # Fetch Live FX Rate
            fx_rate = get_fx_rate(os.getenv("TIINGO_API_KEY"))
            
            # Fetch Live Prices using yfinance fast_info (extremely fast)
            live_prices = {}
            active_tickers = [t for t in df_port['ticker'].unique() if t not in ['USD', 'EUR', 'CASH']]
            
            if active_tickers:
                import yfinance as yf
                for t in active_tickers:
                    try:
                        price_usd = yf.Ticker(t).fast_info['last_price']
                        live_prices[t] = price_usd * fx_rate # Convert live US price to EUR
                    except Exception:
                        pass # If fetch fails, we will fallback to cost basis below
            
            # Map Live Prices to DataFrame
            live_df = df_port.copy()
            def get_live_price(row):
                if row['ticker'] in ['EUR', 'USD', 'CASH']: return 1.0
                return live_prices.get(row['ticker'], row['cost']) 
                
            live_df['Live Price (€)'] = live_df.apply(get_live_price, axis=1)
            live_df['Current Value (€)'] = live_df['Live Price (€)'] * live_df['quantity']
            
            # Calculate Live PnL 
            is_stock = ~live_df['ticker'].isin(['EUR', 'USD', 'CASH'])
            live_df['PnL (€)'] = 0.0
            live_df['PnL (%)'] = 0.0
            live_df.loc[is_stock, 'PnL (€)'] = (live_df['Live Price (€)'] - live_df['cost']) * live_df['quantity']
            live_df.loc[is_stock, 'PnL (%)'] = ((live_df['Live Price (€)'] - live_df['cost']) / live_df['cost']) * 100
            
            st.session_state.live_port_df = live_df
            st.session_state.current_fx_rate = fx_rate

    # 4. Top Level Metrics (Live vs Cost Basis) 
    if st.session_state.live_port_df is not None:
        ldf = st.session_state.live_port_df
        cash = ldf[ldf['ticker'].isin(['EUR', 'USD', 'CASH'])]['Current Value (€)'].sum()
        inv_val = ldf[~ldf['ticker'].isin(['EUR', 'USD', 'CASH'])]['Current Value (€)'].sum()
        inv_cost = ldf[~ldf['ticker'].isin(['EUR', 'USD', 'CASH'])]['cost'].multiply(ldf[~ldf['ticker'].isin(['EUR', 'USD', 'CASH'])]['quantity']).sum()
        pnl_eur = ldf['PnL (€)'].sum()
        total_equity = cash + inv_val
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Live Total Equity", f"€{total_equity:,.2f}", f"{pnl_eur:+,.2f} €")
        c2.metric("💶 Cash Balance", f"€{cash:,.2f}")
        c3.metric("📈 Total Return", f"{(pnl_eur/inv_cost*100 if inv_cost>0 else 0):+.2f}%")
        c4.metric("📊 Live Invested Value", f"€{inv_val:,.2f}")
        st.caption(f"🌍 *Live USD to EUR Conversion Rate:* **{st.session_state.current_fx_rate:.4f}**")
    else:
        summary = pm.get_equity_summary()
        c1, c2, c3 = st.columns(3)
        c1.metric("💰 Total Equity (Cost Basis)", f"€{summary['total_equity']:,.2f}")
        c2.metric("💶 Cash Balance", f"€{summary['cash']:,.2f}")
        c3.metric("📈 Invested Capital", f"€{summary['invested']:,.2f}")

    st.markdown("---")

    # 5. Holdings Display
    st.subheader("📂 Open Positions")
    if st.session_state.live_port_df is not None:
        holdings = st.session_state.live_port_df[~st.session_state.live_port_df['ticker'].isin(['EUR', 'USD', 'CASH'])].copy()
        if not holdings.empty:
            def color_pnl(val):
                if isinstance(val, (int, float)):
                    if val > 0: return 'color: #10b981;' 
                    elif val < 0: return 'color: #ef4444;' 
                return ''
                
            styled_df = holdings[['ticker', 'quantity', 'cost', 'Live Price (€)', 'Current Value (€)', 'PnL (€)', 'PnL (%)']].style.format({
                'cost': '€{:.2f}', 'Live Price (€)': '€{:.2f}', 'Current Value (€)': '€{:.2f}', 
                'PnL (€)': '€{:.2f}', 'PnL (%)': '{:.2f}%'
            }).map(color_pnl, subset=['PnL (€)', 'PnL (%)'])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
        else:
            st.info("No active stock positions.")
    else:
        holdings = df_port[~df_port['ticker'].isin(['EUR', 'USD', 'CASH'])].copy()
        if not holdings.empty:
            st.dataframe(holdings.style.format({'cost': '€{:.2f}', 'quantity': '{:.2f}', 'target': '€{:.2f}'}), use_container_width=True, hide_index=True)
        else:
            st.info("No active stock positions.")

    # 6. Trade Execution Forms
    st.markdown("---")
    st.subheader("🛠️ Trade Execution & Portfolio Editing")
    m_col1, m_col2 = st.columns(2)

    with m_col1:
        with st.expander("➕ Add Single Position / Deposit Cash", expanded=False):
            with st.form("buy_form"):
                b_ticker = st.text_input("Ticker (Use 'EUR' for Cash Deposit)", "AAPL").upper()
                b_price = st.number_input("Entry Price in € (1.0 for EUR)", min_value=0.0, value=1.0)
                b_qty = st.number_input("Quantity", min_value=1.0, value=100.0)

                if st.form_submit_button("Execute Buy / Deposit"):
                    if b_ticker == 'EUR':
                        import sqlite3, time
                        try:
                            conn = sqlite3.connect("data/hedgefund.db")
                            cursor = conn.cursor()
                            cursor.execute("SELECT id, quantity FROM portfolio WHERE ticker = 'EUR'")
                            row = cursor.fetchone()
                            if row:
                                cursor.execute("UPDATE portfolio SET quantity = ? WHERE id = ?", (row[1] + b_qty, row[0]))
                            else:
                                date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                cursor.execute("INSERT INTO portfolio (ticker, cost, quantity, status, date_acquired) VALUES ('EUR', 1.0, ?, 'Liquid', ?)", (b_qty, date_str))
                            conn.commit(); conn.close()
                            st.success(f"Deposited €{b_qty:,.2f} into cash reserves!"); time.sleep(1); st.rerun()
                        except Exception as e:
                            st.error(f"Failed to deposit cash: {e}")
                    else:
                        if pm.execute_buy(b_ticker, b_price, b_qty, reason="Manual Entry"):
                            import time
                            st.success(f"Successfully bought {b_qty} of {b_ticker}!"); time.sleep(1); st.rerun()
                        else:
                            st.error("Trade Failed. Check cash balance.")

    with m_col2:
        with st.expander("✂️ Sell / Trim Position", expanded=False):
            with st.form("sell_form"):
                s_ticker = st.text_input("Ticker to Sell").upper()
                s_price = st.number_input("Exit Price in €", min_value=0.0, value=150.0)
                s_qty = st.number_input("Quantity to Sell", min_value=1.0, value=10.0)

                if st.form_submit_button("Execute Sell / Trim"):
                    if pm.execute_sell(s_ticker, s_price, s_qty, reason="Manual Sell"):
                        import time
                        st.success(f"Successfully sold {s_qty} of {s_ticker}!"); time.sleep(1); st.rerun()
                    else:
                        st.error("Failed. Ensure you own enough shares of this stock.")

    # 7. Trade Journal
    st.markdown("---")
    st.subheader("📓 Trade Journal")
    df_j = get_journal_df()
    if not df_j.empty:
        st.dataframe(df_j.style.format({'entry': '€{:.2f}', 'exit': '€{:.2f}', 'pnl_abs': '€{:.2f}', 'pnl_pct': '{:.2f}%'}), use_container_width=True, hide_index=True)