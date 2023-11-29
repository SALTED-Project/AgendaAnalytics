import uuid
import json
import io
import os
import numpy as np
import pandas as pd
from datetime import datetime
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from statistics import mean


import app.definitions as definitions
from app.logs.logger import logging_text

def calculate(kpi_files, agenda_entity_id):
    try:
        kpivalue = {
            "text": {
                "analysis": [],
                "reference": []            
            },
            "detailed": {
                "description": "The detailed analysis matches every sentence of the analysis text with every sentence of every reference text. The means of the matching results for every reference text level are represented within the aggregated values (null values are ignored). The raw results are represented within the raw values.", 
                "mean_per_level0": [],
                "mean_per_level1": [],
                "raw_values": []
                }, 
            "coarse": {
                "description": "The coarse analysis matches the whole analysis text with every reference text. The means of the matching results for every reference text level are represented within the aggregated values (null values are ignored).", 
                "mean_per_level0": [],
                "mean_per_level1": [],
            }
            }

        single = 0
        list_level0=[]
        for result in kpi_files:              
            # detailed calculation (e.g. for analysis.txt$esg.1-3.txt.detailed.xlsx)            
            if result["filename"].endswith(".detailed.xlsx"):
                filename = result["filename"]
                content = result["content_binary"]
                file_number = filename.split("$")[1].split(".")[1]  
                level0=file_number.split("-")[0]
                level1=file_number.split("-")[1]           
                with io.BytesIO(content) as fh:
                    df_detailed = pd.io.excel.read_excel(fh, index_col=0)
                    mean_calc = np.nanmean(df_detailed[df_detailed!=0], axis=1) # do not include null values into the mean calculation - calculate over axis
                    df_detailed['mean_similarity'] = mean_calc     
                    df_detailed['fragment'] = range(1, int(len(df_detailed)) + 1)                  
                    for index , row in df_detailed.iterrows():
                        kpivalue["detailed"]["raw_values"].append({"level0":level0, "level1":level1, "fragment": int(row["fragment"]), "similarity":row["mean_similarity"]})
                        # fill text analysis only once in kpivalue
                        if single == 0:
                            ana_text = ILLEGAL_CHARACTERS_RE.sub('_',str(index))  
                            kpivalue["text"]["analysis"].append({"fragment":int(row["fragment"]), "text": ana_text})                    
                    target_mean = np.nanmean(df_detailed['mean_similarity']) # do not include nan values into the mean calculation (e.g. when mean of fragment results to np.nan, 0 is not possible since fragment mean is only calculated on not null)
                    target_mean = (target_mean if target_mean is not np.nan else "None") # scorpio does not accept np.nan 
                    kpivalue["detailed"]["mean_per_level1"].append({"level0":level0, "level1":level1, "similarity": target_mean})
                    single = 1    
                list_level0.append(level0)                         
            
            # coarse calculation  
            elif result["filename"]=="analysis.txt.coarse.xlsx":
                content = result["content_binary"]
                with io.BytesIO(content) as fh:
                    df_coarse = pd.read_excel(fh, engine='openpyxl')    
                    # loop over all rows in df_coarse to identify similarity for each target
                    for _ , row in df_coarse.iterrows():  
                        file_number=row["ref_tag"].split(".")[1]
                        level0=file_number.split("-")[0]
                        level1=file_number.split("-")[1]
                        target_name=row["ref_tag"].split(".")[0]  
                        target_text = row["ref_text"]
                        kpivalue["text"]["reference"].append({"title": target_name, "level0": level0 , "level1": level1, "text": target_text})                                 
                        kpivalue["coarse"]["mean_per_level1"].append({"level0":level0, "level1":level1, "similarity": (row["similarity"] if row["similarity"]!=0 else "None")})  # scorpio does not accept np.nan                 
            else:
                continue             
            
        # try to fill aggregated values        
        list_level0 = list(set(list_level0))            
        sim_per_level0_detailed ={}
        for x in list_level0:
            sim_per_level0_detailed[x]=[]
        for value in kpivalue["detailed"]["mean_per_level1"]:
            level0 = value["level0"]
            sim_per_level0_detailed[value["level0"]].append(value["similarity"])          
        for x in list_level0:               
            try:
                mean_value_detailed = mean(d for d in sim_per_level0_detailed[x] if d is not np.nan) 
            except:
                mean_value_detailed = "None"   # scorpio does not accept None          
            kpivalue["detailed"]["mean_per_level0"].append({"level0":x, "similarity": mean_value_detailed})    

        sim_per_level0_coarse ={}
        for x in list_level0:
            sim_per_level0_coarse[x]=[]
        for value in kpivalue["coarse"]["mean_per_level1"]:
            level0 = value["level0"]
            sim_per_level0_coarse[value["level0"]].append(value["similarity"])          
        for x in list_level0:              
            try:
                mean_value_coarse = mean(d for d in sim_per_level0_coarse[x] if d is not np.nan) 
            except:
                mean_value_coarse = "None"    # scorpio does not accept None                 
            kpivalue["coarse"]["mean_per_level0"].append({"level0":x, "similarity": mean_value_coarse})        
    
    
    except Exception as e:
        logging_text.info(e)
    
    return kpivalue




