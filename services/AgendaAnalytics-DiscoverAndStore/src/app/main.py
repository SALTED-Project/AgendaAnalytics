import logging
import os


import sqlalchemy
import json

from fastapi import FastAPI, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware


from dynaconf import Validator



from app.config import settings
from app.db import db_models, crud
from app.db.database import  engine, SessionLocal, metadata
from app.api import pydantic_models
from app.api import wikipedia, googlesearch, osmsearch
from app.logs.logger import CustomRoute, logging_text


from app.utils.utils import PrometheusMiddleware, metrics, setting_otlp


#############################CREATE DATABASE TABLES IF NECESSARY###################################
# The MetaData.create_all() method is, passing in our Engine as a source of database connectivity. 
# For all tables that haven’t been created yet, it issues CREATE TABLE statements to the database.


if not sqlalchemy.inspect(engine).has_table("discoverandstore_organizations"):  # If table don't exist, Create.    
    tableobject_organization = [metadata.tables["discoverandstore_organizations"]]
    db_models.Base.metadata.create_all(engine, tables=tableobject_organization)
    logging_text.info("database table 'discoverandstore_organizations' did not exist yet, therefor one was created.")

if not sqlalchemy.inspect(engine).has_table("discoverandstore_service-logs"):  # If table don't exist, Create.    
    tableobject_servicelog = [metadata.tables["discoverandstore_service-logs"]]
    db_models.Base.metadata.create_all(engine, tables=tableobject_servicelog)
    logging_text.info("database table 'discoverandstore_service-logs' did not exist yet, therefor one was created.")

#############################VALIDATE SETTINGS NEEDED##############################################
# for validation see https://dynaconf.readthedocs.io/en/docs_223/guides/validation.html

# Register validators
settings.validators.register(
    # Ensure some parameters exists (are required)
    Validator('UNWANTED_URLS', must_exist=True),
    Validator('DATABASE_URI', must_exist=True)    
)

# Fire the validator
settings.validators.validate()

logging_text.info("dynaconf settings were succesfully validated.")


#############################CREATE FAST-API APP####################################################

# Dependency: database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

tags_metadata = [
    {
        "name": "searching services",
        "description": "Operations for aquiring organisation information.",
        "externalDocs": {
            "description": "valid country codes (e.g. 08=Baden-Würrtemberg, none=Germany)",
            "url": "https://de.wikipedia.org/wiki/Amtlicher_Gemeindeschl%C3%BCssel#Regionalschl.C3.BCssel",
        },
    }
]

app: FastAPI = FastAPI(title = "SALTED service: discover company data and store (REST API using FastAPI & PostgreSQL)", openapi_tags = tags_metadata)

# add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["application/json"]
)
#####################################for logging################################

# add logging route
app.router.route_class = CustomRoute

######################################for observability##########################

# Setting metrics middleware
APP_NAME = os.environ.get("APP_NAME", "app-default")
logging_text.info(APP_NAME)

