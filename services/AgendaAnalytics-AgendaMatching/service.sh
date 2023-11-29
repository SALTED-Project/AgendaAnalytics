#!/bin/sh


set -e

if [ -z "$1" ];then
    echo "Illegal number of parameters"
    echo "usage: service [start|stop]"
    exit 1
fi

command="$1"
projectname="salted_agendamatching"


export $(grep '^VDPP_MIDDLEWARE_API' .env | xargs )
export $(grep '^SIMCORE_API' .env | xargs )
export $(grep '^MQTT_ENABLED' .env | xargs )
export $(grep '^MQTT_HOST' .env | xargs )
export $(grep '^SALTED_FILESERVER_SERVICE' .env | xargs)


case "${command}" in
	"start")
        echo "Hello! Welcome to the start-up of this SALTED-service AgendaMatching ;D " 
        echo "Checking if docker plugin for loki is installed and enabled..."
        docker_plugin_loki_status=$(docker plugin ls|grep loki|tr -s ' '|cut -d ' ' -f 6)
        if [ "${docker_plugin_loki_status}" != "true" ] 
        then 
            docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions 
            echo "...installed the plugin, since it was not there." 
        else
            echo "... it is."
        fi
        echo "Checking if necessary Commons-Infrastructure is running." 
        echo "Check if commons docker network  is existing ..."
        network_name=$(docker inspect --format='{{json .Name}}' salted_commons_default) || network_name="not  healthy"
        echo ${network_name} 
        if [ "${network_name}" != '"salted_commons_default"' ] 
        then 
            echo "...it is not. Start up the Commons first." 
            exit 1;
        else
            echo "... it is."
        fi  
        echo "Check if postgres db is healthy..."
        commons_status=$(docker inspect --format='{{json .State.Health.Status}}' salted_commons_postgres_db) || commons_status="not  healthy"
        echo ${commons_status} 
        if [ "${commons_status}" != '"healthy"' ] 
        then 
            echo "...it is not. Start up the Commons first." 
            exit 1;
        else
            echo "... it is."
        fi 
        echo "Checking if necessary VDPP-Infrastructure is running." 
        # can not redirect to /dev/null because of missing permissions for jenkins thats why last 3 for write-out are read
        vdpp_status=$(curl -s -w "%{http_code}" "${VDPP_MIDDLEWARE_API}/services/"| tail -c 3)
        echo ${vdpp_status} 
        if [ "${vdpp_status}" != "200" ] 
        then 
            echo "...it is not. Start up VDPP first." 
            exit 1;
        else
            echo "... it is."
        fi  
        echo "Checking if necessary Simcore Service is running." 
        # can not redirect to /dev/null because of missing permissions for jenkins thats why last 3 for write-out are read
        simcore_status=$(curl -s -w "%{http_code}" "${SIMCORE_API}/"| tail -c 3)
        echo ${simcore_status} 
        if [ "${simcore_status}" != "200" ] 
        then 
            echo "...it is not. Start up Simcore first." 
            exit 1;
        else
            echo "... it is."
        fi  
        echo "Checking if necessary SALTED-FileServer is running." 
        fileserver_status=$(curl -s -w "%{http_code}" "${SALTED_FILESERVER_SERVICE}/files/999"| tail -c 3)
        echo ${fileserver_status} 
        if [ "${fileserver_status}" != "404" ] 
        then 
            echo "...it is not. Start up SALTED-FileServer first." 
            exit 127;
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
        # remove env variables, because of interference with .env loaded with docker-compose build
        unset "VDPP_MIDDLEWARE_API"
        unset "SIMCORE_API"
        unset "MQTT_ENABLED"
        unset "MQTT_HOST"
        unset "SALTED_FILESERVER_SERVICE"
        {   echo "First we clean up ..." \
            && ./service.sh stop \
            && echo "Now we can start again..." \
            && docker-compose -p "${projectname}" up -d --build \
            && echo "Started all containers succesfully" \
            && echo "Tests start...." \
            && docker exec -i "${projectname}_service" sh -c "pytest /usr/src/app/tests" \
            && echo "... Tests finished with no errors. :)" \
            && echo "Webserver can be used now."
            } || {
                echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!ERROR!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" \
                && docker-compose -p "${projectname}" rm -s -f -v && echo "Removed all containers and anonymous volumes since an error occured." \
                && echo "The following docker volumes still exist because of data persistence:" \
                && docker volume ls |grep "${projectname}"|tr -s ' '|cut -d ' ' -f 2 \
                && exit 1
            } || {
                echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!ERROR!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" \
                && echo "Sorry - an error occured shutting down after an predeceeding error, please make sure to remove all containers / volumes manually that you dont want to persist. (prefix used: ${projectname}" \
                && exit 1
            }
        ;;
	"stop")
		echo "Stopping and removing all containers and anonymous volumes associated with this service." \
        && docker-compose -p "${projectname}" rm -s -f -v  \
        && echo "The following docker volumes still exist because of data persistence:" \
        && docker volume ls |grep "${projectname}"|tr -s ' '|cut -d ' ' -f 2       
		;;
    *)
		echo "command not found."
		echo "usage: service [start|stop]"
		exit 1;
		;;
esac










