import configparser
from datetime import datetime
import requests
import json
import io
import base64

from folium import IFrame
from folium.plugins import MarkerCluster, FeatureGroupSubGroup
import folium

from branca import element
import branca.colormap as cmp


from shapely.geometry import Point, Polygon
import geopandas as gpd
import pandas as pd
import numpy as np
from sklearn import preprocessing
from sklearn import preprocessing
from urllib.parse import quote
from collections import OrderedDict

import plotly
import plotly.graph_objs as go
import plotly.express as px

import matplotlib.pyplot as plt
from statistics import mean




# get config from ini file
config = configparser.ConfigParser()
configFilePath ='create_map.ini'
config.read(configFilePath)


shp_kr_path =config.get('INPUT', 'shp_kr_file')
shp_la_path =config.get('INPUT', 'shp_la_file')
legend     =config.get('MAP','caption')
map_path1    =config.get('OUTPUT', 'map_file')
map_path2    =config.get('OUTPUT', 'map_copy')
scorpio_api = config.get('SCORPIO', 'api')
scorpio_api_pub = config.get('SCORPIO', 'api_pub')
fileserver_api = config.get('FILESERVER', 'api')
context_organization = config.get('SCORPIO', 'context_organization')
context_dsr = config.get('SCORPIO', 'context_dsr')
context_agenda = config.get('SCORPIO', 'context_agenda')
context_kpi = config.get('SCORPIO', 'context_kpi')

server_url      = config.get('EXCEL', 'server_url')
org_to_excel    = config.get('EXCEL', 'org_to_excel')
score_threshold = config.getfloat('EXCEL', 'score_threshold') 


print ('config file :', configFilePath )
print ('shp_kr_path :', shp_kr_path )
print ('shp_la_path :', shp_la_path )
print ('map_path1    :', map_path1 )
print ('map_path2    :', map_path2 )
print('legend      :',legend)
print('scorpio_api     :',scorpio_api)
print('scorpio_api_pub     :',scorpio_api_pub)
print('fileserver_api     :',fileserver_api)
print('context_organization     :',context_organization)
print('context_dsr:', context_dsr)
print('context_agenda:', context_agenda)
print('context_kpi:', context_kpi)
print('server_url:',server_url)
print('org_to_excel:',org_to_excel)
print('score_threshold:', score_threshold)

#-----------------------------------------------------------------------------------------------------------------
# Functions that are used to generate the map

def get_entities_by_type(entitytype, context):
    # access entities by type within the scorpio broker, using specific context links provided in header
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
        else:
            print(r.text)
            json_entities=[] 
            # broker does not give back attribute values that are null
            # !!! to do: check if different handling is necessary: e.g. append "value": null for concerned attributes
    except:
        json_entities=[]
    return json_entities

def get_entities_by_id(id, context):
    # access entities by type within the scorpio broker, using specific context links provided in header
    url = scorpio_api+"/"+id
    headers = {'Accept': 'application/ld+json','Link': f'<{context}>; rel="http://www.w3.org/ns/json-ld#context"; type="application/ld+json"'}
    r = requests.get(url, headers=headers) 
    print(f"Response from Scorpio for {id}: {r.status_code}")    
    try:
        if r.status_code==200:
            json_entity=r.json()
            # broker does not give back attribute values that are null
            # !!! to do: check if different handling is necessary: e.g. append "value": null for concerned attributes
    except:
        json_entity= None
    return json_entity


