""" Database models for the Fiindo recruitment challenge. """
from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base 
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

# Table 1: Per‑ticker statistics (calculated metrics)
class TickerStatistics(Base):
    __tablename__ = 'ticker_statistics'
    id = Column(Integer, primary_key=True)
    symbol = Column(String, unique=True, nullable=False)
    industry = Column(String, nullable=False)
    pe_ratio = Column(Float)
    revenue_growth = Column(Float)
    net_income_ttm = Column(Float)
    debt_ratio = Column(Float)

# Table 2: Aggregated industry metrics
class IndustryAggregation(Base):
    __tablename__ = 'industry_aggregation'
    id = Column(Integer, primary_key=True)
    industry = Column(String, unique=True, nullable=False)
    avg_pe_ratio = Column(Float)
    avg_revenue_growth = Column(Float)
    sum_of_revenue = Column(Float)


# Database setup
engine = create_engine("sqlite:///fiindo_challenge.db")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)