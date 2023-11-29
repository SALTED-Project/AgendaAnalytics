import logging
import os
from typing import List, Tuple

import sqlalchemy
import datetime
import json
import time
import requests

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from fastapi_utils.timing import add_timing_middleware
from fastapi.encoders import jsonable_encoder

from dynaconf import Validator

from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.api import pydantic_models
from app.db import db_models, crud
from app.db.database import  engine, SessionLocal, metadata
from app.api.ngsild_mapper import map_organization_discoverandstore, map_bikehiredockingstation_mrn, map_evchargingstation_mrn

from app.logs.logger import CustomRoute, logging_text


from app.utils.utils import PrometheusMiddleware, metrics, setting_otlp


#############################CREATE DATABASE TABLES IF NECESSARY###################################
# The MetaData.create_all() method is, passing in our Engine as a source of database connectivity. 
# For all tables that haven’t been created yet, it issues CREATE TABLE statements to the database.

if not sqlalchemy.inspect(engine).has_table("mapping_service-logs"):  # If table don't exist, Create.    
    tableobject_servicelog = [metadata.tables["mapping_service-logs"]]
    db_models.Base.metadata.create_all(engine, tables=tableobject_servicelog)
    logging_text.info("database table 'mapping_service-logs' did not exist yet, therefor one was created.")


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

app: FastAPI = FastAPI(title = "SALTED service: mapping (REST API using FastAPI)", openapi_tags = [])

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
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("GET /metrics") == -1

# Filter out metrics from logs
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

#################################### MQTT #######################################

MQTT_ENABLED = os.environ.get("MQTT_ENABLED", "False")
MQTT_HOST = os.environ.get("MQTT_HOST")
MQTT_PORT = os.environ.get("MQTT_PORT")
logging_text.info(f"MQTT enabled:{MQTT_ENABLED}")
logging_text.info(MQTT_HOST)
logging_text.info(MQTT_PORT)

if MQTT_ENABLED=="True":
    import paho.mqtt.client as mqtt    
    
    logging_text.info('Connecting to MQTT broker.')
    def on_connect(mqtt_client, obj, flags, rc):
        mqtt_client.subscribe("mapping/#", qos=2)

    def on_message(mqtt_client, obj, msg):
        if (msg.topic == "mapping/discoverandstore/dit_orga_general"):
            logging_text.info("on message in mapping/discoverandstore/dit_orga_general")
            data_in = msg.payload.decode()
            mqtt_message=json.loads(data_in)
            organization=mqtt_message["data"]
            agendaanalytics_config = mqtt_message["parameters"]
            try:
                mapped_organizations = run_organization_discoverandstore([organization])
                mqtt_message= { 
                    "parameters": agendaanalytics_config,
                    "data": mapped_organizations[0]
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                (rc, mid)= mqtt_client.publish("publish/mapping/discoverandstore/dit_orga_general", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to publish/mapping/discoverandstore/dit_orga_general: {}".format(rc, mid, mqtt.error_string(rc)))
            except:
                mqtt_message= { 
                "parameters": "None",
                "data": "Error."
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                
                (rc, mid)= mqtt_client.publish("dit_orga_general/mapping", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to dit_orga_general/mapping: {}".format(rc, mid, mqtt.error_string(rc)))


        

    mqtt_client = mqtt.Client(client_id="matching_client", clean_session=False, userdata=None, protocol=mqtt.MQTTv31, transport="tcp")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_HOST, int(MQTT_PORT), keepalive=60)
    mqtt_client.loop_start() # when should loop be stopped? 


####################################endpoints#######################################

@app.post("/organization/jsonlist/discoverandstore", tags=["organization"])
def run_organization_discoverandstore(organizations:pydantic_models.OrganizationList):
    try:
        organizations = jsonable_encoder(organizations)
        ngsild_organizations=[]
        for organization in organizations:   
            try:     
                ngsild_json=map_organization_discoverandstore(organization)
                ngsild_organizations.append(ngsild_json)
            except:
                logging_text.info("Skipping the following entity:")
                logging_text.info(organization)
    except:
        logging_text.info("Last handled entity:")
        logging_text.info(organization)
        raise HTTPException(status_code=500, detail="Service could not perform as intended. Contact support team at team@agenda-analytics.eu \U0001F635")
    return ngsild_organizations


# testing ping
@app.get("/ping")
def pong():
    return {"ping": "pong!"}




