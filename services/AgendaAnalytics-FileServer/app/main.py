import logging
import sys
from typing import Optional
import os

from api.api_v1.api import api_router
from core.config import settings
from core.exceptions import (InvalidReferenceException, ItemNotFoundException, KeyHTTPError, ValueHTTPError, )



from fastapi import FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.responses import JSONResponse

from starlette.middleware.cors import CORSMiddleware

from utils.utils import PrometheusMiddleware, metrics, setting_otlp


logging.basicConfig(
    level=logging.DEBUG,
    #format="%(asctime)s - %(threadName)s [%(levelname)5s] %(name)s: %(message)s",
    format="%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s resource.service.name=%(otelServiceName)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S %z",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logging.getLogger("prisma").setLevel("INFO")
logging.getLogger("urllib3").setLevel("INFO")
logging.getLogger("httpx").setLevel("INFO")


def get_application() -> FastAPI:
    _app = FastAPI(
        title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json"
    )
    _app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    _app.include_router(api_router, prefix=settings.API_V1_STR)
    return _app


app = get_application()



@app.exception_handler(ItemNotFoundException)
@app.exception_handler(InvalidReferenceException)
@app.exception_handler(ValueHTTPError)
@app.exception_handler(KeyHTTPError)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


######################################for observability##########################

# Setting metrics middleware
APP_NAME = os.environ.get("APP_NAME", "app-default")

app.add_middleware(PrometheusMiddleware, app_name=APP_NAME)
app.add_route("/metrics", metrics)

# Setting OpenTelemetry exporter
setting_otlp(app, APP_NAME, "http://tempo:4317")


class EndpointFilter(logging.Filter):
    # Uvicorn endpoint access log filter
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("GET /metrics") == -1


# Filter out /endpoint
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())

