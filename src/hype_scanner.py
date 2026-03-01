import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

class HypeScanner:
    def get_tod_weight(self) -> float:
        """
        Calculates the Time-of-Day (ToD) volume weight based on a standard U-Curve.
        US Market Hours: 9:30 AM to 4:00 PM EST (390 minutes).
        """
        # Always calculate based on Wall Street time
        tz = pytz.timezone('US/Eastern')
        now = datetime.now(tz)
        
        # If it's the weekend or outside market hours, expect 100% of volume
        if now.weekday() >= 5 or now.hour < 9 or (now.hour == 9 and now.minute < 30) or now.hour >= 16:
            return 1.0
            
        elapsed_mins = (now.hour * 60 + now.minute) - (9 * 60 + 30)
        
        # Institutional U-Curve Heuristic Buckets
        # 0-30 mins (9:30-10:00): Expect 20%
        # 30-90 mins (10:00-11:00): Expect 15%
        # 90-330 mins (11:00-15:00): Expect 40%
        # 330-390 mins (15:00-16:00): Expect 25%
        
        if elapsed_mins <= 30:
            return (elapsed_mins / 30.0) * 0.20
        elif elapsed_mins <= 90:
            return 0.20 + ((elapsed_mins - 30) / 60.0) * 0.15
        elif elapsed_mins <= 330:
            return 0.35 + ((elapsed_mins - 90) / 240.0) * 0.40
        else:
            return 0.75 + ((elapsed_mins - 330) / 60.0) * 0.25

    def get_hype_metrics(self, ticker: str) -> dict:
        """Fetches technical data and calculates Time-Adjusted RVOL."""
        try:
            # Suppress yfinance output to keep logs clean
            stock = yf.Ticker(ticker)
            hist = stock.history(period="1mo")
            
            if len(hist) < 6:
                return None
                
            current_price = float(hist['Close'].iloc[-1])
            price_5d_ago = float(hist['Close'].iloc[-6])
            roc_5d = ((current_price - price_5d_ago) / price_5d_ago) * 100
            
            current_vol = float(hist['Volume'].iloc[-1])
            # Average of the previous 20 days (excluding today's incomplete candle)
            avg_vol = float(hist['Volume'].iloc[:-1].tail(20).mean())
            
            if avg_vol == 0:
                return None
                
            # --- THE MAGIC MATH ---
            tod_weight = self.get_tod_weight()
            expected_vol_so_far = avg_vol * tod_weight
            
            # Calculate True Intraday RVOL
            rvol = current_vol / expected_vol_so_far if expected_vol_so_far > 0 else 0
            
            # We also calculate traditional RVOL just for baseline comparison (optional)
            # traditional_rvol = current_vol / avg_vol
            
            return {
                "Ticker": ticker,
                "Price": round(current_price, 2),
                "RVOL": round(rvol, 2),
                "ROC_5_Days": round(roc_5d, 2),
                "Current_Volume": int(current_vol),
                "Expected_Volume": int(expected_vol_so_far)
            }
        except Exception:
            return None