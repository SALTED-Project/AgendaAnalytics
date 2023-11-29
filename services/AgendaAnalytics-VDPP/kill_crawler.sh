#!/usr/bin/env bash
RUNNING="$(docker-compose -p vdpp exec -T storm-nimbus storm list -c nimbus.seeds='["storm-nimbus"]' | grep -Eo "crawl[[:alnum:]-]*")"
if [[ "$RUNNING" == "crawl"* ]]; then
    docker-compose -p vdpp exec -T storm-nimbus storm kill ${RUNNING} -w 10 -c nimbus.seeds='["storm-nimbus"]'
fi

while [[ "$RUNNING" == "crawl"* ]]; do
	echo "Waiting 10 seconds for crawler to stop running"
    sleep 10
    RUNNING="$(docker-compose -p vdpp exec -T storm-nimbus storm list -c nimbus.seeds='["storm-nimbus"]' | grep -Eo "crawl[[:alnum:]-]*")"
done

echo "Crawler stopped"
