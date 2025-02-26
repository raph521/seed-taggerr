import os
import requests
import logging
from logging.handlers import RotatingFileHandler
from common_utils import is_file_seeding, get_log_level
from typing import List, Dict, Any

# Environment variables for Sonarr
SONARR_URL = os.getenv("SONARR_URL", "http://sonarr:8989")
SONARR_API_KEY = os.getenv("SONARR_API_KEY", "your_api_key")
SEEDING_DIR = os.getenv("SEEDING_DIR", "/data/downloads/qbittorrent/seed")
SEEDING_TAG_NAME = os.getenv("SEEDING_TAG_NAME", "seeding")
# Environment variables for logging
LOG_MAX_SIZE = int(
    os.getenv("LOG_MAX_SIZE", 10 * 1024 * 1024)
)  # Default: 10 MB
LOG_BACKUP_COUNT = int(
    os.getenv("LOG_BACKUP_COUNT", 5)
)  # Default: 5 backup files
LOG_DIR = os.getenv("LOG_DIR", "/logs")

# Sonarr API endpoints
SERIES_API_URL = f"{SONARR_URL}/api/v3/series"
EPISODE_FILE_API_URL = f"{SONARR_URL}/api/v3/episodeFile"
TAG_API_URL = f"{SONARR_URL}/api/v3/tag"

# Set up log rotation
log_handler = RotatingFileHandler(
    f"{LOG_DIR}/sonarr.log", maxBytes=LOG_MAX_SIZE, backupCount=LOG_BACKUP_COUNT
)

# Set up logging
logging.basicConfig(
    level=get_log_level(),
    format="%(asctime)s - %(levelname)s - %(message)s",
    # Optional: Keep logging.StreamHandler() for debugging in container logs
    handlers=[
        log_handler,
        logging.StreamHandler(),
    ],
)


def get_series() -> List[Dict[str, Any]]:
    """Fetch all series from Sonarr."""
    headers = {"X-Api-Key": SONARR_API_KEY}
    response = requests.get(SERIES_API_URL, headers=headers)
    response.raise_for_status()
    # Cast the response to the expected type
    series: List[Dict[str, Any]] = response.json()
    return series


def get_episode_files(series_id: str) -> List[Dict[str, Any]]:
    """Fetch all episode files for a series."""
    headers = {"X-Api-Key": SONARR_API_KEY}
    response = requests.get(
        f"{EPISODE_FILE_API_URL}?seriesId={series_id}", headers=headers
    )
    response.raise_for_status()
    files: List[Dict[str, Any]] = response.json()
    return files


def get_or_create_tag(tag_name: str) -> Any:
    """Retrieve tag ID for given tag name, creating it if it doesn't exist."""
    headers = {"X-Api-Key": SONARR_API_KEY}

    # Fetch existing tags
    response = requests.get(TAG_API_URL, headers=headers)
    response.raise_for_status()
    tags = response.json()

    # Check if the tag already exists
    for tag in tags:
        if tag["label"].lower() == tag_name.lower():
            return tag["id"]

    # Create the tag if it doesn't exist
    payload = {"label": tag_name}
    response = requests.post(TAG_API_URL, json=payload, headers=headers)
    response.raise_for_status()
    tag_id = response.json()["id"]
    logging.info(f"Created new tag '{tag_name}' with ID {tag_id}")

    return tag_id


def is_tag_set_on_series(series_id: str, tag_id: str) -> bool:
    """Is the tag already set on this series?"""
    # Fetch the series details to check existing tags
    headers = {"X-Api-Key": SONARR_API_KEY}
    response = requests.get(f"{SERIES_API_URL}/{series_id}", headers=headers)
    response.raise_for_status()
    series_data = response.json()

    existing_tags = series_data.get("tags", [])
    if tag_id in existing_tags:
        logging.debug(f"Tag ID {tag_id} is set for series ID {series_id}")
        return True
    return False


def modify_tag(series_id: str, tag_id: str, add: bool = True) -> None:
    """Add or remove a tag from a series."""
    headers = {"X-Api-Key": SONARR_API_KEY}

    # Fetch the current series details
    response = requests.get(f"{SERIES_API_URL}/{series_id}", headers=headers)
    response.raise_for_status()
    series_data = response.json()

    # Update tags
    tags = set(series_data.get("tags", []))  # Get existing tags as a set
    if add:
        tags.add(tag_id)  # Add the tag
        logging.debug(
            f"Adding tag '{SEEDING_TAG_NAME}' to series ID {series_id}."
        )
    else:
        tags.discard(tag_id)  # Remove the tag if present
        logging.debug(
            f"Removing tag '{SEEDING_TAG_NAME}' from series ID {series_id}."
        )

    # Update the series object with the new tags
    series_data["tags"] = list(tags)
    response = requests.put(
        f"{SERIES_API_URL}/{series_id}",
        json=series_data,
        headers=headers,
    )
    response.raise_for_status()


def process_series() -> None:
    """Process all series in Sonarr."""
    try:
        series_list = get_series()

        # Get or create the 'seeding' tag ID
        seeding_tag_id = get_or_create_tag(SEEDING_TAG_NAME)

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
                if not is_tag_set_on_series(series_id, seeding_tag_id):
                    logging.info(
                        f"Adding {SEEDING_TAG_NAME} to {series_title} "
                        f"(ID: {series_id})"
                    )
                    modify_tag(series_id, seeding_tag_id, add=True)
                else:
                    logging.debug(
                        f"{SEEDING_TAG_NAME} already set on {series_title} "
                        f"(ID: {series_id})"
                    )
            else:
                if is_tag_set_on_series(series_id, seeding_tag_id):
                    logging.info(
                        f"Removing {SEEDING_TAG_NAME} from {series_title} "
                        f"(ID: {series_id})"
                    )
                    modify_tag(series_id, seeding_tag_id, add=False)

    except requests.RequestException as e:
        logging.error(f"Error interacting with Sonarr API: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    logging.info("Starting Sonarr seeding check...")
    process_series()
    logging.info("Sonarr seeding check completed.")
