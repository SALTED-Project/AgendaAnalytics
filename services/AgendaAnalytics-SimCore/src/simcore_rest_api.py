##########################################################################################
###  FastAPI application can be started with uvicorn main:app --reload
###  where "main" is the name of the containing Python file and app is the object within
### the main file holding the FastAPI instance.
### localhost:XXXXX/openapi.json returns a generated API description of the implemented
### API.
##########################################################################################

import os
import logging
from io import BytesIO

import uvicorn
from fastapi import FastAPI, Depends, File, UploadFile
from fastapi.responses import FileResponse

from simcore_api_schema_mod import SCResponse, Status
from handlers.token_handler_mod import TokenHandler
from handlers.dispatcher_mod import Dispatcher

logging.basicConfig(
    filename=os.path.join("./simcore_events.log"),
    filemode="a",
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    level=logging.INFO,
)
logger = logging.getLogger(os.path.basename(__file__))

#
# instantiate dispatcher and collect methods
#
disp = Dispatcher()
custom_methods = [method_name for method_name in dir(disp) if callable(getattr(disp, method_name))]
custom_methods = [x for x in custom_methods if not x.startswith("__")]

#
# instantiate token handler and collect methods
#
th = TokenHandler()
token_methods = [method_name for method_name in dir(th) if callable(getattr(th, method_name))]
token_methods = [x for x in token_methods if not x.startswith("__")]

#
# combine the method lists
#
custom_methods += token_methods

#
# return non-func structure in case of valid/invalid token
#
SuccessTokenValidation = (Status.SUCCESS, "valid token", {})
FailedTokenValidation = (Status.FAILED, "invalid token", {})

#
# definitions to make the appearance of the API endpoints well structured and clear
#
tags_metadata = [
    {
        "name": "system",
        "description": "Root entry point for completeness. No specific functionality",
    },
    {
        "name": "tasks",
        "description": "Start and stop token-based projects. Open task issues a token for all remaining operations"
    },
    {
        "name": "config",
        "description": "Set type of NLP processing and visualization",
    },
    {
        "name": "status",
        "description": "Obtain list of active projects and specific information on projects",
    },
    {
        "name": "upload",
        "description": "Text and reference file upload into an active project",
    },
    {
        "name": "analysis",
        "description": "Start similarity analysis based on transformer models",
    },
    {
        "name": "downloads",
        "description": "Download generated files from an active task",
    },
]

app = FastAPI(
    title="SimCore REST API",
    description="NLP Service to compute document similarities with transformers",
    version="0.1.0",
    openapi_tags=tags_metadata
    # removed server spec, because of CORS error for VM deployment
    #,
    # servers=[
    #     {
    #         "url": "http://localhost:9060",
    #         "description": "SimCore Server"
    #     }
    # ]
)


################################################################################
#
# root entry point. Just returns a json welcome message.
#
@app.get("/", tags=["system"])
async def root_entry():
    return {"message": "****** REST API SimCore ******"}


################################################################################
#
# endpoint for opening a task. Here a token will be issued and the
# folder generated.
#
@app.get("/open_task", tags=["tasks"])
async def open_task() -> SCResponse:

    assert "issue_token" in custom_methods
    assert "create_project" in custom_methods
    #
    # first issue a token, then create a project with the
    # name of the token. A folder with the token string is 
    # generated under /projects but this time this folder
    # is deleted immediately once the token gets invalidated.
    # *** If the folder can not be generated for some reason
    # we have to revoke the token immediately in order
    # to avoid inconsistencies!
    #
    token = th.issue_token()

    s, m, d = disp.create_project(token)

    if s == Status.SUCCESS:
        m = m + " Task activated."
        d = {"token":token}
        logger.info(f"Task with token {token} activated.")
    else:
        d = {"token":''}
        rtoken = th.remove_token(token)
        if rtoken != token:
            raise ValueError ("** internal error E065 **")
        logger.error(f"Task folder could bot be generated.")
    return SCResponse(status=s, message=m, details=d)


################################################################################
#
# endpoint for closing a task. If the running status is terminated then the
# token is revoked and the corresponding folder/subfolder is deleted.
#
@app.get("/close_task/{token}", tags=["tasks"])
async def close_task(checked = Depends(th.check_token)) -> SCResponse:

    assert "purge_project" in custom_methods

    token, valid = checked
    print(token, valid)
    if not valid:
        s, m, d = FailedTokenValidation
    else:
        rtoken = th.remove_token(token)
        if rtoken != token:
            s = Status.FAILED
            m = f"Internal token handling error: {token} not under control"
            d = {}
        else:
            s, m, d = disp.purge_project(token)

    return SCResponse(status=s, message=m, details=d)

################################################################################
#
# endpoint for setting the kind of NLP processing (use case specific)
# Corresponding routines are provided by the SimCore developers. In the token-based
# environment we have to persist the requested NLP processing in the corresponding
# folders and decide in the moment of analysis execution.
#
@app.post("/set_analyzer/{token}", tags=["config"])
async def set_analyzer(analyzer: str, checked = Depends(th.check_token)) -> SCResponse:

    token, valid = checked
    print(token, valid)
    if not valid:
        s, m, d = FailedTokenValidation
    else:
        assert "set_analyzer" in custom_methods
        s, m, d = disp.set_analyzer(token, analyzer)

    return SCResponse(status=s, message=m, details=d)


