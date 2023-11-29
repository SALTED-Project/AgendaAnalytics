from fastapi.testclient import TestClient
import sqlalchemy
import logging
import pandas as pd
import os 
import json

from app.main import app, get_db
from app.api import wikipedia
from app.tests import test_db_models
from app.tests.test_database import TestingSessionLocal, engine, metadata




if not sqlalchemy.inspect(engine).has_table("discoverandstore_organizations"):  # If table don't exist, Create.    
    tableobject_organization = [metadata.tables["discoverandstore_organizations"]]
    test_db_models.Base.metadata.create_all(engine, tables=tableobject_organization)
    logging.info("test database table 'discoverandstore_organizations' did not exist yet, therefor one was created.")

salted_searchengine_service = os.environ.get("SALTED_SEARCHENGINE_SERVICE")



# change db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db


# change RouteHandler to default
client = TestClient(app)




# test for organizations endpoints
#################################################

# test easy endpoint
def test_ping():
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"ping": "pong!"}

# test read request when no organizations are in the db
def test_read_organizations_error404():
    response = client.get(f"/organizations/")
    assert response.status_code == 404
    assert response.text == '{"detail":"No organizations found."}'

# test create & read organization / organizations
def test_create_organization():
    response = client.post(
        "/organizations/",
        json={
            "name": "Test",
            "legalform": "GmbH",
            "city": "Musterort",
            "url_google": "www.example.com",
            "country": "Wunderland",
            "postcode": "00000",
            "street": "Wunderstraße",
            "housenumber": "7",
            "lat": "54.378",
            "long": "124.243",
            "officecategory":"semi-governmental",
            "url_osm": "www.example-wunder.com",
            "origin_service": "wikipedia-test"
            }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test"
    assert data["legalform"] == "GmbH"
    assert data["city"] == "Musterort"
    assert data["url_google"] == "www.example.com"
    assert data["country"] == "Wunderland"
    assert data["postcode"] == "00000"
    assert data["street"] == "Wunderstraße"
    assert data["housenumber"] == "7"
    assert data["lat"] == "54.378"
    assert data["long"] == "124.243"
    assert data["officecategory"] == "semi-governmental"
    assert data["created"] != None
    assert data["modified"] != None
    assert data["origin_service"] == "wikipedia-test"
    organization_name = data["name"]
    response = client.get(f"/organizations/{organization_name}")
    assert response.status_code == 200
    # test reading of multiple organizations
    # add additional entry
    response = client.post(
        "/organizations/",
        json={
            "name": "TestNext",
            "legalform": "GmbH",
            "city": "Musterort",
            "url_google": "www.example.com",
            "country": "Wunderland",
            "postcode": "00000",
            "street": "Wunderstraße",
            "housenumber": "7",
            "lat": "54.378",
            "long": "124.243",
            "officecategory":"semi-governmental",
            "url_osm": "www.example-wunder.com",
            "origin_service": "wikipedia-test"
            }
    )
    assert response.status_code == 200
    response = client.get("/organizations/")
    assert response.status_code == 200
    data = response.json()
    assert len(data)==2
 

# test post request for already existing organization
def test_create_orgnization_error400():
    response = client.post(
        "/organizations/",
        json={
            "name": "Test",
            "legalform": "GmbH",
            "city": "Musterort",
            "url_google": "www.example.com",
            "country": "Wunderland",
            "postcode": "00000",
            "street": "Wunderstraße",
            "housenumber": "7",
            "lat": "54.378",
            "long": "124.243",
            "officecategory":"semi-governmental",
            "url_osm": "www.example-wunder.com",
            "origin_service": "wikipedia-test"
            }
    )
    assert response.status_code == 400
    assert response.text ==  '{"detail":"Organization name already exists."}'

# test read request for not existing organization
def test_read_organization_error404():
    response = client.get(f"/organizations/TestName")
    assert response.status_code == 404
    assert response.text ==  '{"detail":"Organization not found."}'


# test update organization
def test_update_organization():
    response = client.put("/organizations/Test",
        json={
            "legalform": "GmbH",
            "city": "Musterort-Neu",
            "url_google": "www.example2.com",
            "country": "Wunderland",
            "postcode": "00000",
            "street": "Wunderstraße",
            "housenumber": "7",
            "lat": "54.378",
            "long": "124.243",
            "officecategory":"semi-governmental",
            "url_osm": "www.example-wunder.com"
            }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test"
    assert data["legalform"] == "GmbH"
    assert data["city"] == "Musterort-Neu"
    assert data["url_google"] == "www.example2.com"
    assert data["created"] != None
    assert data["modified"] != None
    organization_name = data["name"]
    response = client.get(f"/organizations/{organization_name}")
    assert response.status_code == 200
    assert data["city"] == "Musterort-Neu"
    assert data["url_google"] == "www.example2.com"


# test update of non existent organization
def test_update_organization_error404():
    response = client.put("/organizations/TestName",
        json={
            "legalform": "GmbH",
            "city": "Musterort-Neu",
            "url_google": "www.example2.com",
            "country": "Wunderland",
            "postcode": "00000",
            "street": "Wunderstraße",
            "housenumber": "7",
            "lat": "54.378",
            "long": "124.243",
            "officecategory":"semi-governmental",
            "url_osm": "www.example-wunder.com"
            }
    )
    assert response.status_code == 404
    assert response.text =='{"detail":"Organization not found."}'


    
# test deletion of organization
def test_delete_organization():
    response = client.delete("/organizations/Test")
    assert response.status_code == 200
    response = client.delete("/organizations/TestNext")
    assert response.status_code == 200
    

# test deletion of non existing organization
def test_delete_organization_error404():
    response = client.delete("/organizations/TestName")
    assert response.status_code == 404
    assert response.text == '{"detail":"Organization not found."}'


# deleteing all organizations is tested implicitely, since it is used to clean up for tests


# test for service endpoints
#################################################


# test google enriching service with mocked google request
def test_run_googlesearch_service(requests_mock):  
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, './test-data/test_google_data.json')
    requests_mock.real_http = True
    requests_mock.post(f"{salted_searchengine_service}/google/searchengine/", json=json.load(open(filename)))    
    response = client.post(
        "/organizations/",
        json={
            "name": "50Hertz Transmission",
            "legalform": "GmbH",
            "city": "Berlin",
            "url_google": "string",
            "country": "string",
            "postcode": "string",
            "street": "string",
            "housenumber": "string",
            "lat": "string",
            "long": "string",
            "officecategory":"semi-governmental",
            "url_osm": "string",
            "origin_service": "google-test"
            }
    )
    response = client.get("/service/enrich/googlesearch")    
    print(response.status_code)
    print(response.text)
    data = response.json()
    assert data[0]["name"] == "50Hertz Transmission"
    assert data[0]["url_google"] == "www.50hertz.com"
    assert response.status_code == 200
    response = client.delete("/organizations/50Hertz Transmission")
    assert response.status_code == 200


# test osm enriching service with mocked osm request (after pip install requests-mock)
def test_run_osmsearch_service(requests_mock):  
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, './test-data/test_osminfo_data.json')  
    with open(filename, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    requests_mock.real_http = True    
    requests_mock.get("https://lz4.overpass-api.de/api/interpreter", json=json_data)
    response = client.post(
        "/organizations/",
        json={
            "name": "50Hertz Transmission",
            "legalform": "GmbH",
            "city": "Berlin",
            "url_google": "string",
            "country": "string",
            "postcode": "string",
            "street": "string",
            "housenumber": "string",
            "lat": "string",
            "long": "string",
            "officecategory":"semi-governmental",
            "url_osm": "string",
            "origin_service": "osm-test"
            }
    )
    response = client.get("/service/enrich/osmsearch")    
    data = response.json()
    assert data[0]["name"] == "50Hertz Transmission"
    assert data[0]["url_osm"] == 'https://www.50hertz.com/'
    assert response.status_code == 200
    response = client.delete("/organizations/50Hertz Transmission")
    assert response.status_code == 200



# test wikipedia.get_table() with mock response
def test_get_table(requests_mock):
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, './test-data/test_wiki_data.txt')
    text_file = open(filename, "r")    
    wikitext = text_file.read()    
    text_file.close()
    requests_mock.get('https://de.wikipedia.org/wiki/Liste_privatrechtlicher_Unternehmen_mit_Bundesbeteiligung_in_Deutschland', text=wikitext)
    response, response_status, df_companies, df_companies_status = wikipedia.get_table()
    test_wiki_table= pd.read_pickle(os.path.join(dirname, './test-data/test_wiki_table.pkl'))  
    testvalue = test_wiki_table.equals(df_companies)
    assert True == testvalue
    assert "Table was built successfully." == df_companies_status


