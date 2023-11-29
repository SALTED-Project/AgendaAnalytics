import jmespath, json
import os

from app.api.jmespath_functions import OrganizationFunctionsDiscoverAndStore, BikeHireDockingStationFunctionsMRN, EVChargingStationFunctionsMRN
from app.logs.logger import logging_text
# jmespath documentation
# https://jmespath.org/tutorial.html
# https://jmespath.org/specification.html
# https://github.com/jmespath/jmespath.py

def map_organization_discoverandstore(raw_json):

    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, './templates/organization_template_discoverandstore.jmespath')
    with open(filename) as file: 
        template = file.read()
    
    options = jmespath.Options(custom_functions=OrganizationFunctionsDiscoverAndStore())
    ngsi_json = jmespath.search(template, raw_json, options=options)   
    return ngsi_json


