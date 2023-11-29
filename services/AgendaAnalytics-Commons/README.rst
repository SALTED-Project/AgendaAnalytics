*******************************************
SALTED commons
*******************************************

This repo containes the startup script for all common infrasturcture provided for SALTED services.
**It must be run before the specific SALTED services are deployed, because they use AT LEAST the docker network of the common infrastructure.**
(If usage of common infrastructure is not wanted at all, feel free to define a different network in docker-compose.yaml of specific SALTED service.)
The following components are supplied:

* for visualization:

    * prometheus + loki + tempo + grafana

* for storage:

    * postgres db

* for networking between all SALTED services:

    * docker network



Fast Info 
#############################################

For deploying all services using docker:
    
    .. code-block::
        
        # inside root directory where docker-compose.yaml is
        # for clean start up
        ./service.sh start

        # for a clean stop
        ./service.sh stop

        # quick & without testing
        docker-compose -p salted_commons up -d --build
    
    * visit grafana dashboard: http://localhost:3000/
    * if its your first time, use the search option on the left side and choose the provided FastAPI dashboard
    * see all stats given to Prometheus: http://localhost:9091/targets


Observability via Grafana 
#############################################

* initial idea/set-up/structure from: https://grafana.com/grafana/dashboards/16110 (e.g. https://github.com/blueswen/fastapi-observability)
* since the above links supply deep insights, just some parts from there are refferenced / copied here ...
* through this set-up the FastAPI application is supplied with three pillars of observability on `Grafana <https://github.com/grafana/grafana>`_:

    * Traces with `Tempo <https://github.com/grafana/tempo>`_ and `OpenTelemetry Python SDK <https://github.com/open-telemetry/opentelemetry-python>`_
    * Metrics with `Prometheus <https://github.com/open-telemetry/opentelemetry-python>`_ and `Prometheus Python Client <https://github.com/prometheus/client_python>`_
    * Logs with `Loki <https://github.com/grafana/loki>`_

 
How To "Plug-In" new SALTED service
#############################################

You want to develop your own SALTED service and want to use this common infrastructure?
The following section explains what is necessary and supplies links to the exemplary implemetation for the `AgendaAnalytics-DiscoverAndStore <https://github.com/SALTED-Project/AgendaAnalytics/blob/master/services/AgendaAnalytics-DiscoverAndStore/README.rst#inner-workings>`_.

    * for loki:

        * see: https://grafana.com/docs/loki/latest/clients/docker-driver/configuration/
        * see: https://thesmarthomejourney.com/2021/08/23/loki-grafana-log-aggregation/

            * "Loki only aggregates logs and makes them searchable. It does not find the logs automatically. Instead you need to push them to Loki. There are two main solutions here. Either another service called promtail or a custom docker logging driver."
            * here a custom logging driver for docker is used, therefor the docker plugin needed must be installed on host - here integrated in ``./service.sh`` (``docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions``)
            * this logging driver is added to all services of interest (docker-compose.yaml files of each microservice)

        * added code in ``./docker-compose.yaml`` of each microservice that wants to use loki

            .. code-block::
                
                # top of the file
                x-logging: &default-logging
                driver: loki
                options:
                    loki-url: 'http://localhost:3100/api/prom/push'

                # as specification of the service
                logging: *default-logging


    * for tempo:

        * added code in ``./src/app/main.py`` of each microservice that wants to use tempo 

            .. code-block::

                # Setting OpenTelemetry exporter
                setting_otlp(app, APP_NAME, "http://tempo:4317")
        
        * added code in ``./src/app/utils/utils.py`` of each microservice that wants to use tempo 

            .. code-block::

                def setting_otlp(app: ASGIApp, app_name: str, endpoint: str, log_correlation: bool = True) -> None:
                    ...

    * for prometheus:

        * added code in ``./src/app/main.py`` of each microservice that wants to use prometheus 

            .. code-block::

                app.add_middleware(PrometheusMiddleware, app_name=APP_NAME)

        * added code in ``./src/app/utils/utils.py`` of each microservice that wants to use prometheus 

            .. code-block::

                class PrometheusMiddleware(BaseHTTPMiddleware):
                    ...

        * added code in ``./etc/prometheus/prometheus.yml`` of the Commons infrastructure

            .. code-block::

                - job_name: 'example_service'

                    # Override the global default and scrape targets from this job every 5 seconds.
                    scrape_interval: 5s

                    static_configs:
                    - targets: ['salted_example_service:8000']


Testing / Healthchecks
#############################################

* test of databases: healthchecks via ``pg_isready`` (more info at https://www.postgresql.org/docs/9.4/app-pg-isready.html & https://github.com/peter-evans/docker-compose-healthcheck/issues/16 )
    
    * code location: ``./docker-compose.yaml``
    * time: at startup of service (within ``./service.sh``)







