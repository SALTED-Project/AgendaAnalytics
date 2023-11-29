import mimetypes
from typing import Any, List
import os
import urllib

from api import deps
from db.file_repository import HttpFileRepository
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from prisma import Prisma, models
from pydantic import AnyHttpUrl, parse_obj_as

from schemas import seaweed_file
from schemas.error_message import ErrorMessage
from schemas.seaweed_file import SeaweedFileCreate

router = APIRouter()




@router.get(
    "/{uuid}",
    summary="Returns a single file by its UUID (ref by metadata storage).",
    response_class=StreamingResponse,
    responses={
        404: {"model": ErrorMessage, "description": "The file was not found"},
        200: {
            "description": "The file denoted by the UUID",
            "content": {
                "application/octet-stream": {"type": "string", "format": "binary"}
            },
        },
    },
    name="files:get_file",
)
async def get_file(
    *,
    uuid: str,
    db_client: Prisma = Depends(deps.db_client),
    file_repo: HttpFileRepository = Depends(deps.file_repository),
) -> Any:
    """
    Returns a single file by its UUID (ref by metadata storage).
    """

    file_ref = await db_client.file.find_unique(where={"uuid": uuid})

    if file_ref is None:
        return JSONResponse(
            status_code=404,
            content={"message": "The file does not exist in the metadata storage."},
        )

    file = file_repo.get(parse_obj_as(AnyHttpUrl, file_ref.url))

    if file is None:
        return JSONResponse(
            status_code=404,
            content={"message": "The file does not exist in the metadata storage but not in the file storage."},
        )

    return StreamingResponse(
        file.content,
        headers={"Content-Disposition": f'attachment; filename="{file_ref.name}"'},
        media_type="application/octet-stream",
    )


@router.get(
    "/",
    summary="Returns all files within the metadata storage and the file storage.",
    response_class=JSONResponse,
    responses={
        404: {"model": ErrorMessage, "description": "No files were found"},
        200: {
            "description": "The files denoted by seaweed keys (+name)",
            "content": {
                "application/json": {"files_seaweed_num": "string", "files_mongo_num": "string","files_seaweed": "list", "files_mongo":"list"}
            },
        },
    },
    name="files:get_all_files",
)
async def get_all_files(
    *,
    safety_password: str,
    file_repo: HttpFileRepository = Depends(deps.file_repository),
    db_client: Prisma = Depends(deps.db_client),
) -> Any:
    """
    Returns all files within the metadata storage and the file storage.
    """    
    # to enable some sort of safety net against unwillingly deleting all files
    ENDPOINT_PASSWORD = os.environ.get("ENDPOINT_PASSWORD")
    if safety_password == ENDPOINT_PASSWORD:

        files_seaweed = file_repo.get_all()
        files_mongo_objects = await db_client.file.find_many()
        files_mongo=[]
        if files_mongo_objects != None:
            for file in files_mongo_objects:
                files_mongo.append(file.url)        

        return JSONResponse(
            status_code=200,
                content={"files_seaweed_num": len(files_seaweed), "files_mongo_num": len(files_mongo),"files_seaweed": files_seaweed, "files_mongo": files_mongo},
            )
        
    else:
        return JSONResponse(
            status_code=401,
            content={"message": "Unauthorized."}
            )  



@router.post(
    "/",
    summary="Uploads one or multiple files directly.",
    response_model=List[str],
    name="files:upload_files",
)
async def upload_files(
        *,
        db_client: Prisma = Depends(deps.db_client),
        file_repo: HttpFileRepository = Depends(deps.file_repository),
        file: List[UploadFile] = File(...),
) -> List[str]:
    """
    Uploads one or multiple files directly and returns assigned UUIDs.
    """

    uploaded_files: List[str] = []

    for _file in file:
        # Creating a file entry is a two-step process:
        # 1. We upload the file to our external file repository (SeaweedFS)
        uploaded_file: seaweed_file.File = file_repo.create(
            SeaweedFileCreate(name=_file.filename, content=_file.file)
        )

        # 2. We create a metadata entry in our internal file reference repository (MongoDB)
        file_reference: models.File = await db_client.file.create(
            {"name": _file.filename, "url": uploaded_file.url, "encodingFormat": _file.content_type}
        )

        uploaded_files.append(file_reference.uuid)

    return uploaded_files