def create_kpi(org_entity_id, dsr_id, agenda_id, kpi_value, kpi_file_id):
    salted_fileserver_service_pub_addr = os.environ.get("SALTED_FILESERVER_SERVICE_PUB_ADDR")
    
    kpi_id = "urn:ngsi-ld:KeyPerformanceIndicator:" + str(uuid.uuid4())
    kpi = {
        "id": kpi_id,
        "type": "KeyPerformanceIndicator",
        "calculationFrequency": {
            "type": "Property",
            "value": "inquiry dependent"
            },
        "calculationMethod": {
            "type": "Property",
            "value": "automatic"
            },
        "calculationPeriod": {
            "type": "Property",
            "value": {
                "to": str(datetime.utcnow()),
                "from": ""
                }
            },
        "category": {
            "type": "Property",
            "value": [
                "quantitative"
                ]
            },
        "description": {
            "type": "Property",
            "value": "The kpiValue holds information regarding the matching results of the analysis text (e.g. company text) with the reference texts (e.g. the SDGs). The reference texts are structured within 2 levels (for the SDGs this would be goals on level 0 and targets on level 1).  The results are split into results obtained from the corase approach (full analysis text is matched against all reference texts) and the results obtained from the detailed approach (each sentence of the analysis text is matched against all reference texts). The aggregated results for every level can be seen directly in the corresponding property (null values are ignored). The complete (aggregated and raw) results can be downloaded in json format using the supplied link."
            },
        "kpiValue": {
            "type": "Property",
            "value": {
                "aggregated_values": {
                    "detailed": {
                        "mean_per_level0": kpi_value["detailed"]["mean_per_level0"],
                        "mean_per_level1": kpi_value["detailed"]["mean_per_level1"]
                        },
                    "coarse": {
                        "mean_per_level0": kpi_value["coarse"]["mean_per_level0"],
                        "mean_per_level1": kpi_value["coarse"]["mean_per_level1"]
                        }
                },
                "complete_values": salted_fileserver_service_pub_addr+"/files/"+kpi_file_id
                }
            },
        "modifiedAt": {
            "type": "Property",
            "value": {
                "@type": "DateTime",
                "@value": str(datetime.utcnow())
                }
            },
        "name": {
            "type": "Property",
            "value": "Agenda Analytics Matching Scores"
            },
        "organization": {
            "type": "Property",
            "value": org_entity_id
            },
        "process": {
            "type": "Property",
            "value": "urn:ngsi-ld:DataServiceDCAT-AP:Salted-AgendaMatching"
            },
        "provider": {
            "type": "Property",
            "value": "Agenda Analytics (Kybeidos GmbH)"
            },
        "source": {
            "type": "Property",
            "value": [dsr_id, agenda_id]
            },
        "@context": [
            "https://raw.githubusercontent.com/smart-data-models/dataModel.KeyPerformanceIndicator/master/context.jsonld",
            "https://smartdatamodels.org/context.jsonld"
            ]
        }

    return kpi