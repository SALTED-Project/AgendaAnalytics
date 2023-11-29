from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, PickleType, Time, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB

from app.db.database import Base

# creation of all models (class) attributes
# each of these attributes represents a column in its corresponding database table

class Organization(Base):
    __tablename__ = "discoverandstore_organizations"

    name = Column(String, unique=True, index=True, primary_key=True)
    legalform = Column("legalform", String)
    city = Column("location", String)
    url_google = Column("url_google", String, default="")
    country = Column("country", String, default="")
    postcode = Column("postcode", String, default="")
    street = Column("street", String, default="")
    housenumber = Column("housenumber", String, default="")
    lat = Column("lat", String, default="")
    long = Column("long", String, default="")
    officecategory = Column("officecategory", String, default="")
    url_osm = Column("url_osm", String, default="")
    created = Column("created", DateTime(timezone=True), nullable=False, server_default=func.now())
    modified = Column("modified",DateTime(timezone=True), nullable=True, server_default=func.now(), server_onupdate=func.now())
    origin_service = Column("origin_service", String, nullable=False)



class ServiceLog(Base):
    __tablename__ = "discoverandstore_service-logs"

    id = Column(Integer, unique=True, index=True, primary_key=True)
    service = Column("service", String, nullable=False)
    start = Column("start", DateTime(timezone=True), nullable=False)
    end = Column("end", DateTime(timezone=True),nullable=True )
    duration = Column("duration", Time, nullable=True )
    
    


 