import os
import requests
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from common_utils import is_file_seeding

# Environment variables for Radarr
RADARR_URL = os.getenv("RADARR_URL", "http://radarr:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "your_api_key")
SEEDING_DIR = os.getenv("SEEDING_DIR", "/data/downloads/qbittorrent/seed")
SEEDING_TAG_NAME = os.getenv("SEEDING_TAG_NAME", "seeding")
# Environment variables for logging
LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", 10 * 1024 * 1024))  # Default: 10 MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", 5))  # Default: 5 backup files
LOG_DIR = os.getenv("LOG_DIR", "/logs")

# Radarr API endpoints
MOVIE_API_URL = f"{RADARR_URL}/api/v3/movie"
TAG_API_URL = f"{RADARR_URL}/api/v3/tag"

# Set up log rotation
log_handler = RotatingFileHandler(
    f"{LOG_DIR}/radarr.log", maxBytes=LOG_MAX_SIZE, backupCount=LOG_BACKUP_COUNT
)
#log_handler.setLevel(logging.INFO)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        log_handler,
        logging.StreamHandler()  # Optional: Keep this for debugging in container logs
    ],
)

def get_movies():
    """Fetch all movies from Radarr."""
    headers = {"X-Api-Key": RADARR_API_KEY}
    response = requests.get(MOVIE_API_URL, headers=headers)
    response.raise_for_status()
    return response.json()

def get_or_create_tag(tag_name):
    """Retrieve the tag ID for a given tag name, creating it if it doesn't exist."""
    headers = {"X-Api-Key": RADARR_API_KEY}

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

def is_tag_set_on_movie(movie_id, tag_id):
    """Is the tag already set on this movie?"""
    # Fetch the current movie details to check existing tags
    headers = {"X-Api-Key": RADARR_API_KEY}
    response = requests.get(f"{MOVIE_API_URL}/{movie_id}", headers=headers)
    response.raise_for_status()
    movie_data = response.json()

    existing_tags = movie_data.get("tags", [])
    if tag_id in existing_tags:
        logging.debug(f"Tag ID {tag_id} is set for movie ID {movie_id}")
        return True
    return False

def modify_tag(movie_id, tag_id, add=True):
    """Add or remove a tag from a movie."""
    #headers = {"X-Api-Key": RADARR_API_KEY}
    #if add:
    #    requests.post(f"{MOVIE_API_URL}/{movie_id}/tag", json={"tagIds": [tag_id]}, headers=headers).raise_for_status()
    #    logging.info(f"Added tag '{SEEDING_TAG_NAME}' to movie ID {movie_id}.")
    #else:
    #    requests.delete(f"{MOVIE_API_URL}/{movie_id}/tag/{tag_id}", headers=headers).raise_for_status()
    #    logging.info(f"Removed tag '{SEEDING_TAG_NAME}' from movie ID {movie_id}.")
    logging.info(f"Called modify_tag for movie {movie_id}, with add {add}")

def process_movies():
    """Process all movies in Radarr."""
    try:
        movies = get_movies()

        # Get or create the 'seeding' tag ID
        seeding_tag_id = get_or_create_tag(SEEDING_TAG_NAME)

        for movie in movies:
            movie_id = movie["id"]
            movie_file_path = movie.get("movieFile", {}).get("path")

            if not movie_file_path:
                logging.info(f"No movie file found for movie ID {movie_id}. Skipping.")
                continue

            if is_file_seeding(movie_file_path):
                if not is_tag_set_on_movie(movie_id, seeding_tag_id):
                    logging.info(f"Adding {SEEDING_TAG_NAME} to {movie['title']} (ID: {movie_id})")
                    modify_tag(movie_id, seeding_tag_id, add=True)
                else:
                    logging.info(f"{SEEDING_TAG_NAME} already set on {movie['title']} (ID: {movie_id})")
            else:
                if is_tag_set_on_movie(movie_id, seeding_tag_id):
                    logging.info(f"Removing {SEEDING_TAG_NAME} from {movie['title']} (ID: {movie_id})")
                    modify_tag(movie_id, seeding_tag_id, add=False)

    except requests.RequestException as e:
        logging.error(f"Error interacting with Radarr API: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    logging.info("Starting Radarr seeding check...")
    process_movies()
    logging.info("Radarr seeding check completed.")
