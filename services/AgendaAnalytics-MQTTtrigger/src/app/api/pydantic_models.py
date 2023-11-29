import json
from pydantic import BaseModel, Field, Json
from typing import List, Any
import datetime
import uuid


example_orga = {
    "id": f"urn:ngsi-ld:Organization:{str(uuid.uuid4())}",
    "type": "Organization",
    "dateCreated": {
      "type": "Property",
      "value": str(datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat())
    },
    "dateModified": {
      "type": "Property",
      "value": str(datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat())
    },
    "name": {
      "type": "Property",
      "value": "Stadtwerke Buchholz"
    },
    "location": {
      "type": "GeoProperty",
      "value": {
        "type": "Point",
        "coordinates": [
          53.3458215,
          9.8616456
        ]
      }
    },
    "address": {
      "type": "Property",
      "value": {
        "addressLocality": "Buchholz in der Nordheide",
        "postalCode": "21244",
        "streetAddress": "Maurerstraße 10"
      }
    },
    "url": {
      "type": "Property",
      "value": "http://www.stadtwerke-buchholz.de/"
    },
    "legalName": {
      "type": "Property",
      "value": "Stadtwerke Buchholz"
    },
    "@context": [
      "https://raw.githubusercontent.com/smart-data-models/dataModel.Organization/master/context.jsonld",
      "https://smartdatamodels.org/context.jsonld"
    ]
  }

class TriggerDITDETSpecific(BaseModel):
    parameters: Any
    data: Any

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "parameters": {
                    "publish": {},
                    "crawling": {
                       "approach": "report",
                       "custom_depth": "0",
                       "actuality_days": "7",
                       "keywords": "Nachhaltigkeitsbericht",
                       "language": "",
                       "target_agenda_entity_id": "urn:ngsi-ld:DistributionDCAT-AP:9bd03954-fa71-4fd7-a014-77b79b6534a0",
                       
                    },
                    "agendamatching": {
                        "agenda_entity_id": "urn:ngsi-ld:DistributionDCAT-AP:9bd03954-fa71-4fd7-a014-77b79b6534a0"
                    }
                },
                "data": example_orga
            }            
        }


class TriggerDITGeneral(BaseModel):
    parameters: Any

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "parameters": {
                    "discoverandstore": {
                        "searchscope" : "osm" ,
                        "enrichscope" : "google"
                    },
                    "mapping": {},
                    "publish": {}
                }
            }
        }

class TriggerDETSpecificCrawling(BaseModel):
    parameters: Any
    data: Any

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "parameters": {
                    "publish": {},
                    "crawling": {
                       "approach": "website",
                       "custom_depth": "1",
                       "actuality_days": "7",
                       "keywords": "Künstliche Intelligenz; Artificial Intelligence; KI; AI; Innovation",
                       "language": "de",
                       "target_agenda_entity_id": "urn:ngsi-ld:DistributionDCAT-AP:58e6963c-75af-485c-8f6c-562d3f2b987a"
                    }
                },
                "data": example_orga
            }            
        }


class TriggerDETGeneralCrawling(BaseModel):
    parameters: Any

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "parameters": {
                    "publish": {},
                    "crawling": {
                       "approach": "google",
                       "custom_depth": "0",
                       "actuality_days": "7",
                       "keywords": "Künstliche Intelligenz; Artificial Intelligence; KI; AI; Innovation",
                       "language": "en",
                       "target_agenda_entity_id": "urn:ngsi-ld:DistributionDCAT-AP:58e6963c-75af-485c-8f6c-562d3f2b987a"
                    }
                }
            }
        }

class TriggerDETSpecificAgendaMatching(BaseModel):
    parameters: Any
    data: Any

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "parameters": {
                    "publish": {},
                    "agendamatching": {
                        "agenda_entity_id": "urn:ngsi-ld:DistributionDCAT-AP:f7c6cdd0-3b55-412d-a3d9-0c0fef06fdfd"
                    }
                },
                "data": example_orga
            }            
        }


class TriggerDETGeneralAgendaMatching(BaseModel):
    parameters: Any

    class Config:
        orm_mode = True
        schema_extra = {
            "example": {
                "parameters": {
                    "publish": {},
                    "agendamatching": {
                        "agenda_entity_id": "urn:ngsi-ld:DistributionDCAT-AP:f7c6cdd0-3b55-412d-a3d9-0c0fef06fdfd"
                    }
                }
            }
        }

class ServiceLogBase(BaseModel):
    """
     This is the schema which is used for each single record of a service log / database entry. All timestamps are in UTC.
    """
    id: int
    service: str
    start: datetime.datetime
    end: datetime.datetime 
    duration: datetime.timedelta

    class Config:
        orm_mode = True

class ServiceLogCreate(BaseModel):
    """
        This is used for creating log entry.
    """
    service: str
    start: datetime.datetime
    
    class Config:
        orm_mode = True


class ServiceLogUpdate(BaseModel):
    """
        This is used for updating log entry.
    """
    end: datetime.datetime 
    duration: datetime.timedelta
    
    class Config:
        orm_mode = True