*******************************************
SALTED service: discover company data and store 
*******************************************

REST API using FastAPI & PostgreSQL (+ Observability through Grafana: Prometheus, Tempo, Loki)

This service automatically searches for organizations within Open Street Map and Wikipedia. Results will be obtained in a database. 
The database can be queried for further usage.

For the google enriching the service relies on the `AgendaAnalytics-SearchEngine <https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-SearchEngine/README.rst>`_ , that has Google-API Access via an API-Token. 



Fast Info - API Usage
#############################################

URLs:

    * visit API doc: http://localhost:8001/docs#/


The API is divided into the paths under ``./service/...``  and ``./organizations/...`` . 

The service endpoints handle the start of different tasks regarding the search for new organizations and the enriching of the ones already in the database. The response always contains the full databse records to the organizations "touched" by this service.
The orgnaizations endpoints handle easy CRUD operations on the database.

The following section describes the service endpoints:

* ``/service/search/wikipedia`` :

    * crawls wiki table and saves in dataframe
    * checks for each dataframe entry, if the organization name is already present in the db
    * only new organizations are written to db
    * returns all database entries that were affected, also the ones that were found but already present (! if one wants to see everything in the datbase a GET http://localhost:8001/organizations/ must be performed)
    * example curl:

    .. code-block::

        curl -XGET -H 'Content-Type: application/json'  http://localhost:8001/service/search/wikipedia        

* ``/service/search/osm/{countrycode}`` :

    * crawls open street map to get new organizations within 
        
        * the country code (e.g. "08" for Baden Würrtemberg or "none" for all of Germany ) and
        * office keys for semi-governmental and energy supplier (see: https://wiki.openstreetmap.org/wiki/DE:Key:office) or
        * ownership keys apart from private or private_nonprofit (see: https://wiki.openstreetmap.org/wiki/Key:ownership)
        
    * only new organizations are written to db
    * returns all database entries that were affected, also the ones that were found but already present (! if one wants to see everything in the datbase a GET http://localhost:8001/organizations/ must be performed)
    * used query: 

    .. code-block::

        overpass_query = f"""
        [out:json];
        area[~"de:regionalschluessel"~"{regionalcode}"]->.boundaryarea;
        (node(area.boundaryarea)["office"~"^(energy_supplier|quango)?$"]["name"];
        node(area.boundaryarea)["office"]["name"]["ownership"~"^(municipal|public|national|state|county|public_nonprofit)$"];
        );
        out center;
        """           

    * this is only a test implementation to have an alternative to the wikipedia crawling
    * example curl:

    .. code-block::

        curl -XGET -H 'Content-Type: application/json'  http://localhost:8001/service/search/osm/08



    * for query examples and documentation see https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_API_by_Example
    * for testing overpass turbo queries: https://overpass-turbo.eu/ 

* ``/service/enrich/googlesearch`` :

    * tries to enrich all database records with the organization webiste domain names using the Google API via the Salted-SearchEngine service (see: https://github.com/SALTED-Project/AgendaAnalytics/tree/master/services/AgendaAnalytics-SearchEngine)
    * already existing entries will be overriden, if a domain name is found by the service
    * returns all organizations for which a domain could be determined 
    * example curl:

    .. code-block::

        curl -XGET -H 'Content-Type: application/json'  http://localhost:8001/service/enrich/googlesearch

* ``/service/enrich/osmsearch`` :

    * tries to enrich all database records with adress information & again the webiste domain name
    * already existing entries will be overriden
    * returns all organizations for which osm representation was found (caution: OSM sometimes gives time out errors, see docker logs for info)

    * used query:

    .. code-block::

        overpass_query = f"""
        [out:json];
        area["ISO3166-1"="DE"][admin_level=2];
        (node["addr:city"="{city}"][~"^name(:.*)?$"~"{name}"](area);
        relation["addr:city"="{city}"][~"^name(:.*)?$"~"{name}"](area);
        way["addr:city"="{city}"][~"^name(:.*)?$"~"{name}"](area);
        );
        out center;
        """   

    * example curl:

    .. code-block::

        curl -XGET -H 'Content-Type: application/json'  http://localhost:8001/service/enrich/osmsearch



The following section describes the MQTT functionalities (only working, if service was deployed setting ``MQTT_ENABLED=True`` within ``.env`` file):

    * the DiscoverAndStore service gets triggered by the MQTTtrigger service
    * e.g. the following parameters are used by the "data injection toolchain" - trigger:

    .. code-block::

        {
            "parameters": {
                "discoverandstore": {
                    "searchscope": "osm",
                    "enrichscope": "google"
                },
                "mapping": {},
                "publish": {}
            }
        }               



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
        
        # adapt docker-compose.yaml and comment in the volume mounts of the service for developing purposes if needed
        # inside root directory where docker-compose.yaml is
        # for clean start up
        ./service.sh start

        # for a clean stop
        ./service.sh stop

        # quick & without testing
        docker-compose -p salted_discoverandstore up -d --build

    * visit API doc: http://localhost:8001/docs#/


    


Inner workings
############################################# 


Testing
*********************************************

* tests of code: try/except blocks within code, so that errors can be handled with predefined exceptions for user

    * code location: inside code
    * time: within runtime


* tests of final endpoints (and therefor connection to db): via ``pytest``

    * code location: ``./src/app/tests``
    * time: at startup of service (within ``./service.sh``)
    * for future improvement through creating new db/test client on each test case: see https://www.fastapitutorial.com/blog/unit-testing-in-fastapi/ 
    * you can let ``pytest`` run manually within the running service container: ``pytest /usr/src/app/tests`` (keep in mind, that all containers in docker-compose need to be running for this ... spin up of all containers that are not running already: ``docker-compose up -d``)
    * if you want to print out errors when debugging tests, use print statement within the code (logging is not displayed)
    
    

Logging
*********************************************

* for the enduser: the API endpoints give out dedicated error messages, but no logs (in some cases email-info for support is provided for the /service/.. endpoints)
* for the developer:  logging is done to stdout & logfile.log & to the databse table service-logs via the python logging module and a Custom APIRoute

        * logging to stdout is done via python logging module 
        * ``--log-config ./app/logs/log.ini`` is supplied to the uvicorn start command, which points to the log.ini file specifiying the appearance & location of the logfile.log
        * the custom APIRoute class is defined within ``./src/app/logs/logger.py`` and gets called in ``./src/app/main.py``:

            * CustomRoutes are an alternative to logic in a middleware.
            * They enable you to read requests (& and manipulate) before they are processed by the application.
            * Here: Used for reading requests, timing them and writing a record to the db table service-logs (generates request id to link to deeper information in logfile.log)
            * Problem: When an Exception is raised, the ``response: Response = await original_route_handler(request) `` is in an never ending loop. Therefor the attributes end, duration are never filled within the db.
                
                * reference official documentation: https://fastapi.tiangolo.com/advanced/custom-request-and-route/
                * reference for using as CustomLogging option: https://github.com/tiangolo/fastapi/issues/4683
                * working solution:

                .. code-block::

                # first workaround: use return instead of raise - the main thread keeps running and the Promise in the CustomRoute gets fullfilled
                content = '{"detail":"Organization not found."}'
                return Response(status_code=404, content=content, media_type="application/json")
                # raise HTTPException(status_code=404, detail="Organization not found.")

                # second workaround: catch HTTPException in custom route with try/catch blocks
                # see code



        * attention: 

            * calling docker exec always starts a new process, which causes that the output of this process is not written to docker logs (see https://github.com/moby/moby/issues/8662)
            * workaround: redirect your output into PID 1's (the docker container) file descriptor for STDOUT: echo hello > /proc/1/fd/1 (or for append >>)
            * this works in this case for e.g. the ``pytest`` command in ./service.sh but not for the ``uvicorn`` command
            * therefor the ``uvicorn`` command gets called in the ``docker-compose.yaml`` (for this to work the ``ENTRYPOINT ["tail", "-f", "/dev/null"]`` needs to be removed from the Dockerfile, otherwise an error occurs - this is not a problem since the ``uvicorn`` command keeps the container running)




Observability via Grafana 
*********************************************

* uses Salted-Commons infrastructure 



Configuration Information
*********************************************

* ``.env`` is used to set environmental variables for docker-compose.yaml - it gets read automatically by ``docker-compose up``
* for application specific variables the ``./src/app/settings.yaml`` is used via ``./src/app/config.py``
* for local debugging of the service it is possibel to run the db containers via docker, but start up the service locally with ``uvicorn --port 8055 app.main:app --reload``, or test it with ``pytest`` in the app directory. Therefor the ``./src/app/settings.yaml`` needs to be adjusted to use localhost and external ports instead of service names and internal ports.



PostgreSQL database
#############################################

* This service uses a postgreSQL databse as storage layer. (Salted-Commons infrastructure)

* You can enable the database information for stdout with:

    .. code-block::

        # use echo = True to print out db related information (db.py line 28-29)
        engine = sqlalchemy.create_engine(
            DATABASE_URL, pool_size=3, max_overflow=0, echo=True
        )

* Within  the docker-compose.yaml of Salted-Commons pgadmin gets started up as debugging helper. 

    * Login data & databse is specified in ``.env`` file in the project root directory
    * Remember, that when your db runs in a container, you can not use localhost as hostname since this would point to inside the pgadmin container. Use the bridging networks adress and the db external port or the service name and db inner port instead.

* The service uses (creates if they are not there) two tables: organizations & service-logs

    * organizations: holds each organization / company as one records
    * service-logs: holds each request to the service APi as one record




