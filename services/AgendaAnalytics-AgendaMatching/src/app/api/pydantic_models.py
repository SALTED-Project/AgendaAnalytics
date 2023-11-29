import json
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Any
import datetime
from bson import ObjectId

class ScorpioSubscriptionDSRCrawling(BaseModel):
    id: Any
    type: Any
    subscriptionId: Any
    notifiedAt: Any
    data: Any

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
            "id": "ngsildbroker:notification:-6512655300717763020",
            "type": "Notification",
            "subscriptionId": "urn:subscription:DDSR",
            "notifiedAt": "2023-03-23T15:01:53.679000Z",
            "data": [ ] 
            }}


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