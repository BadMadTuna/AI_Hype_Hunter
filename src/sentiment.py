import requests

class RedditScraper:
    def __init__(self):
        # Swapping to Ape Wisdom to bypass Cloudflare blocks
        self.api_url = "https://apewisdom.io/api/v1.0/filter/all-stocks/page/1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def get_ticker_sentiment(self, ticker: str, limit: int = 10) -> dict:
        """
        Fetches LIVE r/wallstreetbets sentiment data from Ape Wisdom.
        Checks if our target ticker is currently trending on Reddit.
        """
        try:
            response = requests.get(self.api_url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return {"mention_count": 0, "top_posts": [f"Error fetching live Reddit data. Status: {response.status_code}"]}
                
            data = response.json()
            results = data.get("results", [])
            
            # Hunt for our specific ticker in ApeWisdom's trending list
            ticker_data = next((item for item in results if item["ticker"].upper() == ticker.upper()), None)
            
            if ticker_data:
                mentions = ticker_data.get("mentions", 0)
                upvotes = ticker_data.get("upvotes", 0)
                rank = ticker_data.get("rank", "N/A")
                
                return {
                    "mention_count": mentions,
                    "top_posts": [
                        f"🚨 WSB RANKING: #{rank} Most Discussed Stock",
                        f"🗣️ Active Mentions (24h): {mentions}",
                        f"👍 Total Upvotes: {upvotes}"
                    ]
                }
            else:
                return {
                    "mention_count": 0,
                    "top_posts": [f"👻 ${ticker} is currently a ghost on Reddit.", "No massive retail hype detected in the top trending stocks today."]
                }
                
        except Exception as e:
            return {"mention_count": 0, "top_posts": [f"API Error: {e}"]}

# Quick test
if __name__ == "__main__":
    scraper = RedditScraper()
    print("Fetching live WSB data for NVDA from Ape Wisdom...")
    print(scraper.get_ticker_sentiment("NVDA"))