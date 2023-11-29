*******************************************
SALTED service: MQTTtrigger
*******************************************

REST API using FastAPI (+ Observability through Grafana: Prometheus, Tempo, Loki)

This service offers different possibilities to trigger Agenda Analytics pipelines within the SALTED infrastructure.

Fast Info - API Usage
#############################################

URLs:

    * visit API doc: http://localhost:8007/docs#/
    * visit grafana dashboard: see https://github.com/SALTED-Project/AgendaAnalytics/tree/master/services/AgendaAnalytics-MQTTtrigger
    * see all stats given to Prometheus: see https://github.com/SALTED-Project/AgendaAnalytics/tree/master/services/AgendaAnalytics-Commons



The following shows and example of the general mqtt message setup for all mqtt services:

.. code-block:: 

    {"parameters": {
        "discoverandstore": {
                "searchscope" : "" , # since no new organizations should be searched (alternatives: wikipedia, osm)
                "enrichscope" : ""   # since no enriching of the DiscoverAndStore database should take place (alternatives: google, osm)
            },
        "mapping": {},
        "publish": {},
        "crawling": {
            "approach": "report",
            "custom_depth": "0",
            "actuality_days": "7",
            "language": "de",
            "keywords": "Nachhaltigkeitsbericht filetype:pdf",
            "target_agenda_entity_id": "urn:ngsi-ld:DistributionDCAT-AP:f7c6cdd0-3b55-412d-a3d9-0c0fef06fdfd"
        },
        "agendamatching": {
            "agenda_entity_id": "urn:ngsi-ld:DistributionDCAT-AP:f7c6cdd0-3b55-412d-a3d9-0c0fef06fdfd"
        }
    },
    "data": {[<list of NGSI_LD entities>]} # make sure, that provided NGSI-LD entities have clear attribute names and the context supplied within the @context-attribute, since the services might search e.g. for the ``url`` attribute and will not find it, when it is provided via ``https://smart-data-models.github.io/data-models/terms.jsonld#/definitions/url``
    }
  

The provided endpoints are divided into 4 main groups:

    * data injection + enrichment toolchain

        * ``/trigger/dit-det/organization/specific`` : triggers a pipeline that performs publishing, crawling and agenda matching for the supplied NGSI-LD organization entity
    
    * data incetion toolchain

        * ``/trigger/dit/organization/general``: triggers a pipeline for the general discovery, mapping and publishing of organizations 

    * data enrichment toolchain

        * ``/trigger/det/crawling_service/specific``: triggers crawling for one specific organization entity
        * ``/trigger/det/crawling_service/general``: triggers crawling for all organizations within the broker
        * ``/trigger/det/agendamatching_service/specific``: triggers agenda matching for one specific organization, if it has crawled data regarding that specific agenda
        * ``/trigger/det/agendamatching_service/general``: triggers agenda matching for all organizations within the broker that have crawled data regarding the specific agenda

        
Deployment
#############################################

The webserver for serving the fastapi app locally can be started through ``uvicorn --port 8055 app.main:app --reload`` in the ``./src`` directory 

    * (but only on linux, because within e.g. fastapi_utils some modules are not runnable on windows)
    * make sure, that db container (postgres) is reachable:

        * connection string in ``./src/app/settings.yaml`` must be adapted, since the services can not reach each other using service names and inner ports if they are not in one docker network
        * make sure, that connection string in ``./src/app/settings.yaml`` fits with specified ports in ``.env`` 

For deploying all services using docker:
    
    .. code-block::
        
        # inside root directory where docker-compose.yaml is
        # for clean start up
        ./service.sh start

        # for a clean stop
        ./service.sh stop

        # quick & without testing
        docker-compose -p salted_mqtttrigger up -d --build

    * visit API doc: http://localhost:8007/docs#/
    

Inner workings
############################################# 

The service structure (Testing, Logging, Observability, Configuration, Debugging) is set up analog to the `AgendaAnalytics-DiscoverAndStore <https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-DiscoverAndStore/README.rst#inner-workings>`_ .
