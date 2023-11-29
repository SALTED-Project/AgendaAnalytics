import logging
import os
from typing import List, Tuple

import sqlalchemy
import datetime
import json
import time
import requests
import uuid
import urllib.parse

from fastapi import FastAPI, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from fastapi_utils.timing import add_timing_middleware
from fastapi.encoders import jsonable_encoder
from fastapi import status, Form


from pydantic import ValidationError

from dynaconf import Validator

import paho.mqtt.client as mqtt   

from prometheus_fastapi_instrumentator import Instrumentator

import pandas as pd
import numpy as np

from app.config import settings
from app.api import pydantic_models
from app.db import db_models, crud
from app.db.database import  engine, SessionLocal, metadata

from app.logs.logger import CustomRoute, logging_text

from app.utils.utils import PrometheusMiddleware, metrics, setting_otlp


#############################CREATE DATABASE TABLES IF NECESSARY###################################
# The MetaData.create_all() method is, passing in our Engine as a source of database connectivity. 
# For all tables that haven’t been created yet, it issues CREATE TABLE statements to the database.

if not sqlalchemy.inspect(engine).has_table("mqtttrigger_service-logs"):  # If table don't exist, Create.    
    tableobject_servicelog = [metadata.tables["mqtttrigger_service-logs"]]
    db_models.Base.metadata.create_all(engine, tables=tableobject_servicelog)
    logging_text.info("database table 'mqtttrigger_service-logs' did not exist yet, therefor one was created.")


#############################VALIDATE SETTINGS NEEDED##############################################
# for validation see https://dynaconf.readthedocs.io/en/docs_223/guides/validation.html

# Register validators
settings.validators.register(
    # Ensure some parameters exists (are required)
    Validator('DATABASE_URI', must_exist=True)   
    )

# Fire the validator
settings.validators.validate()

logging_text.info("dynaconf settings were succesfully validated.")


#############################CREATE FAST-API APP####################################################

tags_metadata = [
    {
        "name": "data enrichment toolchain",
        "description": "If the general approach is chosen, n random organizations will be used. n is set in the env variables of the crawling / agendamatching service. default=50.",
    }
]

app: FastAPI = FastAPI(title = "SALTED service: MQTTtrigger (REST API using FastAPI)", openapi_tags = tags_metadata)

# add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["application/json"]
)



#####################################for logging################################

# add timing middleware - unneccesary and spams log output
#logger = logging.getLogger(__name__)
#add_timing_middleware(app, record=logger.info, prefix="app", exclude="untimed")

# add logging route
app.router.route_class = CustomRoute

######################################for observability##########################

# Setting metrics middleware
APP_NAME = os.environ.get("APP_NAME", "app-default")
logging_text.info(APP_NAME)

app.add_middleware(PrometheusMiddleware, app_name=APP_NAME)
app.add_route("/metrics", metrics)

# Setting OpenTelemetry exporter
setting_otlp(app, APP_NAME, "http://tempo:4317")


class EndpointFilter(logging.Filter):
    # Uvicorn endpoint access log filter
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("GET /metrics") == -1


# Filter out /endpoint
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

#################################### MQTT #######################################

MQTT_HOST = os.environ.get("MQTT_HOST")
MQTT_PORT = os.environ.get("MQTT_PORT")
logging_text.info(MQTT_HOST)
logging_text.info(MQTT_PORT)

  

mqtt_client = mqtt.Client(client_id="mqtttrigger_client", clean_session=False, userdata=None, protocol=mqtt.MQTTv31, transport="tcp")
mqtt_client.connect(MQTT_HOST, int(MQTT_PORT), keepalive=60)
mqtt_client.loop_start() # when should loop be stopped? 


####################################endpoints#######################################

###############################################

# general endpoints

###############################################


