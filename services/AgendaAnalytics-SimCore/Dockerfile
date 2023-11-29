FROM python:3.8

LABEL authors="m.p. <per@kybeidos.de>"

ARG DEBIAN_FRONTEND=noninteractive

RUN adduser --disabled-password -gecos "" worker
ENV PATH="/home/worker/.local/bin:$PATH"

COPY requirements.txt .
COPY settings.toml settings.toml
COPY ./src src
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN mkdir projects
RUN chown -R worker:worker /src
RUN chown -R worker:worker /projects
RUN touch ./simcore_events.log
RUN chown worker:worker ./simcore_events.log
USER worker

#
# no special nltk related stuff here
#
ENV NLTK_DATA /home/worker/nltk_data
RUN python -c "import nltk;nltk.download('punkt')"

#
# This pipefail setting prevents errors in a pipeline from being masked.
# if an error in a component of the pipe occurs it will be propagated to the end.
#
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV PYTHON_PATH=/usr/local/lib/python3.8/site-packages/
ENV PYTHONPATH="$PYTHON_PATH:${PYTHONPATH}"
ENV MODULE_NAME=simcore.main
EXPOSE 9060
CMD [ "python", "src/simcore_rest_api.py"]
