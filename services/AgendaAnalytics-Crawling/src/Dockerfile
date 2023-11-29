FROM python:3.8-slim

WORKDIR /usr/src/app

COPY ./requirements.txt /usr/src/app/requirements.txt

RUN apt-get update \
    && apt-get install gcc -y \
    && apt-get clean

RUN pip install -r /usr/src/app/requirements.txt \
    && rm -rf /root/.cache/pip

COPY . /usr/src/

EXPOSE 8000

# we need to keep container running when we want to use docker exec , but container would stop before if we do not specify the ENTRYPOINT. Workaround: use commands on startup of container in docker-compose.yaml (!attention: when this entrypoint is specified, errors occur when giving commands in docker-compose.yaml)
#ENTRYPOINT ["tail", "-f", "/dev/null"]