import pandas as pd
from datetime import datetime
from src.database import SessionLocal, Position, Trade

class PortfolioManager:
    def __init__(self):
        # Transaction-based sessions for thread safety in Streamlit
        pass

    def get_equity_summary(self) -> dict:
        """Calculates total account equity, cash, and invested amounts."""
        db = SessionLocal()
        positions = db.query(Position).all()
        db.close()

        cash = 0.0
        invested = 0.0

        for p in positions:
            # We check for both EUR and CASH to be compatible with your previous setup
            if p.ticker in ["EUR", "CASH"]:
                cash += p.quantity
            elif p.quantity > 0:
                # Invested capital based on cost basis
                invested += (p.cost * p.quantity)

        return {
            "total_equity": round(cash + invested, 2),
            "cash": round(cash, 2),
            "invested": round(invested, 2)
        }

    def execute_buy(self, ticker, price, qty, target=0.0, reason="Hype Hunter Buy"):
        """Logs a buy transaction and updates cash balance."""
        db = SessionLocal()
        try:
            cash_pos = db.query(Position).filter(Position.ticker == "CASH").first()
            total_cost = price * qty
            
            if not cash_pos or cash_pos.quantity < total_cost:
                return False

            # 1. Deduct Cash
            cash_pos.quantity -= total_cost
            
            # 2. Add/Update Position
            existing_pos = db.query(Position).filter(Position.ticker == ticker).first()
            if existing_pos:
                # Average down/up logic
                new_total_qty = existing_pos.quantity + qty
                existing_pos.cost = ((existing_pos.cost * existing_pos.quantity) + total_cost) / new_total_qty
                existing_pos.quantity = new_total_qty
            else:
                new_pos = Position(ticker=ticker, cost=price, quantity=qty, date_acquired=datetime.now())
                db.add(new_pos)

            # 3. Log to Journal
            trade_log = Trade(
                ticker=ticker, 
                action="BUY", 
                quantity=qty, 
                price=price,
                date=datetime.now()
            )
            db.add(trade_log)
            
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Buy Error: {e}")
            return False
        finally:
            db.close()