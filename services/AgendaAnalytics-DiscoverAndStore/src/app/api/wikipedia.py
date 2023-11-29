import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np


from app.logs.logger import logging_text



def get_table():        
    url = 'https://de.wikipedia.org/wiki/Liste_privatrechtlicher_Unternehmen_mit_Bundesbeteiligung_in_Deutschland'
    
    try:
        response = requests.get(url,timeout=5)
        response_status = "Sucessful request."
    except requests.exceptions.HTTPError as errh:
        print ("Http Error:",errh)
        response_status = "Http Error"
    except requests.exceptions.ConnectionError as errc:
        print ("Error Connecting:",errc)
        response_status = "Error Connecting"
    except requests.exceptions.Timeout as errt:
        print ("Timeout Error:",errt)
        response_status = "Timeout Error"
    except requests.exceptions.RequestException as err:
        print ("OOps: Something Else",err)
        response_status = "OOps: Something Else"
    
    if response_status != "Sucessful request.":
        response = ""
        df_companies = pd.DataFrame()
        logging_text.error("Error during request to wikipedia.")
        df_companies_status = "Aborted before trying to extract data."
        return response, response_status, df_companies, df_companies_status  
        
     
    try:
        soup = BeautifulSoup(response.text,'html.parser')
        table = soup.find('table',{'class':'wikitable sortable'}).tbody
        rows = table.find_all('tr')
                
        columns = ["name","legalform","city"]

        df_companies = pd.DataFrame(columns=columns)
        for i in range(1,len(rows)):
            tds = rows[i].find_all('td')
            values = [td.text.replace('\n',''.replace('\xa0','')) for td in tds]
            arr=np.array(values[0:3])
            
            if len(values[0:3])!=0:
                df_add = pd.DataFrame([arr], columns = columns)
                df_companies=pd.concat([df_companies, df_add], ignore_index=True)       
        df_companies=df_companies.applymap(lambda x: x.strip() if isinstance(x, str) else x)         
        df_companies_status = "Table was built successfully."
    
    except:
        df_companies = pd.DataFrame()
        logging_text.error("Error while building DataFrame from Wikipedia scraping result.")
        df_companies_status = "Error while building table. May the structure used within Wikipedia-Tables changed. Therefor content could not be extracted."    
    return response, response_status, df_companies, df_companies_status
    

