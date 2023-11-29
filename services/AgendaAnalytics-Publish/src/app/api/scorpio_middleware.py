import requests
import os
import json


from app.logs.logger import logging_text
import app.definitions as definitions


# scorpio API info: https://scorpio.readthedocs.io/en/latest/API_walkthrough.html

def publish(entity, broker_url):
    
    # check if entity is already represented in any way within the broker
    response_text, entity_newid = check_scorpio(entity, broker_url)

    # error handling if entity_check is an error response
    if response_text == definitions.MESSAGE_CLIENT_ERROR:
        response = definitions.MESSAGE_CLIENT_ERROR
        entity_broker = None

    elif response_text == definitions.MESSAGE_ERROR:
        response = definitions.MESSAGE_ERROR
        entity_broker = None

    
    # further handling when entity_check is an actual entity
    elif (response_text == definitions.MESSAGE_SUCCESS) or (response_text== definitions.RESPONSE_204):  
        # try to create new entity
        scorpio_response = post(entity_newid, broker_url) 

        # if successfull return response directly
        if scorpio_response==definitions.RESPONSE_201:
            response = definitions.MESSAGE_SUCCESS
            entity_broker = entity
        
        # if error return response directly
        elif scorpio_response==definitions.RESPONSE_400:
            response = definitions.MESSAGE_CLIENT_ERROR
            entity_broker = None

        # if already exists try to append attributes
        elif scorpio_response==definitions.RESPONSE_409:
            response = merge_and_update_entity(entity_newid, broker_url)
            entity_broker = entity_newid

        # catch error and return 
        else:
            response = definitions.MESSAGE_ERROR
            entity_broker = None

    return response, entity_broker



def post(entity, broker_url):
    logging_text.info("post-method")
    logging_text.info(entity)
    path = definitions.NGSI_API_ENTITIES
    url = broker_url + path
    headers = {'Content-Type': 'application/ld+json'}
    r = requests.post(url, headers=headers, data=json.dumps(entity))
    logging_text.info("Scorpio post response:")
    logging_text.info(r.status_code)
    try:
        logging_text.info(r.json())
    except:
        logging_text.info(r.text)
    try:
        # success
        if r.status_code==201:
            response= definitions.RESPONSE_201  
        # client error: entity not parsable
        elif r.status_code==400:
            response= definitions.RESPONSE_400
        # client error: already exists
        elif r.status_code==409:
            response= definitions.RESPONSE_409
        # unknown
        else:
            response= definitions.MESSAGE_ERROR        
    except:
         response= definitions.MESSAGE_ERROR 

    logging_text.info(response)  
    return response


# loop through attributes of entity and try to append / update everyone to the exiting entity
def merge_and_update_entity(entity, broker_url):
    logging_text.info("merge-method")
    entity_id = entity["id"]
    context_payload = entity["@context"]  
    entity_keys = set(list(entity.keys()))
    to_delete = ['id','type', '@context']
    entity_keys.difference_update(to_delete)
    count_max = len(entity_keys)
    counter = 0
    for attribute in entity_keys:
        attribute_payload = entity[attribute]
        response = append(entity_id,attribute,attribute_payload,context_payload,broker_url)
        if response == definitions.RESPONSE_204:
            counter  += 1
    if counter == count_max:
        response = definitions.MESSAGE_SUCCESS
    else:
        response = definitions.MESSAGE_ERROR
    return response



# appends attributes that are not represented within that entity of scorpio (automatically updates existing attributes)
def append(entity_id,attribute,attribute_payload,context_payload, broker_url):
    path = definitions.NGSI_API_ENTITIES+"/"+entity_id+"/attrs"
    url = broker_url + path    
    headers = {'Content-Type': 'application/ld+json'}
    data = {attribute:attribute_payload, '@context':context_payload}
    data = json.dumps(data)
    r = requests.post(url, headers=headers, data=data) 
    try:
        # success: appended
        if r.status_code==204:
            response= definitions.RESPONSE_204
        # success, but not appended: 'attribute not found in original entity'
        elif r.status_code==207:
            response= definitions.RESPONSE_207
    except:
        response= definitions.MESSAGE_ERROR  
    return response