################################################################################
#
# endpoint for setting the kind of NLP processing (use case specific)
# Corresponding routines are provided by the SimCore developers 
#
@app.post("/set_visualizer/{token}", tags=["config"])
async def set_visualizer(sc_visualizer: str, checked = Depends(th.check_token)) -> SCResponse:

    token, valid = checked
    print(token, valid)
    if not valid:
        s, m, d = FailedTokenValidation
    else:
        assert "set_visualizer" in custom_methods
        s, m, d = disp.set_visualizer(token, sc_visualizer)

    return SCResponse(status=s, message=m, details=d)


################################################################################
#
# endpoint for a list of all active tasks
#
@app.get("/get_active_tasks", tags=["status"])
async def get_active_tasks() -> SCResponse:

    assert "get_active_tasks" in custom_methods

    tasks = th.get_active_tasks()
    s = Status.SUCCESS
    m = "collected all active tasks"
    d = {"active":tasks}
    return SCResponse(status=s, message=m, details=d)


################################################################################
#
# endpoint for setting the kind of NLP processing (use case specific)
# Corresponding routines are provided by the SimCore developers 
#
@app.get("/list_task_files/{token}", tags=["status"])
async def list_task_files(checked = Depends(th.check_token)) -> SCResponse:

    token, valid = checked
    print(token, valid)
    if not valid:
        s, m, d = FailedTokenValidation
    else:
        assert "list_task_files" in custom_methods
        s, m, d = disp.list_task_files(token)

    return SCResponse(status=s, message=m, details=d)


################################################################################
#
# 2 entry points for uploading reference and analysis texts.
# The information of the project name is transferred
# as a >path parameter< in the URL:
# post .... localhost:XXXX/create/project_name
#
# The file upload occurs via the parameter ufile:UploadFile...
#
# A corresponding curl call to address this endpoint with project name and file upload
# would be:
#
# curl -i -F "ufile=@/home/user/company_text.txt" localhost:7705/create/demoproject
#
# keep in mind that the parameter name in the function and in the curl must be identical
# otherwise a 422 unprocessable error will occur.
#
# we need to utilize a buffer since generating a temporary file in the container
# with "non-root" permissions is not possible.
#
@app.post("/upload_text/{token}", tags=["upload"])
async def upload_text(ufile: UploadFile = File(...),
                      checked = Depends(th.check_token)) -> SCResponse:

    token, valid = checked
    print(token, valid)
    if not valid:
        s, m, d = FailedTokenValidation
    else:
        assert "upload_text" in custom_methods
        #
        # get filename and data from ufile
        #
        textfilename = ufile.filename
        buf = BytesIO(await ufile.read())
        s, m, d = disp.upload_text(token, textfilename, buf, is_reference=False)

    return SCResponse(status=s, message=m, details=d)


################################################################################
#
# same for uploading reference. An additional flag is set that indicates that the
# file uploaded by this endpoint should go into the reference folder.
#
@app.post("/upload_reference/{token}", tags=["upload"])
async def upload_reference(ufile: UploadFile = File(...),
                      checked = Depends(th.check_token)) -> SCResponse:

    token, valid = checked
    print(token, valid)
    if not valid:
        s, m, d = FailedTokenValidation
    else:
        assert "upload_text" in custom_methods
        #
        # get filename and data from ufile
        #
        reffilename = ufile.filename
        buf = BytesIO(await ufile.read())
        s, m, d = disp.upload_text(token, reffilename, buf, is_reference=True)

    return SCResponse(status=s, message=m, details=d)


################################################################################
#
# endpoint for starting the similarity analysis. The files to be analyzed are not
# given explicitly because all files uploaded to the project folder will be analyzed
# and the result returned
#
@app.get("/analyze_project/{token}", tags=["analysis"])
async def analyze_project(checked = Depends(th.check_token)) -> SCResponse:

    token, valid = checked
    print(token, valid)
    if not valid:
        s, m, d = FailedTokenValidation
    else:
        assert "analyze_project" in custom_methods
        s, m, d = disp.analyze_project(token)   # NLP config is read from current folder!

    return SCResponse(status=s, message=m, details=d)


################################################################################
#
# endpoint for starting the similarity analysis. The files to be analyzed are not
# given explicitly because all files uploaded to the project folder will be analyzed
# and the result returned
#
@app.get("/visualize_project/{token}", tags=["analysis"])
async def visualize_project(checked = Depends(th.check_token)) -> SCResponse:

    token, valid = checked
    print(token, valid)
    if not valid:
        s, m, d = FailedTokenValidation
    else:
        assert "visualize_project" in custom_methods
        s, m, d = disp.visualize_project(token)  # VIS is read from current folder!

    return SCResponse(status=s, message=m, details=d)


################################################################################
#
# endpoint for downloading files that are given by an absolute path
#
@app.post("/download_file/{token}", tags=["downloads"])
async def download_file(afilepath: str, checked = Depends(th.check_token)) -> FileResponse:

    token, valid = checked
    print(token, valid)
    if not valid:
        s, m, d = FailedTokenValidation
        return None
    else:
        assert "download_file" in custom_methods
        s, m, d = disp.download_file(afilepath)
        print(m)
    if s != Status.SUCCESS:
        return None

    return FileResponse(path=d["file_location"], 
                        media_type=d["media_type"],
                        filename=d["filename"])


################################################################################
#
# main
#
if __name__ == "__main__":
    logger.info("*** SimCore REST interface started ***")
    uvicorn.run(app, host="0.0.0.0", port=9060, workers=1)
