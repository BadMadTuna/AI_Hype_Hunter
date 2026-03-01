import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
from dotenv import load_dotenv

# Import our custom modules
from src.discovery import DiscoveryEngine
from src.hype_scanner import HypeScanner
from src.sentiment import RedditScraper  # Hijacked to fetch Short Data
from src.ai_agent import HypeAgent

# Load environment variables
load_dotenv()
tiingo_key = os.getenv("TIINGO_API_KEY")

# Initialize engines
discovery = DiscoveryEngine()
scanner = HypeScanner()
reddit = RedditScraper()
agent = HypeAgent()

# Helper function to fetch news for the AI Agent
def fetch_recent_news(ticker, api_key):
    try:
        url = f"https://api.tiingo.com/tiingo/news?tickers={ticker}&limit=5"
        headers = {
            'Authorization': f'Token {api_key}',
            'Content-Type': 'application/json'
        }
        res = requests.get(url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            if data:
                return "\n".join([f"- {article['title']}" for article in data])
            return f"No recent news articles found for {ticker}."
        elif res.status_code == 429:
            return "⚠️ API Error: Tiingo Rate Limit Exceeded."
        else:
            return f"⚠️ API Error {res.status_code}: {res.text[:50]}"
            
    except requests.exceptions.Timeout:
        return "⚠️ Error: News API connection timed out."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"

# --- HEADER ---
st.set_page_config(page_title="Hype Hunter Terminal", page_icon="🔥", layout="wide")
st.title("🔥 Hype Hunter: Narrative & Momentum Terminal")
st.markdown("Dynamically hunting for extreme volume anomalies, grading their catalysts, and managing risk.")

# --- TABS ---
tab_radar, tab_deep_dive, tab_risk = st.tabs(["📡 Phase 1: Radar Scan", "🧠 Phase 2: VC Deep Dive", "🛡️ Phase 3: Risk Simulator"])

# ==========================================
# TAB 1: RADAR SCAN
# ==========================================
with tab_radar:
    st.header("Phase 1: Dynamic Discovery & RVOL Scan")
    st.write("Using Yahoo Finance to find today's top movers, then calculating RVOL and Velocity via Tiingo.")
    
    # Initialize session state variables so data survives the download button
    if "hype_scan_results" not in st.session_state:
        st.session_state['hype_scan_results'] = None
    if "hype_scan_debug" not in st.session_state:
        st.session_state['hype_scan_debug'] = None
    
    col1, col2 = st.columns([1, 3])
    with col1:
        min_rvol = st.slider("Minimum RVOL (Relative Volume)", min_value=1.0, max_value=10.0, value=2.0, step=0.5, 
                             help="2.0 means trading at 200% of its normal 20-day volume.")
        run_scan = st.button("🚀 Launch Dynamic Hype Scan", type="primary", use_container_width=True)
        show_debug = st.checkbox("Show Live Scan Logs (Transparency Mode)", value=True)
    
    with col2:
        custom_tickers = st.text_input("Force Scan Specific Tickers (Comma separated)", "")
    
    if run_scan:
        with st.spinner("Hunting Yahoo Finance for today's live market movers..."):
            dynamic_list = discovery.get_live_market_movers()
            
        if custom_tickers:
            added = [t.strip().upper() for t in custom_tickers.split(",") if t.strip()]
            dynamic_list.extend(added)
            
        scan_list = list(set(dynamic_list))
            
        st.info(f"📡 API Connection Established. Scanning {len(scan_list)} dynamic targets...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        rejected_log = []
        
        for i, ticker in enumerate(scan_list):
            status_text.text(f"Analyzing {ticker}...")
            metrics = scanner.get_hype_metrics(ticker)
            
            if metrics:
                rvol_pass = metrics['RVOL'] >= min_rvol
                roc_pass = metrics['ROC_5_Days'] > 0
                
                if rvol_pass and roc_pass:
                    results.append(metrics)
                    rejected_log.append({"Ticker": ticker, "RVOL": metrics['RVOL'], "Velocity": metrics['ROC_5_Days'], "Status": "✅ PASSED"})
                else:
                    reason = []
                    if not rvol_pass: reason.append(f"Low Vol ({metrics['RVOL']}x)")
                    if not roc_pass: reason.append(f"Neg Trend ({metrics['ROC_5_Days']}%)")
                    rejected_log.append({
                        "Ticker": ticker, 
                        "RVOL": metrics['RVOL'], 
                        "Velocity": metrics['ROC_5_Days'], 
                        "Status": f"❌ REJECTED: {', '.join(reason)}"
                    })
            else:
                 rejected_log.append({"Ticker": ticker, "RVOL": 0, "Velocity": 0, "Status": "⚠️ NO DATA (Tiingo)"})
                 
            progress_bar.progress((i + 1) / len(scan_list))
            
        status_text.empty()
        
        # Save results to session state instead of displaying immediately
        if results:
            df_results = pd.DataFrame(results).sort_values(by="RVOL", ascending=False)
            st.session_state['hype_scan_results'] = df_results
            st.session_state['top_hype_tickers'] = df_results['Ticker'].tolist()
        else:
            st.session_state['hype_scan_results'] = pd.DataFrame() 
            
        st.session_state['hype_scan_debug'] = pd.DataFrame(rejected_log)

    # --- Render Scan UI out here so it survives the download button refresh ---
    if st.session_state['hype_scan_results'] is not None:
        df_results = st.session_state['hype_scan_results']
        
        if not df_results.empty:
            st.success(f"🔥 Hype Detected! Found {len(df_results)} stocks exhibiting extreme volume anomalies.")
            
            def highlight_rvol(val):
                if val >= 4.0: return 'background-color: #7f1d1d; color: white;' 
                if val >= 2.5: return 'background-color: #9a3412; color: white;' 
                return ''
                
            styled_df = df_results.style.format({
                'Price': '${:.2f}', 'RVOL': '{:.2f}x', 'Gap_Pct': '{:.2f}%', 'ROC_5_Days': '{:.2f}%'
            }).map(highlight_rvol, subset=['RVOL'])
            
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            st.download_button(
                label="📥 Download Hype Scan Results (CSV)",
                data=df_results.to_csv(index=False).encode('utf-8'),
                file_name=f"hype_hunter_scan_{datetime.today().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("No stocks met the strict Hype thresholds.")

        # --- DEBUG LOG ---
        if show_debug and st.session_state['hype_scan_debug'] is not None:
            debug_df = st.session_state['hype_scan_debug']
            if not debug_df.empty:
                st.divider()
                with st.expander("🕵️‍♂️ Transparency Log: See What Was Scanned", expanded=True):
                    st.write(f"The scanner successfully processed **{len(debug_df)}** unique tickers from the market.")
                    st.dataframe(debug_df, use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: DEEP DIVE & NARRATIVE GRADING
# ==========================================
with tab_deep_dive:
    st.header("Phase 2: AI Venture Capital Catalyst Grading")
    st.write("Does the narrative justify the volume? Let Gemini analyze the news and Short Squeeze potential.")
    
    # Initialize session state for the deep dive data
    if "dd_data" not in st.session_state:
        st.session_state['dd_data'] = None
    if "dd_ticker" not in st.session_state:
        st.session_state['dd_ticker'] = None
        
    default_ticker = "SMCI"
    if 'top_hype_tickers' in st.session_state and st.session_state['top_hype_tickers'] and len(st.session_state['top_hype_tickers']) > 0:
        default_ticker = st.session_state['top_hype_tickers'][0]
        
    target_ticker = st.text_input("Ticker to Analyze", value=default_ticker).upper()
    
    # --- FETCH DATA & SAVE TO STATE ---
    if st.button("🧠 Grade Narrative Catalyst", type="primary"):
        with st.spinner(f"Fetching metrics and news for {target_ticker}..."):
            metrics = scanner.get_hype_metrics(target_ticker)
            
            if not metrics:
                st.error("Could not fetch market data. Check API limits or ticker validity.")
                st.session_state['dd_data'] = None
            else:
                news = fetch_recent_news(target_ticker, scanner.api_key)
                
                with st.spinner("Calculating Institutional Short Float Data..."):
                    social_data = reddit.get_ticker_sentiment(target_ticker) # Actually fetching Short Data
                
                with st.spinner("AI is evaluating the catalyst and short squeeze mechanics..."):
                    verdict_data = agent.get_hype_verdict(target_ticker, metrics, news, social_data)
                    
                    # Lock the results into memory so they survive button clicks
                    st.session_state['dd_data'] = {
                        'metrics': metrics,
                        'news': news,
                        'social_data': social_data,
                        'verdict': verdict_data
                    }
                    st.session_state['dd_ticker'] = target_ticker

    # --- RENDER UI (Outside the button block) ---
    if st.session_state['dd_data'] is not None:
        data = st.session_state['dd_data']
        t_ticker = st.session_state['dd_ticker']
        
        metrics = data['metrics']
        news = data['news']
        social_data = data['social_data']
        verdict_data = data['verdict']
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Price", f"${metrics['Price']}")
        c2.metric("RVOL", f"{metrics['RVOL']}x")
        c3.metric("5-Day Velocity", f"{metrics['ROC_5_Days']}%")
        c4.metric("Short % of Float", social_data['mention_count'])
        
        col_news, col_social = st.columns(2)
        with col_news:
            with st.expander("📰 Recent Headlines", expanded=True):
                st.text(news)
        with col_social:
            with st.expander("🗜️ Short Squeeze Metrics", expanded=True):
                for post in social_data['top_posts']:
                    st.write(post)
        
        st.markdown("---")
        st.subheader("🤖 AI Venture Capital Verdict")
        
        v_col1, v_col2 = st.columns([1, 2])
        
        score = verdict_data.get('hype_score', 0)
        tier = verdict_data.get('catalyst_tier', 'Unknown')
        action = verdict_data.get('verdict', 'WATCH')
        thesis = verdict_data.get('vc_thesis', 'No thesis generated.')
        
        with v_col1:
            st.metric("Institutional Frenzy Score", f"{score}/100")
            
            if "Tier 1" in tier: st.success(f"**Catalyst:** {tier}")
            elif "Tier 2" in tier: st.info(f"**Catalyst:** {tier}")
            else: st.warning(f"**Catalyst:** {tier}")
            
            if "RIDE" in action: st.success(f"**Action:** {action}")
            elif "FADE" in action: st.error(f"**Action:** {action}")
            else: st.warning(f"**Action:** {action}")
            
        with v_col2:
            st.markdown("### VC Thesis")
            st.write(thesis)
            
        st.markdown("---")
        
        # --- GENERATE VC MEMO DOWNLOAD ---
        social_text = "\n".join([f"- {post}" for post in social_data['top_posts']])
        
        memo_text = f"""# AI HYPE HUNTER - VC MEMO: {t_ticker}
Date Generated: {datetime.today().strftime('%Y-%m-%d')}

## 1. AI VERDICT
- Action: {action}
- Institutional Frenzy Score: {score}/100
- Catalyst: {tier}

## 2. VC THESIS
{thesis}

## 3. MARKET METRICS
- Price: ${metrics['Price']}
- RVOL: {metrics['RVOL']}x
- 5-Day Velocity: {metrics['ROC_5_Days']}%

## 4. SHORT SQUEEZE METRICS
- Short % of Float: {social_data['mention_count']}
{social_text}

## 5. RECENT NEWS
{news}
"""
        st.download_button(
            label=f"📥 Download VC Memo for {t_ticker} (.txt)",
            data=memo_text.encode('utf-8'),
            file_name=f"VC_Memo_{t_ticker}_{datetime.today().strftime('%Y%m%d')}.txt",
            mime="text/plain",
            use_container_width=True
        )

# ==========================================
# TAB 3: ATR RISK SIMULATOR
# ==========================================
with tab_risk:
    st.header("Phase 3: ATR Dynamic Risk Simulator")
    st.write("Calculate mathematical trailing stops and exact position sizing to survive hyper-volatile runners.")
    
    # Helper function to calculate ATR via yfinance
    def get_atr_data(ticker_symbol, window=14):
        import yfinance as yf
        try:
            stock = yf.Ticker(ticker_symbol)
            df = stock.history(period="1mo")
            if df.empty or len(df) < window: return None, None
            
            # Math for True Range
            df['Prev_Close'] = df['Close'].shift(1)
            df['TR1'] = df['High'] - df['Low']
            df['TR2'] = abs(df['High'] - df['Prev_Close'])
            df['TR3'] = abs(df['Low'] - df['Prev_Close'])
            df['TR'] = df[['TR1', 'TR2', 'TR3']].max(axis=1)
            
            atr = df['TR'].rolling(window=window).mean().iloc[-1]
            current_price = df['Close'].iloc[-1]
            return round(float(atr), 2), round(float(current_price), 2)
        except Exception as e:
            return None, None

    r_col1, r_col2 = st.columns([1, 2])
    
    with r_col1:
        st.subheader("Trade Parameters")
        default_risk_ticker = st.session_state.get('dd_ticker', 'AAOI')
        risk_ticker = st.text_input("Ticker", value=default_risk_ticker, key="risk_ticker_input").upper()
        account_size = st.number_input("Total Account Size ($)", min_value=1000, value=10000, step=1000)
        risk_pct = st.slider("Account Risk % (If stopped out)", min_value=0.5, max_value=5.0, value=1.0, step=0.1)
        atr_multiplier = st.slider("ATR Multiplier (Wiggle Room)", min_value=1.0, max_value=4.0, value=2.0, step=0.5)
        
        calc_btn = st.button("🛡️ Calculate Safe Entry & Exit", type="primary", use_container_width=True)
        
    with r_col2:
        st.subheader("Execution Plan")
        if calc_btn:
            with st.spinner(f"Calculating mathematical volatility for {risk_ticker}..."):
                atr_val, current_price = get_atr_data(risk_ticker)
                
            if atr_val is None:
                st.error("Could not fetch ATR data. Try a different ticker.")
            else:
                # The Math
                stop_loss_dist = atr_val * atr_multiplier
                stop_loss_price = current_price - stop_loss_dist
                
                max_loss_dollars = account_size * (risk_pct / 100)
                shares_to_buy = int(max_loss_dollars / stop_loss_dist) if stop_loss_dist > 0 else 0
                total_investment = shares_to_buy * current_price
                
                st.success(f"**Target Analyzed:** {risk_ticker} at ${current_price}")
                
                m1, m2, m3 = st.columns(3)
                m1.metric("14-Day ATR", f"${atr_val}/day", help="How much this stock normally swings in a single day.")
                m2.metric("Hard Stop Loss", f"${stop_loss_price:.2f}", f"-${stop_loss_dist:.2f} away")
                m3.metric("Shares to Buy", shares_to_buy)
                
                st.divider()
                st.markdown("### 📋 Your Strict Trading Plan")
                st.markdown(f"""
                1. **Buy** **{shares_to_buy}** shares of {risk_ticker} right now at roughly **${current_price}**.
                2. Your total capital deployed will be **${total_investment:,.2f}**.
                3. **Immediately set a hard stop-loss at ${stop_loss_price:.2f}**. 
                4. If the trade fails and hits your stop, you will only lose exactly **${max_loss_dollars:,.2f}** ({risk_pct}% of your account).
                5. **Trailing Rule:** For every day {risk_ticker} goes up, recalculate the ATR and move your stop loss up behind it. Never move it down.
                """)