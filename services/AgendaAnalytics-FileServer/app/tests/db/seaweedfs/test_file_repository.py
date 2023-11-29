import re
from io import BytesIO

import pytest
from db.seaweedfs.file_repository import SeaweedFileRepository
from db.seaweedfs.master import FID_PATTERN_STR, Master, MasterCredentials
from pydantic import AnyHttpUrl, parse_obj_as
from schemas.seaweed_file import SeaweedFileCreate, SeaweedFileUpdate



@pytest.fixture()
def master(seaweed_master_credentials: MasterCredentials) -> Master:
    return Master(credentials=seaweed_master_credentials)


@pytest.fixture()
def repository(master: Master) -> SeaweedFileRepository:
    return SeaweedFileRepository(master)


@pytest.mark.dependency()
def test_save(repository: SeaweedFileRepository) -> None:
    print("test save")
    input_file = SeaweedFileCreate(name="Test", content=BytesIO(b'{"test": 123}'))
    file_under_test = repository.create(input_file)

    assert None is not file_under_test, "returned file should not be None"
    assert input_file.name == file_under_test.name, "file name should not change"
    assert None is not file_under_test.url, "URL should not be None"
    assert None is not re.search(
        FID_PATTERN_STR, file_under_test.url
    ), "returned URL should contain a file ID"
    # clean up
    del_file = repository.delete(parse_obj_as(AnyHttpUrl, file_under_test.url))
    assert None is not del_file

@pytest.mark.dependency(depends=["test_save"])
def test_get(repository: SeaweedFileRepository) -> None:
    print("test get")
    input_file = SeaweedFileCreate(name="Test", content=BytesIO(b'{"test": 123}'))
    created_file = repository.create(input_file)
    file_under_test = repository.get(parse_obj_as(AnyHttpUrl, created_file.url))
    assert None is not file_under_test, "returned file should be not be None"
    # clean up
    del_file = repository.delete(parse_obj_as(AnyHttpUrl, file_under_test.url))
    assert None is not del_file

@pytest.mark.dependency(depends=["test_save"])
def test_get_all(repository: SeaweedFileRepository) -> None:
    print("test get all")
    input_file = SeaweedFileCreate(name="Test", content=BytesIO(b'{"test": 1234}'))
    created_file = repository.create(input_file)
    files_under_test = repository.get_all()
    assert None is not files_under_test, "returned files should be not be None"
    # clean up
    del_file = repository.delete(parse_obj_as(AnyHttpUrl, created_file.url))
    assert None is not del_file


def test_update(repository: SeaweedFileRepository) -> None:
    with pytest.raises(NotImplementedError):
        repository.update(
            parse_obj_as(AnyHttpUrl, "http://google.com"),
            SeaweedFileUpdate(name="Test", content=BytesIO(b'{"test": 123}')),
        )

@pytest.mark.dependency(depends=["test_save", "test_get"])
def test_delete(repository: SeaweedFileRepository) -> None:
    print("test delete")
    input_file = SeaweedFileCreate(name="Test", content=BytesIO(b'{"test": 123}'))
    created_file = repository.create(input_file)
    file_under_test = repository.delete(parse_obj_as(AnyHttpUrl, created_file.url))
    print(file_under_test)
    assert None is not file_under_test, "a file should be returned"
    assert (
        input_file.name == file_under_test.name
    ), "the name of the deleted file should match the uploaded file"
    assert None is repository.get(
        parse_obj_as(AnyHttpUrl, file_under_test.url)
    ), "file should no longer exist on server"


def test_delete_all(repository: SeaweedFileRepository) -> None:
    with pytest.raises(NotImplementedError):
        repository.delete_all()