def data_prep_import(sh_kr_path,sh_la_path, agenda):
    # create DataFrame, that holds all organization entities, that have location values
    # append information about latest crawling & corresponding matching
    # calculate map popup info for each organization and append to DataFrame
    # append geo info on Gemeinde & Länder (input from shapefiles provided)

    # get agenda id
    agenda_entity_id = agenda["id"]
    
    # get organization's
    organizations = get_entities_by_type("Organization",context_organization)
    print("obtained: ",len(organizations))

    # get dsr's
    dsrs = get_entities_by_type("DataServiceRun",context_dsr)
    print("obtained: ",len(dsrs))

    # get kpi's
    kpis = get_entities_by_type("KeyPerformanceIndicator",context_kpi)
    print("obtained: ",len(kpis))

    
    # setup DataFrame with Organizations (!! if not name, lat or long is specified in entity, it will not be processed for the map!!)
    scorpio_df_orga = pd.DataFrame(columns=["name", "agenda","lat", "lng", "orga_entity_id"])
    for orga in organizations:
        try:
            name = orga["name"]["value"]
            lat = orga["location"]["value"]["coordinates"][0]
            lng = orga["location"]["value"]["coordinates"][1]
        except:
            # print("name, lat or long was not specified")
            continue        
        try:
            # no exception, since name and lat/long are necessary, if not existent it should be skipped
            orga_row = {"orga_entity_id": orga["id"],"name": name, "agenda": agenda_id ,"lat": lat, "lng": lng}
            scorpio_df_orga = pd.concat([scorpio_df_orga, pd.DataFrame([orga_row])], ignore_index=True)
        except Exception as e:
            # print(f"skipped organization row because of: {e}")
            continue
    
    # print(scorpio_df_orga.head())
    print(f"{len(scorpio_df_orga)} rows are in the organization df")

    # setup DataFrame with newest DSRs of Crawling & corresponding AgendaMatching for specific Agenda of interest
    scorpio_df_dsrs_crawling_full = pd.DataFrame(columns=["orga_entity_id", "crawling_dateCreated", "crawling_result_files", "dsr_crawling_entity_id"])
    scorpio_df_dsrs_matching_full = pd.DataFrame(columns=["orga_entity_id", "matching_dateCreated", "matching_result_files","dsr_crawling_entity_id", "dsr_matching_entity_id"])

    for dsr in dsrs:
        try:
            dsr_agenda_id = [configuration["value"] for configuration in (dsr["configuration"]["value"] if isinstance(dsr["configuration"]["value"],list) else [dsr["configuration"]["value"]]) if (configuration["parameter"] in ["target_agenda_entity_id", "agenda_entity_id"])][0]
        except:
            continue
        if "urn:ngsi-ld:DataServiceDCAT-AP:Salted-Crawling" == dsr["service"]["value"]:     
            if (agenda_entity_id == dsr_agenda_id):
                try:
                    sourceEntities= dsr["sourceEntities"]["object"] if isinstance(dsr["sourceEntities"]["object"],list) else [dsr["sourceEntities"]["object"]]
                    crawl_row = {"orga_entity_id": [s for s in sourceEntities if "Organization" in s][0], "crawling_dateCreated": dsr["dateCreated"]["value"], "crawling_result_files": dsr["resultExternal"]["value"] if isinstance(dsr["resultExternal"]["value"],list) else [dsr["resultExternal"]["value"]],  "dsr_crawling_entity_id": dsr["id"] }
                    scorpio_df_dsrs_crawling_full = pd.concat([scorpio_df_dsrs_crawling_full, pd.DataFrame([crawl_row])], ignore_index=True)
                except:
                    continue
            else:
                continue
        
        elif "urn:ngsi-ld:DataServiceDCAT-AP:Salted-AgendaMatching" == dsr["service"]["value"]:
            if (agenda_entity_id == dsr_agenda_id):
                try:
                    sourceEntities= dsr["sourceEntities"]["object"] if isinstance(dsr["sourceEntities"]["object"],list) else [dsr["sourceEntities"]["object"]]
                    agenda_row = {"orga_entity_id": [s for s in sourceEntities if "Organization" in s][0], "matching_dateCreated": dsr["dateCreated"]["value"], "matching_result_files": dsr["resultExternal"]["value"], "dsr_crawling_entity_id": [s for s in sourceEntities if "DataServiceRun" in s][0], "dsr_matching_entity_id": dsr["id"]}
                    scorpio_df_dsrs_matching_full = pd.concat([scorpio_df_dsrs_matching_full, pd.DataFrame([agenda_row])], ignore_index=True)
                except:
                    continue
            else:
                continue
    
    # cleanup AgendaMatching dataframe to only obtain the newest values
    print("creating matching df and add popup info")
    scorpio_df_dsrs_matching = scorpio_df_dsrs_matching_full.sort_values(by=["matching_dateCreated"],axis = 0,ascending=True).drop_duplicates(subset=["orga_entity_id"], keep= "last").copy()

    # add matching score column to the dataframe
    scorpio_df_dsrs_matching["matching_score"]= np.nan
    scorpio_df_dsrs_matching["png_iframe"]= None
    scorpio_df_dsrs_matching["kpi_entity_id"]= None
    
    for index, row in scorpio_df_dsrs_matching.iterrows():
        try:
            # get corresponding KPI entity    
            matching_entity_id = row["dsr_matching_entity_id"]  
            # get first KPI that matches --> should just be one
            kpi_entity = next(filter(lambda kpi: matching_entity_id in kpi["source"]["value"], kpis), None)   
            # check if KPI exists for the DSR of AgendaMatching
            if kpi_entity == None:
                continue
            scorpio_df_dsrs_matching.at[index, "kpi_entity_id"] = kpi_entity["id"]           
            # get complete value from fileserver link
            fileserver_url = fileserver_api+"/"+(kpi_entity["kpiValue"]["value"]["complete_values"]).split("/files/")[-1]
            r = requests.get(fileserver_url)
            kpi_value_full = r.json()
            # get agenda text
            agenda_info_raw = kpi_value_full["text"]["reference"]
            # adapt regarding threshold and reformat (new calculation of means, that repect threshold)
            mean_per_level1_detailed_raw = kpi_value_full["detailed"]["mean_per_level1"]    # example: {'level0': '1', 'level1': '3', 'similarity': 0.2878727668858304}
            mean_per_level0_detailed_raw= kpi_value_full["detailed"]["mean_per_level0"]
            values_detailed_raw = kpi_value_full["detailed"]["raw_values"]  # example: {'level0': '2', 'level1': '4', 'fragment': 29.0, 'similarity': 0.4685954451560974} 
            list_level0 = [value["level0"] for value in mean_per_level0_detailed_raw]          

            mean_per_level1_detailed = []
            for item in mean_per_level1_detailed_raw:
                level0 = item["level0"]
                level1 = item["level1"]
                similarity_values = []
                for raw_value in values_detailed_raw: 
                    if raw_value["level0"]==level0 and raw_value["level1"]==level1:
                        similarity_values.append(raw_value["similarity"])
                # only analysis sentences with score above threshold form the target score
                mean_level1 = np.nanmean( [similarity if similarity > score_threshold else np.nan for similarity in similarity_values ])
                mean_per_level1_detailed.append({'level0': level0, 'level1': level1, 'similarity': mean_level1})
            
            
            sim_per_level0_detailed ={}
            mean_per_level0_detailed={}           
            for x in list_level0:
                sim_per_level0_detailed[x]=[]
            for value in mean_per_level1_detailed:
                level0 = value["level0"]
                sim_value = value["similarity"] # only when all values were below the target value is np.nan
                sim_per_level0_detailed[level0].append(sim_value)          
            for x in list_level0:             
                key = next(filter(lambda agenda_item: agenda_item["level0"]==x, agenda_info_raw), None)["title"]   + "." + x
                mean_value_detailed = np.nansum(sim_per_level0_detailed[x])/len(sim_per_level0_detailed[x]) # form the goal mean from all targets, even when they are np.nan              
                mean_per_level0_detailed[key] = mean_value_detailed
                            
            mean_per_level0_detailed= dict(OrderedDict(sorted(mean_per_level0_detailed.items(), key=lambda t: int(t[0].split(".")[1]))))
            
            mean_similarity=np.nanmean(list(mean_per_level0_detailed.values()))
            scorpio_df_dsrs_matching.at[index, "matching_score"] = (np.nan if np.isnan(mean_similarity) else round(100*mean_similarity))
            
            if np.isnan(mean_similarity) or mean_similarity==0:
                continue

            # create_picture, colors are taken for SGD goals (if more colors are needed, the palette gets used more than once)
            sdg_colors = {'goal': [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17],
                    'color':[ "#e5243b", "#dda63a","#4c9F38", "#c5192d","#ff3a21","#26bde2","#fcc30b","#a21942","#fd6925","#dd1367","#fd9d24","#bf8b2e","#3f7e44","#0a97d9","#56c02b","#00689d","#19486a"]
                        }
            
            level0_colors=sdg_colors
            if len(list_level0)>len(sdg_colors['goal']):
                diff=len(list_level0)-len(sdg_colors['goal'])
                for num in range(1,diff+1):
                    level0_colors["goal"].append(17+num)
                    level0_colors["color"].append(sdg_colors["color"][num])
            elif len(list_level0)<len(sdg_colors['goal']):
                level0_colors["goal"]=level0_colors["goal"][0:len(list_level0)+1]
                level0_colors["color"]=level0_colors["color"][0:len(list_level0)+1]
            
            
            df_colors=pd.DataFrame(level0_colors)
            data_barchart = {'Agenda': list(mean_per_level0_detailed.keys()) , 'Similarity': [0 if np.isnan(item) else item for item in list(mean_per_level0_detailed.values())], 'Color': len(list(mean_per_level0_detailed.keys()))*[None]}
            df_barchart = pd.DataFrame(data=data_barchart)            
            
            for iii in df_barchart.index:
                for jjj in df_colors.index:
                    if str(df_barchart.Agenda[iii].split(".")[1])==str(df_colors.goal[jjj]):
                        df_barchart.loc[iii,'Color']=df_colors.color[jjj]
                        break   
            fig = plt.figure(figsize=(15,10)) # create figure object
            ax = plt.subplot(111, polar=True) # plot polar axis                
            plt.axis('off') # remove grid
            width = 2*np.pi / len(df_barchart.index) # compute the width of each bar - in total we have 2*Pi = 360°
            indexes = list(range(1, len(df_barchart.index)+1)) # compute the angle each bar is centered on
            angles = [element * width for element in indexes]
            heights = df_barchart["Similarity"]
            ax.set_theta_zero_location("N")  # theta=0 at the top
            ax.set_theta_direction(-1)  # theta increasing clockwise
            # draw bars
            bars = ax.bar(
                x=angles, 
                height=heights, 
                width=width, 
                bottom=0,
                linewidth=2, 
                edgecolor="white",
                color=df_barchart["Color"])
              
            # add labels
            memory_padding = df_barchart[df_barchart["Similarity"]!=0]["Similarity"].mean()             
            for angle, height, label in zip(angles, heights, df_barchart["Agenda"].values):
                # labels are rotated (rotation is specified in degrees)
                rotation = np.rad2deg(-angle) + 90
                # flip labels according to their placement
                alignment = ""
                height_label = height
                if angle >= 0 and angle < np.pi:
                    alignment = "left"
                else:
                    rotation = rotation + 180
                    alignment = "right"
                if height<=0:
                    height = 0    
                    labelPadding = memory_padding + 0.005
                else:
                    labelPadding = 0.005  
                number_label = label.split(".")[1]
                text_label_firstline = (" ".join(label.split(".")[0].split(" ")[:-1]) if " ".join(label.split(".")[0].split(" ")[:-1]) != " " else "")
                text_label_secondline = ("\n" + (" ".join(label.split(".")[0].split(" ")[-1:]) + " \u2192 "+ str(round(100*height)) + "%") if text_label_firstline!="" else (" ".join(label.split(".")[0].split(" ")[-1:])+ "\n \u2192 "+ str(round(100*height)) + "%")   )                                                               
                ax.text(
                    x=angle, 
                    y=height + labelPadding,                    
	                s= number_label+"."+ text_label_firstline + text_label_secondline,
                    rotation=rotation,
                    rotation_mode="anchor",
                    ha =alignment,
                    fontsize = 14,
                    #clip_on=True,
                    verticalalignment = "center"
                    ) 
            #plt.tight_layout() # make sure text does not overflow image boundaries 
            plt.subplots_adjust(bottom=0.5)
            png = '/usr/src/app/map/png/{}.png'.format(row["dsr_matching_entity_id"].split("ServiceRun:")[1]) 
            fig.savefig(png, bbox_inches="tight")
            encoded = base64.b64encode(open(png, 'rb').read())
            html = '<div style="text-align: center;"><img src="data:image/png;base64,{}" width=65% ></div>'.format
            html_popup= html(encoded.decode('UTF-8'))
            scorpio_df_dsrs_matching.at[index, "png_iframe"] = html_popup
            plt.close()
        except Exception as e:
            print("An error occured generating png image for map popup:")
            print(e)            
    
    # check if Crawling DataScienceServiceRun id is listed as entry under source_files.value of AgendaMatching DataScienceRun, if yes only keep this one and delete all other crawling runs from df, otherwise keep the newest entry
    scorpio_df_dsrs_crawling = scorpio_df_dsrs_crawling_full.copy()
    for index, row in scorpio_df_dsrs_crawling_full.iterrows():
        if row["dsr_crawling_entity_id"] in scorpio_df_dsrs_matching['dsr_crawling_entity_id'].tolist():
            # delete all crawling runs for this orga_entity_id
            scorpio_df_dsrs_crawling = scorpio_df_dsrs_crawling[scorpio_df_dsrs_crawling["orga_entity_id"] != row["orga_entity_id"]]
            # add only this specific one again
            scorpio_df_dsrs_crawling = pd.concat([scorpio_df_dsrs_crawling, pd.DataFrame([row])], ignore_index=True)
        else:
            scorpio_df_dsrs_crawling = scorpio_df_dsrs_crawling.sort_values(by=["crawling_dateCreated"],axis = 0,ascending=True).drop_duplicates(subset=["orga_entity_id"], keep= "last").copy()

    # merge Crawling and AgendaMatching df
    if scorpio_df_dsrs_matching.empty:
        print("matching df is empty, therefor no merge, only appending of empty columns")
        scorpio_df_dsrs_crawling["matching_dateCreated"]=None
        scorpio_df_dsrs_crawling["matching_result_files"]=None
        scorpio_df_dsrs_crawling["dsr_matching_entity_id"]=None
        scorpio_df_dsrs_crawling["matching_score"]= np.nan
        scorpio_df_dsrs_crawling["png_iframe"]= None
        scorpio_df_dsrs_paired = scorpio_df_dsrs_crawling.copy()
    else:
        scorpio_df_dsrs_paired = scorpio_df_dsrs_crawling.merge(scorpio_df_dsrs_matching, on= ["dsr_crawling_entity_id","orga_entity_id"] , how='left')
 
    # merge all info into dataframe
    scorpio_df = scorpio_df_orga.merge(scorpio_df_dsrs_paired, on= "orga_entity_id" , how='left')

    # output (used by create_excel.py to precalculate reports)
    scorpio_df.to_excel(f"scorpio_df_{agenda_entity_id}.xlsx")  
    
    print("fully merged df, where matching took place:")
    print(scorpio_df[scorpio_df[['matching_result_files']].notnull().all(1)])    
    print("fully merged df, where crawling took place:")
    print(scorpio_df[scorpio_df[['crawling_result_files']].notnull().all(1)])   

    #change the format of geodata to what is needed
    geo_gemeinde= gpd.read_file(sh_kr_path).to_crs(4326)
    geo_laender= gpd.read_file(sh_la_path).to_crs(4326)

    return scorpio_df, geo_gemeinde, geo_laender


