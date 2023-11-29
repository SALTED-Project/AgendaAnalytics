import re
import urllib.parse
from typing import Iterable, Optional, Tuple
import json 

from db.file_repository import HttpFileRepository
from db.seaweedfs.master import (
    FID_PATTERN_STR,
    FILE_NAME_PATTERN_STR,
    Master,
    ServerResponseException,
)
from fastapi import Depends
from pydantic import AnyHttpUrl, parse_obj_as
from schemas.seaweed_file import File, SeaweedFileCreate, SeaweedFileUpdate

import docker


class SeaweedFileRepository(HttpFileRepository):
    def __init__(self, master: Master = Depends(dependency=Master)) -> None:
        super().__init__(File)
        self.master: Master = master

    def create(self, obj_in: SeaweedFileCreate) -> File:
        upload_response = self.master.upload_file_directly(obj_in)
        response_url = (
            f"http://{upload_response.url}/{upload_response.fid}/{urllib.parse.quote(obj_in.name)}"
        )
        return File(**obj_in.dict(), url=parse_obj_as(AnyHttpUrl, response_url))

    def get(self, key: AnyHttpUrl) -> Optional[File]:
        url_path = self._validate_key_and_get_path(key)
        fid, file_name = self._get_fid_and_filename_from_path(url_path)

        try:
            return self.master.get_file(fid=fid, preferred_file_name=file_name)
        except ServerResponseException:
            return None

    def get_all(self) -> list:
        volumes = self.master._lookup_volumes()
        volume_ids = [item["Id"] for item in volumes["Volumes"]]
        client = docker.from_env()    
        container = client.containers.get("salted_fileserver_salted_fileserver_seaweedfs-volume_1")
        outputs = []
        for id in volume_ids:
            # print("----------------------------new volume id------------------------------")     
            exit_code, output = container.exec_run(f"weed export -dir=. -volumeId={id}", stream=False)
            # print(output.decode("utf-8").split('\n')) # list of each line
            # start at second line
            for i, line in enumerate(output.decode("utf-8").split('\n')):                
                if i in [0,1]:
                    #print("skipped lines of container output that shows files:")
                    #print(line)
                    continue
                else:     
                    #print("----------------------------new line------------------------------")               
                    cells = line.split('\t')
                    if cells != ['']:
                        try:
                            url_key = f"http://salted_fileserver_seaweedfs-volume:8080/{cells[0]}/{cells[1]}"
                            outputs.append(url_key)
                        except:
                            continue
        return outputs

    def update(self, key: AnyHttpUrl, obj_in: SeaweedFileUpdate) -> File:
        raise NotImplementedError()

    def delete(self, key: AnyHttpUrl) -> File:
        url_path = self._validate_key_and_get_path(key)
        fid, file_name = self._get_fid_and_filename_from_path(url_path)
        try:
            deleted_file = self.master.delete_file(fid)
            if file_name is not None:
                deleted_file.name = file_name
            return deleted_file
        except:
            return None

    def delete_all(self) -> Iterable[File]:
        raise NotImplementedError()

    @staticmethod
    def _get_fid_and_filename_from_path(url_path: str) -> Tuple[str, Optional[str]]:
        num_slashes = url_path.count("/")
        file_name: Optional[str] = None
        if num_slashes == 2:
            fid, file_name = url_path.rsplit("/", maxsplit=1)
        elif num_slashes == 1 and "," in url_path:
            fid, file_name = url_path.split("/", maxsplit=1)
            fid = fid.replace(",", "/")
        else:
            fid = url_path
        return fid, file_name

    @staticmethod
    def _validate_key_and_get_path(key: AnyHttpUrl) -> str:
        if key.path is None:
            raise ValueError(
                f"URL {key} has no path fragment which could denote a SeaweedFS file ID"
            )

        # URL path should match 3,01637037d6 3/01637037d6 or 3/01637037d6/my_file.json
        url_path = key.path.lstrip("/")
        if not re.fullmatch(f"{FID_PATTERN_STR}(/{FILE_NAME_PATTERN_STR})?", url_path):
            raise ValueError(
                f"URL {key} has wrong path fragment, should look like 3,01637037d6 or 3/01637037d6/my_file.json"
            )
        return url_path
