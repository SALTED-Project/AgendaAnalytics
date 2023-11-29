import requests
import os
import json


from app.logs.logger import logging_text


def get_urls(salted_searchengine_service, query, n_results, language):
    try:
        logging_text.info(salted_searchengine_service)        
        url = salted_searchengine_service + "/google/searchengine/"
        logging_text.info(url)
        params = {
            "searchquery": query,
            "engine": "google",
            "number_search_results": n_results,
            "language": language
        }
        logging_text.info(params)
        # make request to search engine
        logging_text.info(f"request to {url}")
        response = requests.post(url , params = params)
        response.raise_for_status()  # raise an exception if the response status code is not 2xx
        json_response = response.json()
        # debug help
        dirname = os.path.dirname(__file__)
        file = open(os.path.join(dirname, 'test_google_data.txt'),"w")
        file.write(response.text)
        file.close()
        # extract links 
        try: 
            result_links = [item["link"] for item in json_response]
        except Exception as e:
            logging_text.info("OOps: Something went wrong - SearchEgine did not return list items containing link attribut",e)    
            logging_text.info(response.text)
            result_links=[] 
        
    except requests.exceptions.RequestException as err:
        logging_text.info("OOps: Something went wrong - SearchEgine did not return 2xx",err)    
        result_links=[]           
 

    return result_links