# check scorpio for existing entities
def check_scorpio(entity, broker_url):
    app_name = os.environ.get("APP_NAME")
    logging_text.info("checkscorpio-method")
    path = definitions.NGSI_API_ENTITIES
    url = broker_url + path    
    logging_text.info(url)    
    logging_text.info("Checks for the following entity:")
    logging_text.info(entity["id"])
    try:
        context_links = entity["@context"]
        json_bin = {
            "@context":context_links
        }
    except:
        return definitions.MESSAGE_CLIENT_ERROR, entity

    str_bin = json.dumps(json_bin, indent="\t")
    params={"pastebin": str_bin}
    try:
        response = requests.post(f"http://{app_name}:8000/pastebin/", params = params)
        data = response.json()
        bin_id = data["id"]
        bin_data = data["bin"]
        params = {'type': entity["type"]}
        headers = {'Content-Type': 'application/json', 'Link': f'<http://{app_name}:8000/pastebin/{bin_id}>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"'}
        r = requests.get(url, headers=headers, params=params)  
        try:
            logging_text.info(len(r.json()))
            
        except:
            logging_text.info(r.text)
    except:
        return definitions.MESSAGE_ERROR, entity  
    
    try:
        if r.status_code==200 and r.json() != []:
            for scorpioentity in r.json():
                name_list = ['Organization','EVChargingStation', 'DistributionDCAT-AP']
                stationname_list = ['BikeHireDockingStation']
                title_list = ['DataServiceDCAT-AP']
                source_list = ['KeyPerformanceIndicator']
                try:
                    scorpio_name = scorpioentity['name']['value']
                    entity_name = entity['name']['value']
                except:
                    scorpio_name = None
                    entity_name = None
                try:
                    scorpio_stationname = scorpioentity['stationName']['value']
                    entity_stationname = entity['stationName']['value']
                except:
                    scorpio_stationname = None
                    entity_stationname = None
                try:
                    scorpio_title = scorpioentity['title']['value']
                    entity_title = entity['title']['value']
                except:
                    scorpio_title = None
                    entity_title = None
                try:
                    scorpio_source = scorpioentity['source']['value']
                    entity_source = entity['source']['value']
                except:
                    scorpio_source = None
                    entity_source = None
                if ((entity['type'] in name_list) and (entity_name == scorpio_name)) or ((entity['type'] in stationname_list) and (entity_stationname == scorpio_stationname)) or ((entity['type'] in title_list) and (entity_title == scorpio_title)) or ((entity['type'] in source_list) and (entity_source == scorpio_source)):
                    logging_text.info("changing id now")
                    logging_text.info("This is the initial entity id:")
                    logging_text.info(entity["id"])
                    scorpioentity_id = scorpioentity["id"]
                    entity["id"] = scorpioentity_id
                    logging_text.info("This is the id of the scorpio entity found with same info represented:")
                    logging_text.info(scorpioentity_id)
            response_text= definitions.MESSAGE_SUCCESS
            logging_text.info("Went through al possibilities within the scorpio, that have the same type.")
        elif r.status_code==200 and r.json() == []:
            response_text= definitions.RESPONSE_204        
        else:
            response_text= definitions.MESSAGE_ERROR      
    except:
        response_text= definitions.MESSAGE_ERROR     
    return response_text, entity




# gets list of entity ids of specific entity type
def broker_get_by_type(entitytype,broker_url):
    app_name = os.environ.get("APP_NAME")
    path = definitions.NGSI_API_ENTITIES
    url = broker_url + path    
    headers = {'Accept': 'application/ld+json','Link': f'<http://{app_name}:8000/pastebin/defaultcontext/{entitytype}>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"'}
    params = {'type' : entitytype}
    r = requests.get(url, headers=headers, params=params) 
    logging_text.info(r.status_code)    
    try:
        if r.status_code==200:
            response=r.json()
            logging_text.info(f"number results: {len(response)}")
    except:
        response= definitions.MESSAGE_ERROR  
        logging_text.info(response) 
    return response