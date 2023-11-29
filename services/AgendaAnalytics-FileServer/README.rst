*******************************************
SALTED service: FileServer
*******************************************

REST API using FastAPI + seaweedFS + mongoDb (+ Observability through Grafana: Prometheus, Tempo, Loki) 

This service is the file server used within the SALTED infrastructure. Ressources linked within NGSI-LD entities are persisted and offered by this service.



Fast Info - API Usage
#############################################

URLs:

    * visit API doc: http://localhost:8006/docs#/

The service endpoints handle interactions with the FileServer:

* GET ``/files/{uuid}``:  Returns a single file by its UUID (ref by metadata storage).
* DELETE ``/files/{uuid}``: Deletes a single file by its UUID.
* POST ``/files/``: Uploads one or multiple files directly and returns assigned UUIDs.

* "password protected" endpoints:
    
    * "password protetion" is for simplicitly just implemented with check of given parameter request
    * those endpoint should not be used by anormal user, since it gives access to DELETE-operations and access to clear visible file names within the system.
    * GET ``/files/``: Returns all files within the metadata storage and the file storage.
    * DELETE ``/files/``: Deletes all files that have metadata entry in mongodb.
    * GET ``/files/sync/``: Sync files in seaweedfs and mongodb for analysis.
    * DELETE ``/files/sync/``: Sync files in seaweedfs and mongodb and perform clean up.


Deployment
#############################################

Make sure to fill in the ``.env`` file with the correct values for your setup.

For deploying all services using docker:
    
    .. code-block::
        
        # inside root directory where docker-compose.yaml is
        # for clean start up
        ./service.sh start

        # for a clean stop
        ./service.sh stop

        # quick & without testing
        docker-compose -p salted_fileserver up -d --build

    * visit API doc: http://localhost:8006/docs#/