def gemeinde_check(data_df, geo_gemeinde):
    # we match the gemeinde id (OBJECTID) in geo_gemeinde with the location of our firms in data_df to find out if the firms
    # are in the right gemeinde. we can not do that by matching the names, as there are many gemeindes in germany with the same name.


    cities_loc_lst= [Point(data_df.loc[i, 'lng'],data_df.loc[i, 'lat']) for i in data_df.index]
    cities_loc_gdf = gpd.GeoDataFrame(geometry=cities_loc_lst, index=data_df.index)

    for i in cities_loc_gdf.index:
        #---
        ct_i=0 ### with this index I check if there is no match or a match out of germany we remove the company (all ###)
        #---
        for j in geo_gemeinde.index:
            if cities_loc_gdf.loc[i,'geometry'].within(geo_gemeinde.loc[j,'geometry']):
                #cities_in_geo[data_df.loc[i,'Ort']]=geo_gemeinde.loc[j,'OBJECTID']
                data_df.loc[i,'gem_id'] = geo_gemeinde.loc[j,'DEBKG_ID']
                data_df.loc[i,'kreis'] = geo_gemeinde.loc[j,'GEN']
                data_df.loc[i, 'Bundesland_code'] = geo_gemeinde.loc[j,'SN_L']
                #---
                ct_i=1 ###
                #---
                break
        #---
        if ct_i==0 or cities_loc_gdf.loc[i,'geometry'].within(geo_gemeinde.loc[387,'geometry']): ### if not in germany or if in Unstrut-Hainich-Kreis (as this is the centr of germany)
            data_df.drop(i,inplace=True) ###
    
    data_df.reset_index(inplace=True)  ###
    #---
            
    for j in data_df.index:
        for i in geo_laender.index:
            if data_df.loc[j,'Bundesland_code']==geo_laender.loc[i,'SN_L']:
                data_df.loc[j,'Bundesland'] = geo_laender.loc[i,'GEN']
                break
            
            
    # we filter geo_gemeinde to include only gemeinde that are in our data_df, to reduce the file size from 11000 to 100 records.
    geo_gemeinde=geo_gemeinde[geo_gemeinde.DEBKG_ID.isin(data_df['gem_id'])]    
    
    return data_df, geo_gemeinde




