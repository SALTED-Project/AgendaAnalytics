import json
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import datetime
from bson import ObjectId


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