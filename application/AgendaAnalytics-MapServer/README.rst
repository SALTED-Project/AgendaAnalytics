*******************************************
SALTED service: MapServer
*******************************************

The resulting application can be seen at: https://agenda-map.hdkn.eu

For access with user ``salted`` contact the Kybeidos GmbH (contact: team@agenda-analytics.eu)


This service serves the maps for all agendas within the Agenda Analytics use case. Since the SDG agenda is the default one, it is shown under the path ``/``. 
Any agendas map can be shown under ``/<agenda_entity_id>``.

Current links are:

    * Default: https://agenda-map.hdkn.eu --> Sustainable Development Goals (deutsch) - Kurzfassung
    * Environmental Social Governance (deutsch) - by ChatGPT: https://agenda-map.hdkn.eu/urn:ngsi-ld:DistributionDCAT-AP:f7c6cdd0-3b55-412d-a3d9-0c0fef06fdfd.html
    * Strategie Künstliche Intelligenz der Bundesregierung, Fortschreibung 2020: https://agenda-map.hdkn.eu/urn:ngsi-ld:DistributionDCAT-AP:58e6963c-75af-485c-8f6c-562d3f2b987a.html
    * Sustainable Development Goals (deutsch) - Kurzfassung: https://agenda-map.hdkn.eu/urn:ngsi-ld:DistributionDCAT-AP:9bd03954-fa71-4fd7-a014-77b79b6534a0.html    
    * Extract from The EMBL Programme 2022–2026 (engish): https://agenda-map.hdkn.eu/urn:ngsi-ld:DistributionDCAT-AP:c2777763-805e-4e9d-a2de-efea99c6a397.html



Structure
#############################################

This repo contains 2 services, that are started via the docker-compose.yml:

    * app:

        * this container is used for creating the ``.html``-files, which get later served by the nginx-service
        * main files:

                * ``./app/create_map.ini`` holds parameters used (e.g. context links and matching score threshold)
                * ``./app/create_map.py`` (with ``create_map.ini``) does the computation of the agenda maps (``./app/map/archive`` is the output folder that contains ``.html`` files with timestamp, ``./app/map/valid`` contains the newest ``SDG_Map_<agenda_entity_id>.html`` that is mapped into the nginx service, ``./app/map/png`` is used to store the computed SDG pictures - identification via matching entity id for the map pupups )
                * ``./app/create_excel.py`` (with ``create_map.ini``) is used to trigger the report calculation for all organizations displayed on any agenda map, that have matching results (this script relies on the the ``scorpio_df_<agenda_entity_id>.xlsx`` file calculated by the ``create_map.py`` script in advance)
                * ``./app/shapefiles/`` holds the static shapefiles used for the mapping
                * ``./app/crontab`` holds cron commands for python scripts, to ensure they run each night to calculate up to date information for the nginx-service
    
    * nginx:

        * this container is used to serve the created maps
        * this container uses ``fastcgi`` to implement access to ``cgi-bin``-scripts, e.g. used to load excel-Reports on the demand via the html-embedded link (``./nginx/cgi-bin/org_to_excel.py`` uses ``./nginx/cgi-bin/org_to_excel.ini`` for parameters)
        * config specifies, what is looked up where for the web server (``./nginx.conf``:)
            
            * contents within ``./html_usr`` are used for displaying web pages
            * contents within ``./data`` are used for excel displayed reports

        * authentication on the ``/`` path is done via user and password

            * password file ``.htpasswd``
            * tool for generating new entries for the password file if users should be added: ``htpasswd.sh``

For container paths of interest take a look under the mappings in the ``docker-compose.yml``.

        
Deployment
#############################################

Make sure to adapt all the ``.ini`` files, the ``docker-compose.yml`` and the ``nginx.conf`` to your needs.
For deploying all services using docker:
    
    .. code-block::
        
        # inside root directory where docker-compose.yaml is
        # quick & without testing
        docker-compose -p salted_mapserver up -d --build

    * visit map given out by nginx: http://localhost:81/
   
     
For manually triggering new map / excel calculation (those commands also run automatically every night via cron jobs):

    .. code-block::

        docker exec -it mapserver_app /bin/sh
        # inside container
        cd /usr/src/app
        python create_map.py
        python create_excel.py
    
            

