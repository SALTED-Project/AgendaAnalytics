from fastapi.testclient import TestClient
import sqlalchemy
import logging
from fastapi.routing import APIRoute
from starlette.requests import Request
from fastapi import Response
from typing import Callable
import requests
import pandas as pd
import os 
import json

from app.main import app, get_broker_url, get_db
from app.tests.test_database import TestingSessionLocal, engine, metadata
from app.tests import test_db_models


# other env variables set
broker_url = os.environ.get("SCORPIO_TEST_URL")

# change scorpio dependency
def override_get_broker_url():
    return broker_url

app.dependency_overrides[get_broker_url] = override_get_broker_url


# change db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# create db table
if not sqlalchemy.inspect(engine).has_table("publish_pastebin"):     
    tableobject_pastebin = [metadata.tables["publish_pastebin"]]
    test_db_models.Base.metadata.create_all(engine, tables=tableobject_pastebin)
    logging.info("test database table 'publish_pastebin' did not exist yet, therefor one was created.")


# change RouteHandler to default
client = TestClient(app)


# test easy endpoint (check if tests even work)
def test_ping():
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"ping": "pong!"}

# post pastebin test
def test_create_pastebin():
    json_bin = {
        "@context": [
            "http://schema.lab.fiware.org/ld/context",
            "http://schema.org"
        ]
    }
    str_bin = str(json.dumps(json_bin))
    params={"pastebin": str_bin}
    response = client.post("/pastebin/", params = params)
    assert response.status_code == 200
    data = response.json()
    bin_id = data["id"]
    bin = data["bin"]
    assert bin_id == 1
    assert bin == str_bin

    params={"pastebin": "hello world!"}
    response = client.post("/pastebin/", params = params)
    assert response.status_code == 200
    data = response.json()
    bin_id = data["id"]
    bin = data["bin"]
    assert bin_id == 2
    assert bin == "hello world!"

# read pastebin test
def test_read_pastebin():
    response = client.get("/pastebin/1")
    assert response.status_code == 200
    data = response.json()
    json_bin = {
        "@context": [
            "http://schema.lab.fiware.org/ld/context",
            "http://schema.org"
        ]
    }
    assert data == json_bin
    response = client.get("/pastebin/2")
    assert response.status_code == 200
    data = response.text
    assert data == '"hello world!"'

# read pastebin defaultcontext organization
def test_read_default_context_organization():
    response = client.get("/pastebin/defaultcontext/Organization")
    data = response.json()
    json_bin = {
        "@context": [
            "https://raw.githubusercontent.com/smart-data-models/dataModel.Organization/master/context.jsonld",
            "https://smartdatamodels.org/context.jsonld"
    ]
    }
    assert response.status_code == 200
    assert data == json_bin


# post entity
def test_post_publish_jsonlist():
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, './test-data/request.json')  
    with open(filename, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    response = client.post(
        "/publish/jsonlist",
        json=[json_data]
    )
    print(response.text)
    assert response.status_code == 200
    data = response.json()
    assert data == [json_data]
    r = requests.get("http://salted_publish_testscorpio:9090/ngsi-ld/v1/entities?type=EVChargingStation", headers={"Link":'<https://smartdatamodels.org/context.jsonld>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"'})
    r_data = r.json()
    assert r_data[0]['name']['value']=="PP00517"
    assert r_data[0]['capacity']['value']==2

# check if entity gets updated if id is new, but existing name is used
def test_post_publish_jsonlist_updatedidandattr():
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, './test-data/request.json')  
    with open(filename, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    json_data['id']="urn:ngsi-ld:EVChargingStation:updated"
    json_data['capacity']['value']=10
    response = client.post(
        "/publish/jsonlist",
        json=[json_data]
    )
    assert response.status_code == 200
    r = requests.get("http://salted_publish_testscorpio:9090/ngsi-ld/v1/entities?type=EVChargingStation", headers={"Link":'<https://smartdatamodels.org/context.jsonld>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"'})
    r_data = r.json()
    assert len(r_data)==1
    assert r_data[0]['id']=="urn:ngsi-ld:EVChargingStation:bfcfebcf-532b-427e-836d-335d38821ae3Test"
    assert r_data[0]['name']['value']=="PP00517"
    assert r_data[0]['capacity']['value']==10

# test query broker by type    
def test_get_entity_evchargingstation():
    response = client.get("/broker/entities/EVChargingStation")
    assert response.status_code == 200
    r_data = response.json()
    assert len(r_data)==1
    assert r_data[0]['id']=="urn:ngsi-ld:EVChargingStation:bfcfebcf-532b-427e-836d-335d38821ae3Test"

# test query broker by type    
def test_get_entity_organization():
    response = client.get("/broker/entities/Organization")
    assert response.status_code == 200
    r_data = response.json()
    assert r_data==[]

# test query broker by type    
def test_get_entity_bikehiredockingstation():
    response = client.get("/broker/entities/BikeHireDockingStation")
    assert response.status_code == 200
    r_data = response.json()
    assert r_data==[]

# test query broker by type    
def test_get_entity_keyperformanceindicator():
    response = client.get("/broker/entities/KeyPerformanceIndicator")
    assert response.status_code == 200
    r_data = response.json()
    assert r_data==[]

# test query broker by type    
def test_get_entity_dataservice():
    response = client.get("/broker/entities/DataServiceDCAT-AP")
    assert response.status_code == 200
    r_data = response.json()
    assert r_data==[]
    
# test query broker by type    
def test_get_entity_dataservicerun():
    response = client.get("/broker/entities/DataServiceRun")
    print(response.json())
    assert response.status_code == 200
    r_data = response.json()
    assert r_data==[]

# test query broker by type    
def test_get_entity_distribution():
    response = client.get("/broker/entities/DistributionDCAT-AP")
    print(response.json())
    assert response.status_code == 200
    r_data = response.json()
    assert r_data==[]