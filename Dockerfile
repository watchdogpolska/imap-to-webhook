FROM python:3-slim as build
LABEL maintainer="adam.dobrawy{at}siecobywatelska.pl"

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN apt-get update && apt-get install -y g++ &&\
    pip install --no-cache-dir -r requirements.txt &&\
    apt-get remove -y g++ && apt-get autoremove -y
COPY . .

# Testing
FROM build as testing
RUN pip install flake8==3.5.0 &&\
    flake8 &&\
    python test.py

# Actual image
FROM build
CMD [ "python", "./daemon.py" ]
