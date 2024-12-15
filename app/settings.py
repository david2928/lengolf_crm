import os
import base64
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

HEADLESS = True

# Ensure directories exist
for folder in [DOWNLOAD_FOLDER, SCREENSHOT_FOLDER]:
    folder.mkdir(parents=True, exist_ok=True)

try:
    required_vars = ["LOGIN", "PASSWORD", "NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_ANON_KEY"]
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

    # Supabase settings
    SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    SUPABASE_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
    logger.info("Supabase configuration loaded successfully")

except Exception as ex:
    logger.error("ERROR during parsing ENV variables.", exc_info=True)
    exit(1)