import os
import requests
import logging
from logging.handlers import RotatingFileHandler
from common_utils import is_file_seeding, get_log_level
from typing import List, Dict, Any

# Environment variables for Radarr
RADARR_URL = os.getenv("RADARR_URL", "http://radarr:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "your_api_key")
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

# Radarr API endpoints
MOVIE_API_URL = f"{RADARR_URL}/api/v3/movie"
TAG_API_URL = f"{RADARR_URL}/api/v3/tag"

# Set up log rotation
log_handler = RotatingFileHandler(
    f"{LOG_DIR}/radarr.log", maxBytes=LOG_MAX_SIZE, backupCount=LOG_BACKUP_COUNT
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


def get_movies() -> List[Dict[str, Any]]:
    """Fetch all movies from Radarr."""
    headers = {"X-Api-Key": RADARR_API_KEY}
    response: requests.Response = requests.get(MOVIE_API_URL, headers=headers)
    response.raise_for_status()
    # Cast the response to the expected type
    movies: List[Dict[str, Any]] = response.json()
    return movies


def get_or_create_tag(tag_name: str) -> Any:
    """Retrieve tag ID for given tag name, creating it if it doesn't exist."""
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


def is_tag_set_on_movie(movie_id: str, tag_id: str) -> bool:
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


def modify_tag(movie_id: str, tag_id: str, add: bool = True) -> None:
    """Add or remove a tag from a movie."""
    # headers = {"X-Api-Key": RADARR_API_KEY}
    # if add:
    #     requests.post(
    #         f"{MOVIE_API_URL}/{movie_id}/tag",
    #         json={"tagIds": [tag_id]},
    #         headers=headers,
    #     ).raise_for_status()
    #     logging.debug(
    #         f"Added tag '{SEEDING_TAG_NAME}' to movie ID {movie_id}.")
    # else:
    #     requests.delete(
    #         f"{MOVIE_API_URL}/{movie_id}/tag/{tag_id}", headers=headers
    #     ).raise_for_status()
    #     logging.debug(
    #         f"Removed tag '{SEEDING_TAG_NAME}' from movie ID {movie_id}."
    #     )
    logging.info(f"Called modify_tag for movie {movie_id}, with add {add}")


def process_movies() -> None:
    """Process all movies in Radarr."""
    try:
        movies = get_movies()

        # Get or create the 'seeding' tag ID
        seeding_tag_id = get_or_create_tag(SEEDING_TAG_NAME)

        for movie in movies:
            movie_id = movie["id"]
            movie_file_path = movie.get("movieFile", {}).get("path")

            if not movie_file_path:
                logging.debug(
                    f"No movie file found for movie ID {movie_id}. Skipping."
                )
                continue

            if is_file_seeding(movie_file_path):
                if not is_tag_set_on_movie(movie_id, seeding_tag_id):
                    logging.info(
                        f"Adding {SEEDING_TAG_NAME} to {movie['title']} "
                        f"(ID: {movie_id})"
                    )
                    modify_tag(movie_id, seeding_tag_id, add=True)
                else:
                    logging.debug(
                        f"{SEEDING_TAG_NAME} already set on {movie['title']} "
                        f"(ID: {movie_id})"
                    )
            else:
                if is_tag_set_on_movie(movie_id, seeding_tag_id):
                    logging.info(
                        f"Removing {SEEDING_TAG_NAME} from {movie['title']} "
                        f"(ID: {movie_id})"
                    )
                    modify_tag(movie_id, seeding_tag_id, add=False)

    except requests.RequestException as e:
        logging.error(f"Error interacting with Radarr API: {e}")
    except Exception as e:
        logging.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    logging.info("Starting Radarr seeding check...")
    process_movies()
    logging.info("Radarr seeding check completed.")
