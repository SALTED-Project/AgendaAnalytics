import uuid
from datetime import datetime
import os

from app.logs.logger import logging_text
import app.definitions as definitions



def create_dsr(entity, file_server_uuids_with_url, params):
    salted_fileserver_service_pub_addr = os.environ.get("SALTED_FILESERVER_SERVICE_PUB_ADDR")
    
    dsr_id = "urn:ngsi-ld:DataServiceRun:" + str(uuid.uuid4())
    dsr= {
        "id": f"{dsr_id}",
        "type": "DataServiceRun",
        "description": {
            "type": "Property",
            "value": "This entity holds information about one specifc run of the crawling service linked in the attributes below. The source entity specifies the organization for which information was crawled. The result files contain the files that were obtained."
        },
        "configuration": {
            "type": "Property",
            "value": [
                {
                    "parameter": "keywords",
                    "value": params["keywords"]
                },
                {
                    "parameter": "actuality_days",
                    "value": params["actuality_days"]
                },
                {
                    "parameter": "target_agenda_entity_id",
                    "value": params["target_agenda_entity_id"]
                },
                {
                    "parameter": "custom_depth",
                    "value": params["custom_depth"]
                },
                {
                    "parameter": "approach",
                    "value": params["approach"]
                },
                {
                    "parameter": "language",
                    "value": params["language"]
                }
            ]
        },
        "dateCreated": {
            "type": "Property",
            "value": str(datetime.utcnow())
        },
        "service": {
            "type": "Property",
            "value": "urn:ngsi-ld:DataServiceDCAT-AP:Salted-Crawling"
        },
        "resultExternal": {
            "type": "Property",
            "value": [{"fileserver_url":f"{salted_fileserver_service_pub_addr}/files/{entry[0]}","crawled_url":entry[1]} for entry in file_server_uuids_with_url]   # make full urls out of file server uuids
        },
        "sourceEntities": {
            "type": "Relationship",
            "object": [entity["id"]]
        },
        "@context": [
            "https://raw.githubusercontent.com/smart-data-models/dataModel.DCAT-AP/ca169c97d519c5ad77c53e00eafdbd2bdbe90e1b/context.jsonld",
            "https://smartdatamodels.org/context.jsonld"
        ]
    }

    return dsr