FROM python:3
LABEL maintainer="adam.dobrawy{at}siecobywatelska.pl"
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install flake8==3.5.0
COPY . .
RUN flake8
RUN python test.py
FROM python:3.6

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
CMD [ "python", "./daemon.py" ]
