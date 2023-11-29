*******************************************
SALTED service: publish
*******************************************

REST API using FastAPI (+ Observability through Grafana: Prometheus, Tempo, Loki)

This service acts mainly as an upload interface to the Scorpio broker for other SALTED services. This way no other service has to implement upload procedures like checking for already existing entities, appending or updating existing entities.
Further this service holds information regarding the contexts used for uploads, which enables the service to offer endpoints for requesting entities from the broker without user input concerning contexts.
This service can also be used to query the broker for entities of a certain type, using the default context described above, which results in already dissolved attribute names in the results.

Fast Info - API Usage
#############################################

URLs:

    * visit API doc: http://localhost:8003/docs#/


General info about the Scorpio API can be found at: https://scorpio.readthedocs.io/en/latest/API_walkthrough.html


This service constist of the following endpoints:

    * ``POST /publish/jsonlist``:

        * tries to publish / add the given information to the scorpio broker
        * works in the follwong steps:

            * tries to add as new entity 
            * if entity already exists, it tries to append all attributes - already existing attributes will get overwritten

                * check for already existing entity is entity type dependent
                * service compares with all already present entities of the same type for the same:
                    
                    * name ['Organization','EVChargingStation', 'DistributionDCAT-AP']
                    * stationName ['BikeHireDockingStation']
                    * title ['DataServiceDCAT-AP']
                    * source ['KeyPerformanceIndicator']
            
            * info: timeline of "overriding" on all organization entities can be seen under e.g.: ``ngsi-ld/v1/temporal/entities?=Organization&lastN=3`` . The instance-id of each attribute value allows for identification. (Detailed information can be found in scorpio's postgres db tables: ngb.public.temporalentityattrinstance)    
            * if scorpio entity holds more information than the one given as input, the existing entity will be updated with the given information. Not touched attributes stay.
            * retruns all information that could be written to scorpio / aligned with information in scorpio.
    
    * ``GET /broker/entities/{entitytype}``

        * offers an endpoint that retrieves entities from the broker, supplying the default context described above, which results in already dissolved attribute names in the results.

    * ``POST`` and ``GET`` ``/pastebin/...`` :

        * offers the possibility to upload data and use ist later via a ``GET`` - request (needed especially, when supplying context within the header of Scorpio request)
        * the ``defaultcontext`` endpoints show the context used for each entity type that is uploaded via this service.



The following section describes the MQTT functionalities (only working, if service was deployed setting ``MQTT_ENABLED=True`` within ``.env`` file):

    * the Publish service gets triggered by the Mapping Service (Organization type) and the Crawling / AgendaMatching Service (DataServiceRun, KeyPerformanceIndicator types) - the handling is entity type agnostic 
    * the Publish service offers no further parameters, that need to be specified within the parameter section of the MQTT message


Deployment
#############################################

Make sure to fill in the ``.env`` file with the correct values for your setup.

The webserver for serving the fastapi app locally can be started through ``uvicorn --port 8055 app.main:app --reload`` in the ./src directory 

    * (but only on linux, because within e.g. fastapi_utils some modules are not runnable on windows)
    * make sure, that db container (postgres) is reachable:

        * connection string in ``./src/app/settings.yaml`` must be adapted, since the services can not reach each other using service names and inner ports if they are not in one docker network
        * make sure, that connection string in ``./src/app/settings.yaml`` fits with specified ports in ``.env`` 

For deploying all services using docker:
    
    .. code-block::
        
        # adapt docker-compose.yaml and comment in the volume mounts of the service for developing purposes if needed
        # inside root directory where docker-compose.yaml is
        # for clean start up
        ./service.sh start

        # for a clean stop
        ./service.sh stop

        # quick & without testing
        docker-compose -p salted_publish up -d --build

    * visit API doc: http://localhost:8003/docs#/


Inner workings
############################################# 

The service structure (Testing, Logging, Observability, Configuration, Debugging) is set up analog to the `AgendaAnalytics-DiscoverAndStore <https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-DiscoverAndStore/README.rst#inner-workings>`_ .



Steps for adding new entity type
#############################################

* add defaultcontext - endpoint in ``./src/app/main.py``
* add tests for new entity type in ``./src/tests/test_main.py``
* add ruleset for identifying identical entities in ``./src/app/api/scorpio_middleware.py``



