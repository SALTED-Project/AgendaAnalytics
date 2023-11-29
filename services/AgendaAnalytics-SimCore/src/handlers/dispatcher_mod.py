# - standard imports

import glob
import logging
import os
import string
import random
from dynaconf import settings

# - interfaces

from interfaces.handler_interface_mod import HandlerInterface
from interfaces.visualizer_interface_mod import VisualizerInterface

# - analysis modules

from handlers.coarse_handler_mod import CoarseHandler
from handlers.detailed_handler_mod import DetailedHandler

# - visualization modules

from visualizers.coarse_visualizer_mod import CoarseVisualizer
from visualizers.detailed_visualizer_mod import DetailedVisualizer

# - schema definitions

from simcore_api_schema_mod import Status

# - handler classes

NLP_handlers = {"coarse": CoarseHandler,
                "detailed":DetailedHandler,
                }

# - visualizer classes

Visualizers = {"coarse": CoarseVisualizer,
               "detailed":DetailedVisualizer,
                }

logger = logging.getLogger(os.path.basename(__file__))

#
# get root of projects (externally configured)
#
PROJECTFOLDER = settings.PROJECTFOLDER
REFFOLDERNAME = settings.REFFOLDERNAME
ANAFOLDERNAME = settings.ANAFOLDERNAME
RESFOLDERNAME = settings.RESFOLDERNAME


