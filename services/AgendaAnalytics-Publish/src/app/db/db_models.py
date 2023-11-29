from email.policy import default
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, PickleType, Time, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from app.db.database import Base

# creation of all models (class) attributes
# each of these attributes represents a column in its corresponding database table


class ServiceLog(Base):
    __tablename__ = "publish_service-logs"

    id = Column(Integer, unique=True, index=True, primary_key=True)
    service = Column("service", String, nullable=False)
    start = Column("start", DateTime(timezone=True), nullable=False)
    end = Column("end", DateTime(timezone=True),nullable=True )
    duration = Column("duration", Time, nullable=True )
    
    

class PasteBin(Base):
    __tablename__ = "publish_pastebin"

    id = Column(Integer, unique=True, index=True, primary_key=True)
    bin = Column("bin", String)
    