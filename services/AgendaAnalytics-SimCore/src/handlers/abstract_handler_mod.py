from abc import ABC, abstractmethod
#from typing import List, Optional

class AbstractHandler(ABC):
    """
    Abstract handler class that is supposed to enforce
    implementations of all required functions for the 
    concretisations of the individual handlers (use case specific)
    """

    def __init__(self):
        return

    #
    # these methods are to be implemented by the derived classes
    #

    @abstractmethod
    def analyze_project(self, project:str):
        pass
    
