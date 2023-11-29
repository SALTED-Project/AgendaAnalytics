from fastapi.testclient import TestClient
import sqlalchemy
import logging
from fastapi.routing import APIRoute
from starlette.requests import Request
from fastapi import Response
from typing import Callable
import requests
import os 
import json

from app.main import app, get_db



# change RouteHandler to default
client = TestClient(app)


# test easy endpoint (check if tests even work)
def test_ping():
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"ping": "pong!"}

