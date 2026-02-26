import requests

class RedditScraper:
    def __init__(self):
        self.api_url = "https://tradestie.com/api/v1/apps/reddit"

    def get_ticker_sentiment(self, ticker: str, limit: int = 10) -> dict:
        try:
            response = requests.get(self.api_url, timeout=10)
            if response.status_code != 200:
                return {"mention_count": 0, "top_posts": ["Error fetching live Reddit data."]}
                
            data = response.json()
            ticker_data = next((item for item in data if item["ticker"].upper() == ticker.upper()), None)
            
            if ticker_data:
                sentiment = ticker_data.get("sentiment", "Neutral")
                score = ticker_data.get("sentiment_score", 0)
                mentions = ticker_data.get("no_of_comments", 0)
                
                return {
                    "mention_count": mentions,
                    "top_posts": [
                        f"🚨 WSB SENTIMENT ALGORITHM: {sentiment.upper()}",
                        f"📊 Algorithmic Sentiment Score: {score:.3f}",
                        f"🗣️ Total active discussions today: {mentions} threads"
                    ]
                }
            else:
                return {
                    "mention_count": 0,
                    "top_posts": [f"👻 ${ticker} is currently a ghost on r/wallstreetbets.", "No massive retail hype detected in the top 50 today."]
                }
                
        except Exception as e:
            return {"mention_count": 0, "top_posts": [f"API Error: {e}"]}