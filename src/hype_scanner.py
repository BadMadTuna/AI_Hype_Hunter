import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

class HypeScanner:
    def get_tod_weight(self, last_candle_date) -> float:
        """
        Calculates the Time-of-Day (ToD) volume weight based on a standard U-Curve.
        Only applies the fractional weight if the last candle is from TODAY, during active market hours.
        """
        # Always calculate based on Wall Street time
        tz = pytz.timezone('US/Eastern')
        now = datetime.now(tz)
        
        # 1. THE HOLIDAY/WEEKEND FIX: If the data is from a previous day
        # we know it's a 100% completed trading session.
        if last_candle_date < now.date():
            return 1.0
            
        # 2. THE PRE-MARKET FIX: If it is today, but before 9:30 AM EST 
        # (e.g., pre-market data trickling in before the open)
        if now.hour < 9 or (now.hour == 9 and now.minute < 30):
            return 1.0
            
        # 3. THE AFTER-HOURS FIX: If it is today, but after 4:00 PM EST 
        # (the trading session is 100% completed)
        if now.hour >= 16:
            return 1.0
            
        # 4. We are currently IN the active trading session. Apply the U-Curve.
        elapsed_mins = (now.hour * 60 + now.minute) - (9 * 60 + 30)
        
        # Institutional U-Curve Heuristic Buckets
        if elapsed_mins <= 30:
            return max(0.01, (elapsed_mins / 30.0) * 0.20)
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
                
            # Grab the date of the very last candle (Safe extraction)
            try:
                last_candle_date = hist.index[-1].date()
            except AttributeError:
                last_candle_date = hist.index[-1]
            
            current_price = float(hist['Close'].iloc[-1])
            price_5d_ago = float(hist['Close'].iloc[-6])
            roc_5d = ((current_price - price_5d_ago) / price_5d_ago) * 100
            
            current_vol = float(hist['Volume'].iloc[-1])
            # Average of the previous 20 days (excluding the latest candle)
            avg_vol = float(hist['Volume'].iloc[:-1].tail(20).mean())
            
            if avg_vol == 0:
                return None
                
            # --- THE MAGIC MATH ---
            tod_weight = self.get_tod_weight(last_candle_date)
            expected_vol_so_far = avg_vol * tod_weight
            
            # Calculate True Intraday RVOL
            rvol = current_vol / expected_vol_so_far if expected_vol_so_far > 0 else 0
            
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