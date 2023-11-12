FROM python:3.12-bookworm as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /cncnet-map-api

# This is just here to crash the build if you don't make a .env file.
COPY .env /cncnet-map-api/

# Copy files needed for build
COPY requirements.txt /cncnet-map-api
COPY requirements-dev.txt /cncnet-map-api
COPY start.sh /cncnet-map-api

RUN pip install --upgrade pip
RUN pip install -r ./requirements.txt
RUN pip install -r ./requirements-dev.txt

RUN chmod +x /cncnet-map-api/start.sh
ENTRYPOINT "/cncnet-map-api/start.sh"