salted_searchengine_service = os.environ.get("SALTED_SEARCHENGINE_SERVICE")
logging_text.info(salted_searchengine_service)

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
    # Initialize MQTT
    logging_text.info('Connecting to MQTT broker.')
    def on_connect(mqtt_client, obj, flags, rc):
        mqtt_client.subscribe("discoverandstore/#", qos=2)        

    def on_message(mqtt_client, obj, msg):
        # trigger service endpoints depending on config given
        if (msg.topic == "discoverandstore/dit_orga_general"):
            logging_text.info("on message in discoverandstore/dit_orga_general")
            data_in = msg.payload.decode()
            mqtt_message=json.loads(data_in)
            agendaanalytics_config = mqtt_message["parameters"]
            logging_text.info(agendaanalytics_config)
            service_config = agendaanalytics_config["discoverandstore"]
            logging_text.info(service_config)
            try:
                # search & enrich to fully update the database of the service
                if service_config["searchscope"]=="wikipedia":
                    run_wikipedia_service(db = next(get_db()), crawling_function_call = wikipedia.get_table())
                    logging_text.info("ran wikipedia search")
                if service_config["searchscope"]=="osm":
                    run_osm_service("none",db = next(get_db()))
                    logging_text.info("ran osm search")
                if service_config["enrichscope"]=="google":
                    run_googlesearch_service(db = next(get_db()))
                    logging_text.info("ran google enriching")
                if service_config["enrichscope"]=="osm":
                    run_osmsearch_service(db = next(get_db()))
                    logging_text.info("ran osm enriching")     
                # get all results and start mapping & enriching for each individually, since the message size would explode otherwise
                organizations = read_organizations(db = next(get_db())) 
                logging_text.info(organizations)
                for organization in organizations:
                    logging_text.info(f"triggering pipeline for {jsonable_encoder(organization)}")
                    organization = jsonable_encoder(organization)
                    mqtt_message= { 
                        "parameters": agendaanalytics_config,
                        "data": organization
                    }
                    logging_text.info(mqtt_message)  
                    data_out = json.dumps(mqtt_message)   
                    (rc, mid)= mqtt_client.publish("mapping/discoverandstore/dit_orga_general", data_out, qos=2)
                    logging_text.info("Code {} while sending message {} to mapping/discoverandstore/dit_orga_general: {}".format(rc, mid, mqtt.error_string(rc)))                
            except:
                mqtt_message= { 
                "parameters": "None",
                "data": "Error."
                }
                logging_text.info(mqtt_message)  
                data_out = json.dumps(mqtt_message)
                
                (rc, mid)= mqtt_client.publish("discoverandstore/dit_orga_general", data_out, qos=2)
                logging_text.info("Code {} while sending message {} to discoverandstore/dit_orga_general: {}".format(rc, mid, mqtt.error_string(rc)))       
      


    mqtt_client = mqtt.Client(client_id="discoverandstore_client", clean_session=False, userdata=None, protocol=mqtt.MQTTv31, transport="tcp")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(MQTT_HOST, int(MQTT_PORT), keepalive=60)
    mqtt_client.loop_start() 



####################################Endpoints#######################################

@app.get("/service/search/wikipedia", response_model=pydantic_models.OrganizationList, tags=["searching services"])
def run_wikipedia_service(db: Session = Depends(get_db), crawling_function_call: any = Depends(wikipedia.get_table)):
    logging_text.info(db)
    logging_text.info(crawling_function_call)

    status_list = []

    logging_text.info("Trying to crawl the wikipedia table ... (for /service/searchcompanies/wikipedia)")
    wiki_response, wiki_response_status, df_companies, df_companies_status = crawling_function_call
    status_list.append({'wiki_response_status': wiki_response_status})
    status_list.append({'df_companies_status': df_companies_status })    
    logging_text.info("Finished trying to crawl the wikipedia table. (for /service/searchcompanies/wikipedia endpoint)")

    print(df_companies)

    if df_companies.empty:
        logging_text.info("No luck crawling the wikipedia table - abort mission. (for /service/searchcompanies/wikipedia endpoint)")   
        status_list.append({'write_db_status': "No resulting DataFrame exists."})
        logging_text.info(status_list)  
        raise HTTPException(status_code=500, detail="No organizations were found. Contact support team at team@agenda-analytics.eu \U0001F635")

    db_organizations = []
    try:
        for i in range(len(df_companies)):   
            organization_name = df_companies.iloc[i,0]
            db_organization = crud.get_organization_by_name(db, organization_name)
            if db_organization:
                #logging_text.info("Organization already there.")
                db_organizations.append(jsonable_encoder(db_organization))   
                            
            else:
                #logging_text.info("Creating new organization.")
                new_organization = pydantic_models.OrganizationCreate(
                    name=df_companies.iloc[i,0], 
                    legalform=df_companies.iloc[i,1],
                    city=df_companies.iloc[i,2],
                    url_google="",
                    country="",
                    postcode="",
                    street="",
                    housenumber="",
                    lat="",
                    long="",
                    officecategory = "semi-governmental",
                    url_osm="",
                    origin_service="wikipedia"                                      
                )
                response = crud.create_organization(db=db, organization=new_organization)
                db_organizations.append(jsonable_encoder(response))   
        
        status_list.append({'write_db_status': "Resulting DataFrame was successfully writen to db."})
        logging_text.info("Finished writing obtained info to db. (for /service/searchcompanies/wikipedia endpoint)")            
        logging_text.info(status_list)

    except:
        status_list.append({'write_db_status': "Resulting DataFrame was not successfully written to db."})
        logging_text.error("Could not write obtained info to db. (for /service/searchcompanies/wikipedia endpoint)") 
        logging_text.info(status_list)
        raise HTTPException(status_code=500, detail="Found organizations could not be written to database. Contact support team at team@agenda-analytics.eu \U0001F635")
        
    return db_organizations