def data_prep_korp(data_df, server_url,org_to_excel, agenda_entity_id):
    # we make dataframes for länder und gemeinde, and then make a normailzed score for each to color the map with.    
    min_max_scaler = preprocessing.MinMaxScaler()

    #check for matching scores of 0, that can exist when all matchings are under the threshold --> shoukd not be used for mean calculation of areas
    cities_cols = {'kreis': data_df[data_df.matching_score != 0].groupby('gem_id')['matching_score'].mean().index, 
               'matching_score': data_df[data_df.matching_score != 0].groupby('gem_id')['matching_score'].mean().values, 
               'Max_matching_score': data_df[data_df.matching_score != 0].groupby('gem_id')['matching_score'].max().values,
               'gem_id': data_df[data_df.matching_score != 0].groupby('gem_id')['gem_id'].max().values}
    cities_df = pd.DataFrame(cities_cols)
    x = cities_df['matching_score'].values #returns a numpy array
    x_scaled = min_max_scaler.fit_transform(x.reshape(-1, 1))
    cities_df['matching_score_scaled'] = pd.DataFrame(x_scaled)

    states_cols = {'Bundesland': data_df[data_df.matching_score != 0].groupby('Bundesland')['matching_score'].mean().index, 
               'matching_score': data_df[data_df.matching_score != 0].groupby('Bundesland')['matching_score'].mean().values, 
               'Max_matching_score': data_df[data_df.matching_score != 0].groupby('Bundesland')['matching_score'].max().values}
    states_df = pd.DataFrame(states_cols)
    y = states_df['matching_score'].values #returns a numpy array
    y_scaled = min_max_scaler.fit_transform(y.reshape(-1, 1))
    states_df['matching_score_scaled'] = pd.DataFrame(y_scaled)    

    
    for i in data_df.index: 

        try:

            data_df.loc[i,'bp_bund']= data_df['matching_score'].max()
            data_df.loc[i,'bp_ort']= cities_df.loc[cities_df['gem_id'] == data_df.loc[i,'gem_id'],'Max_matching_score'].values
            data_df.loc[i,'bp_land']= states_df.loc[states_df['Bundesland']==data_df.loc[i,'Bundesland'],'Max_matching_score'].values 
            # prepare links for matching results     
            if isinstance(data_df.loc[i,'matching_result_files'],list):        
                matching_text_html = "Corresponding Matching Entity"
                scorpio_matching_url = scorpio_api_pub +"/"+ str(data_df.loc[i,'dsr_matching_entity_id'])
                matching_html='<a href= {scorpio_matching_url}  rel="noopener noreferrer" target="_blank" >{matching_text_html}</a> \n '.format(scorpio_matching_url=scorpio_matching_url,matching_text_html=matching_text_html)
                kpi_text_html = "& Corresponding KPI Entity"
                scorpio_kpi_url = scorpio_api_pub +"/"+ str(data_df.loc[i,'kpi_entity_id'])
                kpi_html = '<a href= {scorpio_kpi_url}  rel="noopener noreferrer" target="_blank" >{kpi_text_html}</a> \n '.format(scorpio_kpi_url=scorpio_kpi_url,kpi_text_html=kpi_text_html)
                domain_createorg='{url}{exl}?org_entity_id={org}&kpi_entity_url={kid}&agenda_entity_url={aid}'.format(org=data_df.loc[i,'orga_entity_id'],
                                                                            url=server_url,
                                                                            exl=org_to_excel,
                                                                            kid=scorpio_kpi_url,
                                                                            aid=scorpio_api_pub +"/"+agenda_id)
                domain_office='https://view.officeapps.live.com/op/embed.aspx?src={url}Compliance_Report_{agenda}_{co}.xlsx'.format(url=server_url,co=data_df.loc[i,'orga_entity_id'],agenda = agenda_entity_id)
                report_html='<a href= {domain_office}  rel="noopener noreferrer" target="_blank" > Open Report </a>      (or <a href= {domain_createorg}  rel="noopener noreferrer" target="_blank" >Generate Report</a>)'.format(domain_office=domain_office,domain_createorg=domain_createorg)
                score = (f"no matching above threshold of {str(round(100*score_threshold))}%" if np.isnan(data_df.loc[i,'matching_score']) else str(round(data_df.loc[i,'matching_score']))+"%")
            else:
                matching_text_html = "No matching has been done yet"
                scorpio_matching_url = ""     
                matching_html='{matching_text_html}'.format(matching_text_html=matching_text_html)
                kpi_html=''
                report_html='<center><i class="fa fa-meh-o"></i></center>'
                score = ("no matching yet")
            
            
            if isinstance(data_df.loc[i,'crawling_result_files'],list): 
                crawling_text_html = "Most recent Crawling Entity"
                scorpio_crawling_url = scorpio_api_pub +"/"+ data_df.loc[i,'dsr_crawling_entity_id']
                crawling_html='<a href= {scorpio_crawling_url}  rel="noopener noreferrer" target="_blank" >{crawling_text_html}</a>'.format(scorpio_crawling_url=scorpio_crawling_url,crawling_text_html=crawling_text_html)
            else:
                crawling_text_html = "No crawling has been done yet"
                scorpio_crawling_url = ""
                crawling_html='{crawling_text_html}'.format(crawling_text_html=crawling_text_html)

        except Exception as e:
            print(e)
            print(i)
            print(data_df.loc[i,:])   
            print(cities_df)
            print(states_df)   
            
        data_df.loc[i,'html'] ="""
        <html style="font-family:arial">
    
    
        <head>
            <title>popup</title>
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css">
        </head>
        <body>
            <p><b>{firm_name}</b></p>
            Overall Agenda Matching Score: {score}
            {png_iframe}
            <p style="font-size:7pt; font-style: italic;" >(*computed by detailed analysis)</p>
            <p style="font-size:7pt; font-style: italic;" >(**matching threshold used for integrating documents: {score_threshold}%)</p>
            <hr/>
            <p> Best-Practice in Deutschland: {bp_bund}
            <p> Best-Practice in {land}: {bp_land}
            <p> Best-Practice in {ort}: {bp_ort}
            <hr/>
            <br/>{report_html}<br/>
            <hr/>
            <p> Take a look at the underlying data within the Scorpio Broker:  
            <ul>
            <li><a href= {scorpio_entity_url}  rel="noopener noreferrer" target="_blank">Organization Entity</a></li>
            <li>{crawling_html}</li>
            <li>{matching_html} {kpi_html} </li>   
            </ul>  
            </p>
        </body>
        </html>

        """.format(bp_bund= ("-" if np.isnan(data_df.loc[i,'bp_bund']) else str(round(data_df.loc[i,'bp_bund']))+"%"),
                bp_ort= ("-" if np.isnan(data_df.loc[i,'bp_ort']) else str(round(data_df.loc[i,'bp_ort']))+"%"), 
                bp_land= ("-" if np.isnan(data_df.loc[i,'bp_land']) else str(round(data_df.loc[i,'bp_land']))+"%"), 
                land=data_df.loc[i,'Bundesland'], 
                ort=data_df.loc[i,'kreis'], 
                firm_name = data_df.loc[i,'name'],
                score = score, 
                scorpio_entity_url = scorpio_api_pub +"/"+ data_df.loc[i,'orga_entity_id'],
                crawling_html=crawling_html,
                matching_html=matching_html,
                kpi_html=kpi_html,
                report_html=report_html,
                png_iframe = ("" if pd.isnull(data_df.loc[i,'png_iframe']) else data_df.loc[i,'png_iframe']),
                score_threshold = round(100*score_threshold)
                )       


    
    return data_df, states_df, cities_df


    