# triggers DIT for one Organization entity, already supplied in NGSI-LD format
@app.post("/trigger/dit-det/organization/specific", tags=["data injection + enrichment toolchain"])
def run_trigger_dit_orga_specific(message:pydantic_models.TriggerDITDETSpecific):
    mqtt_message = jsonable_encoder(message)
    logging_text.info(mqtt_message)  
    data_out = json.dumps(mqtt_message)
    logging_text.info(type(mqtt_message))
    (rc, mid) = mqtt_client.publish("publish/dit_det_orga_specific", data_out, qos=2)    
    return "Code {} while sending message {} to publish/dit_det_orga_specific: {}".format(rc, mid, mqtt.error_string(rc))



# triggers DIT for all
@app.post("/trigger/dit/organization/general", tags=["data injection toolchain"])
def run_trigger_dit_orga_general(message:pydantic_models.TriggerDITGeneral):
    mqtt_message = jsonable_encoder(message)
    logging_text.info(mqtt_message)  
    data_out = json.dumps(mqtt_message)
    logging_text.info(type(mqtt_message))
    (rc, mid) = mqtt_client.publish("discoverandstore/dit_orga_general", data_out, qos=2)    
    return "Code {} while sending message {} to publish/dit_orga_general: {}".format(rc, mid, mqtt.error_string(rc))



# triggers DET Crawling for one Organization entity, already supplied in NGSI-LD format
@app.post("/trigger/det/crawling_service/specific", tags=["data enrichment toolchain"])
def run_trigger_det_crawling_specific(message:pydantic_models.TriggerDETSpecificCrawling):
    mqtt_message = jsonable_encoder(message)
    logging_text.info(mqtt_message)  
    data_out = json.dumps(mqtt_message)
    logging_text.info(type(mqtt_message))
    (rc, mid) = mqtt_client.publish("crawling/det_crawling_specific", data_out, qos=2)    
    return "Code {} while sending message {} to publish/det_crawling_specific: {}".format(rc, mid, mqtt.error_string(rc))


# triggers DET Crawling for all
@app.post("/trigger/det/crawling_service/general", tags=["data enrichment toolchain"])
def run_trigger_det_crawling_general(message:pydantic_models.TriggerDETGeneralCrawling):
    mqtt_message = jsonable_encoder(message)
    logging_text.info(mqtt_message)  
    data_out = json.dumps(mqtt_message)
    logging_text.info(type(mqtt_message))
    (rc, mid) = mqtt_client.publish("crawling/det_crawling_general", data_out, qos=2)    
    return "Code {} while sending message {} to publish/det_crawling_general: {}".format(rc, mid, mqtt.error_string(rc))


# triggers DET AgendaMatching for one Organization entity, already supplied in NGSI-LD format
@app.post("/trigger/det/agendamatching_service/specific", tags=["data enrichment toolchain"], )
def run_trigger_det_agendamatching_specific(message:pydantic_models.TriggerDETSpecificAgendaMatching):
    mqtt_message = jsonable_encoder(message)
    logging_text.info(mqtt_message)  
    data_out = json.dumps(mqtt_message)
    logging_text.info(type(mqtt_message))
    (rc, mid) = mqtt_client.publish("agendamatching/det_agendamatching_specific", data_out, qos=2)    
    return "Code {} while sending message {} to agendamatching/det_agendamatching_specific: {}".format(rc, mid, mqtt.error_string(rc))


# triggers DET AgendaMatching for all
@app.post("/trigger/det/agendamatching_service/general", tags=["data enrichment toolchain"])
def run_trigger_det_agendamatching_general(message:pydantic_models.TriggerDETGeneralAgendaMatching):
    mqtt_message = jsonable_encoder(message)
    logging_text.info(mqtt_message)  
    data_out = json.dumps(mqtt_message)
    logging_text.info(type(mqtt_message))
    (rc, mid) = mqtt_client.publish("agendamatching/det_agendamatching_general", data_out, qos=2)    
    return "Code {} while sending message {} to agendamatching/det_agendamatching_general: {}".format(rc, mid, mqtt.error_string(rc))



# testing ping
@app.get("/ping")
def pong():
    return {"ping": "pong!"}




