import logging
import os
from typing import Tuple, List
import json
import requests
from io import BytesIO
import random

import sqlalchemy



from fastapi import FastAPI, Depends, HTTPException, Response, status, File, UploadFile
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
from app.api import pydantic_models, matcher, broker, distribution, fileserver
from app.logs.logger import CustomRoute, logging_text


from app.utils.utils import PrometheusMiddleware, metrics, setting_otlp
import app.definitions as definitions


#############################CREATE DATABASE TABLES IF NECESSARY###################################
# The MetaData.create_all() method is, passing in our Engine as a source of database connectivity. 
# For all tables that haven’t been created yet, it issues CREATE TABLE statements to the database.

if not sqlalchemy.inspect(engine).has_table("agendamatching_service-logs"):  # If table don't exist, Create.    
    tableobject_servicelog = [metadata.tables["agendamatching_service-logs"]]
    db_models.Base.metadata.create_all(engine, tables=tableobject_servicelog)
    logging_text.info("database table 'agendamatching_service-logs' did not exist yet, therefor one was created.")

#############################VALIDATE SETTINGS NEEDED##############################################
# for validation see https://dynaconf.readthedocs.io/en/docs_223/guides/validation.html

# Register validators
settings.validators.register(
    # Ensure some parameters exists (are required)
    Validator('DATABASE_URI', must_exist=True),
    Validator('VDPP_MONGODB_URI', must_exist=True)
)

# Fire the validator
settings.validators.validate()

logging_text.info("dynaconf settings were succesfully validated.")


# other env variables set
vdpp_middleware_api = os.environ.get("VDPP_MIDDLEWARE_API")
logging_text.info(vdpp_middleware_api)

simcore_api = os.environ.get("SIMCORE_API")
logging_text.info(simcore_api)

salted_fileserver_service = os.environ.get("SALTED_FILESERVER_SERVICE")
logging_text.info(salted_fileserver_service)

salted_publish_service = os.environ.get("SALTED_PUBLISH_SERVICE")
logging_text.info(salted_publish_service)

random_sublist_broker = int(os.environ.get("RANDOM_SUBLIST_BROKER"))
logging_text.info(random_sublist_broker)

#############################CREATE FAST-API APP####################################################

# Dependency: database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# vdpp middleware api dependency
def get_vdpp_middleware_api():
    return vdpp_middleware_api

# vdpp mongodb dependency
def get_vdpp_mongodb_uri():
    return settings.VDPP_MONGODB_URI


# simcore api dependency
def get_simcore_api():
    return simcore_api

# salted fileserver service dependency
def get_salted_fileserver_service():
    return salted_fileserver_service

# salted publish service dependency
def get_salted_publish_service():
    return salted_publish_service

