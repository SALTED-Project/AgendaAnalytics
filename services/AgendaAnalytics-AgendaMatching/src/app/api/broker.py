import requests
import datetime
import json

from app.logs.logger import logging_text
import app.definitions as definitions

def check_crawling_data(salted_publish_service, salted_fileserver_service, entity_id, agenda_entity_id):    
    try:
        # get DataServiceRuns of Crawling
        logging_text.info("Call to publish service to extract DataServiceRun entities regarding Crawling Service (for specific agenda) and use most current")
        url = salted_publish_service+"/broker/entities/DataServiceRun"
        logging_text.info(url)
        r = requests.get(url, headers={
                'accept': 'application/json'
            })
        service_runs = r.json()        
        # filter out DataServiceRuns belonging to entity of question & crawling service
        service_runs_filtered = [run for run in service_runs if ((entity_id in (run["sourceEntities"]["object"] if isinstance(run["sourceEntities"]["object"],list) else [run["sourceEntities"]["object"]])) and (run["service"]["value"]== "urn:ngsi-ld:DataServiceDCAT-AP:Salted-Crawling"))]
        # filter out DataServiceRuns for agenda
        service_runs_filtered = [run for run in service_runs_filtered if (agenda_entity_id == [configuration["value"] for configuration in (run["configuration"]["value"] if isinstance(run["configuration"]["value"],list) else [run["configuration"]["value"]]) if configuration["parameter"] == "target_agenda_entity_id"][0])]
        logging_text.info("Preceeding DataServiceRuns of Crawling Service of interest (for specific agenda):")
        logging_text.info(len(service_runs_filtered))
        # take newest one
        if service_runs_filtered != []:
            crawling_data = max(service_runs_filtered, key=lambda r: datetime.datetime.strptime(r['dateCreated']['value'],'%Y-%m-%d %H:%M:%S.%f'))
            logging_text.info("most up to date crawling entity:")
            logging_text.info(crawling_data["id"])
            if isinstance(crawling_data["resultExternal"]["value"], list):
                # turn public to internal host
                crawling_data_uuids =  [salted_fileserver_service+"/files/"+dict["fileserver_url"].split("/files/")[-1] for dict in crawling_data["resultExternal"]["value"]]
            else:
                crawling_data_uuids =  [salted_fileserver_service+"/files/"+ crawling_data["resultExternal"]["value"]["fileserver_url"].split("/files/")[-1]]
            dsr_crawling_id = crawling_data["id"]
            status_code = definitions.MESSAGE_SUCCESS
        elif service_runs_filtered == []:
            logging_text.info("... no DataServiceRuns of Crawling Service interest found.")
            status_code = definitions.RESPONSE_204
            crawling_data_uuids = []
            dsr_crawling_id = None
    except:
        status_code = definitions.MESSAGE_ERROR
        crawling_data_uuids = None
        dsr_crawling_id = None
    return status_code, crawling_data_uuids, dsr_crawling_id



def check_matching_actuality(salted_publish_service, dsr_crawling_id, agenda_entity_id):
    try:
        # get DataServiceRuns of Agenda Matching
        logging_text.info("Call to publish service to extract DataServiceRun entities regarding AgendaMatching Service")
        url = salted_publish_service+"/broker/entities/DataServiceRun"
        logging_text.info(url)
        r = requests.get(url, headers={
                'accept': 'application/json'
            })
        service_runs = r.json()
        # filter out DataServiceRuns of Agenda Matching, that used crawled data of newest crawling
        service_runs_filtered = [run for run in service_runs if ((dsr_crawling_id in run["sourceEntities"]["object"]) and (run["service"]["value"]== "urn:ngsi-ld:DataServiceDCAT-AP:Salted-AgendaMatching"))]
        # filter out DataServiceRuns for agenda
        service_runs_filtered = [run for run in service_runs_filtered if (agenda_entity_id == [configuration["value"] for configuration in (run["configuration"]["value"] if isinstance(run["configuration"]["value"],list) else [run["configuration"]["value"]]) if (configuration["parameter"] == "agenda_entity_id")][0])]
        logging_text.info("Preceeding DataServiceRuns of AgendaMatching Service of interest (for specific agenda):")
        logging_text.info(len(service_runs_filtered))
        if service_runs_filtered == []:
            actuality_status="notuptodate"
        else:
            actuality_status="uptodate"
    except:
        actuality_status = None
    return actuality_status



def get_agenda_entity(salted_publish_service, entity_id):
    try:
        # get DistributionDCAT-AP Entity
        logging_text.info("Call to publish service to extract Distribution entitiy regarding requested agenda")
        url = salted_publish_service+"/broker/entities/DistributionDCAT-AP"
        logging_text.info(url)
        r = requests.get(url, headers={
                'accept': 'application/json'
            })
        agendas = r.json()    
        for agenda in agendas:
            if agenda["id"] == entity_id:
                agenda_entity = agenda
                break
            else:
                continue
    except:
        agenda_entity = None
    return agenda_entity
