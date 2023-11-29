FROM python:3.7.11

WORKDIR /usr/src/app

COPY ./requirements.txt /usr/src/app/requirements.txt

RUN apt-get update \
    && apt-get install gcc -y \
    && apt-get clean 

RUN pip install -r /usr/src/app/requirements.txt \
    && rm -rf /root/.cache/pip

COPY . /usr/src/

RUN ls -la

EXPOSE 8000

