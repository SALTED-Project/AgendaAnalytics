from typing import List, Any
from fastapi import Query
from pydantic import BaseModel, Field, Json
import datetime


class Parameters(BaseModel):
    """
    This is the schema for posting a searchterm and number of results
    """
    searchquery: str 
    engine: str 
    language: str
    number_search_results: int 

    class Config:
        orm_mode = True

class ParametersCreate(BaseModel):
    """
    This is the schema for creating parameters
    """
    searchquery: str
    number_search_results: int 
    api_json_output: Any
    engine: str
    language: str
    # first_requested_query : datetime.datetime
    # modified: datetime.datetime

    class Config:
        orm_mode = True

class ParametersUpdate(BaseModel):
    """
    This is the schema for updating parameters
    """
    number_search_results: int
    api_json_output: Any
    language: str

    class Config:
        orm_mode = True


    