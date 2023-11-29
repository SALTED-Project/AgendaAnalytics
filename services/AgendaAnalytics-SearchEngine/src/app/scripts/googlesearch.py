# -*- coding: iso-8859-1 -*-
# -*- coding: utf-8 -*-
import collections

from googleapiclient.discovery import build
import pandas as pd
from collections import defaultdict
from collections import Counter
import json
import math
import itertools





def google_search(search_term: str, language:str, api_key: str, cs_id:str, **kwargs) -> json:
    responses = []
    service = build("customsearch", "v1", developerKey=api_key)
    number_search_results = kwargs['num']
    if number_search_results > 60:
        raise NotImplementedError('Google CSE API supports max of 60 results')
    elif number_search_results > 10:
        kwargs['num'] = 10  # max of 10 results per page and cannot exceed > 10 in API request
        no_pages_to_call = math.ceil(number_search_results / 10)
    else:
        no_pages_to_call = 1

    kwargs['start'] = startIndex = 1
    # Execute request
    while no_pages_to_call > 0:
        responses.append((service.cse().list(
            q=search_term,
            cx=cs_id,
            lr=f"lang_{language}", **kwargs).execute()))   # use additional parameters (e.g. cr, gl) if necessary: https://developers.google.com/custom-search/v1/reference/rest/v1/cse/list?hl=de
        no_pages_to_call -= 1
        startIndex += 10
        kwargs['start'] = startIndex
    item_list = []
    for response in responses:
        try: # get items list
            items = response["items"]
            item_list  = item_list + items
        except:
            print("no result items could be extracted")
    
    # return only the number of search results requested
    # check if item_list is shorter than requested number of results
    if len(item_list) <= number_search_results:
        print(f"Only {len(item_list)} results found.")        
        return item_list
    else:
        return item_list[0:number_search_results]



def google_main(google_csid,google_apikey, parameters):
    APIKEY = google_apikey
    CSE_ID = google_csid
    json_input = parameters
    google_result = google_search(json_input["searchquery"], json_input["language"],  APIKEY, CSE_ID, num=json_input["number_search_results"])
    return google_result



