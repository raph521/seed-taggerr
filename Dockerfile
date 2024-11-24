# syntax=docker/dockerfile:1

FROM python:3.11-alpine

# Supported runtime environment variables
# - PUID
# - PGID
# - TZ
# - CRON_SCHEDULE_RADARR
# - CRON_SCHEDULE_SONARR
# - RADARR_URL
# - RADARR_API_KEY
# - SONARR_URL
# - SONARR_API_KEY
# - SEEDING_DIR
# - SEEDING_TAG_NAME
# - LOG_DIR
# - LOG_MAX_SIZE
# - LOG_BACKUP_COUNT

# Install required system dependencies
RUN echo "*** Installing dependencies ***" && \
    apk add --no-cache \
        bash \
        tzdata

# Specify bash as the default shell
SHELL ["/bin/bash", "-c"]

# Create and set working directory
WORKDIR /app

# Copy script and requirements
RUN echo "*** Installing app scripts ***"
COPY app/*.sh /app/
COPY app/*.py /app/
RUN chmod +x /app/entrypoint.sh
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

CMD ["/app/entrypoint.sh"]
