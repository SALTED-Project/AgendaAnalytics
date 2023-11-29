FROM python:3.8-slim

WORKDIR /usr/src/app

COPY . /usr/src/app/

RUN apt-get update \
    && apt-get install gcc -y \
    && apt-get clean

RUN apt-get update \
  && apt-get install -y \
    cron \
    vim

RUN pip3 install -r /usr/src/app/requirements.txt \
    && rm -rf /root/.cache/pip

RUN ls -la

RUN chmod 0744 /usr/src/app/create_map.py   

WORKDIR /

COPY crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/bin/crontab /etc/cron.d/crontab

CMD ["cron", "-f"]

