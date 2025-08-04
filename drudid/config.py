"""
Configuration settings for the drudid project.

This module contains all configuration variables, paths, and settings used
throughout the drudid application, including environment-specific settings,
API configuration, and project structure definitions.
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

# Load environment variables from .env file if it exists
load_dotenv()

DEV_MODE = os.getenv("DEV_MODE", True)

# Paths
PROJ_ROOT = Path(__file__).resolve().parents[1]
logger.info(f"PROJ_ROOT path is: {PROJ_ROOT}")

DATA_DIR = PROJ_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
MODELS_DIR = PROJ_ROOT / "models"
REPORTS_DIR = PROJ_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# Fetcher configuration for Drupal.org
# @see https://www.drupal.org/project/issues
FETCHER_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
    "User-Agent": "DrudidFetcher/1.0",
}
FETCHER_BASE_URL = "https://www.drupal.org/api-d7"
FETCHER_BASE_PARAMS = {
    "resource": "node.json",
    "type": "project_issue",
    "sort": "created",
    "direction": "ASC",
}

# If tqdm is installed, configure loguru with tqdm.write
# https://github.com/Delgan/loguru/issues/135
try:
    from tqdm import tqdm

    logger.remove(0)
    logger.add(lambda msg: tqdm.write(msg, end=""), colorize=True)
except ModuleNotFoundError:
    pass
