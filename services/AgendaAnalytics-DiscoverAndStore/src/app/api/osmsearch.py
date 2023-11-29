import time
import requests
import os
import json

from app.logs.logger import logging_text



def get_osminfo(query_parameters):
    logging_text.info(query_parameters)
    # find working overpass API, when it changes: https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances
    overpass_url = "https://overpass-api.de/api/interpreter"
    name=query_parameters['name']
    city=query_parameters['city']    
    overpass_query = f"""
    [out:json];
    area["ISO3166-1"="DE"][admin_level=2];
    (node["addr:city"="{city}"][~"^name(:.*)?$"~"{name}"](area);
    relation["addr:city"="{city}"][~"^name(:.*)?$"~"{name}"](area);
    way["addr:city"="{city}"][~"^name(:.*)?$"~"{name}"](area);
    );
    out center;
    """           
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, stream=True)
        time.sleep(2)
        
        if response.status_code == 200:
            data_json = response.json()     
            # for creating test data       
            # dirname = os.path.dirname(__file__)
            # with open(os.path.join(dirname, 'test_osminfo_data.json'),"w") as file:
            #     json.dump(data_json, file)            
            response_status="Sucessful request."   
        else:
            data_json= ""
            response_status = "OOps: Maybe overpass API has too many requests."      
    except:
        data_json= ""
        response_status = "OOps: Something Else"       
    return response_status, data_json


def get_osm_companiesbyregion(regionalcode):
    
    # find working overpass API, when it changes: https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances
    overpass_url = "https://overpass-api.de/api/interpreter"   
    
    overpass_query = f"""
    [out:json];
    area[~"de:regionalschluessel"~"{regionalcode}"]->.boundaryarea;
    (node(area.boundaryarea)["office"~"^(energy_supplier|quango)?$"]["name"];
    node(area.boundaryarea)["office"]["name"]["ownership"~"^(municipal|public|national|state|county|public_nonprofit)$"];
    );
    out center;
    """              

    try:
        logging_text.info("Overpass API request...")
        response = requests.get(overpass_url, params={'data': overpass_query}, stream=True)
        time.sleep(2)
        logging_text.info("Overpass API OSM response:")
        logging_text.info(response)
        if response.status_code == 200:
            data_json = response.json()
            # for creating test data 
            # dirname = os.path.dirname(__file__)
            # with open(os.path.join(dirname, 'test_osm_bw_data.json'),"w") as file:
            #     json.dump(data_json, file)
            response_status="Sucessful request."   
        else:
            data_json= ""
            response_status = "OOps: Maybe overpass API has too many requests."      
    except:
        data_json= ""
        response_status = "OOps: Something Else"       
    return response_status, data_json