@app.get("/service/search/osm/{countrycode}", response_model=pydantic_models.OrganizationList, tags=["searching services"])
def run_osm_service(countrycode: str,db: Session = Depends(get_db)):    
    status_list = []
    logging_text.info("Trying to crawl openstreetmap ... (for /service/searchcompanies/osm endpoint )")
    # ^08 for Baden-Wurrtemberg
    # . for all of Germany
    logging_text.info(f"This is the regionalcode provided: {countrycode}")
    # convert countrycode to regex for regionalcode needed for OSM query
    if countrycode == "none":
        regionalcode = "."
    if countrycode!="none":
        regionalcode = "^"+countrycode
    result_status, result_data = osmsearch.get_osm_companiesbyregion(regionalcode=regionalcode)
    logging_text.info(result_data["elements"][0])
    status_list.append({'osm_response_status': result_status}) 
    logging_text.info("Finished trying to crawl openstreetmap. (for /service/searchcompanies/osm endpoint )")

    if result_data=="":
        logging_text.info("No luck crawling openstreetmap - abort mission. (for /service/searchcompanies/osm endpoint)")   
        status_list.append({'write_db_status': "No data exists."})
        logging_text.info(status_list)  
        raise HTTPException(status_code=500, detail="No organizations were found. Contact support team at team@agenda-analytics.eu \U0001F635")    

    db_organizations = []
    
    try:
        for element in result_data["elements"]:                                   
            try:
                organization_name=element["tags"]["name"].strip()   
            except:
                continue
            logging_text.info(organization_name)
            db_organization = crud.get_organization_by_name(db, organization_name)
            if db_organization:
                #logging_text.info("Organization already there.")
                db_organizations.append(jsonable_encoder(db_organization))                               
            else:
                #logging_text.info("Creating new organization.")
                try:
                    organization_lat= str(element["lat"])
                except:
                    organization_lat=""
                try:
                    organization_long= str(element["lon"])
                except:
                    organization_long=""
                try:
                    organization_city= element["tags"]["addr:city"]
                except:
                    organization_city=""
                try:
                    organization_country= element["tags"]["addr:country"]
                except:
                    organization_country=""
                try:
                    organization_postcode= str(element["tags"]["addr:postcode"])
                except:
                    organization_postcode=""
                try:
                    organization_street= element["tags"]["addr:street"]
                except:
                    organization_street="" 
                try:
                    organization_housenumber= str(element["tags"]["addr:housenumber"])
                except:
                    organization_housenumber=""
                try:
                    organization_officecategory= element["tags"]["office"]
                except:
                    organization_officecategory=""
                try:
                    organization_url_osm= element["tags"]["website"]
                except:
                    organization_url_osm=""

                new_organization = pydantic_models.OrganizationCreate(
                    name=organization_name,
                    legalform="",
                    city=organization_city,
                    url_google="",
                    country= organization_country,
                    postcode=organization_postcode,
                    street=organization_street,
                    housenumber=organization_housenumber,
                    lat=organization_lat,
                    long=organization_long,
                    officecategory=organization_officecategory,
                    url_osm=organization_url_osm,
                    origin_service="osm_badenwurrtemberg"                              
                )
                response = crud.create_organization(db=db, organization=new_organization)
                db_organizations.append(jsonable_encoder(response))   
        
        status_list.append({'write_db_status': "Resulting data was successfully writen to db."})
        logging_text.info("Finished writing obtained info to db. (for  /service/searchcompanies/osm_badenwurrtemberg endpoint)")
            
        logging_text.info(status_list)

        
    except:
        status_list.append({'write_db_status': "Resulting data was not successfully written to db."})
        logging_text.error("Could not write obtained info to db. (for  /service/searchcompanies/osm_badenwurrtemberg endpoint)") 
        logging_text.info(status_list)
        raise HTTPException(status_code=500, detail="Found organizations could not be written to database. Contact support team at team@agenda-analytics.eu \U0001F635")
        
    return db_organizations


