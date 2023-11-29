#!/bin/sh

set -e
# if (( $# != 1 )); then
if [ -z "$1" ];then
    echo "Illegal number of parameters"
    echo "usage: service [start|stop]"
    exit 1
fi

command="$1"
projectname="salted_searchengine"

case "${command}" in
	"start")
    echo "Hello! Welcome to the Salted-Service SearchEngine "

    {   echo "Clean up ..." \
        && ./service.sh stop \
        && echo "We build again ..." \
        && docker-compose -p "${projectname}" up -d --build \
        && echo "Started all containers successfully" \
        && echo "Start of Tests ...." \
        && docker ps -a | grep "${projectname}_service" \
        && docker exec -i "${projectname}_service" sh -c "pytest /usr/src/app/tests" \
        && echo "... Tests finished with no errors. :)" \
        && docker-compose rm -s -f -v salted_searchengine_testdb \
        && echo "Removed testing db." \
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
