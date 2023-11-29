import os
import sqlalchemy
import pytz
import json 

from cgitb import handler
from fastapi import FastAPI, File, UploadFile, Request, Depends, HTTPException
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from typing import Callable, List, Tuple

from dynaconf import Validator
from sqlalchemy.orm import Session
from sqlalchemy import func
from starlette.requests import Request
from datetime import datetime, date

from app.scripts import pydantic_models
from app.scripts.pydantic_models import Parameters, ParametersCreate, ParametersUpdate
from app.scripts.googlesearch import google_main


from app.db import db_models, crud
from app.db.database import  engine, metadata, SessionLocal
from app.config import settings

#############################CREATE DATABASE TABLES IF NECESSARY###################################
# The MetaData.create_all() method is, passing in our Engine as a source of database connectivity. 
# For all tables that haven’t been created yet, it issues CREATE TABLE statements to the database.


if not sqlalchemy.inspect(engine).has_table("queryandsearch_engine"):  # If table don't exist, Create.    
    tableobject_organization = [metadata.tables["queryandsearch_engine"]]
    db_models.Base.metadata.create_all(engine, tables=tableobject_organization)

#############################VALIDATE SETTINGS NEEDED##############################################
# for validation see https://dynaconf.readthedocs.io/en/docs_223/guides/validation.html

# Register validators
settings.validators.register(
    # Ensure some parameters exists (are required)
    Validator('DATABASE_URI', must_exist=True)    
)

# Fire the validator
settings.validators.validate()


# Load env variables
google_csid = os.environ.get("GOOGLE_CSID")

google_apikey = os.environ.get("GOOGLE_APIKEY")

query_limit = int(os.environ.get("QUERY_LIMIT"))


# Dependency: database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


#
# definitions to make the appearance of the API endpoints well structured and clear
#
tags_metadata = [
    {
        "name":"system",
        "description": "No specific functionality",
    },
    {
        "name": "google custom searchengine",
        "description": "API call to google custom search engine <br />" + "The minimum number to pass is <b>10<b> for <b>number_search_results<b> <br />",
    },
]

#############################CREATE FAST-API APP####################################################

app = FastAPI(
    title= "REST API for Salted Searchengine Service",
    description="service to give number of hits from searchengines",
    version="0.1.0",
    openapi_tags=tags_metadata,
)

# add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["application/json"],
)

################################################################################
#
# root entry point. Just returns a json welcome message.
#
@app.get("/" , tags=["system"])
async def root_entry():
    return {"message": "****** REST API for Salted Search Engine Service ******"}



################################################################################
#
# end point for a Google Custom SearchEngine
#
@app.post("/google/searchengine/",tags=["google custom searchengine"])
async def google_searchengine(request: Request, db: Session = Depends(get_db), parameters: Parameters = Depends()):
    # Define the valid engine string
    valid_engine = 'google'

    # Convert the engine parameter to lowercase
    parameters.engine = parameters.engine.lower()

    #check if the engine parameter is valid
    if parameters.engine != valid_engine:
        raise HTTPException(status_code=400, detail="Invalid engine. Please use 'google/GOOGLE'.")
    
    # Check the daily query limit
    today = date.today()
    query_count = db.query(func.count(db_models.Parameters.searchquery.distinct())).filter(
                                                db_models.Parameters.engine == parameters.engine,
                                                db_models.Parameters.first_requested_query >= today).scalar()
    if query_count >= query_limit:
        raise HTTPException(status_code=400, detail="Daily query limit exceeded. Maximum 1000 queries allowed per day.")

    # sourcery skip: remove-unnecessary-else, simplify-numeric-comparison
    db_item = db.query(db_models.Parameters).filter(db_models.Parameters.searchquery==parameters.searchquery, 
                                                    db_models.Parameters.language==parameters.language,
                                                    db_models.Parameters.number_search_results>=parameters.number_search_results,
                                                    db_models.Parameters.engine==parameters.engine).first()
    
    if db_item is not None:
        
        delta = datetime.now(pytz.utc) - db_item.modified
        if delta.total_seconds()/3600 < 24:
            db_item = jsonable_encoder(db_item)
            return db_item["api_json_output"][0:parameters.number_search_results]
        
        else:
            input_parameters = dict(parameters)
            google_out = str(google_main(google_csid, google_apikey, input_parameters))
            crud.update_searchquery(db=db, parameter=db_item, 
                                    updated_parameter=ParametersUpdate(number_search_results = input_parameters["number_search_results"],
                                    api_json_output = google_out, language = input_parameters["language"]))
    else:
        input_parameters  = dict(parameters)
        google_out = google_main(google_csid, google_apikey,input_parameters)
        print(type(google_out))
        db_googleoutput = pydantic_models.ParametersCreate(
            searchquery=input_parameters ["searchquery"],
            number_search_results = input_parameters ["number_search_results"],
            language = input_parameters["language"],
            api_json_output = google_out,
            engine = input_parameters ["engine"]
        )
        response = crud.create_searchquery(db=db, parameter=db_googleoutput)

    return google_out




if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, workers=1)

