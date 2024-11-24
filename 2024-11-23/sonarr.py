import os
import requests
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Environment variables for Sonarr
SONARR_URL = os.getenv("SONARR_URL", "http://localhost:8989")
SONARR_API_KEY = os.getenv("SONARR_API_KEY", "your_api_key")
SEEDING_DIR = os.getenv("SEEDING_DIR", "/qbittorrent/seed")
SEEDING_TAG_NAME = os.getenv("SEEDING_TAG_NAME", "seeding")

# Logging setup
log_file = os.getenv("LOG_FILE", "/app/sonarr_seeding.log")
log_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)
logging.basicConfig(handlers=[log_handler], level=logging.INFO, format="%(asctime)s - %(message)s")

# Sonarr API endpoints
SERIES_API_URL = f"{SONARR_URL}/api/v3/series"
EPISODE_FILE_API_URL = f"{SONARR_URL}/api/v3/episodeFile"
TAG_API_URL = f"{SONARR_URL}/api/v3/tag"

def get_series():
    """Fetch all series from Sonarr."""
    headers = {"X-Api-Key": SONARR_API_KEY}
    response = requests.get(SERIES_API_URL, headers=headers)
    response.raise_for_status()
    return response.json()

def get_episode_files(series_id):
    """Fetch all episode files for a series."""
    headers = {"X-Api-Key": SONARR_API_KEY}
    response = requests.get(f"{EPISODE_FILE_API_URL}?seriesId={series_id}", headers=headers)
    response.raise_for_status()
    return response.json()

def get_tag_id(tag_name):
    """Fetch the tag ID for the given tag name."""
    headers = {"X-Api-Key": SONARR_API_KEY}
    response = requests.get(TAG_API_URL, headers=headers)
    response.raise_for_status()
    for tag in response.json():
        if tag["label"].lower() == tag_name.lower():
            return tag["id"]
    return None

def modify_tag(series_id, tag_id, add=True):
    """Add or remove a tag from a series."""
    headers = {"X-Api-Key": SONARR_API_KEY}
    if add:
        requests.post(f"{SERIES_API_URL}/{series_id}/tag", json={"tagIds": [tag_id]}, headers=headers).raise_for_status()
        logging.info(f"Added tag '{SEEDING_TAG_NAME}' to series ID {series_id}.")
    else:
        requests.delete(f"{SERIES_API_URL}/{series_id}/tag/{tag_id}", headers=headers).raise_for_status()
        logging.info(f"Removed tag '{SEEDING_TAG_NAME}' from series ID {series_id}.")

def is_file_seeding(file_path):
    """Check if the file has hardlinks in the specified directory."""
    try:
        hardlinks = [str(p) for p in Path(file_path).parent.glob("*") if p.is_file()]
        return any(SEEDING_DIR in h for h in hardlinks)
    except Exception as e:
        logging.error(f"Error checking hardlinks for {file_path}: {e}")
        return False

def process_series():
    """Process all series in Sonarr."""
    try:
        series_list = get_series()
        tag_id = get_tag_id(SEEDING_TAG_NAME)

        if tag_id is None:
            logging.error(f"Tag '{SEEDING_TAG_NAME}' does not exist in Sonarr.")
            return

        for series in series_list:
            series_id = series["id"]
            series_title = series["title"]

            episode_files = get_episode_files(series_id)
            seeding_found = False

            for episode_file in episode_files:
                file_path = episode_file.get("path")
                if file_path and is_file_seeding(file_path):
                    seeding_found = True
                    break

            if seeding_found:
                modify_tag(series_id, tag_id, add=True)
            else:
                modify_tag(series_id, tag_id, add=False)

    except requests.RequestException as e:
        logging.error(f"Error interacting with Sonarr API: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    logging.info("Starting Sonarr seeding script...")
    process_series()
    logging.info("Sonarr seeding script completed.")

