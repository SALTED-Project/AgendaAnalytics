*******************************************
SALTED service: AgendaMatching
*******************************************

REST API using FastAPI & PostgreSQL (+ Observability through Grafana: Prometheus, Tempo, Loki)

This service performs the matching of texts to user specified agendas of interest.

The service relies on `AgendaAnalytics-VDPP <https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-VDPP/README.rst>`_ for converting PDF to Text.
The service relies on the `AgendaAnalytics-SimCore <https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-SimCore/README.rst>`_ for the actual matching.
The service relies on the `AgendaAnalytics-FileServer <https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-FileServer/README.rst>`_ for uploading reference documents to the created NGSI-LD entities.


Fast Info - API Usage
#############################################

URLs:

    * visit API doc: http://localhost:8005/docs#/


This service constist of the following endpoints:

    * ``/matching/<entity_id>/<agenda_entity_id>`` :

        * checks scorpio broker for corresponding DataServiceRun from Salted-Crawling service, with respect to targeted agenda 
        * transfers & converts pdf to text via vdpp middleware if necessary (files temporarely saved in VDPP mongodb collection ``salted_agendamatching_tmp_{entity_id_cut}``) 
        * concatenates all raw texts and saves temporarely in docker container filesystem directory ``/home/{entity_id_cut}``
        * downloads requested agenda, if not already present in ``/usr/src/app/refcorpora/{agenda_entity_id_cut}/`` 
        * uses simcore service to compute similarities regarding the given agenda
        * response is DataServiceRun entity that refers to the source files and result files and a KeyPerformanceIndicator that holds aggregated results anda download link to a json representation of the raw values

    
    * ``/agenda/text`` :

        * upload endpoint for text files representing an agenda
        * expected are agendas with max 2 levels <level0name>.<level0>-<level1>.txt: e.g. Armut.1-1.txt or Hunger.2-3.txt (the level0name can be used to specify level0 in more detail, e.g. Köpfe.1-1 and Forschung.1-1, but can also be a generic name like sdg - it will be used in the map popup vizualisation)
        * if only one level is supplied, it will look like <level0name>.<level0>-1.txt: e.g. Armut.1-1.txt, Hunger.2-1.txt
        * the name parameter is used for the reports and specifies the agenda e.g. Sustainable Development Goals, Environmental Social Governance, ...
        * the endpoint returns a NGSI-LD entity of type DistributionDCAT-AP that needs to be posted to the broker (the entity contains a plain text representation, which is not used by other services at the moment - they rely on the downloadURL)
        


The following section describes the MQTT functionalities (only working, if service was deployed setting ``MQTT_ENABLED=True`` within ``.env`` file):

    * the AgendaMatching service gets triggered by e.g. the Publish Service or the Crawling Service or the MQTT trigger service depending on the pipeline. A example for parameters specified in the mqtt message can be seen in the following:

    .. code-block:: 

        "parameters": {
            "publish": {},
            "crawling": {
                "approach": "report",
                "actuality_days": "7",
                "keywords": "Nachhaltigkeitsbericht",
                "target_agenda_entity_id": "urn:ngsi-ld:DistributionDCAT-AP:f7c6cdd0-3b55-412d-a3d9-0c0fef06fdfd",
                "custom_depth": "0"
                },
            "agendamatching": {
                "agenda_entity_id": "urn:ngsi-ld:DistributionDCAT-AP:f7c6cdd0-3b55-412d-a3d9-0c0fef06fdfd"
                }
        }   
        


Deployment
#############################################

Make sure the required services are deployed first:

    * VDPP service
    * SimCore service 
    * FileServer service 

Make sure to fill in the ``.env`` file with the correct values for your setup.
Make sure to fill in the ``./src/app/settings.yaml`` file with the correct values for your setup (especially regarding the VDPP service related mongodb user & password in ``VDPP_MONGODB_URI``).


The webserver for serving the FastAPI app locally can be started through ``uvicorn --port 8055 app.main:app --reload`` in the ``./src`` directory 

    * (but only on linux, because within e.g. fastapi_utils some modules are not runnable on windows)
    * make sure, that db container (postgres) is reachable:

        * connection string in ``./src/app/settings.yaml`` must be adapted, since the services can not reach each other using service names and inner ports if they are not in one docker network
        * make sure, that connection string in ``./src/app/settings.yaml`` fits with specified ports in ``.env`` 

For deploying all services using docker:
    
    .. code-block::
        
        # adapt docker-compose.yaml and comment in the volume mounts of the service for developing purposes
        # inside root directory where docker-compose.yaml is
        # for clean start up
        ./service.sh start

        # for a clean stop
        ./service.sh stop

        # quick & without testing
        docker-compose -p salted_agendamatching up -d --build

    * visit API doc: http://localhost:8005/docs#/



Inner workings
############################################# 

The service structure (Testing, Logging, Observability, Configuration, Debugging) is set up analog to the `AgendaAnalytics-DiscoverAndStore <https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-DiscoverAndStore/README.rst#inner-workings>`_ .



NGSI-LD Representation of the service
#############################################

This service is represented within the Scorpio broker in the following way:
(updates are possible, but the id should stay the same, since all generated entities of type DataServiceRun will point to their origin service using the unique id)

.. code-block::
        
        {
            "id": "urn:ngsi-ld:DataServiceDCAT-AP:Salted-AgendaMatching",
            "type": "DataServiceDCAT-AP",
            "alternateName": {
                "type": "Property",
                "value": "AgendaMatching"
            },
            "dataProvider": {
                "type": "Property",
                "value": "Kybeidos GmbH"
            },
            "dataServiceDescription": {
                "type": "Property",
                "value": [
                    "Service that matches documents identified by Salted-Crawling (type DataServiceDCAT-AP) for a specific NGSI-LD entity of type Organization with the a specific agenda."
                ]
            },
            "dateCreated": {
                "type": "Property",
                "value": "2023-06-09T08:00:00Z"
            },
            "dateModified": {
                "type": "Property",
                "value": "2023-06-09T08:00:00Z"
            },
            "description": {
                "type": "Property",
                "value": "Data service for the SALTED Data Enrichment Toolchain"
            },
            "endPointDescription": {
                "type": "Property",
                "value": [
                    "FAST API end point without authentication",
                    "REST API compliant"
                ]
            },
            "endPointURL": {
                "type": "Property",
                "value": [
                    "internal"
                ]
            },
            "seeAlso": {
                "type": "Property",
                "value": [
                    "https://salted-project.eu/"
                ]
            },
            "servesDataset": {
                "type": "Property",
                "value": [
                    "NGSI-LD entities of type DataServiceRun"
                ]
            },
            "title": {
                "type": "Property",
                "value": [
                    "Salted AgendaMatching"
                ]
            },
            "assetProvider": {
                "type": "Property",
                "value": [
                    "https://fastapi.tiangolo.com/"
                ]
            },
            "contactPoint": {
                "type": "Property",
                "value": {
                    "name": "contact point for Salted AgendaMatching",
                    "email": "team@agenda-analytics.eu"
                }
            },
            "configuration": {
                "type": "Property",
                "value": ["agenda_entity_id"]
            },
            "@context": [
                "https://raw.githubusercontent.com/smart-data-models/dataModel.DCAT-AP/ca169c97d519c5ad77c53e00eafdbd2bdbe90e1b/context.jsonld",
                "https://smartdatamodels.org/context.jsonld"
            ]
        }
        
        