app: FastAPI = FastAPI(title = "SALTED service: agendamatching (REST API using FastAPI & PostgreSQL)", openapi_tags = [])



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
        mqtt_client.subscribe("agendamatching/#", qos=2)

    def on_message(mqtt_client, obj, msg):

        logging_text.info(f"on message in {msg.topic}")
        data_in = msg.payload.decode()
        mqtt_message=json.loads(data_in)
        try:
            mqtt_data=mqtt_message["data"]
            print(mqtt_data)
        except: 
            mqtt_data={}
        mqtt_config = mqtt_message["parameters"]

        try:
            

            if (msg.topic == "agendamatching/publish/crawling/publish/dit_det_orga_specific"):
                try:
                    # message comes from publish service and contains published DataServiceRun
                    sourceEntities= mqtt_data["sourceEntities"]["object"] if isinstance(mqtt_data["sourceEntities"]["object"],list) else [mqtt_data["sourceEntities"]["object"]]
                    created_dsr_and_kpi = matching_for_entity_id(response = Response(), entity_id=[s for s in sourceEntities if "Organization" in s][0], agenda_entity_id= mqtt_config["agendamatching"]["agenda_entity_id"],vdpp_middleware_api=get_vdpp_middleware_api(), vdpp_mongodb_uri=get_vdpp_mongodb_uri(), simcore_api=get_simcore_api(), salted_fileserver_service=get_salted_fileserver_service(), salted_publish_service=get_salted_publish_service())
                    if created_dsr_and_kpi != []:
                        # split message due to size
                        mqtt_message= { 
                            "parameters": mqtt_config,
                            "data": created_dsr_and_kpi[0]
                        }
                        logging_text.info(mqtt_message)  
                        data_out = json.dumps(mqtt_message)                
                        (rc, mid)= mqtt_client.publish("publish/agendamatching/publish/crawling/publish/dit_det_orga_specific", data_out, qos=2)
                        logging_text.info("Code {} while sending message {} to publish/agendamatching/publish/crawling/publish/dit_det_orga_specific: {}".format(rc, mid, mqtt.error_string(rc)))

                        mqtt_message= { 
                            "parameters": mqtt_config,
                            "data": created_dsr_and_kpi[1]
                        }
                        logging_text.info(mqtt_message)  
                        data_out = json.dumps(mqtt_message)                
                        (rc, mid)= mqtt_client.publish("publish/agendamatching/publish/crawling/publish/dit_det_orga_specific", data_out, qos=2)
                        logging_text.info("Code {} while sending message {} to publish/agendamatching/publish/crawling/publish/dit_det_orga_specific: {}".format(rc, mid, mqtt.error_string(rc)))
        
                    else:
                        mqtt_message= { 
                        "parameters": "None",
                        "data": "AgendaMatching returned no entities."
                        }
                        logging_text.info(mqtt_message)  
                        data_out = json.dumps(mqtt_message)
                        
                        (rc, mid)= mqtt_client.publish("dit_det_orga_specific/agendamatching", data_out, qos=2)
                        logging_text.info("Code {} while sending message {} to dit_det_orga_specific/agendamatching: {}".format(rc, mid, mqtt.error_string(rc)))
                except:
                    mqtt_message= { 
                    "parameters": "None",
                    "data": "Error."
                    }
                    logging_text.info(mqtt_message)  
                    data_out = json.dumps(mqtt_message)
                    
                    (rc, mid)= mqtt_client.publish("dit_det_orga_specific/agendamatching", data_out, qos=2)
                    logging_text.info("Code {} while sending message {} to dit_det_orga_specific/agendamatching: {}".format(rc, mid, mqtt.error_string(rc)))


                              
            if (msg.topic == "agendamatching/crawling/publish/dit_det_orga_specific"):
                try:
                    # message comes from crawling service directly and contains source Organization
                    created_dsr_and_kpi = matching_for_entity_id(response = Response(), entity_id=mqtt_data["id"], agenda_entity_id= mqtt_config["agendamatching"]["agenda_entity_id"], vdpp_middleware_api=get_vdpp_middleware_api(), vdpp_mongodb_uri=get_vdpp_mongodb_uri(), simcore_api=get_simcore_api(), salted_fileserver_service=get_salted_fileserver_service(), salted_publish_service=get_salted_publish_service())
                    if created_dsr_and_kpi != []:
                        # split message due to size
                        mqtt_message= { 
                            "parameters": mqtt_config,
                            "data": created_dsr_and_kpi[0]
                        }
                        logging_text.info(mqtt_message)  
                        data_out = json.dumps(mqtt_message)                
                        (rc, mid)= mqtt_client.publish("publish/agendamatching/crawling/publish/dit_det_orga_specific", data_out, qos=2)
                        logging_text.info("Code {} while sending message {} to publish/agendamatching/crawling/publish/dit_det_orga_specific: {}".format(rc, mid, mqtt.error_string(rc)))
                    
                        mqtt_message= { 
                            "parameters": mqtt_config,
                            "data": created_dsr_and_kpi[1]
                        }
                        logging_text.info(mqtt_message)  
                        data_out = json.dumps(mqtt_message)                
                        (rc, mid)= mqtt_client.publish("publish/agendamatching/crawling/publish/dit_det_orga_specific", data_out, qos=2)
                        logging_text.info("Code {} while sending message {} to publish/agendamatching/crawling/publish/dit_det_orga_specific: {}".format(rc, mid, mqtt.error_string(rc)))
                    
                    
                    else:
                        mqtt_message= { 
                        "parameters": "None",
                        "data": "AgendaMatching & Crawling returned no entities."
                        }
                        logging_text.info(mqtt_message)  
                        data_out = json.dumps(mqtt_message)
                        
                        (rc, mid)= mqtt_client.publish("dit_det_orga_specific/agendamatching", data_out, qos=2)
                        logging_text.info("Code {} while sending message {} to dit_det_orga_specific/agendamatching: {}".format(rc, mid, mqtt.error_string(rc)))
                except:
                    mqtt_message= { 
                    "parameters": "None",
                    "data": "Error."
                    }
                    logging_text.info(mqtt_message)  
                    data_out = json.dumps(mqtt_message)
                    
                    (rc, mid)= mqtt_client.publish("dit_det_orga_specific/agendamatching", data_out, qos=2)
                    logging_text.info("Code {} while sending message {} to dit_det_orga_specific/agendamatching: {}".format(rc, mid, mqtt.error_string(rc)))



            if (msg.topic == "agendamatching/det_agendamatching_specific"):
                try:
                    # message comes from user directly and contains source Organization
                    created_dsr_and_kpi = matching_for_entity_id(response = Response(), entity_id=mqtt_data["id"], agenda_entity_id= mqtt_config["agendamatching"]["agenda_entity_id"], vdpp_middleware_api=get_vdpp_middleware_api(), vdpp_mongodb_uri=get_vdpp_mongodb_uri(), simcore_api=get_simcore_api(), salted_fileserver_service=get_salted_fileserver_service(), salted_publish_service=get_salted_publish_service())
                    if created_dsr_and_kpi != []:
                        #split message due to size
                        mqtt_message= { 
                            "parameters": mqtt_config,
                            "data": created_dsr_and_kpi[0]
                        }
                        logging_text.info(mqtt_message)  
                        data_out = json.dumps(mqtt_message)                
                        (rc, mid)= mqtt_client.publish("publish/agendamatching/det_agendamatching_specific", data_out, qos=2)
                        logging_text.info("Code {} while sending message {} to publish/agendamatching/det_agendamatching_specific: {}".format(rc, mid, mqtt.error_string(rc)))
                    
                        mqtt_message= { 
                            "parameters": mqtt_config,
                            "data": created_dsr_and_kpi[1]
                        }
                        logging_text.info(mqtt_message)  
                        data_out = json.dumps(mqtt_message)                
                        (rc, mid)= mqtt_client.publish("publish/agendamatching/det_agendamatching_specific", data_out, qos=2)
                        logging_text.info("Code {} while sending message {} to publish/agendamatching/det_agendamatching_specific: {}".format(rc, mid, mqtt.error_string(rc)))
                    
                    
                    else:
                        mqtt_message= { 
                        "parameters": "None",
                        "data": "AgendaMatching returned no entities."
                        }
                        logging_text.info(mqtt_message)  
                        data_out = json.dumps(mqtt_message)
                        
                        (rc, mid)= mqtt_client.publish("det_agendamatching_specific/agendamatching", data_out, qos=2)
                        logging_text.info("Code {} while sending message {} to det_agendamatching_specific/agendamatching: {}".format(rc, mid, mqtt.error_string(rc)))
                except:
                    mqtt_message= { 
                    "parameters": "None",
                    "data": "Error."
                    }
                    logging_text.info(mqtt_message)  
                    data_out = json.dumps(mqtt_message)
                    
                    (rc, mid)= mqtt_client.publish("det_agendamatching_specific/agendamatching", data_out, qos=2)
                    logging_text.info("Code {} while sending message {} to det_agendamatching_specific/agendamatching: {}".format(rc, mid, mqtt.error_string(rc)))



            if (msg.topic == "agendamatching/det_agendamatching_general"):
                # get all entities of type Organization in the broker
                url = salted_publish_service + "/broker/entities/Organization"
                r = requests.get(url, headers={'Accept': 'application/json'})
                entity_list = r.json()
                entity_list = random.sample(entity_list,random_sublist_broker)
                for entity in entity_list:      
                    try:          
                        created_dsr_and_kpi = matching_for_entity_id(response = Response(), entity_id=entity["id"], agenda_entity_id= mqtt_config["agendamatching"]["agenda_entity_id"], vdpp_middleware_api=get_vdpp_middleware_api(), vdpp_mongodb_uri=get_vdpp_mongodb_uri(), simcore_api=get_simcore_api(), salted_fileserver_service=get_salted_fileserver_service(), salted_publish_service=get_salted_publish_service())
                        if created_dsr_and_kpi != []:
                            # split message due to size
                            mqtt_message= { 
                                "parameters": mqtt_config,
                                "data": created_dsr_and_kpi[0] 
                            }
                            logging_text.info(mqtt_message)  
                            data_out = json.dumps(mqtt_message)                
                            (rc, mid)= mqtt_client.publish("publish/agendamatching/det_agendamatching_general", data_out, qos=2)
                            logging_text.info("Code {} while sending message {} to publish/agendamatching/det_agendamatching_general: {}".format(rc, mid, mqtt.error_string(rc)))

                            mqtt_message= { 
                                "parameters": mqtt_config,
                                "data": created_dsr_and_kpi[1]
                            }
                            logging_text.info(mqtt_message)  
                            data_out = json.dumps(mqtt_message)                
                            (rc, mid)= mqtt_client.publish("publish/agendamatching/crawling/publish/dit_det_orga_specific", data_out, qos=2)
                            logging_text.info("Code {} while sending message {} to publish/agendamatching/crawling/publish/dit_det_orga_specific: {}".format(rc, mid, mqtt.error_string(rc)))                            
                        
                        else:
                            mqtt_message= { 
                            "parameters": "None",
                            "data": "AgendaMatching returned no entities."
                            }
                            logging_text.info(mqtt_message)  
                            data_out = json.dumps(mqtt_message)
                            
                            (rc, mid)= mqtt_client.publish("det_agendamatching_general/agendamatching", data_out, qos=2)
                            logging_text.info("Code {} while sending message {} to det_agendamatching_general/agendamatching: {}".format(rc, mid, mqtt.error_string(rc)))
                    except:
                        mqtt_message= { 
                        "parameters": "None",
                        "data": "Error."
                        }
                        logging_text.info(mqtt_message)  
                        data_out = json.dumps(mqtt_message)
                        
                        (rc, mid)= mqtt_client.publish("det_agendamatching_general/agendamatching", data_out, qos=2)
                        logging_text.info("Code {} while sending message {} to det_agendamatching_general/agendamatching: {}".format(rc, mid, mqtt.error_string(rc)))                 

            
        except:
            logging_text.info("ERROR - abort MQTT?")


        

    mqtt_client = mqtt.Client(client_id="agendamatching_client", clean_session=False, userdata=None, protocol=mqtt.MQTTv31, transport="tcp")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_HOST, int(MQTT_PORT), keepalive=60)
    mqtt_client.loop_start() 

