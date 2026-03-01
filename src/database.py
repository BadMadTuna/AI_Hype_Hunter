import os
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# --- PATH SETUP ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'hype_hunter.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# --- DATABASE SETUP ---
engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- TABLE SCHEMAS ---
class Position(Base):
    __tablename__ = 'portfolio'
    id = Column(Integer, primary_key=True)
    ticker = Column(String, nullable=False)
    cost = Column(Float)
    quantity = Column(Float)
    date_acquired = Column(DateTime, default=datetime.now)

class Trade(Base):
    __tablename__ = 'journal'
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.now)
    ticker = Column(String)
    action = Column(String) # BUY, SELL
    quantity = Column(Float)
    price = Column(Float)
    pnl_pct = Column(Float)

Base.metadata.create_all(bind=engine)

# --- HELPER FUNCTIONS FOR STREAMLIT ---

def init_cash(amount=10000.0):
    """Sets the initial virtual trading balance."""
    db = SessionLocal()
    # Using 'CASH' as the ticker for the balance row
    if not db.query(Position).filter(Position.ticker == "CASH").first():
        db.add(Position(ticker="CASH", quantity=amount, cost=1.0))
        db.commit()
    db.close()

def get_portfolio_df() -> pd.DataFrame:
    """Returns current holdings as a Pandas DataFrame for the UI."""
    db = SessionLocal()
    positions = db.query(Position).all()
    db.close()
    
    if not positions:
        return pd.DataFrame()
        
    data = [{
        "Ticker": p.ticker, 
        "Avg Cost": p.cost, 
        "Quantity": p.quantity, 
        "Acquired": p.date_acquired.strftime("%Y-%m-%d")
    } for p in positions]
    return pd.DataFrame(data)

def get_journal_df() -> pd.DataFrame:
    """Returns trade history as a Pandas DataFrame for the UI."""
    db = SessionLocal()
    trades = db.query(Trade).order_by(Trade.date.desc()).all()
    db.close()
    
    if not trades:
        return pd.DataFrame()
        
    data = [{
        "Date": t.date.strftime("%Y-%m-%d %H:%M"), 
        "Ticker": t.ticker, 
        "Action": t.action, 
        "Qty": t.quantity, 
        "Price": t.price
    } for t in trades]
    return pd.DataFrame(data)