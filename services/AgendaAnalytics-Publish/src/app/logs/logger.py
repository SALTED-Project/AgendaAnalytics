import datetime

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from fastapi.routing import APIRoute
from typing import Callable, List
from starlette.requests import Request
from fastapi import Response

import logging
import json

from app.db import crud
from app.db.database import  SessionLocal
from app.api import pydantic_models

# get logger once and import it in other modules
logging_text = logging.getLogger('textlogger')


# Dependency: database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CustomRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:   
            logging_text = logging.getLogger('textlogger')
            db = SessionLocal()     
            start = datetime.datetime.utcnow()
            new_servicelog = pydantic_models.ServiceLogCreate(
                service = f"{request.method}  {request.url}",
                start = datetime.datetime.utcnow()                   
            )
            db_servicelog = crud.create_servicelog(db, servicelog=new_servicelog)
            id = db_servicelog.id
            logging_text.info(f"#####################################Logged in db table service-logs under id:{id}#############")  

            try:
                response: Response = await original_route_handler(request)
                res_headers = response.headers
                res_body = response.body
                logging_text.info(f"***************************************ResponseHeaders for service-log id:{id}****************************************")
                logging_text.info(res_headers)
                logging_text.info(f"***************************************ResponseBody for service-log id:{id}*******************************************")
                # only in Publish service not loggend, because too long
                logging_text.info("Due to transparency issues, the response.body is not logged. To change that, go to: /src/logs/logger.py")
                #logging_text.info(json.dumps(json.loads(res_body), indent="\t"))
                # update log in db           
                end = datetime.datetime.utcnow()
                updated_servicelog = pydantic_models.ServiceLogUpdate(
                    end = end,
                    duration = end-start            
                )
                db_servicelog = crud.get_servicelog_by_id(db, servicelog_id=id)            
                db_servicelog_updated = crud.update_servicelog(db, servicelog=db_servicelog, updated_servicelog=updated_servicelog) 
                return response
            
            
            except HTTPException as exc:
                logging_text.info(f"***************************************Response for service-log id:{id}****************************************")
                logging_text.info("HTTPException was thrown.")
                # update log in db           
                end = datetime.datetime.utcnow()
                updated_servicelog = pydantic_models.ServiceLogUpdate(
                    end = end,
                    duration = end-start            
                )
                db_servicelog = crud.get_servicelog_by_id(db, servicelog_id=id)            
                db_servicelog_updated = crud.update_servicelog(db, servicelog=db_servicelog, updated_servicelog=updated_servicelog) 
                raise exc         

        return custom_route_handler