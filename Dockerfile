# --- Lint & test image ---
FROM python:3
# it disappears completely and no impact on final image size
# if lint/fails it block to build final image
LABEL maintainer="adam.dobrawy{at}siecobywatelska.pl"
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install flake8==3.5.0
COPY . .
RUN flake8
RUN python test.py
# --- Final image ---
FROM python:3
RUN pip install dumb-init
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["/usr/local/bin/dumb-init", "--"]
CMD [ "python", "./daemon.py" ]
