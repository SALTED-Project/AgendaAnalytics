import os
import json
import time
import validators
import pandas as pd

from app.logs.logger import logging_text
import app.definitions as definitions
from app.api import vdpp_api_runner 
from app.api import googlesearch
from app.config import settings


def crawlprocessing(entity, salted_searchengine_service, vdpp_middleware_api, vdpp_mongodb_uri, approach, keywords, custom_depth, language):
    entity_url = entity['url']['value']
    entity_name = entity['name']['value']
    entity_id = entity['id']
    logging_text.info(entity_url)
    logging_text.info(f"used approach:{approach}")    
    if approach == "report":
        # get all urls from a google search 
        max_depth = custom_depth
        mimetypes = ["application/pdf"]
        keywords = keywords.replace(";", " OR ")
        query = f'allintext:{entity_name} {keywords} filetype:pdf'
        result_links = googlesearch.get_urls(salted_searchengine_service, query, settings.GOOGLE_N_RESULTS_REPORT, language)
        if result_links == []:
            logging_text.info("No links could be extracted from google response.")
            status_code = definitions.RESPONSE_204
            crawl_results = []
            return status_code, crawl_results
        # check if all urls are in valid format     
        logging_text.info(result_links)
        crawl_results = []
        for i, url in enumerate(result_links):        
            # trying to clean url of false pdf endings
            split_parts = url.split(".pdf")
            if len(split_parts) > 0:
                url = split_parts[0]+ ".pdf"
            logging_text.info(url)
            # check url syntax and move on to next if necessary
            logging_text.info("########################################################")
            logging_text.info(f"Starting crawling process for {url} using report approach")
            if is_string_an_url(url) == False:
                logging_text.info("skip entity since url is not valid")
                continue
            if url.endswith(".pdf")==False:
                logging_text.info("skip entity since is is not a pdf")
                continue        
            # send request to middleware and wait for crawling to be finished
            status_code, documents = post_crawlrequest(url, vdpp_middleware_api, vdpp_mongodb_uri, entity_id, max_depth, mimetypes)
            if status_code == definitions.MESSAGE_SUCCESS:
                crawl_results = crawl_results + documents 
        # set status for all crawling runs, since otherwiese the last status defined handling!
        if crawl_results!=[]:
            status_code=definitions.MESSAGE_SUCCESS
        elif crawl_results == []:
            status_code=definitions.RESPONSE_204
        else: 
            status_code=definitions.MESSAGE_ERROR

    elif approach == "google":
        # get all urls from a google search 
        max_depth = custom_depth
        mimetypes = ["application/pdf", "text/html"]
        crawl_results = []     
        keywordlist = list(keywords.split(";"))
        result_links = []
        for keyword in keywordlist:   
            logging_text.info(f"Google request for: {keyword}")
            query = f'site:{entity_url} {keyword}'
            results = googlesearch.get_urls(salted_searchengine_service,query, settings.GOOGLE_N_RESULTS_GOOGLE, language)
            if results != []:
                result_links= result_links + results        
        if result_links == []:
                logging_text.info("No links could be extracted from google response.")
                status_code = definitions.RESPONSE_204
                return status_code, crawl_results  
        # already deduplicate
        result_links=list(set(result_links))
        logging_text.info(result_links)
        for i, url in enumerate(result_links):        
            logging_text.info("########################################################")
            logging_text.info(f"Starting crawling process for {url} using google approach")
            if is_string_an_url(url) == False:
                logging_text.info("skip entity since url is not valid")
                continue  
            # send request to middleware and wait for crawling to be finished
            status_code, documents = post_crawlrequest(url, vdpp_middleware_api, vdpp_mongodb_uri, entity_id, max_depth, mimetypes)
            if status_code == definitions.MESSAGE_SUCCESS:
                crawl_results = crawl_results + documents 
        # set status for all crawling runs, since otherwiese the last status defined handling!
        if crawl_results!=[]:
            status_code=definitions.MESSAGE_SUCCESS
        elif crawl_results == []:
            status_code=definitions.RESPONSE_204
        else: 
            status_code=definitions.MESSAGE_ERROR
    elif approach == "website":
        max_depth = custom_depth
        mimetypes = ["text/html"]
        crawl_results = []        
        logging_text.info("########################################################")
        logging_text.info(f"Starting crawling process for {entity_url} using website approach")
        if not entity_url.startswith(('http://', 'https://')):
            entity_url = "https://"+ entity_url                  
        if is_string_an_url(entity_url) == False:
            logging_text.info("skip entity since url is not valid")
            status_code=definitions.RESPONSE_204
        else:
            # send request to middleware and wait for crawling to be finished
            status_code, documents = post_crawlrequest(entity_url, vdpp_middleware_api, vdpp_mongodb_uri, entity_id, max_depth, mimetypes)
            if status_code == definitions.MESSAGE_SUCCESS:
                crawl_results = crawl_results + documents 
            else:
                status_code=definitions.RESPONSE_204    
    else: 
        logging_text.info("No valid approach parameter was supplied")
        status_code = definitions.RESPONSE_204
        crawl_results = []
    
    if crawl_results != []:
        # deduplicate crawl_results
        df = pd.DataFrame(crawl_results)
        df = df.drop_duplicates(subset=['url'], keep='first')
        logging_text.info("deduplicated list of documents from mongodb results")        
        crawl_results = df.to_dict("records")
        logging_text.info([result["url"] for result in crawl_results])
    return status_code, crawl_results



def post_crawlrequest(url,vdpp_middleware_api,vdpp_mongodb_uri, originator_id, max_depth, mimetypes):
    middleware_document = {
        "crawling_job_definitions": [{
            "parameters": {
                "url": url,
                "originator": f"salted_crawling_service_entityid_{originator_id}",
                # e.g. "mimetypes": ["application/pdf", "application/xhtml+xml", "text/html"],
                "mimetypes": mimetypes,
                # e.g. 0 - only url, 1 - all you can find on seed aswell, -1 - endless
                "max_depth": max_depth 
            }
        }]
    }
    middleware_document_object = json.dumps(middleware_document, indent=4)  
    timestr = time.strftime("%Y%m%d-%H%M%S")    
    dirname = os.path.dirname(__file__)
    logging_text.info(f"job definitions directory used: {dirname}")
    filename = os.path.join(dirname, f'./job_definitions/crawl_file_{timestr}.json')  
    with open(filename, "w") as f:
        f.write(middleware_document_object)
    logging_text.info("Those are the crawling definitions used in the following:")
    logging_text.info(middleware_document)
    logging_text.info("Starting Runner")
    runner = vdpp_api_runner.mid_runner(
        stages= [
            {
                "serviceCode": "CRAWLING_STORM",
                'documents': [
                    filename
                ],
                'documentUuids': [],
                "parameters": []
            }
        ], 
        settings = {
            'vdpp_middleware_api':vdpp_middleware_api,
            'vdpp_mongodb_uri':vdpp_mongodb_uri, 
            'originator': middleware_document["crawling_job_definitions"][0]["parameters"]["originator"]           
        }
    )
    logging_text.info(runner)
    status_code, documents = runner.run()    
    return status_code, documents


def is_string_an_url(url_string: str) -> bool:
    try:
        result = validators.url(url_string)
        if isinstance(result, validators.ValidationError):
            return False
    except Exception as e:
        logging_text.info(e)
        result = False
    return result
