import os
import requests
import logging
import fnmatch
from logging.handlers import RotatingFileHandler

# Configuration
RADARR_URL = "http://radarr:7878"  # Replace with your Radarr URL
RADARR_API_KEY = "your_api_key"  # Replace with your Radarr API key
SEEDING_TAG_NAME = "seeding"  # Replace with the desired tag name
LOG_FILE = "/logs/radarr_seeding.log"  # Path to the log file

# Configuration from environment variables with defaults
RADARR_URL = os.getenv("RADARR_URL", "http://radarr:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "your_api_key")
SEEDING_TAG_NAME = os.getenv("SEEDING_TAG_NAME", "seeding")
SEEDING_DIRECTORY = os.getenv("SEEDING_DIRECTORY", "/data/downloads/qbittorrent/seed/")
LOG_FILE = os.getenv("LOG_FILE", "/logs/hardlink-checkerr.log")
LOG_MAX_SIZE = int(os.getenv("LOG_MAX_SIZE", 10 * 1024 * 1024))  # Default: 10 MB
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", 5))  # Default: 5 backup files

# Set up log rotation
log_handler = RotatingFileHandler(
    LOG_FILE, maxBytes=LOG_MAX_SIZE, backupCount=LOG_BACKUP_COUNT
)
log_handler.setLevel(logging.INFO)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        log_handler,
        logging.StreamHandler()  # Optional: Keep this for debugging in container logs
    ],
)

# Helper functions
def get_all_movies():
    """Fetch all movies from the Radarr library."""
    url = f"{RADARR_URL}/api/v3/movie"
    headers = {"X-Api-Key": RADARR_API_KEY}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def get_hardlink_count(file_path):
    """Get the hardlink count of the file."""
    try:
        return os.stat(file_path).st_nlink
    except FileNotFoundError:
        logging.warning(f"File not found: {file_path}")
        return 0

def find_hardlinked_files(file_path):
    """Find all other files with the same inode (hardlinks)."""
    inode = os.stat(file_path).st_ino
    hardlinked_files = []

    # Walk the file system and check all files (can be optimized for specific directories)
    for root, _, files in os.walk(SEEDING_DIRECTORY):
        for file in files:
            full_path = os.path.join(root, file)
            if os.stat(full_path).st_ino == inode and full_path != file_path:
                hardlinked_files.append(full_path)

    return hardlinked_files

def get_or_create_tag(tag_name):
    """Retrieve the tag ID for a given tag name, creating it if it doesn't exist."""
    url = f"{RADARR_URL}/api/v3/tag"
    headers = {"X-Api-Key": RADARR_API_KEY}

    # Fetch existing tags
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    tags = response.json()

    # Check if the tag already exists
    for tag in tags:
        if tag["label"].lower() == tag_name.lower():
            return tag["id"]

    # Create the tag if it doesn't exist
    payload = {"label": tag_name}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    tag_id = response.json()["id"]
    logging.info(f"Created new tag '{tag_name}' with ID {tag_id}")

    return tag_id

def is_tag_set_on_movie(movie_id, tag_id):
    """Is the tag already set on this movie?"""
    # Fetch the current movie details to check existing tags
    url = f"{RADARR_URL}/api/v3/movie/{movie_id}"
    headers = {"X-Api-Key": RADARR_API_KEY}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    movie_data = response.json()

    existing_tags = movie_data.get("tags", [])
    if tag_id in existing_tags:
        logging.debug(f"Tag ID {tag_id} is already present for movie ID {movie_id}. Skipping.")
        return True
    return False

def add_tag_to_movie(movie_id, tag_id):
    """Add a tag to the movie in Radarr."""
    # Fetch the current movie details to check existing tags
    url = f"{RADARR_URL}/api/v3/movie/{movie_id}"
    headers = {"X-Api-Key": RADARR_API_KEY}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    movie_data = response.json()

    existing_tags = movie_data.get("tags", [])
    if tag_id in existing_tags:
        logging.debug(f"Tag ID {tag_id} is already present for movie ID {movie_id}. Skipping.")
        return

    # Add the tag if it is not already present
    url = f"{RADARR_URL}/api/v3/movie/editor"
    headers = {"X-Api-Key": RADARR_API_KEY, "Content-Type": "application/json"}
    payload = {
        "movieIds": [movie_id],
        "applyTags": [tag_id],
        "tags": [tag_id],
        "replaceExistingTags": False,
    }
    # TODO - don't actually update
    #response = requests.put(url, json=payload, headers=headers)
    #response.raise_for_status()
    logging.info(f"Added tag ID {tag_id} to movie ID {movie_id}")

# Radarr API URL to get movie data
MOVIE_API_URL = f"{RADARR_URL}/api/v3/movie"
TAG_API_URL = f"{RADARR_URL}/api/v3/tag"
# Function to remove a tag from a movie
def remove_tag_from_movie(movie_id, tag_id):
    headers = {"X-Api-Key": RADARR_API_KEY}
    response = requests.delete(f"{MOVIE_API_URL}/{movie_id}/tag/{tag_id}", headers=headers)
    response.raise_for_status()
    logging.info(f"Tag '{SEEDING_TAG_NAME}' removed from movie {movie_id}")

# Main logic
def main():
    # Get all movies
    movies = get_all_movies()
    if not movies:
        logging.warning("No movies found in the Radarr library.")
        return

    # Get or create the 'seeding' tag ID
    seeding_tag_id = get_or_create_tag(SEEDING_TAG_NAME)

    for movie in movies:
        movie_id = movie["id"]
        movie_file = movie.get("movieFile")

        if not movie_file or not movie_file.get("path"):
            # Movie likely not released yet
            logging.debug(f"No file found for movie: {movie['title']} (ID: {movie_id})")
            continue

        if hardlink_count > 1:
            logging.info(f"Movie: {movie['title']} (ID: {movie_id}) has a hardlink count of {hardlink_count}.")

            # See if this same file is hardlinked under torrent seeding directory
            hardlinked_files = find_hardlinked_files(file_path)
            # Did we find any files earlier?
            if hardlinked_files:
                logging.info(f"Movie: {movie['title']} (ID: {movie_id}) has hardlinked files in seeding directory ({hardlinked_files}). Tagging as 'seeding'.")
                add_tag_to_movie(movie_id, seeding_tag_id)
            else:
                logging.debug(f"Movie: {movie['title']} (ID: {movie_id}) does not have hardlinked files in a seeding directory.")
        else:
            # TODO - check if the tag exists and remove it if it does
            logging.debug(f"Movie: {movie['title']} (ID: {movie_id}) has a hardlink count of {hardlink_count}. No tag added.")

if __name__ == "__main__":
    main()
