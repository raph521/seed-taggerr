import os
import logging
import subprocess
from pathlib import Path

SEEDING_DIR = os.getenv("SEEDING_DIR", "/data/downloads/qbittorrent/seed")

def get_log_level():
    # Map log level strings to logging constants
    LOG_LEVELS = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    # Get the log level from an environment variable, default to INFO
    log_level_name = os.getenv("LOG_LEVEL", "INFO").upper()  # Default to INFO
    log_level = LOG_LEVELS.get(log_level_name, logging.INFO)  # Fallback to INFO if invalid

    if log_level_name not in LOG_LEVELS:
        print(f"Invalid LOG_LEVEL '{log_level_name}' provided. Defaulting to INFO.")

    return log_level

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
    for root, _, files in os.walk(SEEDING_DIR):
        for file in files:
            full_path = os.path.join(root, file)
            if os.stat(full_path).st_ino == inode and full_path != file_path:
                hardlinked_files.append(full_path)

    return hardlinked_files

def is_file_seeding(file_path):
    """Check if this file has a hardlink in the seeding directory."""
    if get_hardlink_count(file_path) == 1:
        return False

    return find_hardlinked_files(file_path) != []
