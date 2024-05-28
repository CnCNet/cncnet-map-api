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

RUN apt-get update && apt-get install -y liblzo2-dev  # Compression library used by westwood.
RUN apt-get install libmagic1  # File type checking.
RUN pip install --upgrade pip
# The cflags are needed to build the lzo library on Apple silicon.
RUN CFLAGS=-I$(brew --prefix)/include LDFLAGS=-L$(brew --prefix)/lib pip install -r ./requirements-dev.txt

RUN chmod +x /cncnet-map-api/start.sh
ENTRYPOINT "/cncnet-map-api/start.sh"
