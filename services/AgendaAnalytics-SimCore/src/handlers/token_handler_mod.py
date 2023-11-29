import logging
import uuid

logger = logging.getLogger(__name__)

class TokenHandler:
    """
    This class provides functionality for token generation and deletion
    """

    def __init__(self):
        self.tokenset = set()
        return
    
    # ---------------------------------------------------------------------------
    def issue_token(self) -> str:
        """
        This method generates a hex string representation
        of a UUID and checks for consistency.
        """
        token = uuid.uuid4().hex   # hex string representation of uuid token
        if token in self.tokenset:
            logger.error("UUID handling inconsistency. Token exists already.")
            raise ValueError("*** intenal error ***")
        self.tokenset.add(token)
        return token
    
    
    # ---------------------------------------------------------------------------
    def get_active_tasks(self):
        return list(self.tokenset)
    

    # ---------------------------------------------------------------------------
    def check_token(self, token:str) -> bool:
        if token in self.tokenset:
            return (token, True)
        else:
            return (token, False)
    

    # ---------------------------------------------------------------------------
    def remove_token(self, token:str) -> str:
        if token not in self.tokenset:
            logger.warning("Trying to remove a nonexisting token. No further action")
            return ''
        self.tokenset.remove(token)
        return token
        