@router.delete(
    "/{uuid}",
    summary="Deletes a single file by its UUID.",
    response_class=StreamingResponse,
    responses={
        404: {"model": ErrorMessage, "description": "The file was not found"},
        200: {
            "description": "The file denoted by the UUID, which is now deleted.",
            "content": {
                "application/octet-stream": {"type": "string", "format": "binary"}
            },
        },
    },
    name="files:delete_file",
)
async def delete_file(
        *,
        uuid: str,
        db_client: Prisma = Depends(deps.db_client),
        file_repo: HttpFileRepository = Depends(deps.file_repository),
) -> Any:
    """
    Deletes a single file by its UUID.
    """

    file_ref = await db_client.file.find_unique(where={"uuid": uuid})

    if file_ref is None:
        return JSONResponse(
            status_code=404,
            content={"message": "The file does not exist in the metadata storage."},
        )
    try:
        file = file_repo.delete(parse_obj_as(AnyHttpUrl, file_ref.url))

        # in case the mongodb entry should not be deleted without notice of missing file storage entry
        # if file is None:
        #     return JSONResponse(
        #         status_code=404,
        #         content={"message": "The file does not exist in the file storage."},
        #     ) 

        file_ref_del = await db_client.file.delete(where={"uuid": uuid})

        return StreamingResponse(
            file.content,
            headers={"Content-Disposition": f'attachment; filename="{file_ref.name}"'},
            media_type="application/octet-stream",
        )
    except:
        return JSONResponse(
                status_code=500,
                content={"message": "Internal Error. Maybe the reference of metadata does not point to valid volume server location."},
            )     

@router.delete(
    "/",
    summary="Deletes all files that are referenced in metadata storage from all systems.",
    #response_model=JSONResponse,   # throws error, see: https://github.com/tiangolo/fastapi/issues/5861
    responses={
        401: {"model": ErrorMessage, "description": "Unauthorized."},
        404: {"model": ErrorMessage, "description": "No files exist in the system."},
        200: {
            "description": "The files denoted by the UUID, which are now deleted.",
            "content": {
                "application/json": {"zombies_within_deleted": "string", "deleted": "list", "error": "string"}
            },
        },
    },
    name="files:delete_all_files_ref_mongo",
)
async def delete_all_files_ref_mongo(
        *,
        safety_password: str,
        db_client: Prisma = Depends(deps.db_client),
        file_repo: HttpFileRepository = Depends(deps.file_repository),
) -> Any:
    """
    Deletes all files that have metadata entry in mongodb.
    """
    # to enable some sort of safety net against unwillingly deleting all files
    ENDPOINT_PASSWORD = os.environ.get("ENDPOINT_PASSWORD")
    if safety_password == ENDPOINT_PASSWORD:
        
        file_refs = await db_client.file.find_many()
        print(file_refs)
        if file_refs is None:
            return JSONResponse(
                status_code=404,
                content={"message": "No files exist in the metadata storage."},
            )        
        zombie_files=[]
        response_files=[]
        error_files=[]
        for file_ref in file_refs:
            try:
                file = file_repo.delete(parse_obj_as(AnyHttpUrl, file_ref.url))
                if file is None:
                    zombie_files.append(file_ref.name)                       
                file_ref_del = await db_client.file.delete(where={"uuid": file_ref.uuid})
                response_files.append(file_ref.name)
            except:
                error_files.append(file_ref.name)
                continue
        return JSONResponse(
            status_code=200,
            content={"zombies_within_deleted": zombie_files, "deleted":response_files, "error": error_files},
            )     
    else:
        return JSONResponse(
            status_code=401,
            content={"message": "Unauthorized."}
            )     


