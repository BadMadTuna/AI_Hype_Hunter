import yfinance as yf

class RedditScraper: # Keeping the class name so we don't break app.py imports
    def __init__(self):
        pass

    def get_ticker_sentiment(self, ticker: str, limit: int = 10) -> dict:
        """
        Fetches Short Interest & Float data.
        Cleaned to provide pure quantitative data to the AI without prompt injection.
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Extract squeeze metrics
            short_float = info.get('shortPercentOfFloat')
            short_pct = round(short_float * 100, 2) if short_float else 0.0
            short_ratio = info.get('shortRatio', 0)
            float_shares = info.get('floatShares', 0)
            
            # Format large numbers for readability
            def fmt(n):
                if not n: return "N/A"
                if n >= 1e9: return f"{n/1e9:.2f}B"
                if n >= 1e6: return f"{n/1e6:.2f}M"
                return str(n)

            return {
                "mention_count": f"{short_pct}%", # Hijacking this variable for the UI metric box
                "top_posts": [
                    f"🔥 Short % of Float: {short_pct}%",
                    f"⏳ Days to Cover (Short Ratio): {short_ratio}",
                    f"🌊 Public Float: {fmt(float_shares)} shares"
                    # Removed the "SYSTEM OVERRIDE" prompt injection hack.
                    # The AI will now evaluate these pure metrics based on its updated system prompt.
                ]
            }
        except Exception as e:
            return {
                "mention_count": "N/A", 
                "top_posts": [f"Error fetching squeeze data: {e}"]
            }