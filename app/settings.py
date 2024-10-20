import os
import base64
import json
from pathlib import Path
from dotenv import load_dotenv
import logging

# Setup logging
load_dotenv()
DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
logging.basicConfig(level=logging.DEBUG if DEBUG else logging.INFO)
logger = logging.getLogger(__name__)

# Define base directory
BASE_DIR = Path(__file__).resolve().parent

# Configuration variables
URL = os.getenv("URL", "https://hq.qashier.com/#/login")
URL_CUST_MAGEMENT = os.getenv("URL_CUST_MAGEMENT")

# Paths
DOWNLOAD_FOLDER = Path(os.getenv("DOWNLOAD_FOLDER", BASE_DIR / "tmp" / "browserdownload"))
SCREENSHOT_FOLDER = Path(os.getenv("SCREENSHOT_FOLDER", BASE_DIR / "tmp" / "browserscreenshots"))
PATH_TO_GOOGLE_KEY = Path(os.getenv("PATH_TO_GOOGLE_KEY", BASE_DIR / "tmp" / "service_account.json"))

HEADLESS = True

DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1gJJn48WyvrYWjq7pcZ1qGZDNQsDYjMME")
FILE_NAME_PREFIX = os.getenv("FILE_NAME_PREFIX", "LENGOLF_CRM")

# Ensure directories exist
for folder in [DOWNLOAD_FOLDER, SCREENSHOT_FOLDER, PATH_TO_GOOGLE_KEY.parent]:
    folder.mkdir(parents=True, exist_ok=True)

try:
    required_vars = ["LOGIN", "PASSWORD", "GOOGLE_KEY"]
    missing_vars = [var for var in required_vars if var not in os.environ]
    if missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}. Exiting.")
        exit(1)

    # Decode LOGIN and PASSWORD
    APP_LOGIN_ENCODED = os.getenv("LOGIN")
    APP_LOGIN = base64.b64decode(APP_LOGIN_ENCODED).decode('utf-8')
    logger.debug(f"Decoded LOGIN: {APP_LOGIN}")

    APP_PASSWORD_ENCODED = os.getenv("PASSWORD")
    APP_PASSWORD = base64.b64decode(APP_PASSWORD_ENCODED).decode('utf-8')
    logger.debug(f"Decoded PASSWORD: {APP_PASSWORD}")

    # Decode GOOGLE_KEY
    GOOGLE_KEY_ENCODED = os.getenv("GOOGLE_KEY")
    decoded_google_key = base64.b64decode(GOOGLE_KEY_ENCODED).decode('utf-8')

    # Validate JSON
    google_key_json = json.loads(decoded_google_key)

    # Write the decoded key to the file
    with open(PATH_TO_GOOGLE_KEY, "w") as f:
        json.dump(google_key_json, f, indent=2)
    logger.info(f"Google key decoded and placed in {PATH_TO_GOOGLE_KEY}")

except Exception as ex:
    logger.error("ERROR during parsing ENV variables.", exc_info=True)
    exit(1)
