import datetime
from email.policy import default
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB


from app.db.database import Base

"""
Changed/removed unique = True for searchquery
"""



class Parameters(Base):
    __tablename__ = "queryandsearch_engine"
    
    searchquery = Column(String, index = True, nullable=False, primary_key=True)
    number_search_results = Column("number_search_results", Integer, primary_key=True)
    language: str = Column("language", String, primary_key=True)
    api_json_output = Column("api_json_output", JSON)
    engine = Column(String, nullable=False,primary_key=True)
    # engine = Column("engine", String, nullable=False,primary_key=True)
    first_requested_query = Column("first_requested_query", DateTime(timezone=True), nullable=False, server_default=func.now())
    modified = Column("modified",DateTime(timezone=True), nullable=False, default=func.now(), server_onupdate=func.now()) 
    