# override before testing wikipedia service call to mock external API call
def override_get_table():
    dirname = os.path.dirname(__file__)
    df_companies = pd.read_pickle(os.path.join(dirname, './test-data/test_wiki_table.pkl'))  
    df_companies_status = "Table was built successfully."
    # response is never used after a function call of get_table, therefor it should be removed from the code in general
    response = ""
    response_status = "Sucessful request."    
    return response, response_status, df_companies, df_companies_status

app.dependency_overrides[wikipedia.get_table] = override_get_table


# test search wikipedia service with overridden get_table function
def test_run_wikipedia_service():    
    response = client.get("/service/search/wikipedia")    
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, './test-data/test_wiki.json')    
    with open(filename, "r", encoding="utf-8") as f:
        json_data = json.load(f)    
    json_data_list =[item["name"]for item in json_data]
    wiki_data = response.text
    wiki_data_list =[item["name"]for item in json.loads(wiki_data)]    
    assert set(json_data_list) == set(wiki_data_list)
    assert response.status_code == 200

    
# test search osm service
def run_osm_service(requests_mock):
    requests_mock.real_http = True 
    response = client.delete("/organizations/")
    assert response.status_code == 200
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, './test-data/test_osminfo_result.json')  
    with open(filename, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    json_data_list =[item["name"]for item in json_data]
    requests_mock.real_http = True    
    requests_mock.get("https://lz4.overpass-api.de/api/interpreter", json=json_data)
    response = client.get("/service/search/osm")
    osm_data = response.text
    osm_data_list =[item["name"]for item in json.loads(osm_data)]
    assert set(json_data_list) == set(osm_data_list)
    assert response.status_code == 200




