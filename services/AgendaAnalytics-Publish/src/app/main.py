from base64 import encode
from email import header
import logging
import os
from typing import List, Tuple

import sqlalchemy
import datetime
import json

from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from fastapi_utils.timing import add_timing_middleware
from fastapi.encoders import jsonable_encoder

from dynaconf import Validator

from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.api import pydantic_models
from app.api.scorpio_middleware import publish, broker_get_by_type
from app.db.database import  engine, SessionLocal, metadata
from app.db import db_models, crud

from app.logs.logger import CustomRoute, logging_text
import app.definitions as definitions


from app.utils.utils import PrometheusMiddleware, metrics, setting_otlp



#############################CREATE DATABASE TABLES IF NECESSARY###################################
# The MetaData.create_all() method is, passing in our Engine as a source of database connectivity. 
# For all tables that haven’t been created yet, it issues CREATE TABLE statements to the database.


if not sqlalchemy.inspect(engine).has_table("publish_service-logs"):  # If table don't exist, Create.    
    tableobject_servicelog = [metadata.tables["publish_service-logs"]]
    db_models.Base.metadata.create_all(engine, tables=tableobject_servicelog)
    logging_text.info("database table 'publish_service-logs' did not exist yet, therefor one was created.")

if not sqlalchemy.inspect(engine).has_table("publish_pastebin"):  # If table don't exist, Create.    
    tableobject_pastebin = [metadata.tables["publish_pastebin"]]
    db_models.Base.metadata.create_all(engine, tables=tableobject_pastebin)
    logging_text.info("database table 'publish_pastebin' did not exist yet, therefor one was created.")



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


# other env variables set
broker_url = os.environ.get("SCORPIO_URL")




#############################CREATE FAST-API APP####################################################

# Dependency: database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# scorpio dependency
def get_broker_url():
    return broker_url

app: FastAPI = FastAPI(title = "SALTED service: publish (REST API using FastAPI)", openapi_tags = [])



