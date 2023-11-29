import configparser
import pandas as pd
import requests

config = configparser.ConfigParser()
configFilePath ='create_map.ini'   
config.read(configFilePath)


scorpio_api = config.get('SCORPIO', 'api')
context_organization = config.get('SCORPIO', 'context_organization')
context_dsr = config.get('SCORPIO', 'context_dsr')
server_url      = config.get('EXCEL', 'server_url')
org_to_excel    = config.get('EXCEL', 'org_to_excel')
context_agenda = config.get('SCORPIO', 'context_agenda')

def get_entities_by_type(entitytype, context):
    # access entities by type within the scorpio broker, using specific context links provided in header
    # return entities as json
    url = scorpio_api
    headers = {'Accept': 'application/ld+json','Link': f'<{context}>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"'}
    params = {'type' : entitytype}
    r = requests.get(url, headers=headers, params=params) 
    print(f"Response from Scorpio for {entitytype}: {r.status_code}")    
    try:
        if r.status_code==200:
            json_entities=r.json()
            if not isinstance(json_entities,list):
                json_entities=[json_entities]     
            # broker does not give back attribute values that are null
            # !!! to do: check if different handling is necessary: e.g. append "value": null for concerned attributes
        else:
            print(r.text)
            json_entities=[]   
    except:
        json_entities= None
    return json_entities

# get all agendas within the broker
agendas = get_entities_by_type("DistributionDCAT-AP", context_agenda)

print("The following agendas were obtained:")
for agenda in agendas:
    print(agenda["id"])

for agenda in agendas:

    agenda_name = agenda["name"]["value"]
    agenda_id = agenda["id"]

    try:
        scorpio_df = pd.read_excel(f"scorpio_df_{agenda_id}.xlsx", index_col=0)  
        scorpio_df_kpi = scorpio_df[scorpio_df['kpi_entity_id'].notnull()]


        print(scorpio_df_kpi)

        for index, row in scorpio_df_kpi.iterrows():   
            org_entity_id = row["orga_entity_id"]
            print("starting excel creation for:")
            print(org_entity_id)
            kpi_entity_id = row ["kpi_entity_id"]
            url='{url}{exl}?org_entity_id={org}&kpi_entity_url={mid}&agenda_entity_url={aid}'.format(org=org_entity_id,
                                                                                url=server_url,
                                                                                exl=org_to_excel,
                                                                                mid=scorpio_api+"/"+kpi_entity_id,
                                                                                aid=scorpio_api+"/"+agenda_id)
            try:
                r = requests.get(url)
                print(r.status_code)
                print(r.content)
            except Exception as e: 
                print(e)
                
    except Exception as e:
        print(e)




        
