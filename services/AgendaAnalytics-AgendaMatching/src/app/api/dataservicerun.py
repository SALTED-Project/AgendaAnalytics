import uuid
from datetime import datetime
import os

from app.logs.logger import logging_text
import app.definitions as definitions


def create_dsr(source_entity_id, file_server_uuids_with_name, dsr_crawling_id, params):
    salted_fileserver_service_pub_addr = os.environ.get("SALTED_FILESERVER_SERVICE_PUB_ADDR")
    
    dsr_id = "urn:ngsi-ld:DataServiceRun:" + str(uuid.uuid4())
    dsr= {
        "id": f"{dsr_id}",
        "type": "DataServiceRun",
        "description": {
            "type": "Property",
            "value": "This entity holds information about one specifc run of the agenda matching service linked in the attributes below. The source entity specifies the organization for which the matching takes place. The result files contain the files that were obtained."
        },
        "configuration": {
            "type": "Property",
            "value": [
                {
                    "parameter": "agenda_entity_id",
                    "value": params["agenda_entity_id"]
                }
            ]
        },
        "dateCreated": {
            "type": "Property",
            "value": str(datetime.utcnow())
        },
        "service": {
            "type": "Property",
            "value": "urn:ngsi-ld:DataServiceDCAT-AP:Salted-AgendaMatching"
        },
        "sourceEntities": {
            "type": "Relationship",
            "object": [source_entity_id, dsr_crawling_id, params["agenda_entity_id"]]
        },
        "resultExternal": {
            "type": "Property",
            "value": [{"fileserver_url":f"{salted_fileserver_service_pub_addr}/files/{entry[0]}","filename":entry[1]} for entry in file_server_uuids_with_name]    # make full urls out of file server uuids
        },
        "@context": [
            "https://raw.githubusercontent.com/smart-data-models/dataModel.DCAT-AP/ca169c97d519c5ad77c53e00eafdbd2bdbe90e1b/context.jsonld",
            "https://smartdatamodels.org/context.jsonld"
        ]
    }

    return dsr