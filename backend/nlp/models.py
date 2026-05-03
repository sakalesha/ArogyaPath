from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from database import Base

class ProcedureRate(Base):
    """
    Official benchmark rates (CGHS / PM-JAY Master Data).
    """
    __tablename__ = "procedure_rates"

    id = Column(Integer, primary_key=True, index=True)
    pathway_id = Column(String, unique=True, index=True) # e.g., "pathway_angina"
    condition_name = Column(String)
    icd10 = Column(String)
    
    # Official benchmarks
    cghs_base_rate = Column(Float)
    pmjay_limit = Column(Float)
    is_pmjay_covered = Column(Boolean, default=True)
    
    # Components (stored as JSON for flexibility)
    base_components = Column(JSON) 
    
    last_synced = Column(DateTime(timezone=True), server_default=func.now())

class UserReportedCost(Base):
    """
    Crowdsourced data from real patients.
    """
    __tablename__ = "user_reported_costs"

    id = Column(Integer, primary_key=True, index=True)
    pathway_id = Column(String, index=True)
    hospital_id = Column(String, index=True) # ID from Maps or internal DB
    hospital_name = Column(String)
    city = Column(String, index=True)
    
    actual_cost_paid = Column(Float)
    user_rating_of_experience = Column(Integer, nullable=True)
    reported_at = Column(DateTime(timezone=True), server_default=func.now())
    is_verified = Column(Boolean, default=False)
