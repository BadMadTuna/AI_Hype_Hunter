from src.database import SessionLocal, Position, Trade
from datetime import datetime

class PortfolioManager:
    def get_summary(self):
        db = SessionLocal()
        pos = db.query(Position).all()
        db.close()
        cash = sum(p.quantity for p in pos if p.ticker == "CASH")
        invested = sum(p.cost * p.quantity for p in pos if p.ticker != "CASH")
        return {"cash": cash, "invested": invested, "total": cash + invested}

    def execute_buy(self, ticker, price, qty):
        db = SessionLocal()
        cash_pos = db.query(Position).filter(Position.ticker == "CASH").first()
        cost = price * qty
        
        if cash_pos.quantity >= cost:
            cash_pos.quantity -= cost
            new_pos = Position(ticker=ticker, cost=price, quantity=qty)
            db.add(new_pos)
            db.add(Trade(ticker=ticker, action="BUY", quantity=qty, price=price))
            db.commit()
            db.close()
            return True
        db.close()
        return False