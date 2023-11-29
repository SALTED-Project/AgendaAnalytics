import requests
import datetime
import json
import time
import sys
import ntpath
import os
import re
from io import BytesIO
from bson.objectid import ObjectId
from pymongo import MongoClient
from os import listdir
from os.path import isfile, join



from app.logs.logger import logging_text
import app.definitions as definitions

class simcore_runner:

    def __init__(self,settings=None):
        self.settings = {
            'simcore_api_url': None,
            'entity_id': None,
            'params': None,
            'sleep': 180
        }
        if settings is not None:
            logging_text.info("updating settings cause not None")
            self.settings.update(settings)
        pass    

    
    def host_files(self, text_type):
        if text_type=="analysis":
            entity_id_cut= self.settings['entity_id'].split(":")[-1]
            dirname = f"/home/{entity_id_cut.replace('-','_')}/"
            filename = os.path.join(dirname, f'./analysis.txt')   
            file_binary = open(filename,'rb')
            file_binary_tupel = ('analysis.txt',file_binary)
            return file_binary_tupel
        if text_type=="reference":
            agenda_entity_id = self.settings['params']['agenda_entity_id']     
            agenda_entity_id_cut= agenda_entity_id.split(":")[-1]   
            dirname = f"/usr/src/app/refcorpora/{agenda_entity_id_cut}/"       
            logging_text.info(f"trying to get all files from {dirname}")  
            for f in listdir(dirname):
                logging_text.info(f)
            files_binary_tupel = [(f,open(join(dirname, f),'rb')) for f in listdir(dirname) if isfile(join(dirname, f))]
    
            return files_binary_tupel

    def open_task(self):
        url = self.settings['simcore_api_url']+"/open_task"
        logging_text.info("creating project")
        r = requests.get(url)
        logging_text.info(r.status_code)
        logging_text.info(r.text)        
        return r.status_code, r.json()
    
    def upload_anatext(self, token, anatext_binary):
        url = self.settings['simcore_api_url']+f"/upload_text/{token}"
        logging_text.info("uploading analysis text")
        files = [('ufile', anatext_binary)]
        r = requests.post(url, files = files)
        logging_text.info(r.status_code)
        logging_text.info(r.text)
        return r.status_code, r.json()

    def upload_reftext(self, token, reftext_binary):
        url = self.settings['simcore_api_url']+f"/upload_reference/{token}"
        logging_text.info("uploading reference text")
        files = [('ufile',reftext_binary)]
        r = requests.post(url, files = files)
        logging_text.info(r.status_code)
        logging_text.info(r.text)
        return r.status_code, r.json()
    
    def set_analyzer(self, token, analyzer):
        url = self.settings['simcore_api_url']+f"/set_analyzer/{token}"
        params = {'analyzer': analyzer}
        logging_text.info("setting analyzer")
        r = requests.post(url, params = params)
        logging_text.info(r.status_code)
        logging_text.info(r.text)
        return r.status_code, r.json()
    
    def analyse_project(self, token, analyzer , num_reftexts):
        url = self.settings['simcore_api_url']+f"/analyze_project/{token}"
        logging_text.info("analyzing project")
        try:
            start_simcore = time.time()
            try:
                r = requests.get(url, timeout = 1)       
            except requests.exceptions.ReadTimeout: 
                pass                 
            logging_text.info("sending checking status")
            while True:
                code, response = self.simcore_status(token)
                if ('details' not in response):
                    logging_text.info("checking status has no details specified")
                    time.sleep(self.settings['sleep'])
                    continue
                elif analyzer == "coarse":
                    if ((response['status'] == 1) and (len([s for s in response['details']['files'] if "results" in s]) != 2)):
                            logging_text.info("not all files are computed yet")
                            time.sleep(self.settings['sleep'])
                            continue
                    elif ((response['status'] == 1) and (len([s for s in response['details']['files'] if "results" in s]) == 2)):
                        logging_text.info("finished in %fs"%(time.time() - start_simcore))
                        status_code = definitions.MESSAGE_SUCCESS
                        break
                    elif (response['status'] == -1):
                        logging_text.info("finished in %fs"%(time.time() - start_simcore))
                        status_code = definitions.MESSAGE_ERROR
                        break
                    else:
                        logging_text.info(response)
                        time.sleep(self.settings['sleep'])
                        continue
                elif analyzer == "detailed":
                    if ((response['status'] == 1) and (len([s for s in response['details']['files'] if "results" in s]) != (num_reftexts*2+2))):
                            logging_text.info("not all files are computed yet")
                            time.sleep(self.settings['sleep'])
                            continue
                    elif ((response['status'] == 1) and (len([s for s in response['details']['files'] if "results" in s]) == (num_reftexts*2+2))):
                        logging_text.info("finished in %fs"%(time.time() - start_simcore))
                        status_code = definitions.MESSAGE_SUCCESS
                        break
                    elif (response['status'] == -1):
                        logging_text.info("finished in %fs"%(time.time() - start_simcore))
                        status_code = definitions.MESSAGE_ERROR
                        break
                    else:
                        logging_text.info(response)
                        time.sleep(self.settings['sleep'])
                        continue     

        except Exception as exc:
            logging_text.info("Starting simcore service threw error")
            logging_text.info(exc)
            status_code = definitions.MESSAGE_ERROR
            return status_code
        return status_code

    def simcore_status(self, token):
        # for each analysis text, 2 files get calcualted (.joblib and .xlsx) --> in the "files" attribute there must be num analysis * 2 + 1 entries
        try:
            url = self.settings['simcore_api_url']+f"/list_task_files/{token}"
            logging_text.info("getting project info for status update")
            r = requests.get(url, timeout = 10)
            logging_text.info(r.json)
            logging_text.info(r.status_code)
            logging_text.info(r.text)
        except requests.exceptions.ReadTimeout: 
            logging_text.info("ran in ReadTimeout error")
            return definitions.MESSAGE_ERROR, {}                
        return r.status_code, r.json()

    def set_vizualizer(self, token, vizualizer):
        url = self.settings['simcore_api_url']+f"/set_visualizer/{token}"
        params = {'sc_visualizer': vizualizer}
        logging_text.info("setting visualizer")
        r = requests.post(url, params = params)
        logging_text.info(r.status_code)
        logging_text.info(r.text)
        return r.status_code, r.json()
    
    def visualize_project(self, token):
        url = self.settings['simcore_api_url']+f"/visualize_project/{token}"
        logging_text.info("visualizing project")
        r = requests.get(url)
        logging_text.info(r.status_code)
        logging_text.info(r.text)
        return r.status_code, r.json()

    def get_result_files(self,token):
        url = self.settings['simcore_api_url']+f"/list_task_files/{token}"
        logging_text.info("getting project info downloading project files")
        r = requests.get(url)
        logging_text.info(r.status_code)
        logging_text.info(r.text)
        files = r.json()["details"]["files"] 
        matching_files = []
        for file in files:
            file_name = file.split("/")[-1]
            url = self.settings['simcore_api_url']+f"/download_file/{token}"
            params = {"afilepath": file}
            r = requests.post(url, params = params, timeout = 1200)
            matching_files.append({"file_name": file_name, "file_content_binary": r.content})
        return matching_files
    
    def close_task(self, token):
        url = self.settings['simcore_api_url']+f"/close_task/{token}"
        logging_text.info("closing project")
        r = requests.get(url)
        logging_text.info(r.status_code)
        logging_text.info(r.text)        
        return r.status_code, r.json()
    

        
    
    def run(self):
        try:
            logging_text.info('Starting pipeline')
            logging_text.info('Simcore URL: '+ self.settings['simcore_api_url'])
            logging_text.info('-------------------------')
            # getting all documents stored for corresponding entity in crawled documents 
            logging_text.info(f"Getting analysis text from host file system")
            analysis_text_binary_tupel= self.host_files("analysis")
            logging_text.info(f"Getting reference text from host file system")
            reference_texts_binary_tupel = self.host_files("reference")
            logging_text.info(analysis_text_binary_tupel)
            logging_text.info(reference_texts_binary_tupel)
            code, response = self.open_task()
            project_token = response["details"]["token"]
            logging_text.info(f"The following token was obtained: {project_token}")
            if code == 200:
                # upload orga text as analysis text
                code, response = self.upload_anatext(project_token,analysis_text_binary_tupel)
                if code == 200:
                    # upload reference texts as reference text
                    for tupel in reference_texts_binary_tupel:
                        code, response = self.upload_reftext(project_token, tupel)
                        if code == 200:
                            continue
                        else:
                            break          
                    # only continues when last code is also 200
                    if code == 200:
                        code, response = self.set_analyzer(project_token, "coarse")
                        if code == 200:                            
                            code = self.analyse_project(project_token, "coarse", len(reference_texts_binary_tupel))
                            if code == definitions.MESSAGE_SUCCESS:
                                code, response = self.set_vizualizer(project_token, "coarse")                     
                                if code == 200:                                    
                                    code, response = self.set_analyzer(project_token, "detailed")        
                                    if code == 200:                        
                                        code = self.analyse_project(project_token, "detailed", len(reference_texts_binary_tupel))
                                        if code == definitions.MESSAGE_SUCCESS:
                                            matching_files = self.get_result_files(project_token)
                                            code, response =self.close_task(project_token)  
                                            status_code = definitions.MESSAGE_SUCCESS                                            
                                        else:
                                            return definitions.MESSAGE_ERROR
                                    else:
                                        status_code = definitions.MESSAGE_ERROR
                                else:
                                    status_code = definitions.MESSAGE_ERROR
                            else:
                                return definitions.MESSAGE_ERROR
                        else:
                            return definitions.MESSAGE_ERROR  
                    else:
                        return definitions.MESSAGE_ERROR                
                else:
                    return definitions.MESSAGE_ERROR        
            else:
                return definitions.MESSAGE_ERROR
            logging_text.info('-------------------------')
            logging_text.info('Pipeline finished')

        except: 
            status_code = definitions.MESSAGE_ERROR
            matching_files = []
        
        
        return status_code, matching_files
        
