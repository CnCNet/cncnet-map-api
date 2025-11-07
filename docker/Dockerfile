FROM python:3.12-bookworm AS base

# Base environment configuration
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /cncnet-map-api

# Install system dependencies
RUN apt-get update && apt-get install -y liblzo2-dev libmagic1


# Copy necessary files for the build
COPY requirements.txt /cncnet-map-api
COPY requirements-dev.txt /cncnet-map-api
COPY web_entry_point.sh /cncnet-map-api

# Set permissions and make script executable
RUN chmod +x /cncnet-map-api/web_entry_point.sh

RUN pip install --upgrade pip

FROM base AS dev
RUN pip install -r ./requirements-dev.txt
ENTRYPOINT ["/cncnet-map-api/web_entry_point.sh"]

FROM base AS prod
COPY . /cncnet-map-api
RUN pip install -r ./requirements.txt
ENTRYPOINT ["/cncnet-map-api/web_entry_point.sh"]

FROM base AS debugger
# Just build, but don't run anything. Your debugger will run pytest, manage.py, etc for you.
RUN CFLAGS=-I$(brew --prefix)/include LDFLAGS=-L$(brew --prefix)/lib pip install -r ./requirements-dev.txt
