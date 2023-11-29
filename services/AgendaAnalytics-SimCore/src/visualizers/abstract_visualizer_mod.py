from abc import ABC, abstractmethod
import os
import joblib
from dynaconf import settings
from simcore_api_schema_mod import Status
import pandas as pd

REFFOLDERNAME = settings.REFFOLDERNAME
PROJECTFOLDER = settings.PROJECTFOLDER

class AbstractVizualizer(ABC):
    """
    Abstract handler class that enforcing corresponding
    method implementations
    """

    def __init__(self):
        return
    

    @abstractmethod
    def visualize_project(self, project: str):
        """
        Method must be implemented by all visualizers
        """