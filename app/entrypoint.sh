#!/usr/bin/env bash

# Environment variables for user and group IDs
PUID=${PUID:-1000}  # Default to 1000 if not set
PGID=${PGID:-1000}  # Default to 1000 if not set

# Default user and group names
USER_NAME="appuser"
GROUP_NAME="appgroup"

# Check if a group with the specified PGID already exists
existing_group=$(getent group "$PGID" | cut -d: -f1)
if [ -z "$existing_group" ]; then
    echo "Creating group with GID $PGID..."
    addgroup -g "$PGID" "$GROUP_NAME"
else
    echo "Reusing existing group '$existing_group' with GID $PGID."
    GROUP_NAME="$existing_group"
fi

# Check if a user with the specified PUID already exists
existing_user=$(getent passwd "$PUID" | cut -d: -f1)
if [ -z "$existing_user" ]; then
    echo "Creating user with UID $PUID..."
    adduser -D -u "$PUID" -G "$GROUP_NAME" "$USER_NAME"
else
    echo "Reusing existing user '$existing_user' with UID $PUID."
    USER_NAME="$existing_user"
    # Add user to the group if not already in it
    user_groups=$(id -Gn "$USER_NAME")
    if ! echo "$user_groups" | grep -qw "$GROUP_NAME"; then
        echo "Adding user '$USER_NAME' to group '$GROUP_NAME'..."
        adduser "$USER_NAME" "$GROUP_NAME"
    fi
fi

# Adjust permissions for the log directory
echo "Setting permissions for log directory..."
LOG_DIR=${LOG_DIR:-"/logs"}
mkdir -p "$LOG_DIR"
chown -R "$USER_NAME":"$GROUP_NAME" "$LOG_DIR"

# Environment variables
CRON_SCHEDULE_RADARR=${CRON_SCHEDULE_RADARR:-"0 0 * * *"}  # Default: Run every day
CRON_SCHEDULE_SONARR=${CRON_SCHEDULE_SONARR:-"30 0 * * *"} # Default: Run every day, 30 min offset

# Immediate first run
echo "Running Radarr script for the first time..."
su "$USER_NAME" -c 'python3 /app/radarr.py'

echo "Running Sonarr script for the first time..."
su "$USER_NAME" -c 'python3 /app/sonarr.py'

# Create cron jobs
echo "Setting up cron jobs..."
echo "$CRON_SCHEDULE_RADARR su $USER_NAME -c 'python3 /app/radarr.py'" >> /etc/crontabs/root
echo "$CRON_SCHEDULE_SONARR su $USER_NAME -c 'python3 /app/sonarr.py'" >> /etc/crontabs/root


## Start cron in the foreground
echo "Starting cron..."
exec crond -f -l 8
