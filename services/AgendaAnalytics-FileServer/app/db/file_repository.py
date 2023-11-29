from typing import Any, Iterable, Optional

from db.crud_repository import CrudRepository
from schemas.seaweed_file import File, SeaweedFileCreate, SeaweedFileUpdate


class HttpFileRepository(CrudRepository[File, SeaweedFileCreate, SeaweedFileUpdate]):
    def create(self, obj_in: SeaweedFileCreate) -> File:
        raise NotImplementedError()

    def get(self, key: Any) -> Optional[File]:
        raise NotImplementedError()

    def get_all(self) -> Iterable[File]:
        raise NotImplementedError()

    def update(self, key: Any, obj_in: SeaweedFileUpdate) -> File:
        raise NotImplementedError()

    def delete(self, key: Any) -> File:
        raise NotImplementedError()

    def delete_all(self) -> Iterable[File]:
        raise NotImplementedError()
