import requests
import os
import pytest
import re
import json
from fastapi import FastAPI
from unittest import mock
from unittest.mock import patch
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient
import sqlalchemy
from fastapi.routing import APIRoute
from fastapi import Response

from app.searchengine_rest_api import app, get_db
from app.scripts.googlesearch import google_main


from app.tests import test_db_models
from app.tests.test_database import TestingSessionLocal, engine, metadata


if not sqlalchemy.inspect(engine).has_table("queryandsearch_engine"):  # If table don't exist, Create.    
    tableobject_organization = [metadata.tables["queryandsearch_engine"]]
    test_db_models.Base.metadata.create_all(engine, tables=tableobject_organization)

# change db dependency
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)
client.headers["Content-Type"] = "application/json"

def override_google_main(*args, **kwargs):
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, r'./data/google_api_response.json')

    with open(filename,"r", encoding="utf-8") as f:
        expected_data = json.load(f)
    return expected_data

app.dependency_overrides[google_main] = override_google_main()



# Test cases

def test_root_entry():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "****** REST API for Salted Search Engine Service ******"}

def test_google_searchengine():  
    with patch("app.searchengine_rest_api.google_main", side_effect=override_google_main):  
        # Load expected data from file
        dirname = os.path.dirname(__file__)
        filename = os.path.join(dirname, r'./data/google_api_response.json')

        with open(filename,"r", encoding="utf-8") as f:
            json_data = json.load(f)

        # Create a test search query
        searchquery = "site:abbvie.com compliance"
        engine = "google"
        number_search_results = 2
        language = "en"
        parameters = {
            "searchquery": searchquery,
            "engine": engine,
            "number_search_results": number_search_results,
            "language": language
        }
        # Make a POST request to the endpoint
        response = client.post("/google/searchengine/", params=parameters)
        actual_data = response.json()
        print("Actual Data::", response.json())
        expected_data = json_data
        print("*********************************************")
        print("Expected Data:", expected_data)
        assert actual_data == expected_data
        assert response.status_code == 200


