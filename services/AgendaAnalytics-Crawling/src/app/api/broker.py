import requests
import datetime
import json

from app.logs.logger import logging_text
import app.definitions as definitions

def check_crawling_actuality(salted_publish_service, entity, actuality_days, target_agenda_entity_id):    
    try:
        # get DataServiceRuns 
        logging_text.info("Call to publish service to extract DataServiceRun entities")
        url = salted_publish_service+"/broker/entities/DataServiceRun"
        logging_text.info(url)
        r = requests.get(url, headers={
                'accept': 'application/json'
            })
        service_runs = r.json()  
        logging_text.info(len(service_runs))
        if service_runs == []:
            actuality_status="notuptodate"
        else:
            # filter out DataServiceRuns belonging to entity of question
            service_runs_filtered = [run for run in service_runs if ((entity["id"] in (run["sourceEntities"]["object"] if isinstance(run["sourceEntities"]["object"],list) else [run["sourceEntities"]["object"]])) and (run["service"]["value"]== "urn:ngsi-ld:DataServiceDCAT-AP:Salted-Crawling"))]
            # check for agenda
            service_runs_filtered = [run for run in service_runs_filtered if (target_agenda_entity_id == [configuration["value"] for configuration in run["configuration"]["value"] if configuration["parameter"] == "target_agenda_entity_id"][0])]
            logging_text.info("Preceeding DataServiceRuns of Crawling Service (for requested agenda) of interest (first 3):")
            logging_text.info(service_runs_filtered[0:3])
            # set default, until changed due to found job
            actuality_status="notuptodate"
            if service_runs_filtered != []:
                dtnow = datetime.datetime.now()
                logging_text.info(f"time now: {dtnow}")
                check = dtnow-datetime.timedelta(days=int(actuality_days))
                logging_text.info(f"check time: {check}")
                for service_run in service_runs_filtered:
                    crawling_job_date = service_run["dateCreated"]["value"]
                    crawling_job_date=datetime.datetime.strptime(crawling_job_date,'%Y-%m-%d %H:%M:%S.%f')
                    if check < crawling_job_date:
                        logging_text.info("found at least this one, that is up to date:")
                        logging_text.info(crawling_job_date)
                        actuality_status="uptodate"
                        break
    except:
        actuality_status = None
    return actuality_status