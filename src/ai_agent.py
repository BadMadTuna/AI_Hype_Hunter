import os
import json
import google.generativeai as genai

class HypeAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def get_hype_verdict(self, ticker: str, hype_metrics: dict, news: str, social_data: dict):
        system_prompt = f"""
        You are a highly aggressive Momentum Trader and Venture Capitalist.
        Analyze a stock that just experienced a massive, unusual volume spike.
        
        TICKER: {ticker}
        HYPE METRICS (Volume & Velocity): {hype_metrics}
        RECENT NEWS & CATALYSTS: {news}
        SHORT SQUEEZE METRICS: {social_data}
        
        YOUR RULES:
        1. Ignore traditional valuation. We only care about ATTENTION, NARRATIVE, and CROWD PSYCHOLOGY.
        2. Grade the Catalyst: 
           - 'Tier 1 Structural': Paradigm shift, massive new TAM, AI breakthroughs.
           - 'Tier 2 Material': Massive earnings beat, multi-year contract, extreme retail short-squeeze.
           - 'Tier 3 Fluff': Analyst upgrades, CEO buzzwords.
        3. Evaluate the Short Squeeze Metrics: High short interest (>10%) combined with high RVOL means short sellers are trapped. Increase the Hype Score significantly if these align.
        4. Provide a punchy, 2-3 sentence thesis focused on the narrative and crowd momentum. Do NOT mention WallStreetBets, Reddit, or social media.
        
        You MUST respond ONLY in this exact JSON format.
        {{
            "hype_score": [Integer 0-100 indicating crowd frenzy and narrative strength],
            "catalyst_tier": "Tier 1 Structural" or "Tier 2 Material" or "Tier 3 Fluff",
            "verdict": "RIDE THE HYPE" or "WATCH" or "FADE (Sell Short)",
            "vc_thesis": "[Your 2-3 sentence narrative thesis incorporating the short squeeze metrics]"
        }}
        """
        try:
            # CLEAN FIX: Force JSON output at the API level
            response = self.model.generate_content(
                system_prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception as e:
            return {"hype_score": 0, "catalyst_tier": "Error", "verdict": "ERROR", "vc_thesis": f"AI Error: {e}"}
        
    def get_guardian_audit(self, ticker, cost, live_price, pnl_pct, news):
        system_prompt = f"""
        You are the Chief Risk Officer for a quantitative hedge fund. 
        Your job is to audit an open position in the portfolio and enforce strict risk management rules.
        
        TICKER: {ticker}
        ENTRY COST: {cost}
        LIVE PRICE: {live_price}
        CURRENT PNL %: {pnl_pct:.2f}%
        RECENT NEWS: {news}
        
        YOUR RUTHLESS RULES:
        1. CUT LOSERS: If CURRENT PNL % is worse than -8.0%, you MUST advise "SELL". Capital preservation is priority #1.
        2. TAKE PROFITS: If CURRENT PNL % is greater than +20.0%, you MUST advise "TRIM" to lock in partial gains.
        3. LET WINNERS RIDE: If PNL is between 0% and +19%, advise "KEEP" but propose a trailing stop loss at the 20-day moving average or 8% below current price.
        4. UNDERWATER BUT SAFE: If PNL is between -0.1% and -7.9%, advise "WATCH" and define the exact hard stop loss price.
        
        You MUST respond ONLY in this exact JSON format.
        {{
            "action": "KEEP" or "TRIM" or "SELL" or "WATCH",
            "reasoning": "[2 sentences explaining the action based on the rules and news]",
            "proposed_stop": "[Exact dollar/euro amount or logic, e.g., 'Trail stop at €X']"
        }}
        """
        try:
            # CLEAN FIX: Force JSON output at the API level
            response = self.model.generate_content(
                system_prompt,
                generation_config=genai.GenerationConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception as e:
            return {"action": "ERROR", "reasoning": f"AI parsing failed: {e}", "proposed_stop": "N/A"}