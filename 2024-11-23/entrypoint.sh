#!/bin/sh

## Environment variables
#CRON_SCHEDULE_RADARR=${CRON_SCHEDULE_RADARR:-"0 * * * *"}  # Default: Run every hour
#CRON_SCHEDULE_SONARR=${CRON_SCHEDULE_SONARR:-"15 * * * *"} # Default: Run every hour, 15 min offset
#LOG_DIR=${LOG_DIR:-"/app/logs"}
#
## Ensure log directory exists
#mkdir -p $LOG_DIR
#
## Immediate first run
#echo "Running Radarr script for the first time..."
#python3 /app/radarr_seeding.py
#
#echo "Running Sonarr script for the first time..."
#python3 /app/sonarr_seeding.py
#
## Create cron jobs
#echo "Setting up cron jobs..."
#echo "$CRON_SCHEDULE_RADARR python3 /app/radarr_seeding.py >> $LOG_DIR/radarr_seeding.log 2>&1" >> /etc/crontabs/root
#echo "$CRON_SCHEDULE_SONARR python3 /app/sonarr_seeding.py >> $LOG_DIR/sonarr_seeding.log 2>&1" >> /etc/crontabs/root
#
## Start cron in the foreground
echo "Starting cron..."
exec crond -f -l 8