@router.delete(
    "/sync/",
    summary="Sync files in seaweedfs and mongodb and perform clean up.",
    #response_model=JSONResponse,    # throws error, see: https://github.com/tiangolo/fastapi/issues/5861
    responses={
        200: {
            "description": "Sync successfull",
            "content": {
                "application/json": {"deleted_zombies_seaweed": "string", "deleted_zombies_mongodb": "string", "error": "string"}
            },
        },
    },
    name="files:sync_mongo_seaweedfs_delete",
)
async def sync_mongo_seaweedfs_delete(
        *,
        safety_password: str,
        db_client: Prisma = Depends(deps.db_client),
        file_repo: HttpFileRepository = Depends(deps.file_repository),
) -> Any:
    """
    Sync files in seaweedfs and mongodb and perform clean up.
    """

    # to enable some sort of safety net 
    ENDPOINT_PASSWORD = os.environ.get("ENDPOINT_PASSWORD")
    if safety_password == ENDPOINT_PASSWORD:

        # get all files in the system
        response_files = await get_all_files(file_repo= file_repo, db_client=db_client, safety_password=safety_password)
        from fastapi.encoders import jsonable_encoder
        import json
        response_content = json.loads(jsonable_encoder(response_files.body)) #jsonable_encoder(response_files)["body"]

        # separate into files from mongodb and seaweedfs
        files_seaweed = response_content["files_seaweed"]
        # augment encoded file names
        files_seaweed = [urllib.parse.unquote(item) for item in files_seaweed]

        files_mongo = response_content["files_mongo"]
        # augment encoded file names
        files_mongo = [urllib.parse.unquote(item) for item in files_mongo]

        # identify differences
        files_diff_sea = set(files_seaweed)-(set(files_mongo)) 
        files_diff_mongo = set(files_mongo)-(set(files_seaweed))    

        deleted_zombies_sea=[]
        deleted_zombies_mongo=[]
        error_files=[]
        # delete diff that is only in seaweed
        for file_url in files_diff_sea:
            try:
                file = file_repo.delete(parse_obj_as(AnyHttpUrl, file_url))
                deleted_zombies_sea.append(file_url)
            except:
                error_files.append(file_url)

        # delete diff that is only in mongo
        for file_url in files_diff_mongo:
            print(file_url)
            try:
                ref_del = await db_client.file.delete_many(where={"url": file_url})
                deleted_zombies_mongo.append(file_url)
            except Exception as e :
                print(e)
                error_files.append(file_url)
        
        return JSONResponse(
            status_code=200,
            content={"deleted_zombies_seaweed": deleted_zombies_sea, "deleted_zombies_mongodb": deleted_zombies_mongo, "error": error_files},
            )    
        
    else:
        return JSONResponse(
            status_code=401,
            content={"message": "Unauthorized."}
            )     
    




@router.get(
    "/sync/",
    summary="Sync files in seaweedfs and mongodb for analysis.",
    #response_model=JSONResponse,    # throws error, see: https://github.com/tiangolo/fastapi/issues/5861
    responses={
        200: {
            "description": "Sync successfull",
            "content": {
                "application/json": {"proposed_for_deletion_zombies_seaweed": "string", "proposed_for_deletion_zombies_mongodb": "string"}
            },
        },
    },
    name="files:sync_mongo_seaweedfs",
)
async def sync_mongo_seaweedfs(
        *,
        safety_password: str,
        db_client: Prisma = Depends(deps.db_client),
        file_repo: HttpFileRepository = Depends(deps.file_repository),
) -> Any:
    """
    Sync files in seaweedfs and mongodb for analysis.
    """

    # to enable some sort of safety net 
    ENDPOINT_PASSWORD = os.environ.get("ENDPOINT_PASSWORD")
    if safety_password == ENDPOINT_PASSWORD:

        # get all files in the system
        response_files = await get_all_files(file_repo= file_repo, db_client=db_client, safety_password=safety_password)
        from fastapi.encoders import jsonable_encoder
        import json
        response_content = json.loads(jsonable_encoder(response_files.body)) #jsonable_encoder(response_files)["body"]

        # separate into files from mongodb and seaweedfs
        files_seaweed = response_content["files_seaweed"]
        # augment encoded file names
        files_seaweed = [urllib.parse.unquote(item) for item in files_seaweed]
        
        files_mongo = response_content["files_mongo"]
        # augment encoded file names
        files_mongo = [urllib.parse.unquote(item) for item in files_mongo]

        # identify differences
        files_diff_sea = list(set(files_seaweed)-(set(files_mongo)))
        files_diff_mongo = list(set(files_mongo)-(set(files_seaweed)))   
        
        return JSONResponse(
            status_code=200,
            content={"proposed_for_deletion_zombies_seaweed": files_diff_sea, "proposed_for_deletion_zombies_mongodb": files_diff_mongo},
            )    
        
    else:
        return JSONResponse(
            status_code=401,
            content={"message": "Unauthorized."}
            )     