def map_prep (data_df):

    # randomly slide locations to make sure no markers are in the exakt same spot
    data_df['lat'] = data_df['lat'].apply(lambda x: x + np.random.uniform(0.0005, 0.0001))
    data_df['lng'] = data_df['lng'].apply(lambda x: x + np.random.uniform(0.0005, 0.0001))

    
    # location of firms to be plot on the map
    locations = list(zip(data_df['lat'], data_df['lng']))
    
    # we prepare popups. when we click on a firm marker, these popups will appear            
    popups ={}
    
    for i in data_df.index:
        iframe = folium.IFrame(html=data_df.loc[i,'html'], 
                               width=600, 
                               height=400
                              )
        popups[i] = folium.Popup(iframe)   

    return data_df, locations, popups



def map_initiate():
    
    m = folium.Map(location=[50,10], # location of focus is the mean of available firms
                   zoom_start=6,
                   max_bounds=True,
                   min_zoom=5,
                   max_zoom=18,
                   min_lat=42, 
                   max_lat=57, 
                   min_lon=-10, 
                   max_lon=30, 
                   control_scale=True, 
                   tiles=None
                  ) 
    
    folium.TileLayer('cartodbpositron',
                     overlay = False,
                     min_zoom = 5,
                     max_zoom = 18,
                     show = True,
                     name='Leicht').add_to(m)
    
    folium.TileLayer('stamenterrain',
                     overlay = False,
                     min_zoom = 5,
                     max_zoom = 18,
                     show = False, 
                     name='Terrain').add_to(m)
    
    folium.TileLayer('OpenStreetMap',
                     overlay = False,
                     min_zoom = 5,
                     max_zoom = 18,
                     show = False,
                     name='Open Street Map').add_to(m)

    return m

