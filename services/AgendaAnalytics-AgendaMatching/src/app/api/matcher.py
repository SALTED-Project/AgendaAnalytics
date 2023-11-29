import os
import json
import time
import validators
import re
from collections import OrderedDict

# for debugging requests
# ###############################################
# import logging
# import http.client
# http.client.HTTPConnection.debuglevel = 1

# #logging.basicConfig()
# #logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True
# ##################################################

from app.logs.logger import logging_text
import app.definitions as definitions
from app.api import vdpp_api_runner, simcore_api_runner, kpi, fileserver, dataservicerun
from app.config import settings




def post_matchingrequest(vdpp_middleware_api, vdpp_mongodb_uri, simcore_api, salted_fileserver_service, entity_id, crawling_data_uuids, dsr_crawling_id, params):
    salted_fileserver_service_pub_addr = os.environ.get("SALTED_FILESERVER_SERVICE_PUB_ADDR")
    logging_text.info("Starting VDPP Runner")      
    agenda_id = params["agenda_entity_id"] 
    entity_id_cut= entity_id.split(":")[-1]
    vdpp_runner = vdpp_api_runner.vdpp_runner([
                    {
                        "serviceCode": "TRANSFER_DOCS",
                        "parameters": [
                            {"name": "DST_DATABASE",   "values": [f"salted_agendamatching_tmp_{entity_id_cut}"]},
                            {"name": "DST_COLLECTION", "values": ["pdf"]},
                        ],
                        "documents": [], 
                    },
                    {
                        "serviceCode": "CONVERT_DOCUMENTS",
                        "parameters": [
                            {"name": "SRC_DATABASE",   "values": [f"salted_agendamatching_tmp_{entity_id_cut}"]},
                            {"name": "SRC_COLLECTION", "values": ["pdf"]},
                            {"name": "DST_DATABASE",   "values": [f"salted_agendamatching_tmp_{entity_id_cut}"]},
                            {"name": "DST_COLLECTION", "values": ["text"]},
                        ],
                        "documentUuids": [],
                    }
                ],settings = {'vdpp_mongodb_uri':vdpp_mongodb_uri, 'vdpp_api_url':vdpp_middleware_api, 'entity_id':entity_id, 'crawling_data_uuids': crawling_data_uuids}
    )
    
    
    
    logging_text.info("Initiated the vdpp runner")
    status_code, text_documents = vdpp_runner.run()   
    logging_text.info(f"Vdpp runner is finished with status_code: {status_code}")

    # check if any crawled data could be obtained or not
    if status_code==definitions.RESPONSE_204:
        status_code = definitions.RESPONSE_204
    
    # get text and post to simcore service
    elif status_code==definitions.MESSAGE_SUCCESS:
        # example documents: documents = [{"name": document['name'], "text": document['text'], "text_content_url": document["content_url"]} for document in document_entries]
        # try to create directory in case it does not exist yet and catch exception if it does       
        dirname = f"/home/{entity_id_cut.replace('-','_')}/"
        try: 
            os.mkdir(dirname) 
        except OSError as error: 
            logging_text.info(error)  
            # clear out all contents
            try:
                logging_text.info("trying to clean out dir")
                for f in os.listdir(dirname):
                    os.remove(os.path.join(dirname, f))
                logging_text.info("cleaned out dir")
            except:
                logging_text.info("nothing to clean out of dir")

        # save document list in ./text_info.json
        filename = os.path.join(dirname, './text_info.json')  
        logging_text.info(f"trying to write:{filename}")        
        try: 
            with open(filename, "w") as f:
                json.dump(text_documents, f, ensure_ascii=False, indent=4)       
        except Exception as e: 
            logging_text.info(e)  
        
        try:
            logging_text.info("Following texts will be concatenated:")
            for document in text_documents:
                logging_text.info(document.keys())
                logging_text.info(document["name"])
        except Exception as e:
            logging_text.info(e)
        
        
        # save concat text of all documents in document list (preprocessing should be extended!)            
        text_analysis=" "
        for document in text_documents:             
            if isinstance(document['text'],str):
                text_analysis = text_analysis+"\n"+document['text']
            else:
                logging_text.info(f"skip concat text of {document['name']} since its not a valid string")
            
        if text_analysis !=" ":
            filename = os.path.join(dirname, 'analysis_raw.txt')  
            with open(filename, "w") as f:
                f.write(text_analysis)

            with open(filename) as f, open(dirname + "analysis_raw_cut.txt", 'w') as f2:
                for line in f:
                    line = line.strip()
                    if (len(line) >= 43):
                        f2.write(line + '\n')

            filename = os.path.join(dirname, 'analysis_raw_cut.txt')          
            with open(filename, 'r') as f:
                text_analysis_raw_cut = f.read()       
            
            # remove newline tokens and long white spaces
            text_mod = text_analysis_raw_cut.replace('\n', ' ')
            text_mod = re.sub(' +', ' ', text_mod)
            # add newline after punctuation
            text_mod = re.sub("^[.!?]\s", ".\n", text_mod)              
            # remove duplicate lines
            try:
                text_mod = "\n".join(list(OrderedDict.fromkeys(text_mod.split("\n"))))
            except e as Exception:
                logging_text.info(e)
                    
            # save concat processed text of all documents in document list
            filename = os.path.join(dirname, 'analysis.txt')  
            with open(filename, "w") as f:
                f.write(text_mod)

            # save concat processed text of all documents in document list also in shared mount, for debugging
            filename_debug = os.path.join("/usr/src/", 'analysis.txt')  
            with open(filename_debug, "w") as f:
                f.write(text_mod)            

                
            # start simcore runner
            simcore_runner = simcore_api_runner.simcore_runner(settings = {'simcore_api_url':simcore_api, 'entity_id':entity_id, 'params': params})
            logging_text.info("Initiated Simcore Runner")
            logging_text.info(simcore_runner)
            status_code, matching_files = simcore_runner.run() 

            logging_text.info("This status_code was given by the simcore_runner:")
            logging_text.info(status_code)

            # clear out all contents within container
            try:
                logging_text.info("trying to clean out dir")
                for f in os.listdir(dirname):
                    os.remove(os.path.join(dirname, f))
                logging_text.info("cleaned out dir")
            except:
                logging_text.info("nothing to clean out of dir")

            # take simcore results and create DSR 
            if status_code == definitions.MESSAGE_SUCCESS:
                # upload results to SALTED file server and create DSR & KPI entity
                file_server_uuids_with_name = []
                kpi_files = []
                for matching_file in matching_files:
                    content_binary = matching_file["file_content_binary"]
                    filename = matching_file["file_name"]
                    status_code, fileserver_uuid = fileserver.upload(salted_fileserver_service, content_binary, filename)
                    if status_code == definitions.MESSAGE_SUCCESS:
                        file_server_uuids_with_name.append([fileserver_uuid,filename])  
                    kpi_files.append({"filename": filename, "content_binary": content_binary})   
                
            
                if file_server_uuids_with_name != []:
                    # create DataScieneServiceRun    
                    logging_text.info("creating DataServiceRun entity")
                    dsr_entity = dataservicerun.create_dsr(entity_id, file_server_uuids_with_name, dsr_crawling_id, params)            
                    logging_text.info(dsr_entity["id"])      
                    # create KPI
                    logging_text.info("creating KPI entity")
                    kpi_value = kpi.calculate(kpi_files, agenda_id)   
                    # upload kpi_value to fileserver
                    status_code, kpi_file_id = fileserver.upload(salted_fileserver_service, json.dumps(kpi_value, ensure_ascii=False).encode("utf8") , "kpi_value.json")
                    if status_code == definitions.MESSAGE_SUCCESS:
                        kpi_entity = kpi.create_kpi(entity_id, dsr_entity["id"], agenda_id, kpi_value, kpi_file_id)        
                        logging_text.info(kpi_entity["id"])                                                                  
            else:
                dsr_entity= None
                kpi_entity= None
                status_code = definitions.MESSAGE_ERROR           
        else:
            logging_text.info("analysis text is empty - skipping simcore runner - returning no entities")
            dsr_entity= None
            kpi_entity= None
            status_code = definitions.MESSAGE_ERROR     
    else:
        dsr_entity= None
        kpi_entity= None
        status_code = definitions.MESSAGE_ERROR    

    return status_code, dsr_entity, kpi_entity

