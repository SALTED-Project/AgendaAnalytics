from typing import Any, Optional

from pydantic import AnyUrl, BaseModel, Field


# Shared properties
class SeaweedFileBase(BaseModel):
    name: str = Field(description="The name of the file")

    content: Any = Field(
        default=None,
        description="The content of the file",
    )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SeaweedFileBase):
            return NotImplemented

        return self.name == other.name


# Properties to receive via API on creation
class SeaweedFileCreate(SeaweedFileBase):
    pass


# Properties to receive via API on update
class SeaweedFileUpdate(SeaweedFileBase):
    pass


# Properties shared by models stored in DB
class SeaweedFileInDbBase(SeaweedFileBase):
    pass


# Properties to return to client
class File(SeaweedFileInDbBase):
    url: Optional[AnyUrl]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, File):
            return NotImplemented

        return self.name == other.name and self.url == other.url


# Properties stored in DB
class FileInDb(SeaweedFileInDbBase):
    pass
