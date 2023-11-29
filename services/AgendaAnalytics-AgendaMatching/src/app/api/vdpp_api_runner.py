import requests
import json
import time
from pymongo import MongoClient
import time
import html2text



from app.logs.logger import logging_text
import app.definitions as definitions

class vdpp_runner:

    def __init__(self,stages,settings=None):
        self.settings = {
            'entity_id': None,
            'crawling_data_uuids': None,
            'vdpp_mongodb_uri': None,
            'vdpp_api_url': None,
            'sleep': 60
        }
        if settings is not None:
            logging_text.info("updating settings cause not None")
            self.settings.update(settings)
        self.stages = stages        
        pass
    

    def mongo_service_get_client(self): 
        logging_text.info(f'Client used: {self.settings["vdpp_mongodb_uri"]}')
        client = MongoClient(self.settings["vdpp_mongodb_uri"])
        return client


    def fileserver_service_download(self,content_url):
        logging_text.info(content_url)
        r = requests.get(content_url)
        logging_text.info(r.status_code)        
        filename=r.headers['content-disposition'].split("filename=")[1][1:-1]  
        logging_text.info(filename)      
        return filename, r.content

    def vdpp_api_upload(self,documents):
        files = []
        logging_text.info("prepare files in binary format")
        for p, document in enumerate(documents):
            files.append(('files',document))
            logging_text.info(document[0])  
            logging_text.info(type(document[1]))         
        url = self.settings['vdpp_api_url']+"/documents"
        r = requests.post(
            url,
            files = files
            )
        logging_text.info(r.status_code)
        logging_text.info(r.text)
        return r.status_code, r.json()

    def vdpp_api_download(self,url,name):
        r = requests.get(url)
        filePath = self.settings['dir_results']+f"/{name}"
        open(filePath, "wb").write(r.content)
    
    def vdpp_api_service_start(self,data):
        # send job request to the middleware
        logging_text.info("service input:")
        logging_text.info(json.dumps(data))
        url = self.settings['vdpp_api_url']+"/requests"
        r = requests.post(
            url, headers={
                'Content-Type': 'application/json'
            }, data=json.dumps(data)
        )
        return r.status_code, r.json()

    def vdpp_api_service_status(self,uuid):
        # request information about the service
        url = self.settings['vdpp_api_url']+f"/requests/{uuid}/status"
        r = requests.get(
            url, headers={
                'accept': 'application/json'
            }
        )
        return r.status_code, r.json()

    def vdpp_api_service_results(self,uuid):
        # request result of the service
        r = requests.get(
            self.settings['vdpp_api_url']+f"/requests/{uuid}/result", headers={
                'accept': 'application/json'
            }
        )
        return r.status_code, r.json()

    def mongo_results_download(self):
        try: 
            # download result webdata if text format
            client = self.mongo_service_get_client()
            logging_text.info("got mongodb client")
            db_name=self.stages[1]['parameters'][0]["values"][0]
            logging_text.info(f"Getting results from {db_name}")
            # Get db and col
            db = client[db_name]
            logging_text.info(db)
            col = db.text
            logging_text.info(col)
            document_entries = col.find()
            documents = [{"name": document['name'], "text": document['text'], "text_content_url": document["content_url"]} for document in document_entries]
            # remove db and collection
            client.drop_database(db_name)
            status_code = definitions.MESSAGE_SUCCESS            
        except:
            documents = []
            status_code = definitions.MESSAGE_ERROR
        
        return status_code, documents
        
    
    def run(self):
        logging_text.info('Starting pipeline')
        logging_text.info('Middleware URL: '+ self.settings['vdpp_api_url'])
        logging_text.info('-------------------------')
        
        # lists for processing different file types
        pdf_documents=[]   
        rawtxt_documents=[]

        # final processed list with results
        text_documents = []
        
        
        for fileserver_uuid in self.settings['crawling_data_uuids']:            
            logging_text.info("Downloading document from SALTED file server:")
            filename, content = self.fileserver_service_download(fileserver_uuid)
            # get pdf files that need to be converted to text via VDPP 
            if filename.lower().endswith(".pdf"):
                pdf_documents.append((filename,content))       
            # get txt files, that only need to be decoded
            elif filename.lower().endswith(".txt"):
                rawtxt_documents.append((filename,content))                    
                
        if (pdf_documents == []) and (rawtxt_documents == []):
            status_code = definitions.RESPONSE_204
            return status_code, text_documents
        
        if pdf_documents != []:
            logging_text.info("going through pdf documents")
            self.stages[0]["documents"]= pdf_documents  
            logging_text.info("Those are the documents downloaded from SALTED file server:")     
            logging_text.info([doc[0] for doc in pdf_documents]) 
            
            # start processing in stages if it is an pdf document
            for s,stage in enumerate(self.stages):
                start = time.time()
                            
                logging_text.info(f"Stage {s+1}: Running service "+stage['serviceCode'])
                if (stage['serviceCode']=='TRANSFER_DOCS'):
                    logging_text.info(f"Uploading documents to the middleware")
                    code, response1 = self.vdpp_api_upload(stage['documents'])
                    for i,res in enumerate(response1):
                        logging_text.info(res['uuid'])
                        
                    logging_text.info(f"saving documents in the database")
                    code, response2 = self.vdpp_api_service_start({
                        'serviceCode':   stage['serviceCode'],
                        'documentUuids': [item['uuid'] for item in response1],
                        'parameters':    stage['parameters']
                    })
                    uuid = response2['uuid']
                else:
                    logging_text.info(f"starting the service")
                    code, response = self.vdpp_api_service_start(stage)
                    uuid = response['uuid']

                logging_text.info("SENT Checking status")
                while True:
                    code, response = self.vdpp_api_service_status(uuid)
                    if ('statusCode' not in response):
                        logging_text.info("SENT Checking status")
                        time.sleep(self.settings['sleep'])
                    elif (response['statusCode'] in ['SUCCESS']):
                        logging_text.info(response['statusCode']+response['statusMessage'])
                        logging_text.info("Finished in %fs"%(time.time() - start))
                        status_code = definitions.MESSAGE_SUCCESS
                        break
                    elif (response['statusCode'] in ['FAILED']):
                        logging_text.info(response['statusCode']+response['statusMessage'])
                        logging_text.info("Finished in %fs"%(time.time() - start))
                        status_code = definitions.MESSAGE_ERROR
                        break
                    else:
                        logging_text.info(response['statusCode']+response['statusMessage'])
                        if stage['serviceCode']=="CONVERT_DOCUMENTS":
                            time.sleep(2*self.settings['sleep'])
                        else:
                            time.sleep(self.settings['sleep'])
                
                if (response['statusCode']=='FAILED'):
                    logging_text.info('Terminating whole pipeline')
                    status_code = definitions.MESSAGE_ERROR
                    break        

            if status_code == definitions.MESSAGE_SUCCESS:
                # get results
                status_code, text_documents_from_pdf = self.mongo_results_download()   
                text_documents = text_documents+text_documents_from_pdf   

        
        if rawtxt_documents != []:  
            logging_text.info("going through txt documents")
            for rawtxt_document in rawtxt_documents:
                rawtxt_document_filename, rawtxt_document_content = rawtxt_document
                text_documents.append({"name": rawtxt_document_filename, "text": rawtxt_document_content.decode("utf-8"), "text_content_url": "tbd"})
        
        if text_documents == []:
            status_code = definitions.RESPONSE_204
        else:
            status_code = definitions.MESSAGE_SUCCESS
             
            
        logging_text.info('-------------------------')
        logging_text.info('Pipeline finished')
        
        return status_code, text_documents
        
