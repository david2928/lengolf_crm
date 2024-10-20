import re
import os
import time  # Added import for time.sleep
from pathlib import Path
import logging
from datetime import datetime

# Playwright imports
from playwright.sync_api import sync_playwright, TimeoutError

# Google API imports
from google.oauth2 import service_account  # Added missing import
from googleapiclient.errors import HttpError
import gspread

# Data handling imports
import pandas as pd

# Import settings from settings.py or define them here
from settings import (
    DOWNLOAD_FOLDER,
    SCREENSHOT_FOLDER,
    DEBUG,
    HEADLESS,
    APP_LOGIN,
    APP_PASSWORD,
    URL,
    URL_CUST_MAGEMENT,
    PATH_TO_GOOGLE_KEY,
    FILE_NAME_PREFIX,
    DRIVE_FOLDER_ID
)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def screenshot(filename, page):
    if DEBUG:
        path = os.path.join(SCREENSHOT_FOLDER, filename)
        page.screenshot(path=path)
        logger.debug(f"Screenshot saved to {path}")

def get_file():
    logger.info("Getting files from CMS")
    with sync_playwright() as p:
        if DEBUG:
            logger.debug(f"HEADLESS = {HEADLESS}")
            logger.debug(f"APP_LOGIN = {APP_LOGIN}")
            logger.debug(f"APP_PASSWORD = {APP_PASSWORD}")
            logger.debug(f"URL = {URL}")
            logger.debug(f"URL_CUST_MAGEMENT = {URL_CUST_MAGEMENT}")
        
        browser = p.chromium.launch(headless=HEADLESS)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/58.0.3029.110 Safari/537.3",
            accept_downloads=True  # Ensure downloads are accepted
        )
        page = context.new_page()

        # Navigate to the login page
        login_url = "https://hq.qashier.com/login?redirect=/customer-management#/customer-management"
        logger.info(f"Navigating to login page: {login_url}")
        page.goto(login_url, wait_until='networkidle', timeout=60000)
        logger.info(f"Login page loaded: {page.title()}")

        # Wait for the username input to be visible
        try:
            page.wait_for_selector('label:has-text("Username")', timeout=10000)
            logger.info("Username input is available.")
        except Exception as e:
            logger.error(f"Username input not found: {e}")
            screenshot(filename="LoginPageTimeout.png", page=page)
            browser.close()
            raise

        screenshot(filename="LoginPageBefore.png", page=page)

        # Input credentials using get_by_label
        page.get_by_label("Username").click()
        page.get_by_label("Username").fill(APP_LOGIN)
        page.get_by_label("Username").press("Tab")
        page.get_by_label("Password").fill(APP_PASSWORD)

        logger.info("Inputted login credentials.")
        logger.info("Pressing LOGIN...")

        screenshot(filename="LoginPageAfter.png", page=page)

        # Click the login button
        try:
            with page.expect_navigation(timeout=60000):
                page.get_by_role("button", name="Login").click()
            logger.info("Pressed LOGIN and navigated.")
        except Exception as e:
            logger.error(f"Error during login: {e}")
            screenshot(filename="LoginNavigationTimeout.png", page=page)
            browser.close()
            raise

        # Verify successful login by checking for the Export button
        try:
            page.wait_for_selector('button:has-text("Export")', timeout=15000)
            logger.info("Login successful. Export button found.")
        except Exception as e:
            logger.error(f"Login did not complete within timeout. Export button not found: {e}")
            screenshot(filename="LoginFailed.png", page=page)
            browser.close()
            raise

        # Wait for 10 seconds before exporting
        logger.info("Waiting for 10 seconds to allow data to load.")
        time.sleep(10)

        # Proceed to export data
        page.locator('button:has-text("Export")').click()
        page.wait_for_selector('button:has-text("Confirm")', timeout=10000)
        
        with page.expect_download() as download_info:
            # Perform the action that initiates download
            page.locator('button:has-text("Confirm")').click()
            logger.info("Download confirmed.")
            download = download_info.value

            # Wait for the download process to complete and save the downloaded file
            download_path = os.path.join(DOWNLOAD_FOLDER, download.suggested_filename)
            download.save_as(download_path)
            logger.info(f"Downloaded file to {download_path}")
        
        browser.close()

def list_download_dir():
    logger.info("Listing downloaded CSV files locally.")
    files = []
    for child in [i for i in Path(DOWNLOAD_FOLDER).iterdir() if i.suffix.lower() == ".csv"]:
        logger.info(f"Found file: {child}")
        files.append(child)
    return files

def convert_file_to_sheets_data(file_path):
    try:
        logger.info(f"Converting file to pandas DataFrame: {file_path}")
        df_data = pd.read_csv(file_path)
        logger.debug(f"DataFrame head:\n{df_data.head()}")
        df_data_cleaned = df_data.fillna('')
        
        # Add a column with the current timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        df_data_cleaned['UpdateTime'] = current_time

        logger.info("Conversion to DataFrame completed.")
        return df_data_cleaned

    except Exception as ex:
        logger.error("Error during reading CSV into pandas and formatting.")
        raise ex

def push_to_google_sheets(df_data):
    try:
        logger.info("Pushing data to Google Sheets.")

        # Set up credentials
        credentials = service_account.Credentials.from_service_account_file(PATH_TO_GOOGLE_KEY)

        # Set up gspread lib
        gc = gspread.service_account(filename=PATH_TO_GOOGLE_KEY)

        # Open the Google Sheet by ID
        sheet_id = '1XE5OLufFXk_Ob2oMzB37VYgeKUjri5iTjMUDi3Q1KG8'  # Replace with your actual sheet ID
        worksheet = gc.open_by_key(sheet_id).sheet1  # Assuming you want the first sheet

        # Clear the worksheet
        worksheet.clear()
        logger.info("Worksheet cleared.")

        # Prepare data to update
        data_to_update = []
        data_to_update.append(df_data.columns.values.tolist())
        data_to_update.extend(df_data.values.tolist())

        # Log the data being sent to Google Sheets
        logger.debug(f"Data to update (first 5 rows):\n{data_to_update[:5]}")

        # Update the worksheet starting from cell A1 using named arguments to avoid DeprecationWarning
        worksheet.update(values=data_to_update, range_name='A1')
        logger.info("Google Sheet populated with data.")

    except HttpError as error:
        logger.error(f"An error occurred during updating Google Sheets: {error}")
        raise error

    except Exception as ex:
        logger.error(f"An unexpected error occurred: {ex}")
        raise ex

def main():
    logger.info("APP START")
    
    try:
        get_file()
        files = list_download_dir()
        for file_path in files:
            body = convert_file_to_sheets_data(file_path)
            push_to_google_sheets(body)
    except Exception as e:
        logger.error(f"An error occurred in main: {e}")
    
    logger.info("APP END")

if __name__=="__main__":
    main()
