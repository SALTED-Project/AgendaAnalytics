import json
import datetime
from pydantic import parse_obj_as
from typing import List
from sqlalchemy.orm import Session
from app.db import db_models
from app.scripts import pydantic_models

def get_searchqueries(db:Session):
    return db.query(db_models.Parameters).all()

def create_searchquery(db: Session, parameter: pydantic_models.ParametersCreate):
    db_searchengine = db_models.Parameters(
        searchquery = parameter.searchquery,
        number_search_results = parameter.number_search_results,
        language = parameter.language,
        api_json_output = parameter.api_json_output,
        engine = parameter.engine
    )
    db.add(db_searchengine)
    db.commit()
    db.refresh(db_searchengine)
    return db_searchengine


def update_searchquery(db: Session, parameter: db_models.Parameters, updated_parameter: pydantic_models.ParametersUpdate):
    parameter.number_search_results = updated_parameter.number_search_results
    parameter.api_json_output = updated_parameter.api_json_output
    parameter.language = updated_parameter.language 
    parameter.modified = datetime.datetime.utcnow()
    db.commit()
    db.refresh(parameter)
    return parameter