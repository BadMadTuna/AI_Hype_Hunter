import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class HypeScanner:
    def __init__(self):
        self.api_key = os.getenv("TIINGO_API_KEY")
        if not self.api_key:
            raise ValueError("⚠️ TIINGO_API_KEY not found in .env file.")
        
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {self.api_key}'
        }

    def get_hype_metrics(self, ticker: str, lookback_days: int = 40) -> dict:
        try:
            start_date = (datetime.now() - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
            url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices?startDate={start_date}"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return None
                
            data = response.json()
            if len(data) < 20: 
                return None 

            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df.sort_values('date', inplace=True)

            # --- THE FIX: Calculate ALL math on the dataframe first ---
            df['Volume_SMA_20'] = df['volume'].rolling(window=20).mean()
            df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
            df['ROC_5'] = df['close'].pct_change(periods=5) * 100

            # --- NOW take the snapshot of the latest day ---
            latest = df.iloc[-1]
            prev = df.iloc[-2]
            
            current_vol = latest['volume']
            avg_vol = latest['Volume_SMA_20']
            rvol = current_vol / avg_vol if avg_vol > 0 else 0
            gap_pct = ((latest['open'] - prev['close']) / prev['close']) * 100

            return {
                "Ticker": ticker,
                "Price": round(latest['close'], 2),
                "RVOL": round(rvol, 2),
                "Gap_Pct": round(gap_pct, 2),
                "ROC_5_Days": round(latest['ROC_5'], 2),
                "Above_9_EMA": latest['close'] > latest['EMA_9'],
                "Volume": int(current_vol)
            }
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            return None