import os
import json
import google.generativeai as genai

class HypeAgent:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def _clean_json(self, text):
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def get_hype_verdict(self, ticker: str, hype_metrics: dict, news: str, social_data: dict):
        system_prompt = f"""
        You are a highly aggressive Momentum Trader and Venture Capitalist.
        Analyze a stock that just experienced a massive, unusual volume spike.
        
        TICKER: {ticker}
        HYPE METRICS (Volume & Velocity): {hype_metrics}
        RECENT NEWS & CATALYSTS: {news}
        WALLSTREETBETS SENTIMENT: {social_data}
        
        YOUR RULES:
        1. Ignore traditional valuation. We only care about ATTENTION, NARRATIVE, and CROWD PSYCHOLOGY.
        2. Grade the Catalyst: 
           - 'Tier 1 Structural': Paradigm shift, massive new TAM, AI breakthroughs.
           - 'Tier 2 Material': Massive earnings beat, multi-year contract, extreme retail short-squeeze.
           - 'Tier 3 Fluff': Analyst upgrades, CEO buzzwords.
        3. Evaluate the WSB Data: If the algorithm says "BULLISH" and there are high discussion threads, drastically increase the Hype Score.
        4. Provide a punchy, 2-3 sentence thesis focused on the narrative and crowd momentum.
        
        You MUST respond ONLY in this exact JSON format. Do not include any other text:
        {{
            "hype_score": [Integer 0-100 indicating crowd frenzy and narrative strength],
            "catalyst_tier": "Tier 1 Structural" or "Tier 2 Material" or "Tier 3 Fluff",
            "verdict": "RIDE THE HYPE" or "WATCH" or "FADE (Sell Short)",
            "vc_thesis": "[Your 2-3 sentence narrative thesis incorporating the WSB sentiment]"
        }}
        """
        try:
            response = self.model.generate_content(system_prompt)
            clean_text = self._clean_json(response.text)
            return json.loads(clean_text)
        except Exception as e:
            return {"hype_score": 0, "catalyst_tier": "Error", "verdict": "ERROR", "vc_thesis": f"AI Error: {e}"}