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

from app.main import app



# change RouteHandler to default
client = TestClient(app)


# test easy endpoint (check if tests even work)
def test_ping():
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"ping": "pong!"}


def test_organization_jsonlist_discoverandstore():
    dirname = os.path.dirname(__file__)
    filename = os.path.join(dirname, './test-data/test_organization_discoverandstore.json')  
    with open(filename, "r", encoding="utf-8") as f:
        json_data = json.load(f)
    response = client.post(
        "/organization/jsonlist/discoverandstore",
        json=json_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data[0]["@context"] == [
      "https://raw.githubusercontent.com/smart-data-models/dataModel.Organization/master/context.jsonld",
      "https://smartdatamodels.org/context.jsonld"
    ]


