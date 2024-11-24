# syntax=docker/dockerfile:1

FROM python:3.11-alpine

# Default to running every day at midnight
ENV CRON_SCHEDULE="0 0 * * *"
ENV TZ="America/New_York"


#RUN echo "*** Installing dependencies ***" && \
#    apk --no-cache add jq curl bash tzdata file

# Install required system dependencies
RUN echo "*** Installing dependencies ***" && \
    apk add --no-cache \
        gcc \
        bash \
        musl-dev \
        libffi-dev \
        python3-dev \
        openssl-dev

# Create and set working directory
WORKDIR /app

# Copy script and requirements
RUN echo "*** Installing app scripts ***"
COPY *.sh /app/
COPY *.py /app/
COPY requirements.txt /app/

#WORKDIR /discord-sh
#RUN echo "*** Installing fieu/discord.sh ***" && \
#    wget https://github.com/fieu/discord.sh/releases/latest/download/discord.sh && \
#    chmod +x discord.sh

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

#WORKDIR /

# Specify bash as the default shell
SHELL ["/bin/bash", "-c"]

CMD ["/app/entrypoint.sh"]

# Command to run the script
#CMD ["python", "/app/script.py"]
