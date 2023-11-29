import json
from pydantic import BaseModel
from typing import List
import datetime


# Pydantic models define more or less a "schema" (a valid data shape). They are used when reading data / returning it from the API.
# not to be confused with SQLAlchemy models that define database tables.   



class OrganizationBase(BaseModel):
    """
     This is the response model which is used for each single record of an organization / database entry. All timestamps are in UTC.
    It is also used through list[OrganizationBase] when a representation of multiple organizations is needed.
    """
    name: str
    legalform: str
    city: str
    url_google: str
    country: str
    postcode: str
    street: str
    housenumber: str
    lat: str
    long: str
    url_osm: str
    officecategory: str
    created: datetime.datetime
    modified: datetime.datetime
    origin_service: str 

    class Config:
        orm_mode = True

class OrganizationCreate(BaseModel):
    """
     This is the schema for posting a record.
    """
    name: str
    legalform: str
    city: str
    url_google: str
    country: str
    postcode: str
    street: str
    housenumber: str
    lat: str
    long: str
    officecategory: str
    url_osm: str
    origin_service: str

    class Config:
        orm_mode = True



class OrganizationUpdate(BaseModel):
    """
     This is the schema for updating a record.
    """
    legalform: str
    city: str
    url_google: str
    country: str
    postcode: str
    street: str
    housenumber: str
    lat: str
    long: str
    officecategory: str
    url_osm: str

    class Config:
        orm_mode = True


class OrganizationGoogleUpdate(BaseModel):
    """
     This is the schema for updating a record.
    """

    url_google: str

    class Config:
        orm_mode = True

class OrganizationOSMUpdate(BaseModel):
    """
     This is the schema for updating a record.
    """

    country: str
    postcode: str
    street: str
    housenumber: str
    lat: str
    long: str
    officecategory: str
    url_osm: str

    class Config:
        orm_mode = True


class OrganizationList(BaseModel):
    """
     This is a list of organizations.
    """
    __root__:List[OrganizationBase]




class ServiceLogBase(BaseModel):
    """
     This is the schema which is used for each single record of a service log / database entry. All timestamps are in UTC.
    """
    id: int
    service: str
    start: datetime.datetime
    end: datetime.datetime 
    duration: datetime.timedelta

    class Config:
        orm_mode = True

class ServiceLogCreate(BaseModel):
    """
        This is used for creating log entry.
    """
    service: str
    start: datetime.datetime
    
    class Config:
        orm_mode = True


class ServiceLogUpdate(BaseModel):
    """
        This is used for updating log entry.
    """
    end: datetime.datetime 
    duration: datetime.timedelta
    
    class Config:
        orm_mode = True