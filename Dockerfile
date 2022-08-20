FROM python:3.10 as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /python-map-api

# This is just here to crash the build if you don't make a .env file.
COPY .env /python-map-api/

# No need to copy other files, they're mounted with docker compose.
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install -r requirements-dev.txt
