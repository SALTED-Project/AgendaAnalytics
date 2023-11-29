import requests
from urllib.parse import urlparse
import os

from app.logs.logger import logging_text



def get_urls(salted_searchengine_service, query, unwanted_urls):
    try:
        logging_text.info(salted_searchengine_service)        
        url = salted_searchengine_service + "/google/searchengine/"
        logging_text.info(url)
        params = {
            "searchquery": query,
            "engine": "google",
            "number_search_results": 1,
            "language": "de"
        }
        logging_text.info(params)
        # make request to search engine
        logging_text.info(f"request to {url}")
        response = requests.post(url , params = params)
        # raise an exception if the response status code is not 2xx
        response.raise_for_status()  
        json_response = response.json()
        logging_text.info(response.text)
        # debug help
        # dirname = os.path.dirname(__file__)
        # file = open(os.path.join(dirname, 'test_google_data.text'),"w")
        # file.write(response.text)
        # file.close()
        # extract links 
        try: 
            item_link = [item["link"] for item in json_response][0]
            # get domain
            result_link = urlparse(item_link).netloc
            if result_link not in unwanted_urls:
                result_link_status = "Link was extracted succesfully."
            else:
                logging_text.info("Extracted link represents unwandet URL")    
                result_link=""
                result_link_status = "Error. Link could not be extracted."
        except Exception as e:
            logging_text.info("OOps: Something went wrong - SearchEngine did not return list items containing link attribut",e)    
            result_link=""
            result_link_status = "Error. Link could not be extracted."        
    except requests.exceptions.RequestException as err:
        logging_text.info("OOps: Something went wrong - SearchEgine did not return 2xx",err)    
        result_link=""      
        result_link_status = "Error. Link could not be extracted."   
    return result_link, result_link_status



