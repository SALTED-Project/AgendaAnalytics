FROM tiangolo/uvicorn-gunicorn:python3.9-slim

RUN apt-get update \
    && apt-get install curl -y \
    && apt-get clean

RUN pip install --no-cache-dir \
    uvicorn[standard]==0.18.3 \ 
    fastapi[all]==0.85.0

RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python - --version 1.2.0 && \
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    poetry config virtualenvs.create false


COPY ./pyproject.toml ./poetry.lock* /app/

ARG INSTALL_DEV=false
RUN bash -c "if [ $INSTALL_DEV == 'true' ] ; then poetry install --no-root ; else poetry install --no-root --only main ; fi"

RUN prisma -v

COPY ./*.sh /

COPY ./app /app

RUN curl -o /root/docker.tgz https://get.docker.com/builds/Linux/x86_64/docker-1.12.5.tgz && tar -C /root -xvf /root/docker.tgz && mv /root/docker/docker /usr/local/bin/docker && rm -rf /root/docker*
RUN curl -L https://github.com/docker/compose/releases/download/1.7.1/docker-compose-`uname -s`-`uname -m` > /usr/local/bin/docker-compose && chmod +x /usr/local/bin/docker-compose


ENV PYTHONPATH=.
