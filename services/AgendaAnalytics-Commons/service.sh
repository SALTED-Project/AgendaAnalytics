#!/bin/sh

set -e

if [ -z "$1" ];then
    echo "Illegal number of parameters"
    echo "usage: service [start|stop]"
    exit 1
fi

command="$1"
projectname="salted_commons"


case "${command}" in
	"start")
        echo "Hello! Welcome to the start-up of the SALTED COMMONS ;D "         
        echo "Checking if docker plugin for loki is installed and enabled..."
        docker_plugin_loki_status=$(docker plugin ls|grep loki|tr -s ' '|cut -d ' ' -f 6)
        if [ "${docker_plugin_loki_status}" = "false" ] 
        then 
            docker plugin enable loki
            echo "...enabled the plugin." 
        fi
        if [ "${docker_plugin_loki_status}" != "true" ] && [ "${docker_plugin_loki_status}" != "false" ]
        then            
            docker plugin install grafana/loki-docker-driver:latest --alias loki --grant-all-permissions 
            echo "...installed the plugin, since it was not there."
        fi    
        if [ "${docker_plugin_loki_status}" = "true" ] 
        then 
            echo "... it is."
        fi        
        {   echo "First we clean up ..." \
            && ./service.sh stop \
            && echo "Now we can start again..." \
            && docker-compose -p "${projectname}" up -d --build \
            && echo "Started all containers succesfully" \
            && echo "Commons can be used now."
            } || {
                echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!ERROR!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!" \
                && echo "Sorry - an error occured shutting down after an predeceeding error." \
                && echo "Please make sure all containers / volumes are removed (prefix used: ${projectname}" \
                && echo "Trying to help with that automatically ..." \
                && ./service.sh stop \
                && echo ".. removed all succesfully" \
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










