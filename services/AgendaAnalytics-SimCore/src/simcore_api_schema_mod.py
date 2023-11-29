from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel


class Status(Enum):
    FAILED = -1
    SUCCESS = 1
    RUNNING = 2
    WARNING = 3


class SCResponse(BaseModel):
    status: Status  # SC status (see above)
    message: str  # short message
    details: Optional[Dict] = None  # other details arranged in a dictionary, no longer optional


class SCStatus(BaseModel):
    project: str  # analysis ID
    status: Status  # status of the analysis
    files: List[str] = []  # list of resulting files


class SCFile(BaseModel):
    name: str  # name of the file
    mimetype: str  # file mimetype
    content: str  # conten of the file (text/plain for a text file)


class FileItems(BaseModel):
    filenames: List[str] = [""]
