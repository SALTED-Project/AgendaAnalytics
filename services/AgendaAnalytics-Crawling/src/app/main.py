import logging
import os
from typing import Tuple, List

import sqlalchemy
import json
import uuid
import time
import requests
import random



from fastapi import FastAPI, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from fastapi_utils.timing import add_timing_middleware
from fastapi.encoders import jsonable_encoder

from dynaconf import Validator

from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.db import db_models, crud
from app.db.database import  engine, SessionLocal, metadata
from app.api import pydantic_models, crawler, broker, fileserver, dataservicerun
from app.logs.logger import CustomRoute, logging_text


from app.utils.utils import PrometheusMiddleware, metrics, setting_otlp
import app.definitions as definitions


#############################CREATE DATABASE TABLES IF NECESSARY###################################
# The MetaData.create_all() method is, passing in our Engine as a source of database connectivity. 
# For all tables that haven’t been created yet, it issues CREATE TABLE statements to the database.

if not sqlalchemy.inspect(engine).has_table("crawling_service-logs"):  # If table don't exist, Create.    
    tableobject_servicelog = [metadata.tables["crawling_service-logs"]]
    db_models.Base.metadata.create_all(engine, tables=tableobject_servicelog)
    logging_text.info("database table 'crawling_service-logs' did not exist yet, therefor one was created.")

#############################VALIDATE SETTINGS NEEDED##############################################
# for validation see https://dynaconf.readthedocs.io/en/docs_223/guides/validation.html

# Register validators
settings.validators.register(
    # Ensure some parameters exists (are required)
    Validator('DATABASE_URI', must_exist=True),
    Validator('GOOGLE_N_RESULTS_REPORT', must_exist=True),
    Validator('GOOGLE_N_RESULTS_GOOGLE', must_exist=True),
    Validator('VDPP_MONGODB_URI', must_exist=True)
)

# Fire the validator
settings.validators.validate()

logging_text.info("dynaconf settings were succesfully validated.")


# other env variables set
vdpp_middleware_api = os.environ.get("VDPP_MIDDLEWARE_API")
logging_text.info(vdpp_middleware_api)

salted_fileserver_service = os.environ.get("SALTED_FILESERVER_SERVICE")
logging_text.info(salted_fileserver_service)

salted_publish_service = os.environ.get("SALTED_PUBLISH_SERVICE")
logging_text.info(salted_publish_service)

random_sublist_broker = int(os.environ.get("RANDOM_SUBLIST_BROKER"))
logging_text.info(random_sublist_broker)

salted_searchengine_service = os.environ.get("SALTED_SEARCHENGINE_SERVICE")
logging_text.info(salted_searchengine_service)

#############################CREATE FAST-API APP####################################################

# Dependency: database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app: FastAPI = FastAPI(title = "SALTED service: crawling (REST API using FastAPI & PostgreSQL)", openapi_tags = [])

# vdpp middleware api dependency
def get_vdpp_middleware_api():
    return vdpp_middleware_api

# vdpp mongodb dependency
def get_vdpp_mongodb_uri():
    return settings.VDPP_MONGODB_URI

# salted fileserver service dependency
def get_salted_fileserver_service():
    return salted_fileserver_service