##################################

# testing ping
@app.get("/ping",tags=["testing :)"])
def pong():
    return {"ping": "pong!"}



@app.get("/matching/{entity_id}/{agenda_entity_id}",tags=["agenda matching"])
def matching_for_entity_id(response: Response, entity_id: str, agenda_entity_id : str, vdpp_middleware_api=Depends(get_vdpp_middleware_api), vdpp_mongodb_uri= Depends(get_vdpp_mongodb_uri), simcore_api=Depends(get_simcore_api), salted_fileserver_service=Depends(get_salted_fileserver_service), salted_publish_service=Depends(get_salted_publish_service)):
    #not used yet
    params = {"agenda_entity_id": agenda_entity_id}
    entities = []
    # check if crawled data is present in the broker
    status_code, crawling_data_uuids, dsr_crawling_id  = broker.check_crawling_data(salted_publish_service,salted_fileserver_service, entity_id, agenda_entity_id)
    logging_text.info("crawling data uuids")
    logging_text.info(crawling_data_uuids)
    if status_code == definitions.RESPONSE_204:
        response.status_code = status.HTTP_204_NO_CONTENT      
        response.detail = "No crawled data could be found for this entity id. Try to run the crawling service first (port 8004)."
        return entities
    elif status_code == definitions.MESSAGE_ERROR:
        raise HTTPException(status_code=500, detail="Error in service logic. Contact support team at team@agenda-analytics.eu \U0001F635")
    # check if crawled data was already used in the the calcualtion of a KPI
    actuality_status = broker.check_matching_actuality(salted_publish_service, dsr_crawling_id, agenda_entity_id)
    if actuality_status == "uptodate":
        # in casy no new crawled data is provided (that was not already used)
        response.status_code = status.HTTP_204_NO_CONTENT         
        response.detail = "The output of the latest crawling run was already used in the calculation of the AgendaMatching service before. Check those linked results. Try to run the crawling service again, for new data (port 8004)." 
        return entities
    elif actuality_status == "notuptodate":
        try:
            # check if needed agenda is locally available - if not download it
            agenda_entity_id = params['agenda_entity_id']     
            agenda_entity_id_cut= agenda_entity_id.split(":")[-1]   
            dirname_agenda = f"/usr/src/app/refcorpora/{agenda_entity_id_cut}/" 
            if os.path.isdir(dirname_agenda) == True:   
                if len(os.listdir(dirname_agenda)) ==0:
                        os.rmdir(dirname_agenda) 
            if os.path.isdir(dirname_agenda) == True: 
                logging_text.info("Requested agenda is available locally, no download needed")            
            else:
                agenda_entity = broker.get_agenda_entity(salted_publish_service, agenda_entity_id)
                if agenda_entity != None:
                    logging_text.info(agenda_entity["id"])
                    os.mkdir(dirname_agenda)
                    logging_text.info("in agenda processing")
                    if isinstance(agenda_entity["downloadURL"]["value"],list):
                        agenda_files = agenda_entity["downloadURL"]["value"]
                    else:
                        agenda_files =  [agenda_entity["downloadURL"]["value"]]
                    for agenda_file in agenda_files:
                        try:
                            # turn public to internal host
                            agenda_file_url = salted_fileserver_service + "/files/" + agenda_file.split("/files/")[-1]
                            logging_text.info(agenda_file_url)
                            r = requests.get(agenda_file_url)       
                            filename= r.headers['content-disposition'].split("filename=")[1][1:-1]  
                            logging_text.info(filename)
                            savepath = dirname_agenda+filename                    
                            with open(savepath, "wb") as file:
                                file.write(r.content)
                                logging_text.info(r.content)
                        except Exception as e:
                            logging_text.info(e)
                    logging_text.info("Downloaded requested agenda and persisted it locally.")
                else:
                    raise HTTPException(status_code=500, detail="Requested agenda not valid. Contact support team at team@agenda-analytics.eu \U0001F635")
        except Exception as e:
            logging_text.info(e)
        # give links to crawled data to further processing
        status_code, dsr_entity, kpi_entity = matcher.post_matchingrequest(vdpp_middleware_api, vdpp_mongodb_uri, simcore_api, salted_fileserver_service, entity_id, crawling_data_uuids, dsr_crawling_id, params)
        if status_code==definitions.MESSAGE_ERROR:
            raise HTTPException(status_code=500, detail="Error in service logic. Contact support team at team@agenda-analytics.eu \U0001F635")
        entities.append(dsr_entity)
        entities.append(kpi_entity)
    else:
        raise HTTPException(status_code=500, detail="Error occured. Contact support team at team@agenda-analytics.eu \U0001F635")
    return entities
     
        

