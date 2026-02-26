import requests

class DiscoveryEngine:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.base_url = "https://query1.finance.yahoo.com/v1/finance/screener/predefined/saved"

    def _fetch_screener(self, screener_id: str, count: int = 50) -> list:
        try:
            params = {"formatted": "false", "scrIds": screener_id, "count": count}
            response = requests.get(self.base_url, headers=self.headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            quotes = data['finance']['result'][0]['quotes']
            tickers = [q['symbol'] for q in quotes if 'symbol' in q and "^" not in q['symbol'] and "-" not in q['symbol']]
            return tickers
        except Exception as e:
            print(f"Failed to fetch {screener_id}: {e}")
            return []

    def get_live_market_movers(self) -> list:
        print("Scouting Yahoo Finance for today's live movers...")
        gainers = self._fetch_screener("day_gainers", 50)
        active = self._fetch_screener("most_active", 50)
        
        combined_tickers = list(set(gainers + active))
        clean_tickers = [t for t in combined_tickers if len(t) <= 5]
        return clean_tickers