# salted publish service dependency
def get_salted_publish_service():
    return salted_publish_service





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
        mqtt_client.subscribe("crawling/#", qos=2)

    def on_message(mqtt_client, obj, msg):
        
        logging_text.info(f"on message in {msg.topic}")
        data_in = msg.payload.decode()
        mqtt_message=json.loads(data_in)
        try:
            mqtt_data=mqtt_message["data"]
        except: 
            mqtt_data={}
            
        mqtt_config = mqtt_message["parameters"]

        if isinstance(mqtt_data , list):
            mqtt_data_list = mqtt_data
        else:
            mqtt_data_list = [mqtt_data]        
        
        if (msg.topic == "crawling/publish/dit_det_orga_specific"):
            try:
                dsr_entities = get_organization_webdata(response = Response(),approach = mqtt_config["crawling"]["approach"],keywords=mqtt_config["crawling"]["keywords"],language=mqtt_config["crawling"]["language"],custom_depth=mqtt_config["crawling"]["custom_depth"],actuality_days=mqtt_config["crawling"]["actuality_days"], target_agenda_entity_id=mqtt_config["crawling"]["target_agenda_entity_id"],jsonlist=mqtt_data_list, vdpp_middleware_api=get_vdpp_middleware_api(), vdpp_mongodb_uri=get_vdpp_mongodb_uri(), salted_fileserver_service=get_salted_fileserver_service(), salted_publish_service=get_salted_publish_service())
                if dsr_entities != []:
                    mqtt_message= { 
                        "parameters": mqtt_config,
                        "data": dsr_entities
                    }
                    logging_text.info(mqtt_message)  
                    data_out = json.dumps(mqtt_message)
                    (rc, mid)= mqtt_client.publish("publish/crawling/publish/dit_det_orga_specific", data_out, qos=2)
                    logging_text.info("Code {} while sending message {} to publish/crawling/publish/dit_det_orga_specific : {}".format(rc, mid, mqtt.error_string(rc)))
                else:
                    mqtt_message= { 
                    "parameters": mqtt_config,
                    "data": mqtt_data_list[0]
                    }
                    logging_text.info(mqtt_message)  
                    data_out = json.dumps(mqtt_message)
                    
                    (rc, mid)= mqtt_client.publish("agendamatching/crawling/publish/dit_det_orga_specific", data_out, qos=2)
                    logging_text.info("Code {} while sending message {} to agendamatching/crawling/publish/dit_det_orga_specific: {}".format(rc, mid, mqtt.error_string(rc)))
            except:
                mqtt_message= { 
                "parameters": "None",
                "data": "Error."
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                
                (rc, mid)= mqtt_client.publish("dit_det_orga_specific/crawling", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to dit_det_orga_specific/crawling: {}".format(rc, mid, mqtt.error_string(rc)))


        if (msg.topic == "crawling/det_crawling_specific"):
            try:
                dsr_entities = get_organization_webdata(response = Response(),approach = mqtt_config["crawling"]["approach"],keywords=mqtt_config["crawling"]["keywords"],language=mqtt_config["crawling"]["language"],custom_depth=mqtt_config["crawling"]["custom_depth"],actuality_days=mqtt_config["crawling"]["actuality_days"],target_agenda_entity_id=mqtt_config["crawling"]["target_agenda_entity_id"], jsonlist=mqtt_data_list, vdpp_middleware_api=get_vdpp_middleware_api(), vdpp_mongodb_uri=get_vdpp_mongodb_uri(), salted_fileserver_service=get_salted_fileserver_service(), salted_publish_service=get_salted_publish_service())
                if dsr_entities != []:
                    mqtt_message= { 
                        "parameters": mqtt_config,
                        "data": dsr_entities
                    }
                    logging_text.info(mqtt_message)  
                    data_out = json.dumps(mqtt_message)
                    (rc, mid)= mqtt_client.publish("publish/crawling/det_crawling_specific", data_out, qos=2)
                    logging_text.info("Code {} while sending message {} to publish/crawling/det_crawling_specific : {}".format(rc, mid, mqtt.error_string(rc)))
                else:
                    mqtt_message= { 
                        "parameters": "None",
                        "data": "Crawling returned no entities."
                    }
                    logging_text.info(mqtt_message)  
                    data_out = json.dumps(mqtt_message)
                    
                    (rc, mid)= mqtt_client.publish("det_crawling_specific/crawling", data_out, qos=2)
                    logging_text.info("Code {} while sending message {} to det_crawling_specific/crawling: {}".format(rc, mid, mqtt.error_string(rc)))
            except:
                mqtt_message= { 
                "parameters": "None",
                "data": "Error."
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                
                (rc, mid)= mqtt_client.publish("det_crawling_specific/crawling", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to det_crawling_specific/crawling: {}".format(rc, mid, mqtt.error_string(rc)))
        
        
        
        
        if (msg.topic == "crawling/det_crawling_general"):
            url = salted_publish_service + "/broker/entities/Organization"
            r = requests.get(url, headers={'Accept': 'application/json'})
            entity_list = r.json()
            entity_list = random.sample(entity_list,random_sublist_broker)
            for entity in entity_list:
                try:
                    dsr_entities = get_organization_webdata(response = Response(),approach = mqtt_config["crawling"]["approach"],keywords=mqtt_config["crawling"]["keywords"],language=mqtt_config["crawling"]["language"],custom_depth=mqtt_config["crawling"]["custom_depth"],actuality_days=mqtt_config["crawling"]["actuality_days"],target_agenda_entity_id=mqtt_config["crawling"]["target_agenda_entity_id"], jsonlist=[entity], vdpp_middleware_api=get_vdpp_middleware_api(), vdpp_mongodb_uri=get_vdpp_mongodb_uri(), salted_fileserver_service=get_salted_fileserver_service(), salted_publish_service=get_salted_publish_service())
                    if dsr_entities != []:
                        mqtt_message= { 
                            "parameters": mqtt_config,
                            "data": dsr_entities
                        }
                        logging_text.info(mqtt_message)  
                        data_out = json.dumps(mqtt_message)
                        (rc, mid)= mqtt_client.publish("publish/crawling/det_crawling_general", data_out, qos=2)
                        logging_text.info("Code {} while sending message {} to publish/crawling/det_crawling_general : {}".format(rc, mid, mqtt.error_string(rc)))
                    else:
                        mqtt_message= { 
                            "parameters": "None",
                            "data": "Crawling returned no entities."
                        }
                        logging_text.info(mqtt_message)  
                        data_out = json.dumps(mqtt_message)
                        
                        (rc, mid)= mqtt_client.publish("det_crawling_general/crawling", data_out, qos=2)
                        logging_text.info("Code {} while sending message {} to det_crawling_general/crawling: {}".format(rc, mid, mqtt.error_string(rc)))
                except:
                    mqtt_message= { 
                    "parameters": "None",
                    "data": "Error."
                    }
                    logging_text.info(mqtt_message)  
                    data_out = json.dumps(mqtt_message)
                    
                    (rc, mid)= mqtt_client.publish("det_crawling_general/crawling", data_out, qos=2)
                    logging_text.info("Code {} while sending message {} to det_crawling_general/crawling: {}".format(rc, mid, mqtt.error_string(rc)))
                    
                

    mqtt_client = mqtt.Client(client_id="crawling_client", clean_session=False, userdata=None, protocol=mqtt.MQTTv31, transport="tcp")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_HOST, int(MQTT_PORT), keepalive=60)
    mqtt_client.loop_start() # when should loop be stopped? 

##################################


####################################endpoints#######################################

# testing ping
@app.get("/ping",tags=["testing :)"])
def pong():
    return {"ping": "pong!"}


@app.post("/service/search/webdata/organization/", tags=["searching services"] )
def get_organization_webdata( response: Response, approach: str, keywords: str, custom_depth: int, language: str, jsonlist: List, actuality_days: int, target_agenda_entity_id: str, vdpp_middleware_api=Depends(get_vdpp_middleware_api), vdpp_mongodb_uri=Depends(get_vdpp_mongodb_uri), salted_fileserver_service=Depends(get_salted_fileserver_service), salted_publish_service=Depends(get_salted_publish_service)):
    try:
        logging_text.info(f"vdpp middleware inner port: {vdpp_middleware_api}")
        entities = jsonable_encoder(jsonlist)
        dsr_entities = []
        for entity in entities: 
            logging_text.info(entity) 
            # check in broker for ServiceRun that fits actuality requirements
            actuality_status = broker.check_crawling_actuality(salted_publish_service, entity ,actuality_days, target_agenda_entity_id )
            logging_text.info("actuality status:")
            logging_text.info(actuality_status)
            if actuality_status == "uptodate":
                # in casy no new content can could be provided with the actuality days given
                # response.status_code = status.HTTP_204_NO_CONTENT       --> not possible here, since it tries to crawl for multiple entities, therefor empty list is given back     
                continue
            elif actuality_status == "notuptodate":
                logging_text.info(entity)
                # check if url is present in entity json representation, if not continue with next entity
                try:
                    if entity['url']['value']== "":
                        logging_text.info("skip entity since url is empty")
                        continue  
                except:
                    continue
                status_code, crawl_results=crawler.crawlprocessing(entity,salted_searchengine_service, vdpp_middleware_api, vdpp_mongodb_uri, approach, keywords, custom_depth, language)
                logging_text.info("Those are the crawl results obtained from the service:")
                logging_text.info([crawl_result["content_filename"] for crawl_result in crawl_results])
                logging_text.info(status_code)
                if status_code==definitions.MESSAGE_SUCCESS:
                    # upload to own file server 
                    file_server_uuids_with_url = []
                    for crawl_result in crawl_results:
                        logging_text.info("#####################################")
                        logging_text.info(f"crawling result processing for {crawl_result['content_filename']} using website approach")
                        logging_text.info(f"text: {crawl_result['text'][:50] if len(crawl_result['text'])>50 else crawl_result['text']} ...")                        
                        # get content: if text value is non-empty, take text, otherwise reference pdf
                        if crawl_result["text"] != "":
                            logging_text.info("it is a text document")
                            content = crawl_result["text"]
                            if not crawl_result["content_filename"].endswith(".txt"):
                                filename = crawl_result["content_filename"]+".txt"  
                            else:
                                filename = crawl_result["content_filename"]
                            # if its text, precheck matching to keywords provided (especially needed for website approach)
                            if approach == "website":
                                keywords_list = keywords.split(";")
                                if not any(keyword in content for keyword in keywords_list):
                                    logging_text.info("does not contain any of the keywords")
                                    continue 
                        else:
                            logging_text.info("it is a pdf document")
                            content = crawl_result["content_binary"]
                            if not crawl_result["content_filename"].endswith(".pdf"):
                                filename = crawl_result["content_filename"]+".pdf"    
                            else:
                                filename = crawl_result["content_filename"]                                                

                        status_code, fileserver_uuid = fileserver.upload(salted_fileserver_service, content, filename)                      
                        logging_text.info(status_code)
                        if status_code == definitions.MESSAGE_SUCCESS:
                            file_server_uuids_with_url.append([fileserver_uuid,crawl_result["url"]])
                        else:
                            raise HTTPException(status_code=500, detail="Error occured. Contact support team at team@agenda-analytics.eu \U0001F635")
                    logging_text.info(file_server_uuids_with_url)
                    if file_server_uuids_with_url != []:
                        # create DataScieneServiceRun    
                        logging_text.info("creating DataServiceRun entity")
                        params = {
                            "keywords": keywords,
                            "language": language,
                            "actuality_days": actuality_days,
                            "target_agenda_entity_id": target_agenda_entity_id,
                            "custom_depth": custom_depth,
                            "approach": approach
                        }
                        dsr_entity = dataservicerun.create_dsr(entity, file_server_uuids_with_url,params)
                        logging_text.info(dsr_entity["id"])
                        dsr_entities.append(dsr_entity)                             
                elif status_code==definitions.RESPONSE_204:
                    continue
                else:
                    raise HTTPException(status_code=500, detail="Error occured. Contact support team at team@agenda-analytics.eu \U0001F635")                    
            else:
                raise HTTPException(status_code=500, detail="Error occured. Contact support team at team@agenda-analytics.eu \U0001F635")
    except:
        raise HTTPException(status_code=500, detail="Error occured. Contact support team at team@agenda-analytics.eu \U0001F635")
    return dsr_entities