class Dispatcher:

    def __init__(self):
        """
        Initialize Dispatcher class that takes calls from the REST API and distributes
        task accordingly
        """
    
    # ---------------------------------------------------------------------------
    def create_project(self, project):

        dir_project = os.path.join(PROJECTFOLDER, project)
        try:
            # project folder
            os.makedirs(dir_project, exist_ok=False)
            # reference folder
            dir_reference = os.path.join(dir_project, REFFOLDERNAME)
            os.makedirs(dir_reference)
            # analysis folder
            dir_reference = os.path.join(dir_project, ANAFOLDERNAME)
            os.makedirs(dir_reference)
            # result folder
            dir_reference = os.path.join(dir_project, RESFOLDERNAME)
            os.makedirs(dir_reference)

            s = Status.SUCCESS
            m = "Temporary folders generated."
            d = {}
        except Exception as e:
            s = Status.FAILED
            m = f"Problem with temporary file structure: {e}"
            d = {}
        return s, m, d

    # ---------------------------------------------------------------------------
    def purge_project(self, project):
        dir_project = os.path.join(PROJECTFOLDER, project)
        if os.path.exists(dir_project):
            #
            # we do not recursively remove the tree but deactivate it
            # by prefixing the name with "$$$"
            # shutil.rmtree(dir_project)
            # Recursive delete is very dangerous in case of wrongly
            # initialized path variables and can destroy user data.
            # Only activate this if you have totally 
            # separated file systems (e.g. in a Docker container) 
            #
            nonce = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase, k=40))
            nonce = "$$$" + nonce
            deac_project_name = os.path.join(PROJECTFOLDER, nonce)
            os.rename(dir_project, deac_project_name)
            s = Status.SUCCESS
            m = f"Project {project} deactivated"
            d = {}
        else:
            s = Status.FAILED
            m = f"Internal error: project folder {project} does not exist!"
            d = {}
        return s, m, d

    
    # ---------------------------------------------------------------------------
    def set_analyzer(self, token, sc_usecase):
        if sc_usecase not in NLP_handlers:
            avail_usecases = ", ".join(list(NLP_handlers.keys()))
            details = {"available":avail_usecases}
            return Status.FAILED, f"NLP analyzer {sc_usecase} not implemented", details
        else:
            dir_project = os.path.join(PROJECTFOLDER, token, "nlp.conf")
            with open(dir_project, "w") as f:
                f.write(sc_usecase)
            return Status.SUCCESS, f"NLP analyzer set to {sc_usecase}", {}

    # ---------------------------------------------------------------------------
    def set_visualizer(self, token, sc_visualizer):
        if sc_visualizer not in Visualizers:
            avail_usecases = ", ".join(list(Visualizers.keys()))
            details = {"available":avail_usecases}
            return Status.FAILED, f"Visualizer {sc_visualizer} not implemented", details
        else:
            dir_project = os.path.join(PROJECTFOLDER, token, "vis.conf")
            with open(dir_project, "w") as f:
                f.write(sc_visualizer)
            return Status.SUCCESS, f"Visualizer set to {sc_visualizer}", {}

    # ---------------------------------------------------------------------------
    def list_task_files(self, project):

        dir_project = os.path.join(PROJECTFOLDER, project)

        if os.path.exists(dir_project):

            results = []
            for path in glob.glob(f"{dir_project}/**/*", recursive=True):
                if not os.path.isdir(path):
                    results.append(path)

            s = Status.SUCCESS
            m = f"Files of task {project}"
            d = {"files": results}

        else:

            s = Status.FAILED
            m = f"Project {project} doess not exist"
            d = {}

        return s, m, d

    # ---------------------------------------------------------------------------
    def upload_text(self, project, textfilename, buf, is_reference=False):

        if is_reference:
            targetfolder = os.path.join(PROJECTFOLDER, project, REFFOLDERNAME)
        else:
            targetfolder = os.path.join(PROJECTFOLDER, project, ANAFOLDERNAME)

        if not os.path.exists(targetfolder):
            s = Status.FAILED
            m = f"Destination {targetfolder} does not exist. Was the project generated?"
            d = {}
            return s, m, d

        target = os.path.join(targetfolder, textfilename)
        try:
            with open(target, "wb") as fh:
                fh.write(buf.getbuffer())
            s = Status.SUCCESS
            m = f"File {textfilename} copied to destination {target}"
            d = {}
        except Exception as e:
            s = Status.FAILED
            m = f"Problem uploading {textfilename}: {e}"
            d = {}
        return s, m, d

    # ---------------------------------------------------------------------------
    def analyze_project(self, project):
        dir_project = os.path.join(PROJECTFOLDER, project)

        if not os.path.exists(dir_project):
            s = Status.FAILED
            m = f"Project {project} does not exist"
            d = {}
            return s, m, d

        sc_usecase = "coarse"
        nlp_config_file = os.path.join(dir_project, "nlp.conf")
        if os.path.exists(nlp_config_file):
            with open(nlp_config_file, "r") as f:
                sc_usecase = f.read()
        #
        # invoke specific handler through interface
        # that deals with the specific analysis
        #
        print(f"NLP handler >{sc_usecase}< was selected")
        hi = HandlerInterface(NLP_handlers[sc_usecase])
        s, m, d = hi.analyze_project(dir_project)
        return s, m, d

    # ---------------------------------------------------------------------------
    def visualize_project(self, project):
        dir_project = os.path.join(PROJECTFOLDER, project)

        if not os.path.exists(dir_project):
            s = Status.FAILED
            m = f"Project {project} does not exist"
            d = {}
            return s, m, d
        
        sc_visualizer = "coarse"
        vis_config_file = os.path.join(dir_project, "vis.conf")
        if os.path.exists(vis_config_file):
            with open(vis_config_file, "r") as f:
                sc_visualizer = f.read()

        #
        # invoke specific visualizer through interface
        # that reads the pandas dataframes
        # generated by the NLP analysis module.
        #
        vi = VisualizerInterface(Visualizers[sc_visualizer])
        s, m, d = vi.visualize_project(dir_project)
        return s, m, d

    # ---------------------------------------------------------------------------
    def download_file(self, absfilename):
        if not os.path.exists(absfilename):
            s = Status.FAILED
            m = f"File {absfilename} not found in task."
            d = {}
        else:
            s = Status.SUCCESS
            m = f"File {absfilename} found."
            onlyfilename = os.path.basename(absfilename)
            d = {
                "file_location": absfilename,
                "media_type": "application/octet-stream",
                "filename": onlyfilename,
            }
        return s, m, d

    