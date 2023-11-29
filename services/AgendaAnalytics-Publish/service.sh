#!/bin/sh


set -e

if [ -z "$1" ];then
    echo "Illegal number of parameters"
    echo "usage: service [start|stop]"
    exit 1
fi


command="$1"
projectname="salted_publish"

# needs to be removed later, beacuse of interference with .env loaded with docker-compose build
export $(grep '^MQTT_ENABLED' .env | xargs )
export $(grep '^MQTT_HOST' .env | xargs )
export $(grep '^SCORPIO_URL' .env | xargs )

echo "${MQTT_ENABLED}"
echo "${MQTT_HOST}"
echo "${SCORPIO_URL}}"



case "${command}" in
	"start")
        echo "Hello! Welcome to the start-up of this SALTED-service Publish ;D "
        echo "Checking if docker plugin for loki is installed and enabled..."
        docker_plugin_loki_status=$( docker plugin ls|grep loki|tr -s ' '|cut -d ' ' -f 6 )
        if [ "${docker_plugin_loki_status}" != "true" ] 
        then 
            docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions 
            echo "...installed the plugin, since it was not there." 
        else
            echo "... it is."
        fi
        echo "Checking if necessary Commons-Infrastructure is running." 
        echo "Check if commons docker network  is existing ..."
        network_name=$( docker network inspect --format='{{json .Name}}' salted_commons_default ) || network_name="not found"
        echo ${network_name} 
        if [ "${network_name}" != '"salted_commons_default"' ] 
        then 
            echo "...it is not. Start up the Commons first." 
            exit 1;
        else
            echo "... it is."
        fi  
        echo "Check if postgres db is healthy..."
        commons_status=$( docker inspect --format='{{json .State.Health.Status}}' salted_commons_postgres_db ) || commons_status="not healthy"
        echo ${commons_status} 
        if [ "${commons_status}" != '"healthy"' ] 
        then 
            echo "...it is not. Start up the Commons first." 
            exit 1;
        else
            echo "... it is."
        fi     
        echo "Checking if necessary Scorpio-Infrastructure is running."   
        scorpio_status=$( curl --write-out '%{http_code}' --silent --output /dev/null ${SCORPIO_URL}/ngsi-ld/v1/entities/?type=Organization?limit=1 ) || scorpio_status="not running"
        echo ${scorpio_status} 
        if [ "${scorpio_status}" != '200' ] 
        then 
            echo "...it is not. Start up the Scorpio Broker first." 
            exit 1;
        else
            echo "... it is."
        fi     
        echo "Checking if MQTT option is enabled and running." 
        if [ "${MQTT_ENABLED}" = "True" ]
        then   
            echo "MQTT option is enabled."     
            echo "Check if MQTT broker is running..."
            # if no connection can be established it aborts
            echo "mqtt://${MQTT_HOST}/testtopic"
            (curl -s -v -d "testmessage" "mqtt://${MQTT_HOST}/testtopic") || (echo "...it is not. Start up MQTT broker first." && exit 1; )
            echo "... it is." 
        else
            echo "MQTT option is not enabled."  
        fi        
        # remove env variables
        unset "MQTT_ENABLED"
        unset "MQTT_HOST"
        unset "SCORPIO_URL"
        {   echo "First we clean up ..." \
            && ./service.sh stop \
            && echo "Now we can start again..." \
            && docker-compose -p "${projectname}" up -d --build \
            && echo "Started all containers succesfully" \
            && echo "Tests start...." \
            && docker exec -i "${projectname}_service" sh -c "pytest /usr/src/app/tests" \
            && echo "... Tests finished with no errors. :)" \
            && docker-compose rm -s -f -v salted_publish_testzookeeper salted_publish_testkafka salted_publish_testpostgres salted_publish_testscorpio salted_publish_testdb \
            && docker network disconnect salted_publish_network salted_publish_service \
            && echo "Removing network salted_publish_network, since it was only used for tests:" \
            && docker network rm salted_publish_network \
            && echo "Removed testing scorpio and testing db and testnetwork." \
            && echo "Webserver can be used now."
            } || {
                echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!ERROR!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" \
                && echo "Sorry - an error occured shutting down after an predeceeding error." \
                && echo "Please make sure all containers / volumes are removed (prefix used: ${projectname}" \
                && echo "Trying to help with that automatically ..." \
                && ./service.sh stop \
                && echo ".. removed succesfully" \
                && exit 1;
            }
        ;;
	"stop")
		echo "Stopping and removing all containers and anonymous volumes associated with this service." \
        && docker-compose -p "${projectname}" rm -s -f -v  \
        && echo "Removing network salted_publish_network, since it was only used for tests:" \
        && docker network rm salted_publish_network || echo "no such network" \
        && echo "The following docker volumes still exist because of data persistence:" \
        && docker volume ls |grep "${projectname}"|tr -s ' '|cut -d ' ' -f 2       
		;;
    *)
		echo "command not found."
		echo "usage: service [start|stop]"
		exit 127;
		;;
esac