# add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
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
        mqtt_client.subscribe("publish/#", qos=2)

    def on_message(mqtt_client, obj, msg):

        logging_text.info(f"on message in {msg.topic}")
        data_in = msg.payload.decode()
        mqtt_message=json.loads(data_in)
        mqtt_data=mqtt_message["data"]
        mqtt_config = mqtt_message["parameters"]
        try:
            if isinstance(mqtt_data , list):
                mqtt_data_list = mqtt_data
            else:
                mqtt_data_list = [mqtt_data]
            published_entities = run_publish(jsonlist=mqtt_data_list, broker_url=get_broker_url())
            logging_text.info("feedback")
            logging_text.info(published_entities)
            if (msg.topic == "publish/dit_det_orga_specific"):
                mqtt_message= { 
                    "parameters": mqtt_config,
                    "data": published_entities[0]
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                
                (rc, mid)= mqtt_client.publish("crawling/publish/dit_det_orga_specific", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to crawling/dit_det_orga_specific: {}".format(rc, mid, mqtt.error_string(rc)))

            if (msg.topic == "publish/crawling/publish/dit_det_orga_specific"):
                mqtt_message= { 
                    "parameters": mqtt_config,
                    "data": published_entities[0]
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                
                (rc, mid)= mqtt_client.publish("agendamatching/publish/crawling/publish/dit_det_orga_specific", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to agendamatching/publish/crawling/publish/dit_det_orga_specific: {}".format(rc, mid, mqtt.error_string(rc)))
            
            if (msg.topic == "publish/agendamatching/publish/crawling/publish/dit_det_orga_specific"):
                mqtt_message= { 
                    "parameters": "None",
                    "data": "Done"
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                
                (rc, mid)= mqtt_client.publish("dit_det_orga_specific/publish", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to dit_det_orga_specific/publish: {}".format(rc, mid, mqtt.error_string(rc)))

            if (msg.topic == "publish/agendamatching/crawling/publish/dit_det_orga_specific"):
                mqtt_message= { 
                    "parameters": "None",
                    "data": "Done"
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                
                (rc, mid)= mqtt_client.publish("dit_det_orga_specific/publish", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to dit_det_orga_specific/publish: {}".format(rc, mid, mqtt.error_string(rc)))            
            
            
            if (msg.topic == "publish/mapping/discoverandstore/dit_orga_general"):
                mqtt_message= { 
                    "parameters": "None",
                    "data": "Done"
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                (rc, mid)= mqtt_client.publish("dit_orga_general/publish", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to dit_orga_general/publish: {}".format(rc, mid, mqtt.error_string(rc)))

            
            
            
            if (msg.topic == "publish/agendamatching/broker/urn:subscription:DDSRforAgendaMatching"):
                mqtt_message= { 
                    "parameters": "None",
                    "data": "Done"
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                (rc, mid)= mqtt_client.publish("urn:subscription:DDSRforAgendaMatching/publish", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to urn:subscription:DDSRforAgendaMatching/publish: {}".format(rc, mid, mqtt.error_string(rc)))

            
            if (msg.topic == "publish/agendamatching/det_agendamatching_specific"):
                mqtt_message= { 
                    "parameters": "None",
                    "data": "Done"
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                (rc, mid)= mqtt_client.publish("det_agendamatching_specific/publish", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to det_agendamatching_specific/publish: {}".format(rc, mid, mqtt.error_string(rc)))
            
            if (msg.topic == "publish/crawling/det_crawling_specific"):
                mqtt_message= { 
                    "parameters": "None",
                    "data": "Done"
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                (rc, mid)= mqtt_client.publish("det_crawling_specific/publish", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to det_crawling_specific/publish: {}".format(rc, mid, mqtt.error_string(rc)))
            
            
            
            if (msg.topic == "publish/crawling/det_crawling_general"):
                mqtt_message= { 
                    "parameters": "None",
                    "data": "Done"
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                (rc, mid)= mqtt_client.publish("det_crawling_general/publish", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to det_crawling_general/publish: {}".format(rc, mid, mqtt.error_string(rc)))

            if (msg.topic == "publish/agendamatching/det_agendamatching_general"):
                mqtt_message= { 
                    "parameters": "None",
                    "data": "Done"
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                (rc, mid)= mqtt_client.publish("det_agendamatching_general/publish", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to det_agendamatching_general/publish: {}".format(rc, mid, mqtt.error_string(rc)))


        
        except:
            mqtt_message= { 
            "parameters": "None",
            "data": "Error."
            }
            logging_text.info(mqtt_message)  
            data_out = json.dumps(mqtt_message)
            
            (rc, mid)= mqtt_client.publish(f"{msg.topic.split('/')[-1]}/publish", data_out, qos=2)
            logging_text.info("Code {} while sending message {} to discoverandstore/dit_orga_general: {}".format(rc, mid, mqtt.error_string(rc)))

               
      

    mqtt_client = mqtt.Client(client_id="publish_client", clean_session=False, userdata=None, protocol=mqtt.MQTTv31, transport="tcp")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_HOST, int(MQTT_PORT), keepalive=60)
    mqtt_client.loop_start() 



####################################endpoints#######################################

@app.post("/publish/jsonlist")
def run_publish(jsonlist:List, broker_url=Depends(get_broker_url)):
    try:
        logging_text.info(f"Scorpio inner port: {broker_url}")
        entities = jsonable_encoder(jsonlist)
        responses = []
        for entity in entities:    
            response, entity_broker=publish(entity,broker_url)
            if response==definitions.MESSAGE_SUCCESS:
                responses.append(entity_broker)       
    except:
        raise HTTPException(status_code=500, detail="Error occured. Contact support team at team@agenda-analytics.eu \U0001F635")
    return responses

@app.get("/broker/entities/{entitytype}",  tags=["query broker"])
def get_entities_bytype(entitytype: str, broker_url=Depends(get_broker_url),):
    try:
        logging_text.info(f"Scorpio inner port: {broker_url}")
        response = broker_get_by_type(entitytype,broker_url)        
        if response==definitions.MESSAGE_ERROR:
            raise HTTPException(status_code=500, detail="Error occured. Contact support team at team@agenda-analytics.eu \U0001F635")
    except:
        raise HTTPException(status_code=500, detail="Error occured. Contact support team at team@agenda-analytics.eu \U0001F635")
    return response


@app.post("/pastebin/", response_model=pydantic_models.PasteBinBase, tags=["pastebin"])
def create_pastebin(pastebin: str, db: Session = Depends(get_db)):
    logging_text.info(type(pastebin))
    return crud.create_pastebin(db=db, pastebin=pastebin)   



@app.get("/pastebin/{pastebin_id}", tags=["pastebin"]) 
def read_pastebin(pastebin_id:int, db:Session = Depends(get_db)):
    db_pastebin = crud.get_pastebin_by_id(db, pastebin_id=pastebin_id)
    if db_pastebin is None:
        raise HTTPException(status_code=404, detail="pastebin not found.", headers={"X-Error": "There goes my error"})
    try:
        json_test = json.loads(db_pastebin.bin)
        return Response(content=db_pastebin.bin, media_type="application/json")        
    except:
        logging_text.info("parsing str was not possible, therefor text response")
        return db_pastebin.bin        


@app.get("/pastebin/defaultcontext/Organization", tags=["pastebin"]) 
def read_pastebin_organization():
    json_bin = {
        "@context": [
            "https://raw.githubusercontent.com/smart-data-models/dataModel.Organization/master/context.jsonld",
            "https://smartdatamodels.org/context.jsonld"
    ]
    }

    return json_bin


@app.get("/pastebin/defaultcontext/EVChargingStation", tags=["pastebin"]) 
def read_pastebin_evchargingstation():
    json_bin = {
        "@context": [
        "https://raw.githubusercontent.com/smart-data-models/dataModel.Transportation/master/context.jsonld",
        "https://smartdatamodels.org/context.jsonld"
    ]
    }

    return json_bin


@app.get("/pastebin/defaultcontext/BikeHireDockingStation", tags=["pastebin"]) 
def read_pastebin_bikehiredockingstation():
    json_bin = {
        "@context": [
        "https://raw.githubusercontent.com/smart-data-models/dataModel.Transportation/master/context.jsonld",
        "https://smartdatamodels.org/context.jsonld"
    ]
    }

    return json_bin


@app.get("/pastebin/defaultcontext/KeyPerformanceIndicator", tags=["pastebin"]) 
def read_pastebin_keyperformanceindicator():
    json_bin = {
        "@context": [
        "https://raw.githubusercontent.com/smart-data-models/dataModel.KeyPerformanceIndicator/master/context.jsonld",
        "https://smartdatamodels.org/context.jsonld"
    ]
    }

    return json_bin



@app.get("/pastebin/defaultcontext/DataServiceDCAT-AP", tags=["pastebin"]) 
def read_pastebin_service():
    json_bin = {
        "@context": [
            "https://raw.githubusercontent.com/smart-data-models/dataModel.DCAT-AP/ca169c97d519c5ad77c53e00eafdbd2bdbe90e1b/context.jsonld",
            "https://smartdatamodels.org/context.jsonld"
        ]
    }
    return json_bin


@app.get("/pastebin/defaultcontext/DataServiceRun", tags=["pastebin"]) 
def read_pastebin_servicerun():
    json_bin = {
        "@context": [
            "https://raw.githubusercontent.com/smart-data-models/dataModel.DCAT-AP/ca169c97d519c5ad77c53e00eafdbd2bdbe90e1b/context.jsonld",
            "https://smartdatamodels.org/context.jsonld"
        ]
    }
    return json_bin


@app.get("/pastebin/defaultcontext/DistributionDCAT-AP", tags=["pastebin"]) 
def read_pastebin_distribution():
    json_bin = {       
        "@context": [
            "https://raw.githubusercontent.com/smart-data-models/dataModel.DCAT-AP/ca169c97d519c5ad77c53e00eafdbd2bdbe90e1b/context.jsonld",
            "https://smartdatamodels.org/context.jsonld"
        ]
    }
    return json_bin




# testing ping
@app.get("/ping")
def pong():
    return {"ping": "pong!"}