from app.config import settings
from dynaconf import Validator

import logging


from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


DATABASE_URL = settings.DATABASE_URI

# create a SQLAlchemy "engine"
engine = create_engine(
    DATABASE_URL, pool_size=10, max_overflow=0, echo = False
)


# creates SessionLocal class - can be used, if needed
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# use function declarative_base() that returns a class - later used by inheriting from that class to create each of the database models
Base = declarative_base()


# Each Table object is a member of larger collection known as MetaData and this object is available using the .metadata attribute of declarative base class. 
metadata = Base.metadata




