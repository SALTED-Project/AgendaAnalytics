#!/bin/sh


set -e

if [ -z "$1" ];then
    echo "Illegal number of parameters"
    echo "usage: service [start|stop]"
    exit 1
fi

command="$1"
projectname="salted_fileserver"




case "${command}" in
	"start")
        echo "Hello! Welcome to the start-up of this SALTED-service FileServer ;D " 
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
        {   echo "First we clean up ..." \
            && ./service.sh stop \
            && echo "Now we can start again..." \
            && docker-compose -p "${projectname}" up -d --build \
            && echo "Started all containers succesfully" \
            && echo "Tests start...." \
            && docker ps -a | grep "${projectname}_service" \
            && docker exec -i "${projectname}_service" sh -c "python ./backend_pre_start.py && pytest ./tests" \
            && echo "... Tests finished with no errors. :)" \
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
        && echo "The following docker volumes still exist because of data persistence:" \
        && docker volume ls |grep "${projectname}"|tr -s ' '|cut -d ' ' -f 2       
		;;
    *)
		echo "command not found."
		echo "usage: service [start|stop]"
		exit 1;
		;;
esac










