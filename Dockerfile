# syntax=docker/dockerfile:1

FROM python:3.13-alpine

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
RUN pip install --root-user-action=ignore --no-cache-dir -r requirements.txt

CMD ["/app/entrypoint.sh"]
