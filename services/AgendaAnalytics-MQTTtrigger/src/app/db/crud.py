from codecs import StreamWriter
from sys import set_coroutine_origin_tracking_depth
from pytz import country_names
from sqlalchemy.orm import Session
import datetime
import json

from pydantic import parse_obj_as
from typing import List

from app.db import db_models
from app.api import pydantic_models
from app.logs.logger import logging_text


def create_servicelog(db: Session, servicelog: pydantic_models.ServiceLogCreate):
    db_servicelog = db_models.ServiceLog(
            service = servicelog.service,
            start=servicelog.start
    )
    db.add(db_servicelog)
    db.commit()  
    return db_servicelog


def update_servicelog(db: Session, servicelog: db_models.ServiceLog, updated_servicelog: pydantic_models.ServiceLogUpdate):
    servicelog.end = updated_servicelog.end
    servicelog.duration = updated_servicelog.duration
    db.commit()
    return servicelog



def get_servicelog_by_id(db: Session, servicelog_id: int):
    servicelog = db.query(db_models.ServiceLog).filter(db_models.ServiceLog.id == servicelog_id).first()
    return servicelog