@app.post("/agenda/text", tags=["agenda posting"])
def post_agenda(name: str, file: List[UploadFile] = File(...)):
    try:
        agenda_list = []
        for _file in file:
            agenda_list.append((_file.filename, _file.file, _file.file.read().decode("utf-8") ))

        # upload fileserver
        logging_text.info("uploading results to fileserver for references in DSR entity...")
        fileserver_uuids = []
        
        for agenda_file in agenda_list:
            status_code, fileserver_uuid = fileserver.upload(salted_fileserver_service, agenda_file[2], agenda_file[0])
            logging_text.info(status_code)
            if status_code == definitions.MESSAGE_SUCCESS:
                fileserver_uuids.append(fileserver_uuid)
        
        # create agenda dict
        logging_text.info("creating plaintext agenda representation for reference in DSR entity...")
        agenda_dict=[]
        for agenda_file in agenda_list:
            level0_name = agenda_file[0].split(".")[0]
            filenumber = agenda_file[0].split(".")[1]
            level0 = filenumber.split("-")[0]
            level1 = filenumber.split("-")[1]
            target_text= agenda_file[2]      
            agenda_dict.append({"title": level0_name, "level0": level0 , "level1": level1, "text": target_text}) 


        # create DCAT-AP Distribution entity
        distribution_entity = distribution.create_distribution(name, fileserver_uuids, agenda_dict)     
    except:
        raise HTTPException(status_code=500, detail="Error occured. Contact support team at team@agenda-analytics.eu \U0001F635")
    return distribution_entity