@app.get("/service/enrich/googlesearch", response_model=pydantic_models.OrganizationList, tags=["enriching services"])
def run_googlesearch_service(db: Session = Depends(get_db)):
    

    unwanted_urls = settings.UNWANTED_URLS 
    status_list = []
    db_organizations_updated = []

    logging_text.info("Trying to crawl the google results ... (for /service/enrichcompanies/googlesearch endpoint)")

    db_organizations = crud.get_organizations(db)
    if db_organizations == []:
        raise HTTPException(status_code=404, detail="No organizations found that could be enriched. Please use a service under /service/searchcompanies first to obtain organizations.")
    
    status_counter = 0
    counter = 0
    try:
        for db_organization in db_organizations:
            try:
                counter +=1
                organization_name = db_organization.name
                print(organization_name)
                query = "Unternehmen "+organization_name+" Website"
                result_link, result_link_status = googlesearch.get_urls(salted_searchengine_service,query, unwanted_urls)
                print(result_link)
                if result_link_status != "Link was extracted succesfully.":
                    status_counter += 1
                else:
                    updated_organization = pydantic_models.OrganizationGoogleUpdate(
                            url_google=result_link
                    ) 
                    response = crud.update_google_organization(db=db, organization=db_organization, updated_organization=updated_organization)     
                    db_organizations_updated.append(jsonable_encoder(response)) 
                
            except:
                continue
        
        status = f"Links for {counter-status_counter} out of {counter} companies could be extracted and written to db as update."
        status_list.append({'googlesearch_status': status})         
        logging_text.info("Finished trying to crawl the google results. (for /service/enrichcompanies/googlesearch endpoint)")
        logging_text.info(status_list)


    except:
        status = f"Links for {counter-status_counter} out of {counter} companies could be extracted and written to db as update."
        status_list.append({'googlesearch_status': status})     
        logging_text.info("Error when trying to crawl the google results. (for /service/enrichcompanies/googlesearch endpoint)")    
        logging_text.info(status_list)
        raise HTTPException(status_code=500, detail="Found information could not be written to database. Contact support team at team@agenda-analytics.eu \U0001F635")
        
    return db_organizations_updated    
    




@app.get("/service/enrich/osmsearch", response_model=pydantic_models.OrganizationList, tags=["enriching services"])
def run_osmsearch_service(db: Session = Depends(get_db)):

    status_list = []
    db_organizations_updated = []

    logging_text.info("Trying to crawl the openstreetmap results ... (for /service/enrichcompanies/osmsearch endpoint)")

    db_organizations = crud.get_organizations(db)
    if db_organizations == []:
        raise HTTPException(status_code=404, detail="No organizations found that could be enriched. Please use a service under /service/searchcompanies first to obtain organizations.")
    

    status_counter = 0
    counter = 0
    try:
        for db_organization in db_organizations:
            try:
                counter +=1
                organization_name = db_organization.name
                organization_city = db_organization.city

                query_parameters={
                    "name": organization_name,
                    "city": organization_city
                }
                result_status, result_data = osmsearch.get_osminfo(query_parameters)
                print(result_status)
                print(result_data)
                if result_status != "Sucessful request.":            
                    status_counter += 1
                else:
                    try:
                        organization_lat= str(result_data["elements"][0]["lat"])
                    except:
                        organization_lat=""
                    try:
                        organization_long= str(result_data["elements"][0]["lon"])
                    except:
                        organization_long=""
                    try:
                        organization_country= result_data["elements"][0]["tags"]["addr:country"]
                    except:
                        organization_country=""
                    try:
                        organization_postcode= str(result_data["elements"][0]["tags"]["addr:postcode"])
                    except:
                        organization_postcode=""   
                    try:
                        organization_street= result_data["elements"][0]["tags"]["addr:street"]
                    except:
                        organization_street="" 
                    try:
                        organization_housenumber= str(result_data["elements"][0]["tags"]["addr:housenumber"])
                    except:
                        organization_housenumber=""
                    try:
                        organization_officecategory= result_data["elements"][0]["tags"]["office"]
                    except:
                        organization_officecategory=""
                    try:
                        organization_url_osm= result_data["elements"][0]["tags"]["website"]
                    except:
                        organization_url_osm=""
                    updated_organization = pydantic_models.OrganizationOSMUpdate(
                            country=organization_country,
                            postcode=organization_postcode,
                            street=organization_street,
                            housenumber=organization_housenumber,
                            lat=organization_lat,
                            long=organization_long,
                            officecategory=organization_officecategory,
                            url_osm=organization_url_osm
                    ) 
                    response = crud.update_osm_organization(db=db, organization=db_organization, updated_organization=updated_organization)     
                    logging_text.info(jsonable_encoder(response))
                    db_organizations_updated.append(jsonable_encoder(response)) 
            except:
                continue
        
        status = f"Info for {counter-status_counter} out of {counter} companies was extracted from openstreetmap (could be empty if there is no info)."
        status_list.append({'osm_status': status})         
        logging_text.info("Finished trying to crawl the openstreetmap results. (for /service/enrichcompanies/osmsearch endpoint)")
        logging_text.info(status_list)


    except:
        status = f"Info for {counter-status_counter} out of {counter} companies was extracted from openstreetmap (could be empty if there is no info)."
        status_list.append({'osmearch_status': status})     
        logging_text.info("Error when trying to crawl the openstreetmap results. (for /service/enrichcompanies/osmsearch endpoint)")    
        logging_text.info(status_list)
        raise HTTPException(status_code=500, detail="Found information could not be written to database. Contact support team at team@agenda-analytics.eu \U0001F635")
        
    return db_organizations_updated



