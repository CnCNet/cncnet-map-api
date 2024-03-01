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

RUN apt-get update && apt-get install -y liblzo2-dev
RUN pip install --upgrade pip
RUN CFLAGS=-I$(brew --prefix)/include LDFLAGS=-L$(brew --prefix)/lib pip install -r requirements-dev.txt
