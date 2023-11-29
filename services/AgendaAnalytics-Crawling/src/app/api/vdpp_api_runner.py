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



from app.logs.logger import logging_text
import app.definitions as definitions

class mid_runner:
    def __init__(self,stages,settings=None):
        self.settings = {
            'vdpp_middleware_api': None,
            'vdpp_mongodb_uri': None,
            'originator': None,
            'sleep': 3
        }
        if settings is not None:
            self.settings.update(settings)
        self.stages = stages     
        logging_text.info(self.settings)   
        pass
    
    def api_upload(self,paths):
        # prepare files in the binary format
        files = {}
        logging_text.info("prepare files in binary format")
        for p, path in enumerate(paths):
            data = open(path, 'rb')            
            files[f"file_{p}"] = (
                'crawling_definition.json',
                data
            )
        logging_text.info(files[f"file_{0}"])            
        # send files to middleware
        r = requests.post(
            self.settings['vdpp_middleware_api']+"/documents",
            files={"files": files[f"file_{0}"]}
            )
        return r.status_code, r.json()

    def api_download(self,url,name):
        r = requests.get(url)
        filePath = self.settings['dir_results']+f"/{name}"
        open(filePath, "wb").write(r.content)
    
    def api_service_start(self,data):
        # send job request to the middleware
        logging_text.info("service input:")
        logging_text.info(data)
        r = requests.post(
            self.settings['vdpp_middleware_api']+"/requests", headers={
                'Content-Type': 'application/json'
            }, data=json.dumps(data)
        )
        return r.status_code, r.json()

    def api_service_status(self,uuid):
        # request information about the service
        r = requests.get(
            self.settings['vdpp_middleware_api']+f"/requests/{uuid}/status", headers={
                'accept': 'application/json'
            }
        )
        return r.status_code, r.json()

    def api_service_results(self,uuid):
        # request results of service
        r = requests.get(
            self.settings['vdpp_middleware_api']+f"/requests/{uuid}/result", headers={
                'accept': 'application/json'
            }
        )
        return r.status_code, r.json()
    
    def api_service_files(self, file_uuid):
        r = requests.get(
            self.settings['vdpp_middleware_api']+f"/files/{file_uuid}"
        )
        filename=r.headers['content-disposition'].split("filename=")[1][1:-1]  
        return r.status_code, r.content, filename

    def mongo_service_get_client(self): 
        CONNECTION_STRING=self.settings["vdpp_mongodb_uri"] 
        client = MongoClient(CONNECTION_STRING)
        return client

    def mongo_service_download(self, uuid):
        try: 
            # download result webdata if text format
            client = self.mongo_service_get_client()
            # Get db and col
            db = client.crawl_v2
            print(db)
            col = db.crawling_jobs
            print(col)
            # find crawling job with uuid
            crawling_job_ids = col.find({"middleware_request_id": uuid}).distinct('_id')
            # find corresponding documents
            col = db.documents
            document_entries = col.find({'crawlingJobId': { '$in': crawling_job_ids}})
            documents = [{"vdpp_mongodb_document_id": document['_id'],"url": document['url'], "text": document['text'], "mimetype":document['mimetype'], "content_url": document["content_url"]} for document in document_entries]
            # result documents identified within VDPP mongodb
            logging_text.info("full list of documents from mongodb results:")
            logging_text.info([document["url"] for document in documents])
            # for each document download data from VDPP fileserver 
            for document in documents:
                logging_text.info(f"trying document download from vdpp fileserver...")
                file_uuid = document["content_url"].split("/")[-1]
                status_code, file_binary, filename = self.api_service_files(file_uuid)
                document["content_binary"]= file_binary
                document["content_filename"]= filename
                logging_text.info(f"status_code for document download from vdpp fileserver:{status_code}")
            status_code = definitions.MESSAGE_SUCCESS
        except Exception as e:
            logging_text.info(f"error: {e}")
            documents = []
            status_code = definitions.RESPONSE_204        
        return status_code, documents
    

    
    def run(self):      
        logging_text.info('Starting pipeline')
        logging_text.info('Middleware URL: '+ self.settings['vdpp_middleware_api'])
        logging_text.info('VDPP Mongo DB URI: ' + self.settings['vdpp_mongodb_uri'])
        logging_text.info('-------------------------')
        for s,stage in enumerate(self.stages):
            try:
                dtnow = datetime.datetime.now().strftime("%H:%M:%S")
                start = time.time()            
                logging_text.info(f"Stage {s+1}: Running service "+stage['serviceCode'])            
                logging_text.info(f"uploading following documents to the middleware:")
                logging_text.info(stage['documents'])
                code, response1 = self.api_upload(stage['documents'])
                            
                for i,res in enumerate(response1):
                    logging_text.info(res['uuid'])
                    logging_text.info(stage['documents'][i])
                    
                logging_text.info(f"saving documents in the database")
                code, response2 = self.api_service_start({
                    'serviceCode':   stage['serviceCode'],
                    'documentUuids': [item['uuid'] for item in response1],
                    'parameters':    stage['parameters']
                })
                uuid = response2['uuid']


                logging_text.info("SENT Checking status")
                while True:
                    code, response = self.api_service_status(uuid)
                    if ('statusCode' not in response):
                        logging_text.info("SENT Checking status")
                        time.sleep(self.settings['sleep'])
                    elif (response['statusCode'] in ['SUCCESS']):
                        logging_text.info(response['statusCode']+response['statusMessage'])
                        logging_text.info("Finished in %fs"%(time.time() - start))
                        status_code, documents = self.mongo_service_download(uuid)
                        break
                    elif (response['statusCode'] in ['FAILED']):
                        logging_text.info(response['statusCode']+response['statusMessage'])
                        logging_text.info("Finished in %fs"%(time.time() - start))
                        status_code = definitions.MESSAGE_ERROR
                        documents = []
                        break
                    else:
                        logging_text.info(response['statusCode']+response['statusMessage'])
                        time.sleep(self.settings['sleep'])
                if (response['statusCode']=='FAILED'):
                    logging_text.info('Terminating whole pipeline')
                    status_code = definitions.MESSAGE_ERROR
                    documents = []
                    break
                
                logging_text.info('-------------------------')
                logging_text.info('Pipeline finished')
            except:
                status_code = definitions.MESSAGE_ERROR
                documents = []
        
        return status_code, documents
        
