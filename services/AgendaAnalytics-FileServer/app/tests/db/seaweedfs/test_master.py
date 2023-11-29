from io import BytesIO

import pytest
from db.seaweedfs.master import Master, MasterCredentials, ServerResponseException
from schemas.seaweed_file import File


@pytest.fixture()
def master(seaweed_master_credentials: MasterCredentials) -> Master:
    return Master(credentials=seaweed_master_credentials)


@pytest.mark.dependency(depends=["test_assign_file_key", "test_upload_file"])
def test_upload_file_directly(master: Master) -> None:
    file_content = b'{"test": 123}'
    file = File(name="Test.json", content=BytesIO(file_content))

    response = master.upload_file_directly(file)

    assert None is not response, "should return a response"
    assert 1 == response.count, "should assign 1 file only"
    assert None is not response.fid, "fid should exist"
    assert (
        "salted_fileserver_seaweedfs-volume:8080" == response.url
    ), "should return the internal volume server hostname:port"
    assert (
        len(file_content) == response.size
    ), "file size on server should be the same as local"
    # clean up
    del_file = master.delete_file(response.fid)
    assert ServerResponseException is not del_file


@pytest.mark.dependency(depends=["test_assign_file_key"])
def test_upload_file(master: Master) -> None:
    file_content = b'{"test": 123}'
    file = File(name="Test.json", content=BytesIO(file_content))

    file_key = master.assign_file_key()
    response = master.upload_file(file=file, fid=file_key.fid)

    assert None is not response, "should return a response"
    assert (
        len(file_content) == response.size
    ), "file size on server should be the same as local"
    # clean up
    del_file = master.delete_file(file_key.fid)
    assert ServerResponseException is not del_file


@pytest.mark.dependency()
def test_assign_file_key(master: Master) -> None:
    response = master.assign_file_key()

    assert None is not response, "should return a response"
    assert 1 == response.count, "should assign 1 file only"
    assert (
        "salted_fileserver_seaweedfs-volume:8080" == response.url
    ), "should return the internal volume server hostname:port"


@pytest.mark.dependency(depends=["test_upload_file_directly"])
def test_get_file(master: Master) -> None:
    file = File(name="Test.json", content=BytesIO(b'{"test": 123}'))

    upload_response = master.upload_file_directly(file)
    file_to_check = master.get_file(
        fid=upload_response.fid, preferred_file_name=file.name
    )

    full_url = f"http://{upload_response.url}/{upload_response.fid.replace(',', '/')}/{file.name}"
    assert None is not file_to_check, "should return a file response"
    assert (
        file.name == file_to_check.name
    ), "file name on server should be the same as local"
    assert full_url == file_to_check.url, "the file URL should not change"
    # clean up
    del_file = master.delete_file(upload_response.fid)
    assert ServerResponseException is not del_file


@pytest.mark.dependency(depends=["test_upload_file_directly", "test_get_file"])
def test_delete_file(master: Master) -> None:
    file = File(name="Test.json", content=BytesIO(b'{"test": 123}'))

    upload_response = master.upload_file_directly(file)

    assert ServerResponseException is not upload_response
    assert None is not master.get_file(upload_response.fid)

    master.delete_file(upload_response.fid)

    with pytest.raises(ServerResponseException):
        master.get_file(upload_response.fid)


