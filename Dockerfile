FROM python:3.12-slim as build
LABEL maintainer="adam.dobrawy{at}siecobywatelska.pl"

WORKDIR /usr/src/app
COPY requirements.txt ./
COPY requirements.dev.txt ./
RUN apt-get update \
 && apt-get install -y --no-install-recommends g++ git make nano \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/* \
 && pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir -r requirements.dev.txt \
 && apt-get remove -y g++ && apt-get autoremove -y
ENV PYTHONUNBUFFERED=1
COPY . .

# Testing
FROM build as testing
RUN python test.py

# Actual image
FROM build
# CMD [ "python", "./daemon.py" ]
# Chended to allow VScode run and debug app or debug container starting errors:
CMD [ "bash", "-c", "echo 'imap-to-webhook container started' ;  sleep infinity " ]
