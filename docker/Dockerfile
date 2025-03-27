FROM python:3.12-bookworm AS base

# Base environment configuration
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Configurable user setup
ENV USER=cncnet
ENV UID=1000

WORKDIR /cncnet-map-api

# Install system dependencies
RUN apt-get update && apt-get install -y liblzo2-dev libmagic1

# Create non-root user with configurable name and UID
RUN useradd -m -u ${UID} ${USER}

# Copy necessary files for the build
COPY requirements.txt /cncnet-map-api
COPY requirements-dev.txt /cncnet-map-api
COPY web_entry_point.sh /cncnet-map-api
COPY .env /cncnet-map-api/

# Set permissions and make script executable
RUN chmod +x /cncnet-map-api/web_entry_point.sh && \
    chown -R ${USER}:${USER} /cncnet-map-api

RUN pip install --upgrade pip

FROM base AS dev
RUN pip install -r ./requirements-dev.txt
USER ${USER}
ENTRYPOINT ["/cncnet-map-api/web_entry_point.sh"]

FROM base AS prod
COPY . /cncnet-map-api
RUN pip install -r ./requirements.txt
USER ${USER}
ENTRYPOINT ["/cncnet-map-api/web_entry_point.sh"]
