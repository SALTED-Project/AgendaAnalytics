import logging
import random
import re
import urllib.parse
from io import BytesIO
from typing import Annotated, Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from httpx import Response
from pydantic import AnyHttpUrl, BaseModel, Field, parse_obj_as, validate_arguments
from schemas.seaweed_file import File, SeaweedFileCreate

FILE_NAME_PATTERN_STR = r"[\w\.%_-]*\.?[a-zA-Z0-9]+"
FID_PATTERN_STR = r"\d+[,/][a-zA-Z0-9]+(_\d+)?"


class ServerResponseException(Exception):
    def __init__(
        self, status_code: int, status_message: Optional[str] = None, *args: object
    ) -> None:
        super().__init__(*args)
        self.status_code = status_code
        self.status_message = status_message


class MasterCredentials(BaseModel):
    url: str
    volume_url: str


class VolumeServerInformation(BaseModel):
    url: str = Field(description="The internal URL of the SeaweedFS volume server")
    publicUrl: str = Field(description="The public URL of the SeaweedFS volume server")


class AssignResponse(VolumeServerInformation):
    count: int = Field(description="The number of files uploaded")
    fid: str = Field(description="The SeaweedFS file id")


class UploadFileResponse(BaseModel):
    size: int = Field(description="The size of the file uploaded, in bytes")


class UploadFileDirectlyResponse(AssignResponse, UploadFileResponse):
    pass


class VolumeServerLookupResponse(BaseModel):
    locations: List[VolumeServerInformation] = Field(
        description="A list of volume server locations"
    )


