FROM python:3.12-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /cncnet-map-api

# This is just here to crash the build if you don't make a .env file.
COPY .env /cncnet-map-api/

# Copy files needed for build
COPY requirements.txt /cncnet-map-api
COPY requirements-dev.txt /cncnet-map-api
COPY web_entry_point.sh /cncnet-map-api

# liblzo2 is a compression library used by westwood.
# libmagic1 is used for detecting file mime types by analyzing the file contents.
RUN apt-get update && apt-get install -y liblzo2-dev libmagic1
RUN pip install --upgrade pip
RUN chmod +x /cncnet-map-api/web_entry_point.sh

FROM base AS dev
# The cflags are needed to build the lzo library on Apple silicon.
RUN CFLAGS=-I$(brew --prefix)/include LDFLAGS=-L$(brew --prefix)/lib pip install -r ./requirements-dev.txt
ENTRYPOINT "/cncnet-map-api/web_entry_point.sh"

FROM base AS prod
# The cflags are needed to build the lzo library on Apple silicon.
RUN CFLAGS=-I$(brew --prefix)/include LDFLAGS=-L$(brew --prefix)/lib pip install -r ./requirements.txt

COPY . /cncnet-map-api

ENTRYPOINT "/cncnet-map-api/web_entry_point.sh"