def map_create(m, data_df,laender_df, gemeinde_df, geo_laender, geo_gemeinde, locations, popups, legend, agenda_entity_id, agenda_name, other_agendas):    
  
    # get min and max scores for flexible legend 
    min_matching_all = (np.nanmin(data_df[data_df.matching_score != 0]['matching_score'].values) if np.isnan(np.nanmin(data_df[data_df.matching_score != 0]['matching_score'].values))==False else 0)
    max_matching_all = (np.nanmax(data_df['matching_score'].values) if np.isnan(np.nanmax(data_df['matching_score'].values))==False else 0)

    # color scheme 1
    # step = cmp.StepColormap(
    #     [ '#0B3D4F', '#1B6986', '#248CB3','#DD7A57', '#FC5F26', '#BD471C'],
    #     vmin=0, vmax=100,
    #     index=[0, 10, 30, 50, 70, 90, 100],  #for change in the colors, not used for linear
    #     caption=legend    #Caption for Color scale or Legend
    # )   
    #  
    # color scheme 2
    # step = cmp.StepColormap(
    #     [ '#e34234', '#ef7460', '#f69f8e', '#92be89', '#61a557', '#228b22'], 
    #     vmin=0, vmax=100,
    #     index=[0, 40, 45, 50, 55,  60, 100],  #for change in the colors, not used for linear
    #     caption=legend    #Caption for Color scale or Legend
    # )    

    # color scheme 3
    step = cmp.StepColormap(
        [
            "#E34234",  # Red
            "#DD4D31",
            "#D6572E",
            "#D0622B",
            "#C96C28",
            "#C27725",  
            "#BB8122",  
            "#B68B1F",
            "#B1951C",
            "#AFAF1A",
            "#9BB219",
            "#8AA918",  
            "#7A9317",  
            "#6A8C16",  
            "#598515",  
            "#4A7F14"   # Green
        ],
        vmin=round(min_matching_all), 
        vmax=round(max_matching_all),
        caption=legend    #Caption for Color scale or Legend
    ) 

    # if this part gets calculated even when not matching value is present the code runs into an index error on th np.nan values of matching_score
    if np.nansum(data_df["matching_score"].values) != 0:  
    
        # handle nan values, since na_fill_color does not work
        laender_df = laender_df[laender_df['matching_score'].notna()]  
        laender_df_dict = laender_df.set_index('Bundesland')['matching_score']
        lst = laender_df['Bundesland']
        geo_laender_current=geo_laender.query('GEN in @lst')
        geo_laender_json = geo_laender_current.to_json()
        geo_laender_dict = json.loads(geo_laender_json)   

        laender= folium.GeoJson(
            geo_laender_dict,
            style_function=lambda x: {
                'fillColor': step(laender_df_dict[x['properties']['GEN']]),
                'color': '#1B6986',       #border color for the color fills
                'weight': 1,            #how thick the border has to be
                'opacity': 1,
                'fillOpacity': 0.3
            },
            highlight_function=lambda x: {'weight':5, 'color':'#1B6986'},
            smooth_factor=2.0,
            tooltip=folium.features.GeoJsonTooltip(
                fields=['GEN'],
                labels=False
            ),
            name='States',   
            zoom_on_click= True,
            show= True
        ).add_to(m)    
    
        # handle nan values, since na_fill_color does not work
        gemeinde_df = gemeinde_df[gemeinde_df['matching_score'].notna()] 
        gemeinde_df_dict = gemeinde_df.set_index('kreis')['matching_score']
        lst = gemeinde_df['kreis']
        geo_gemeinde_current=geo_gemeinde.query('DEBKG_ID in @lst')
        geo_gemeinde_json = geo_gemeinde_current.to_json()
        geo_gemeinde_dict = json.loads(geo_gemeinde_json)

        gemeinde= folium.GeoJson(
            geo_gemeinde_dict,
            style_function=lambda x: {
                'fillColor': step(gemeinde_df_dict[x['properties']['DEBKG_ID']]),
                'color': '#1B6986',       #border color for the color fills
                'weight': 1,            #how thick the border has to be
                'opacity': 1,
                'fillOpacity': 0.3
            },
            highlight_function=lambda x: {'weight':5, 'color':'#1B6986'},
            smooth_factor=2.0,
            tooltip=folium.features.GeoJsonTooltip(
                fields=['GEN'],
                labels=False                
            ),
            name='Counties',   
            zoom_on_click= True,
            show= False
        ).add_to(m)

        
    step.add_to(m)     

    m.get_root().header.add_child(element.CssLink('./style.css')) # style.css needs to be supplied to webserver 


    # prepare links for other agendas
    other_agendas_html = ""
    for agenda in agendas:
        aid = server_url +"/"+agenda["id"] + ".html"
        agenda = agenda["name"]["value"]
        html = f'<a class=custom-small href= {aid}  rel="noopener noreferrer" target="_blank">{agenda}<span id=customsidebar_point>.</span></a><br><hr/>'
        other_agendas_html= other_agendas_html + html
    
    
    sidebar_html = '''
                <header id=customsidebar> 
                    <div id=customsidebar_link_frame>
                        <a href= {aid}  rel="noopener noreferrer" target="_blank">{agenda}<span id=customsidebar_point>.</span></a> 
                        <br>
                        <br>
                        Other agendas: 
                        <hr/>
                        {other_agendas} 
                        <br>        
                        <a href="https://www.kybeidos.de/loesungen/grc"rel="noopener noreferrer" target="_blank">Agenda Analytics</a>           
                    </div>
                    <a id=customsidebar_link_kybeidos href="http://www.kybeidos.de"><img src="./Logo.svg"></a>                    
                </header>
                '''.format(aid=scorpio_api_pub +"/"+ agenda_entity_id, agenda = agenda_name, other_agendas = other_agendas_html )
                                  
    m.get_root().html.add_child(folium.Element(sidebar_html))   
    
    marker_cluster = MarkerCluster(name= 'Companies', show= False, control = False, disableClusteringAtZoom=8)

    sub1 = folium.plugins.FeatureGroupSubGroup(marker_cluster, u'\u2B68 Companies (status=discovered)', control = True ) 
    sub2 = folium.plugins.FeatureGroupSubGroup(marker_cluster, u'\u2B68 Companies (status=crawled)',control = True  )  
    sub3 = folium.plugins.FeatureGroupSubGroup(marker_cluster, u'\u2B68 Companies (status=matched)' , control = True )  

    print(data_df.head())
    # we make marker signs based on the search_hits
    for i in data_df.index:
        try:
            j = int(i) 
            if isinstance(data_df['matching_result_files'].iloc[j],list):
                marker = folium.Marker(
                    location=locations[j],
                    popup=popups[i],
                    tooltip=data_df['name'].iloc[j],
                    icon=folium.Icon(color="green", icon="ok-sign")
                )
                sub3.add_child(marker)


            elif isinstance(data_df['crawling_result_files'].iloc[j],list): 
                marker = folium.Marker(
                    location=locations[j],
                    popup=popups[i],
                    tooltip=data_df['name'].iloc[j],
                    icon=folium.Icon(color="blue", icon='file-arrow-down', prefix="fa")
                )
                sub2.add_child(marker)

                
            else:
                marker = folium.Marker(
                        location=locations[j],
                        popup=popups[i],
                        tooltip=data_df['name'].iloc[j],
                        icon=folium.Icon(color="orange", icon='exclamation-sign')
                )
                sub1.add_child(marker) 
                
        except Exception as e:
            print(e)

    marker_cluster.add_to(m)
    sub1.add_to(m)
    sub2.add_to(m)
    sub3.add_to(m)
    
    return m


