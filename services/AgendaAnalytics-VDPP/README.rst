*******************************************
SALTED - VDPP
*******************************************

This is the repository for the VDPP project. It is used within the Agenda Analytics project for providing crawling and document converting functionalities.
The docker images are used from the kybeidos docker hub repository. If you are interested, please contact Kybeidos GmbH (team@agenda-analytics.eu)


Fast Info - API Usage
#############################################

URLs:

    * visit API doc of middleware: http://localhost:8083/docs#/
    * visit Storm UI: http://localhost:8100/index.html


Deployment
#############################################

Make sure to fill the ``DB_URI`` environmental variable for the middleware service in the ``./docker-compose.yml`` with the username & password defined by the mongodb service. This connection string will be later used by the AgendaAnalytics-Crawling service and the AgendaAnalytics-AgendaMatching service.

For deploying all services using docker:
    
    .. code-block::
        
        # inside root directory where docker-compose.yaml is
        docker login docker.io -u $DOCKERHUB_CREDENTIALS_USR -p $DOCKERHUB_CREDENTIALS_PSW && docker-compose -p vdpp up -d && docker-compose -p vdpp exec -T crawler-selenium sudo chmod 1777 /dev/shm

