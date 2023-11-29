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

# number of reusable functions dedicated to interacting with the db independent of path operations

def get_organization_by_name(db: Session, organization_name: str):
    return db.query(db_models.Organization).filter(db_models.Organization.name == organization_name).first()

def get_organizations(db: Session):
    return db.query(db_models.Organization).all()


def create_organization(db: Session, organization: pydantic_models.OrganizationCreate):
    db_organization = db_models.Organization(
        name=organization.name,
        legalform=organization.legalform,
        city=organization.city,
        url_google=organization.url_google,
        country=organization.country,
        postcode=organization.postcode,
        street=organization.street,
        housenumber=organization.housenumber ,
        lat=organization.lat, 
        long=organization.long,
        officecategory=organization.officecategory,
        url_osm=organization.url_osm,
        origin_service=organization.origin_service
    )
    db.add(db_organization)
    db.commit()    
    db.refresh(db_organization)
    return db_organization


def update_organization(db: Session, organization: db_models.Organization, updated_organization: pydantic_models.OrganizationUpdate):    
    organization.legalform = updated_organization.legalform
    organization.city = updated_organization.city
    organization.url_google = updated_organization.url_google
    organization.country = updated_organization.country
    organization.postcode = updated_organization.postcode
    organization.street = updated_organization.housenumber
    organization.lat = updated_organization.lat
    organization.long = updated_organization.long
    organization.officecategory = updated_organization.officecategory
    organization.url_osm = updated_organization.url_osm
    organization.modified = datetime.datetime.utcnow()
    db.commit()
    db.refresh(organization)
    return organization

def update_google_organization(db: Session, organization: db_models.Organization, updated_organization: pydantic_models.OrganizationGoogleUpdate):
    organization.url_google = updated_organization.url_google
    organization.modified = datetime.datetime.utcnow()
    db.commit()
    db.refresh(organization)
    return organization   

def update_osm_organization(db: Session, organization: db_models.Organization, updated_organization: pydantic_models.OrganizationOSMUpdate):
    organization.country=updated_organization.country
    organization.postcode=updated_organization.postcode
    organization.street=updated_organization.street
    organization.housenumber=updated_organization.housenumber
    organization.lat=updated_organization.lat
    organization.long=updated_organization.long
    organization.officecategory = updated_organization.officecategory
    organization.url_osm=updated_organization.url_osm
    organization.modified = datetime.datetime.utcnow()
    db.commit()
    db.refresh(organization)
    return organization   


def delete_organization_by_name(db: Session, organization: db_models.Organization):
    db.delete(organization)
    db.commit()
    return {"Deleted organization successfully."}


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