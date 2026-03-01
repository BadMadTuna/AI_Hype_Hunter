import os
import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'hype_hunter.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={'check_same_thread': False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
    action = Column(String) # BUY, SELL, TRIM
    quantity = Column(Float)
    price = Column(Float)
    pnl_pct = Column(Float)

Base.metadata.create_all(bind=engine)

def init_cash(amount=100000.0):
    db = SessionLocal()
    if not db.query(Position).filter(Position.ticker == "CASH").first():
        db.add(Position(ticker="CASH", quantity=amount, cost=1.0))
        db.commit()
    db.close()