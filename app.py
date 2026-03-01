import streamlit as st
import pandas as pd
import requests
import os
from dotenv import load_dotenv

# Import our custom modules
from src.hype_scanner import HypeScanner
from src.ai_agent import HypeAgent
from src.discovery import DiscoveryEngine
from src.sentiment import RedditScraper

# Load environment variables
load_dotenv()

# --- INIT ---
st.set_page_config(page_title="🚀 Hype Hunter Terminal", layout="wide", page_icon="🔥")

@st.cache_resource
def get_clients():
    return HypeScanner(), HypeAgent(), DiscoveryEngine(), RedditScraper()

scanner, agent, discovery, reddit = get_clients()

# Helper function to fetch news for the AI Agent
def fetch_recent_news(ticker, api_key):
    try:
        url = f"[https://api.tiingo.com/tiingo/news?tickers=](https://api.tiingo.com/tiingo/news?tickers=){ticker}&limit=5"
        headers = {'Authorization': f'Token {api_key}'}
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200 and res.json():
            return "\n".join([f"- {article['title']}" for article in res.json()])
        return "No recent news found."
    except Exception:
        return "Error fetching news."

# --- HEADER ---
st.title("🔥 Hype Hunter: Narrative & Momentum Terminal")
st.markdown("Dynamically hunting for extreme volume anomalies and grading their narrative catalysts.")

# --- TABS ---
tab_radar, tab_deep_dive = st.tabs(["🎯 Hype Radar (Live Scan)", "🔬 VC Deep Dive & AI Grading"])

