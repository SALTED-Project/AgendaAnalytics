*******************************************
SALTED service: crawling
*******************************************

REST API using FastAPI & PostgreSQL (+ Observability through Grafana: Prometheus, Tempo, Loki)

This service takes an organization entity and query parameters as input and tries to crawl information.

The service relies on the `AgendaAnalytics-SearchEngine <https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-SearchEngine/README.rst>`_, that has Google-API Access via an API-Token. 
The service relies on some services provided by the `AgendaAnalytics-VDPP <https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-VDPP/README.rst>`_, especially for Crawling.
The service relies on the `AgendaAnalytics-FileServer <https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-FileServer/README.rst>`_ for uploading reference documents to the created NGSI-LD entities.


Fast Info - API Usage
#############################################

URLs:

    * visit API doc: http://localhost:8004/docs#/

This service constist of the following endpoints:

* ``/service/search/webdata/organization/``:

        * this service endpoint takes 6 query parametrs (``approach``, ``keywords``, ``actuality_days``, ``target_agenda_entity_id``, ``custom depth``, ``language`` ) and a list of NGSI-LD entities as input
        * there are 3 main approaches, which have influence on the reasonable occupation of the other parameters:

            * approach: report 

                * for each NGSI-LD entity, google search is used to retrieve the first ``n`` results (suggestion: 1) (set in ``/src/app/settings.yaml GOOGLE_N_RESULTS_REPORT``) with the query: ``f'allintext:{entity_name} {keywords.replace(";"," OR ")} filetype:pdf '`` 
                * the result urls are given to the stormcrawler of the VDPP through the middleware API, which crawls the urls with ``custom depth`` (suggestion: 0) and extract only files of format ``application/pdf``
            
            * approach: website 

                * for each NGSI-LD entity, the url referenced within the entity is given to the stormcrawler of the VDPP through the middleware API, which crawls the url with ``custom depth`` (suggestion: 1) and extract only files of format ``text/html``
                * the result texts are further checked, if ``keywords`` (read as ``;`` separated list) are represented

            * approach: google

                * for each NGSI-LD entity, google search is used to retrieve the first ``n`` results (suggestion: 1) (set in ``/src/app/settings.yaml GOOGLE_N_RESULTS_GOOGLE``) with the query: ``f'site:{entity_url} {keyword}'``  for all keywords given
                * the result urls are given to the stormcrawler of the VDPP through the middleware API, which crawls the urls with ``custom depth`` (suggestion: 0) and extract only files of format ``application/pdf`` and ``text/html``
                
        * the crawling results are persited by the Salted-FileServer and integrated into the DataServiceRun entiy which is given as response, but will also persist in the VDPP mongodb ``crawl_v2`` linked with the unique originator id (f'salted_crawling_service_entityid_{entity_id}') to the NGSI-LD entity 
    

The following section describes the MQTT functionalities (only working, if service was deployed setting ``MQTT_ENABLED=True`` within ``.env`` file):

    * the Crawling service gets triggered by e.g. the Publish Service or the MQTTtrigger service, depending on the pipeline. A example for parameters specified in the mqtt message can be seen in the following:

    .. code-block:: 

        # for the report approach the depth should be 0, to only extract the pdf found
        "parameters": {
            "publish": {},
            "crawling": {
                "approach": "report",
                "actuality_days": "7",
                "keywords": "Nachhaltigkeitsbericht",
                "language": "",  # not used
                "target_agenda_entity_id": "urn:ngsi-ld:DistributionDCAT-AP:f7c6cdd0-3b55-412d-a3d9-0c0fef06fdfd",
                "custom_depth": "0"
                },
            "agendamatching": {
                "agenda_entity_id": "urn:ngsi-ld:DistributionDCAT-AP:f7c6cdd0-3b55-412d-a3d9-0c0fef06fdfd"
                }
        }

        # for the website approach the depth can vary, but ressource limitations should be considered
        "parameters": {
            "publish": {},
            "crawling": {
                "approach": "website",
                "actuality_days": "7",
                "keywords": "Künstliche Intelligenz; Artificial Intelligence; Innovation",
                "language": "de",
                "target_agenda_entity_id": "urn:ngsi-ld:DistributionDCAT-AP:f7c6cdd0-3b55-412d-a3d9-0c0fef06fdfd",
                "custom_depth": "1"
                },
            "agendamatching": {
                "agenda_entity_id": "urn:ngsi-ld:DistributionDCAT-AP:f7c6cdd0-3b55-412d-a3d9-0c0fef06fdfd"
                }
        }

        # for the google approach the depth can vary, adjustments via number of google results (suggestion: 5) should be considered before adjusting crawling depth 
        "parameters": {
            "publish": {},
            "crawling": {
                "approach": "google",
                "actuality_days": "7",
                "keywords": "Künstliche Intelligenz; Artificial Intelligence; Innovation",
                "language": "en",
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
    * SearchEngine service 
    * FileServer service 

Make sure to fill in the ``.env`` file with the correct values for your setup.
Make sure to fill in the ``./src/app/settings.yaml`` file with the correct values for your setup (especially regarding the VDPP service related mongodb user & password in ``VDPP_MONGODB_URI``).

The webserver for serving the fastapi app locally can be started through ``uvicorn --port 8055 app.main:app --reload`` in the ./src directory 

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
        docker-compose -p salted_crawling up -d --build

    * visit API doc: http://localhost:8004/docs#/
    



Inner workings
############################################# 

The service structure (Testing, Logging, Observability, Configuration, Debugging) is set up analog to the `AgendaAnalytics-DiscoverAndStore <https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-DiscoverAndStore/README.rst#inner-workings>`_



NGSI-LD Representation
#############################################

This service is represented within the Scorpio broker in the following way:
(updates are possible, but the id should stay the same, since all generated entities of type DataServiceRun will point to their origin service using the unique id)

.. code-block::
        
        {
            "id": "urn:ngsi-ld:DataServiceDCAT-AP:Salted-Crawling",
            "type": "DataServiceDCAT-AP",
            "alternateName": {
                "type": "Property",
                "value": "Crawling"
            },
            "dataProvider": {
                "type": "Property",
                "value": "Kybeidos GmbH"
            },
            "dataServiceDescription": {
                "type": "Property",
                "value": [
                    "Service that crawls documents for a specific NGSI-LD entity of type Organization"
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
                    "Salted Crawling"
                ]
            },
            "assetProvider": {
                "type": "Property",
                "value": [
                    "https://fastapi.tiangolo.com/",
                    "https://github.com/DigitalPebble/storm-crawler/"
                ]
            },
            "contactPoint": {
                "type": "Property",
                "value": {
                    "name": "contact point for Salted Crawling",
                    "email": "team@agenda-analytics.eu"
                }
            },
            "configuration": {
                "type": "Property",
                "value": [
                    "approach",
                    "custom_depth",
                    "keywords",
                    "actuality_days",
                    "target_agenda_entity_id",
                    "language"
                ]
            },
            "@context": [
                "https://raw.githubusercontent.com/smart-data-models/dataModel.DCAT-AP/ca169c97d519c5ad77c53e00eafdbd2bdbe90e1b/context.jsonld",
                "https://smartdatamodels.org/context.jsonld"
            ]
        }