def map_finalise(m):

    folium.LayerControl(collapsed=False).add_to(m)    
    
    return m
    
    

##-----------------------------------------------------------------------------------------------------------
# get all agendas within the broker
agendas = get_entities_by_type("DistributionDCAT-AP", context_agenda)

print("The following agendas were obtained:")
for agenda in agendas:
    print(agenda["id"])

for agenda in agendas:

    try:
        agenda_name = agenda["name"]["value"]
        agenda_id = agenda["id"]

        other_agendas = agendas.copy()
        other_agendas = other_agendas.remove(agenda)
        ##-----------------------------------------------------------------------------------------------------------

        # Map Data Preparation
        print("############################################")
        print("############################################")
        print("############################################")
        print ('agenda     :', agenda_name, 'id     :',agenda_id, 'start     :', datetime.now().strftime("%H:%M:%S") )
            

        # import data from data sources 
        data_df,geo_gemeinde, geo_laender = data_prep_import(shp_kr_path,shp_la_path, agenda)
        print ('data_prep_import    :', datetime.now().strftime("%H:%M:%S") )

        ##-----------------------------------

        # check if the companies are in the right district, because there are many districts with the same name in germany
        # and include only those districts who has a match in our data. otherwise the map will be too heavy
        data_df, geo_gemeinde = gemeinde_check(data_df, geo_gemeinde)
        print(data_df.head())
        print ('gemeinde_check    :', datetime.now().strftime("%H:%M:%S") )
        #---------------------------------

        # calculate data for maps, normalise them, and prepare popups
        data_df, laender_df, gemeinde_df = data_prep_korp(data_df, server_url,org_to_excel,agenda_id)
        print ('data_prep_korp    :', datetime.now().strftime("%H:%M:%S") )

        ##---------------------------------------

        #---------------------------------------------------------------------------------------------------------
        # map creation
            

        data_df, locations, popups = map_prep(data_df)
        print ('map_prep    :', datetime.now().strftime("%H:%M:%S") )

        m = map_initiate()

        m = map_create(m, data_df,laender_df, gemeinde_df, geo_laender, geo_gemeinde, locations, popups,legend, agenda_id, agenda_name, other_agendas)
        print ('map_create    :', datetime.now().strftime("%H:%M:%S") )

        m = map_finalise(m)
        print ('map_finalise    :', datetime.now().strftime("%H:%M:%S") )       

        m.save(map_path1+agenda_id+".html")
        print ('map_save1    :', datetime.now().strftime("%H:%M:%S") )

        m.save(map_path2+agenda_id+"_"+datetime.now().strftime("%Y.%m.%d_%H%M%S")+".html") 
        print ('map_save2    :', datetime.now().strftime("%H:%M:%S") )
        

    except Exception as e:
        print(e)
        continue





