import abc
from typing import Any, AsyncIterable, Generic, Iterable, Optional, Type, TypeVar

from pydantic import BaseModel

# Allow any types for ModelType for compatibility with MongoDB and SeaweedFS
ModelType = TypeVar("ModelType")
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CrudRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType], abc.ABC):
    """
    An abstract repository with Create, Read, Update and Delete functionality.
    """

    def __init__(self, model: Type[ModelType]) -> None:
        self.model = model

    @abc.abstractmethod
    def create(self, obj_in: CreateSchemaType) -> ModelType:
        """
        Creates the given value in the repository.

        :param obj_in: the object to persist
        :return: the persisted objected as in the repository
        """

    @abc.abstractmethod
    def get(self, key: Any) -> Optional[ModelType]:
        """
        Returns the value for the given key in the repository.

        :param key: the key to return the value for
        :return: the value for the given key
        """

    @abc.abstractmethod
    def get_all(self) -> Iterable[ModelType]:
        """
        Returns all values in the repository.

        :return: all values in the repository
        """

    @abc.abstractmethod
    def update(self, key: Any, obj_in: UpdateSchemaType) -> ModelType:
        """
        Updates the value in the repository.

        :param key: the key to update
        :param obj_in: the value
        :return: the updated value as persisted in the repository
        """

    @abc.abstractmethod
    def delete(self, key: Any) -> ModelType:
        """
        Deletes the value for the given key.

        :param key: the key to delete the value for
        :return: the deleted value
        """

    @abc.abstractmethod
    def delete_all(self) -> Iterable[ModelType]:
        """
        Deletes everything in the repository.
        """


class AsyncCrudRepository(
    Generic[ModelType, CreateSchemaType, UpdateSchemaType], abc.ABC
):
    """
    An abstract repository with Create, Read, Update and Delete functionality.
    """

    def __init__(self, model: Type[ModelType]) -> None:
        self.model = model

    @abc.abstractmethod
    async def create(self, obj_in: CreateSchemaType) -> ModelType:
        """
        Creates the given value in the repository.

        :param obj_in: the object to persist
        :return: the persisted objected as in the repository
        """

    @abc.abstractmethod
    async def get(self, key: Any) -> Optional[ModelType]:
        """
        Returns the value for the given key in the repository.

        :param key: the key to return the value for
        :return: the value for the given key
        """

    @abc.abstractmethod
    async def get_all(self) -> AsyncIterable[ModelType]:
        """
        Returns all values in the repository.

        :return: all values in the repository
        """

    @abc.abstractmethod
    async def update(self, key: Any, obj_in: UpdateSchemaType) -> ModelType:
        """
        Updates the value in the repository.

        :param key: the key to update
        :param obj_in: the value
        :return: the updated value as persisted in the repository
        """

    @abc.abstractmethod
    async def delete(self, key: Any) -> ModelType:
        """
        Deletes the value for the given key.

        :param key: the key to delete the value for
        :return: the deleted value
        """

    @abc.abstractmethod
    async def delete_all(self) -> AsyncIterable[ModelType]:
        """
        Deletes everything in the repository.
        """