class Master:
    """
    This class interfaces with the SeaweedFS Master component.
    """

    def __init__(self, credentials: MasterCredentials) -> None:
        self._logger = logging.getLogger(self.__class__.__name__)
        self.url = credentials.url 
        self.volume_url = credentials.volume_url
        self.client = httpx.AsyncClient

    def upload_file_directly(
        self, file: SeaweedFileCreate, **query_params: Dict[Any, Any]
    ) -> UploadFileDirectlyResponse:
        """
        Directly uploads a file. This is a convenience method to execute both
        :meth:`.assign_file_key` and :meth:`.upload_file` in sequence.

        :param file: the file to upload
        :param query_params: optional query parameters as used in :meth:`.assign_file_key` and :meth:`.upload_file`
        :return: the combined response as `UploadFileDirectlyResponse`
        :raises RuntimeError: if the file assignment key could not be requested or the file upload failed
        """
        assign_response = self.assign_file_key(**query_params)
        upload_response = self.upload_file(file, assign_response.fid, **query_params)

        return UploadFileDirectlyResponse(
            **{**assign_response.dict(), **upload_response.dict()}
        )

    @validate_arguments()
    def upload_file(
        self,
        file: SeaweedFileCreate,
        fid: Annotated[str, Field(regex=FID_PATTERN_STR)],
        **query_params: Dict[Any, Any],
    ) -> UploadFileResponse:
        """
        Uploads a file to the given volume server with the given file ID.
        See `<https://github.com/chrislusf/seaweedfs/wiki/Volume-Server-API#volume-server-writes>`_.

        :param file: the file to upload
        :param fid: the file ID returned from `Master.assign_file_key().fid`
        :param query_params: optional query parameters as described in
        https://github.com/chrislusf/seaweedfs/wiki/Volume-Server-API#volume-server-writes
        :return: the response wrapped as `UploadFileResponse`
        :raises ServerResponseException: if the file upload failed
        """

        # File IDs for uploads must use the format 3,01637037d6, otherwise the server returns
        # {"error":"Parse needleId error: needle id /3/01 format error: strconv.ParseUint:
        # parsing \"/3/01\": invalid syntax"}
        fid = fid.replace("/", ",")

        volume_server_locations = self._lookup_volume_server(fid)
        upload_url = (
            f"http://{self._pick_random_volume_server(volume_server_locations)}/{fid}"
        )

        query = urlencode(query_params)
        if query is not None and len(query) > 0:
            upload_url += f"?{query}"

        with httpx.Client(timeout=httpx.Timeout(None, connect=5.0)) as client:
            raw_response = client.post(
                upload_url,
                files={"file": (file.name, file.content)},
            )

        if self.response_is_ok(raw_response):
            upload_response = UploadFileResponse(**raw_response.json())
        else:
            raise ServerResponseException(
                raw_response.status_code,
                raw_response.text,
                f"Failed uploading file to {upload_url}. Status code: {raw_response.status_code}. Message: {raw_response.text}",
            )

        return upload_response

    def assign_file_key(self, **query_params: Dict[Any, Any]) -> AssignResponse:
        """
        Requests a file assignment key. SeaweedFS requires this call before a file can be uploaded.
        See https://github.com/chrislusf/seaweedfs/wiki/Master-Server-API#assign-a-file-key.

        :param query_params: optional query parameters as described in
        https://github.com/chrislusf/seaweedfs/wiki/Master-Server-API#assign-a-file-key
        :return: the response wrapped as `AssignResponse`
        :raises ServerResponseException: if the file assignment key could not be requested
        """
        assign_url = f"{self.url}/dir/assign"
        query = urlencode(query_params)
        if query is not None and len(query) > 0:
            assign_url += f"?{query}"

        raw_response = httpx.get(assign_url)

        if self.response_is_ok(raw_response):
            assign_response = AssignResponse(**raw_response.json())
        else:
            raise ServerResponseException(
                raw_response.status_code,
                raw_response.text,
                f"Failed getting file assignment from {assign_url}",
            )

        return assign_response

    @staticmethod
    def response_is_ok(response: Response) -> bool:
        return response.status_code in range(200, 400)

    def _lookup_volume_server(self, fid: str) -> VolumeServerLookupResponse:
        """
        Performs a volume server lookup using the given SeaweedFS file ID.

        :param fid: the file ID to perform the lookup with
        :return: the response wrapped as `VolumeServerLookupResponse`
        """
        if not self.is_fid(fid):
            raise ValueError(
                f"{fid} is not a valid SeaweedFS file ID, should match 3,01637037d6 3/01637037d6 or 3,01637037d6_1"
            )

        if "," in fid:
            # Format: 3,01637037d6
            volume_id = fid.split(",")[0]
        else:
            # Format: 3/01637037d6
            volume_id = fid.split("/")[0]

        lookup_url = f"{self.url}/dir/lookup?volumeId={volume_id}"
        raw_response = httpx.get(lookup_url)

        if self.response_is_ok(raw_response):
            lookup_response = VolumeServerLookupResponse(**raw_response.json())
        else:
            raise ServerResponseException(
                raw_response.status_code,
                raw_response.text,
                f"Failed looking up volume using URL {lookup_url}",
            )

        return lookup_response
    
    
    def _lookup_volumes(self) -> List:
        """
        Performs a volume server lookup.

        :return: the response wrapped as List 
        """
        
        lookup_url = f"{self.volume_url}/status"
        raw_response = httpx.get(lookup_url)

        if self.response_is_ok(raw_response):
            lookup_response = raw_response.json()
        else:
            raise ServerResponseException(
                raw_response.status_code,
                raw_response.text,
                f"Failed looking up volumes using URL {lookup_url}",
            )

        return lookup_response
    

    @staticmethod
    def _pick_random_volume_server(candidates: VolumeServerLookupResponse) -> str:
        """
        Given a `VolumeServerLookupResponse`, returns a random volume server URL from the available locations.

        :param candidates: the `VolumeServerLookupResponse`
        :return: a random volume server URL
        """
        return candidates.locations[random.randrange(0, len(candidates.locations))].url
    
     

    @staticmethod
    def is_fid(fid: str) -> bool:
        """
        Checks if the given str is a SeaweedFS file ID.

        :param fid: the str to check
        :return: True if the given str is a SeaweedFS file ID, otherwise False
        """
        return re.fullmatch(FID_PATTERN_STR, fid) is not None

    @validate_arguments
    def get_file(
        self,
        fid: Annotated[str, Field(regex=FID_PATTERN_STR)],
        preferred_file_name: Annotated[
            Optional[str], Field(regex=FILE_NAME_PATTERN_STR)
        ] = None,
        **query_params: Dict[Any, Any],
    ) -> File:
        """
        Returns the file using the given SeaweedFS file ID.

        :param fid: the SeaweedFS file ID used to retrieve the file
        :param preferred_file_name: the preferred file name to assign to the retrieved file
        :param query_params: optional query parameters as described in
        https://github.com/chrislusf/seaweedfs/wiki/Volume-Server-API#volume-server-reads
        :return: the file
        """
        volume_server_locations = self._lookup_volume_server(fid)
        full_url = (
            f"http://{self._pick_random_volume_server(volume_server_locations)}/{fid}"
        )

        file_name = "file"
        if preferred_file_name is not None:
            preferred_file_name_quoted = urllib.parse.quote(preferred_file_name)
            # URLs with a preferred file name require the SeaweedFS FID part to use slashes instead of commas
            full_url = f"{full_url.replace(',', '/')}/{preferred_file_name_quoted}"
            file_name = preferred_file_name

        query = urlencode(query_params)
        if query is not None and len(query) > 0:
            full_url += f"?{query}"

        raw_response = httpx.get(full_url)

        if self.response_is_ok(raw_response):
            return File(
                name=file_name,
                content=BytesIO(raw_response.content),
                url=parse_obj_as(AnyHttpUrl, full_url),
            )
        else:
            raise ServerResponseException(
                raw_response.status_code,
                raw_response.text,
                f"Failed getting file from {full_url}",
            )

    @validate_arguments
    def delete_file(self, fid: Annotated[str, Field(regex=FID_PATTERN_STR)]) -> File:
        """
        Deletes the file given by the SeaweedFS file ID and returns the deleted file.

        :param fid: the SeaweedFS file ID used to delete the file
        :return: the deleted file
        """
        volume_server_locations = self._lookup_volume_server(fid)

        for volume_server in volume_server_locations.locations:
            full_url = f"http://{volume_server.url}/{fid}"
            file_to_delete = self.get_file(fid)
            raw_response = httpx.delete(full_url)

            if not self.response_is_ok(raw_response):
                raise ServerResponseException(
                    raw_response.status_code,
                    raw_response.text,
                    f"Failed deleting file at {full_url}",
                )

        return file_to_delete
