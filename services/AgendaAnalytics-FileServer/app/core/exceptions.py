from fastapi import HTTPException


class ItemNotFoundException(HTTPException):
    """
    Raised when an item is not found in the database.
    Counts as a HTTP '404 - Not Found' error.
    """

    def __init__(self, msg: str, item_id: str) -> None:
        super().__init__(404, msg)
        self.item_id = item_id


class InvalidReferenceException(HTTPException):
    """
    Raised when an item has or attempts to make an invalid reference to another item.
    Counts as a HTTP '400 - Bad Request' error.
    """

    def __init__(self, msg: str, item_id: str, ref_id: str) -> None:
        super().__init__(400, msg)
        self.item_id = item_id
        self.ref_id = ref_id


class ValueHTTPError(HTTPException):
    """
    Raised when a value of the correct data type but with illegal value is passed.
    Counts as a HTTP '400 - Bad Request' error.
    """

    def __init__(self, msg: str) -> None:
        super().__init__(400, msg)


class KeyHTTPError(HTTPException):
    """
    Raised when a key is missing from data (i.e. a header is missing, or a JSON key is missing).
    Counts as a HTTP '400 - Bad Request' error.
    """

    def __init__(self, msg: str) -> None:
        super().__init__(400, msg)