@app.post("/organizations/", response_model=pydantic_models.OrganizationBase, tags=["crud operations on db"])
def create_organization(organization: pydantic_models.OrganizationCreate, db: Session = Depends(get_db)):
    db_organization = crud.get_organization_by_name(db, organization.name)
    if db_organization:        
        raise HTTPException(status_code=400, detail="Organization name already exists.")
    return crud.create_organization(db=db, organization=organization)          


@app.get("/organizations/{organization_name}", response_model=pydantic_models.OrganizationBase, tags=["crud operations on db"]) 
def read_organization(organization_name:str, db:Session = Depends(get_db)):
    db_organization = crud.get_organization_by_name(db, organization_name=organization_name)
    if db_organization is None:
        raise HTTPException(status_code=404, detail="Organization not found.", headers={"X-Error": "There goes my error"})
    return db_organization


@app.put("/organizations/{organization_name}", response_model=pydantic_models.OrganizationBase, tags=["crud operations on db"])
def update_organization(organization_name:str, updated_organization: pydantic_models.OrganizationUpdate, db: Session = Depends(get_db)):
    db_organization = crud.get_organization_by_name(db, organization_name)
    if db_organization is None:
        raise HTTPException(status_code=404, detail="Organization not found.") 
    return crud.update_organization(db=db, organization=db_organization, updated_organization=updated_organization)


@app.get("/organizations/", response_model=pydantic_models.OrganizationList, tags=["crud operations on db"]) 
def read_organizations(db:Session = Depends(get_db)):   
    db_organizations = crud.get_organizations(db)
    if db_organizations == []:
        raise HTTPException(status_code=404, detail="No organizations found.")
    return db_organizations


@app.delete("/organizations/{organization_name}", tags=["crud operations on db"]) 
def delete_organization(organization_name:str, db:Session = Depends(get_db)):   
    db_organization = crud.get_organization_by_name(db, organization_name=organization_name)
    if db_organization is None:
        raise HTTPException(status_code=404, detail="Organization not found.")
    return crud.delete_organization_by_name(db=db, organization=db_organization)


@app.delete("/organizations/", tags=["crud operations on db"]) 
def delete_organizations(db:Session = Depends(get_db)):   
    db_organizations = crud.get_organizations(db)
    if db_organizations == []:
        raise HTTPException(status_code=404, detail="No organizations found.")
    for db_organization in db_organizations:
        response_text = crud.delete_organization_by_name(db=db, organization=db_organization)
        if response_text != {"Deleted organization successfully."}:
            raise HTTPException(status_code=500, detail="Error when attempting to delete organization. Check what organizations are remaining.")           
    return {"Deleted organizations successfully."}


# testing ping
@app.get("/ping",tags=["testing :)"])
def pong():
    return {"ping": "pong!"}




