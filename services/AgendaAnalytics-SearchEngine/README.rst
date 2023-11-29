*******************************************
SALTED service: searchengine
*******************************************

REST API using FastAPI & PostgreSQL 

The Search Engine(SE) Service take domain names along with the search term to crawl information in Google engine. 



Fast Info - API Usage
#############################################

URLs:

    * visit API doc: http://localhost:8000/docs#/


This service constist of the following endpoint:

* /google/searchengine/


Additional info:

* this endpoints takes 4 query parameters (searchquery, engine, number_search_results, language)
* "searchquery" (str): could be "Aktuelle Neuigkeiten für Heidelberg" but also "site:mrn.com Nachhaltigkeit"
* "engine" (str): you pass "google" for google end point 
* "number_search_results" (int): The min and max number can be passed is 10 & 60.
* "language" (str): for google e.g. "en" (will be completetd to "lang_en" by the service) 
* The output for the requested search query is json, which is saved back in DB.
* The following entities searchquery, engine, number_search_results, language, api_json_output, first_requested_query & modified are saved in DB.
* The service checks for persited requests in the db, that could be used to generate a response, if its not older than 24 hours


The query limit can be set in the ``.env`` file. The default is 1000 queries per day. If the limit is reached, the service will return a error code.

Deployment
#############################################

Make sure to fill in the ``.env`` file with the correct values for your setup.

The webserver for serving the fastapi app locally can be started through ``uvicorn --port 8055 app.main:app --reload`` in the ``./src`` directory 

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
        docker-compose -p salted_searchengine_service up -d --build

    * visit API doc: http://localhost:8009/docs#/


Inner workings
############################################# 

The service structure (Testing, Logging, Observability, Configuration, Debugging) is set up analog to the `AgendaAnalytics-DiscoverAndStore <https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-DiscoverAndStore/README.rst#inner-workings>`_ .
    






