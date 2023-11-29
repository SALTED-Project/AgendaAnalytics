from api.api_v1.endpoints import (
    files
)
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(files.router, prefix="/files", tags=["files"])

