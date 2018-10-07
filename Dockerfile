FROM python:3-slim as build
LABEL maintainer="adam.dobrawy{at}siecobywatelska.pl"

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN apt-get update && \
    apt-get install -y --no-install-recommends g++=4:6.3.0-4 &&\
    pip install --no-cache-dir -r requirements.txt &&\
    apt-get remove -y g++ && apt-get autoremove -y &&\
    rm /var/lib/apt/lists -r
COPY . .

# Testing
FROM build as testing
RUN python test.py

# Actual image
FROM build
CMD [ "python", "./daemon.py" ]
