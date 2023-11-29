from app.config import settings
from dynaconf import Validator

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


import logging



# for validation see https://dynaconf.readthedocs.io/en/docs_223/guides/validation.html

# Register validators
settings.validators.register(
    # Ensure some parameters exists (are required)
    Validator('DATABASE_URI_TEST', must_exist=True)
)

# Fire the validator
settings.validators.validate()

logging.info("dynaconf settings for test-db access were succesfully validated.")

DATABASE_URL_TEST = settings.DATABASE_URI_TEST


# create a SQLAlchemy "engine"
engine = create_engine(
    DATABASE_URL_TEST, pool_size=10, max_overflow=0, echo = False
)

# not used at the moment
# creates SessionLocal class - can be used, if needed
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# use function declarative_base() that returns a class - later used by inheriting from that class to create each of the database models
Base = declarative_base()


# Each Table object is a member of larger collection known as MetaData and this object is available using the .metadata attribute of declarative base class. 
metadata = Base.metadata