# ==========================================
# TAB 1: RADAR SCAN
# ==========================================
with tab_radar:
    st.header("Phase 1: Dynamic Discovery & RVOL Scan")
    st.write("Using Yahoo Finance to find today's top movers, then calculating RVOL and Velocity via Tiingo.")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        min_rvol = st.slider("Minimum RVOL (Relative Volume)", min_value=1.0, max_value=10.0, value=2.0, step=0.5, 
                             help="2.0 means trading at 200% of its normal 20-day volume.")
        run_scan = st.button("🚀 Launch Dynamic Hype Scan", type="primary", use_container_width=True)
        # NEW: Debug Checkbox
        show_debug = st.checkbox("Show Live Scan Logs (Transparency Mode)", value=True)
    
    with col2:
        custom_tickers = st.text_input("Force Scan Specific Tickers (Comma separated)", "")
    
    if run_scan:
        with st.spinner("Hunting Yahoo Finance for today's live market movers..."):
            dynamic_list = discovery.get_live_market_movers()
            
        if custom_tickers:
            added = [t.strip().upper() for t in custom_tickers.split(",") if t.strip()]
            dynamic_list.extend(added)
            
        scan_list = list(set(dynamic_list)) # Remove duplicates
            
        st.info(f"📡 API Connection Established. Scanning {len(scan_list)} dynamic targets...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        results = []
        rejected_log = [] # Store rejected stocks for the debug view
        
        for i, ticker in enumerate(scan_list):
            status_text.text(f"Analyzing {ticker}...")
            metrics = scanner.get_hype_metrics(ticker)
            
            if metrics:
                # Check logic explicitly to log reasons
                rvol_pass = metrics['RVOL'] >= min_rvol
                roc_pass = metrics['ROC_5_Days'] > 0
                
                if rvol_pass and roc_pass:
                    results.append(metrics)
                    rejected_log.append({"Ticker": ticker, "RVOL": metrics['RVOL'], "Velocity": metrics['ROC_5_Days'], "Status": "✅ PASSED"})
                else:
                    # Log why it failed
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
            
        status_text.empty() # Clear the "Analyzing..." text
            
        # --- DISPLAY RESULTS ---
        if results:
            df_results = pd.DataFrame(results).sort_values(by="RVOL", ascending=False)
            st.success(f"🔥 Hype Detected! Found {len(df_results)} stocks anomalies.")
            
            def highlight_rvol(val):
                if val >= 4.0: return 'background-color: #7f1d1d; color: white;' 
                if val >= 2.5: return 'background-color: #9a3412; color: white;' 
                return ''
                
            styled_df = df_results.style.format({
                'Price': '${:.2f}', 'RVOL': '{:.2f}x', 'Gap_Pct': '{:.2f}%', 'ROC_5_Days': '{:.2f}%'
            }).map(highlight_rvol, subset=['RVOL'])
            
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            st.session_state['top_hype_tickers'] = df_results['Ticker'].tolist()
        else:
            st.warning("No stocks met the strict Hype thresholds.")

        # --- DEBUG / TRANSPARENCY SECTION ---
        if show_debug and rejected_log:
            st.divider()
            with st.expander("🕵️‍♂️ Transparency Log: See What Was Scanned", expanded=True):
                st.write(f"The scanner successfully processed **{len(rejected_log)}** unique tickers from the market.")
                st.write("If this table is populated, your system is working perfectly—the market is just quiet.")
                
                debug_df = pd.DataFrame(rejected_log)
                st.dataframe(debug_df, use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: DEEP DIVE & NARRATIVE GRADING
# ==========================================
with tab_deep_dive:
    st.header("Phase 2: AI Venture Capital Catalyst Grading")
    st.write("Does the narrative justify the volume? Let Gemini analyze the news and sentiment.")
    
    default_ticker = "SMCI"
    if 'top_hype_tickers' in st.session_state and st.session_state['top_hype_tickers']:
        default_ticker = st.session_state['top_hype_tickers'][0]
        
    target_ticker = st.text_input("Ticker to Analyze", value=default_ticker).upper()
    
    if st.button("🧠 Grade Narrative Catalyst", type="primary"):
        with st.spinner(f"Fetching metrics and news for {target_ticker}..."):
            metrics = scanner.get_hype_metrics(target_ticker)
            
            if not metrics:
                st.error("Could not fetch market data. Check API limits or ticker validity.")
            else:
                news = fetch_recent_news(target_ticker, scanner.api_key)
                
                with st.spinner("Scraping live WallStreetBets sentiment..."):
                    social_data = reddit.get_ticker_sentiment(target_ticker)
                
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Current Price", f"${metrics['Price']}")
                c2.metric("RVOL", f"{metrics['RVOL']}x")
                c3.metric("5-Day Velocity", f"{metrics['ROC_5_Days']}%")
                c4.metric("WSB Mentions (Today)", social_data['mention_count'])
                
                col_news, col_social = st.columns(2)
                with col_news:
                    with st.expander("📰 Recent Headlines", expanded=True):
                        st.text(news)
                with col_social:
                    with st.expander("🔥 Live WSB Sentiment", expanded=True):
                        for post in social_data['top_posts']:
                            st.write(post)
                
                st.markdown("---")
                st.subheader("🤖 AI Venture Capital Verdict")
                
                with st.spinner("AI is evaluating the catalyst and crowd psychology..."):
                    verdict_data = agent.get_hype_verdict(target_ticker, metrics, news, social_data)
                    
                    v_col1, v_col2 = st.columns([1, 2])
                    
                    with v_col1:
                        score = verdict_data.get('hype_score', 0)
                        tier = verdict_data.get('catalyst_tier', 'Unknown')
                        action = verdict_data.get('verdict', 'WATCH')
                        
                        st.metric("Crowd Frenzy Score", f"{score}/100")
                        
                        if "Tier 1" in tier: st.success(f"**Catalyst:** {tier}")
                        elif "Tier 2" in tier: st.info(f"**Catalyst:** {tier}")
                        else: st.warning(f"**Catalyst:** {tier}")
                        
                        if "RIDE" in action: st.success(f"**Action:** {action}")
                        elif "FADE" in action: st.error(f"**Action:** {action}")
                        else: st.warning(f"**Action:** {action}")
                        
                    with v_col2:
                        st.markdown("### VC Thesis")
                        st.write(verdict_data.get('vc_thesis', 'No thesis generated.'))