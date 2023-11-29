import uuid
from datetime import datetime
import os

from app.logs.logger import logging_text
import app.definitions as definitions

# see: https://github.com/smart-data-models/dataModel.DCAT-AP/blob/master/DistributionDCAT-AP/examples/example-normalized.jsonld
# see: https://www.dcat-ap.de/def/dcatde/2.0/spec/specification.pdf

def create_distribution(name, files, agenda_dict):
    salted_fileserver_service_pub_addr = os.environ.get("SALTED_FILESERVER_SERVICE_PUB_ADDR")
    
    dataset_id = "urn:ngsi-ld:DistributionDCAT-AP:" + str(uuid.uuid4())
    dsr= {
        "id": f"{dataset_id}",
        "type": "DistributionDCAT-AP",
        "description": {
            "type": "Property",
            "value": "This entity holds information about one specifc representation of an agenda. The text files, that make up the agenda can be seen under the downloadURL property. Each file needs to comply to the syntax of <level0_name>.<level0>-<level1>.txt. The parsed representation of the agenda in json format can be seen under the documentation property."
        },
        "downloadURL": {
            "type": "Property",
            "value": [f"{salted_fileserver_service_pub_addr}/files/{entry}" for entry in files]   # make full urls out of file server uuids
        },
        "format": {
            "type": "Property",
            "value": "text"
        },
        "dateCreated": {
            "type": "Property",
            "value": str(datetime.utcnow())
        },
        "name": {
            "type": "Property",
            "value": name
        },
        "documentation": {
            "type": "Property",
            "value": agenda_dict
        },
        "@context": [
            "https://raw.githubusercontent.com/smart-data-models/dataModel.DCAT-AP/ca169c97d519c5ad77c53e00eafdbd2bdbe90e1b/context.jsonld",
            "https://smartdatamodels.org/context.jsonld"
        ]
    }

    return dsr