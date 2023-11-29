*******************************************
SALTED service: mapping
*******************************************

REST API using FastAPI (+ Observability through Grafana: Prometheus, Tempo, Loki)

This service maps json input to specific NGSI-LD smartdatamodels (see: https://github.com/smart-data-models)

Fast Info - API Usage
#############################################

URLs:

    * visit API doc: http://localhost:8002/docs#/

The API naming convention is the following ``/<EntityType>/<InputFormat>/<SourceService>``

* ``/organization/jsonlist/discoverandstore`` :

    * maps data from the discoverandstore output to the smartdatamodel Organization
    * within the response are all sucessfully mapped entities (entities that are not mapped can be found in docker logs)
    * example curl:


The following section describes the MQTT functionalities (only working, if service was deployed setting ``MQTT_ENABLED=True`` within ``.env`` file):

    * the Mapping service gets triggered by the DiscoverAndStore service
    * the Mapping service offers no further parameters, that need to be specified within the parameter section of the MQTT message




Deployment
#############################################

Make sure to fill in the ``.env`` file with the correct values for your setup.

The webserver for serving the fastapi app locally can be started through ``uvicorn --port 8055 app.main:app --reload`` in the ./src directory 

    * (but only on linux, because within e.g. fastapi_utils some modules are not runnable on windows)
    * make sure, that db container (postgres) is reachable:

        *  connection string in ``./src/app/settings.yaml`` must be adapted, since the services can not reach each other using service names and inner ports if they are not in one docker network
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
        docker-compose -p salted_mapping up -d --build

    * visit API doc: http://localhost:8002/docs#/
    

Inner workings
############################################# 

The service structure (Testing, Logging, Observability, Configuration, Debugging) is set up analog to the `AgendaAnalytics-DiscoverAndStore <https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-DiscoverAndStore/README.rst#inner-workings>`_

