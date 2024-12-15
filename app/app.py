import re
import os
import time
from pathlib import Path
import logging
import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from functools import wraps
from dotenv import load_dotenv
from flask import Flask, jsonify

# Playwright imports
from playwright.sync_api import sync_playwright, TimeoutError

# Supabase
from supabase import create_client, Client

# Data handling imports
import pandas as pd
import numpy as np

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Import settings from settings.py or define them here
from settings import (
    DOWNLOAD_FOLDER,
    SCREENSHOT_FOLDER,
    DEBUG,
    HEADLESS,
    APP_LOGIN,
    APP_PASSWORD,
    URL,
    URL_CUST_MAGEMENT
)

# Supabase setup
supabase: Client = create_client(
    os.getenv('NEXT_PUBLIC_SUPABASE_URL'),
    os.getenv('NEXT_PUBLIC_SUPABASE_ANON_KEY')
)

class CloudLoggingFormatter(logging.Formatter):
    def format(self, record):
        message = super().format(record)
        
        log_entry = {
            "severity": record.levelname,
            "message": message,
            "timestamp": datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
            "logger": record.name,
        }
        
        if record.exc_info:
            log_entry["error"] = {
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info)
            }
            
        return json.dumps(log_entry)

# Setup logging for Google Cloud
logger = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(CloudLoggingFormatter())
logger.handlers = [handler]
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)

# Column name mapping
COLUMN_MAP = {
    'Store': 'store',
    'Customer': 'customer_name',
    'Contact Number': 'contact_number',
    'Address': 'address',
    'Email': 'email',
    'Date of Birth': 'date_of_birth',
    'Date Joined': 'date_joined',
    'Available Credit': 'available_credit',
    'Available Point': 'available_point',
    'Source': 'source',
    'SMS PDPA': 'sms_pdpa',
    'Email PDPA': 'email_pdpa'
}

# Retry decorator
def retry_on_exception(retries=3, delay=1):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < retries - 1:
                        sleep_time = delay * (2 ** attempt)
                        logger.error(f"Attempt {attempt + 1}/{retries} failed: {str(e)}")
                        logger.info(f"Retrying in {sleep_time} seconds...")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"All {retries} attempts failed. Last error: {str(e)}")
            raise last_exception
        return wrapper
    return decorator

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
            accept_downloads=True
        )
        page = context.new_page()

        try:
            # Navigate to the login page
            login_url = "https://hq.qashier.com/#/login?redirect=/customer-management"
            logger.info(f"Navigating to login page: {login_url}")
            page.goto(login_url, wait_until='networkidle', timeout=60000)
            logger.info(f"Login page loaded: {page.title()}")

            # Wait for the username input to be visible
            page.wait_for_selector('label:has-text("Username")', timeout=10000)
            logger.info("Username input is available.")

            screenshot(filename="LoginPageBefore.png", page=page)

            # Input credentials using get_by_label
            page.get_by_label("Username").click()
            page.get_by_label("Username").fill(APP_LOGIN)
            page.get_by_label("Username").press("Tab")
            page.get_by_label("Password").fill(APP_PASSWORD)

            logger.info("Inputted login credentials.")
            screenshot(filename="LoginPageAfter.png", page=page)

            # Click the login button and wait for navigation
            with page.expect_navigation(timeout=60000):
                page.get_by_role("button", name="Login").click()
            logger.info("Pressed LOGIN and navigated.")

            # Verify successful login by checking for the Export button
            page.wait_for_selector('button:has-text("Export")', timeout=15000)
            logger.info("Login successful. Export button found.")

            # Wait for data to load
            logger.info("Waiting for 10 seconds to allow data to load.")
            time.sleep(10)

            # Export data
            page.locator('button:has-text("Export")').click()
            page.wait_for_selector('button:has-text("Confirm")', timeout=10000)
            
            with page.expect_download() as download_info:
                page.locator('button:has-text("Confirm")').click()
                logger.info("Download confirmed.")
                download = download_info.value

                download_path = os.path.join(DOWNLOAD_FOLDER, download.suggested_filename)
                download.save_as(download_path)
                logger.info(f"Downloaded file to {download_path}")

        except Exception as e:
            logger.error(f"Error during file download: {str(e)}", exc_info=True)
            screenshot(filename="ErrorState.png", page=page)
            raise
        finally:
            browser.close()

def list_download_dir():
    logger.info("Listing downloaded CSV files locally.")
    files = []
    for child in [i for i in Path(DOWNLOAD_FOLDER).iterdir() if i.suffix.lower() == ".csv"]:
        logger.info(f"Found file: {child}")
        files.append(child)
    return files

def parse_date(date_str):
    if not date_str or pd.isna(date_str):
        return None
    try:
        return datetime.strptime(date_str, '%d/%m/%Y').strftime('%Y-%m-%d')
    except:
        return None

def clean_numeric(value):
    if pd.isna(value) or value == '':
        return 0
    if isinstance(value, str):
        return float(value.replace(',', ''))
    return float(value)

@retry_on_exception(retries=3, delay=1)
def convert_file_to_data(file_path):
    logger.info(f"Converting file to pandas DataFrame: {file_path}")
    try:
        df_data = pd.read_csv(file_path)
        logger.debug(f"DataFrame head:\n{df_data.head()}")
        
        # Create unique customer identifiers
        df_data['customer_name_count'] = df_data.groupby('Customer')['Customer'].transform('count')
        df_data['customer_name_group'] = df_data.groupby('Customer').cumcount() + 1
        df_data['Customer'] = df_data.apply(lambda x: 
            f"{x['Customer']}_{x['customer_name_group']}" if x['customer_name_count'] > 1 else x['Customer'], 
            axis=1)
        
        # Drop the helper columns
        df_data = df_data.drop(['customer_name_count', 'customer_name_group'], axis=1)
        
        # Rename columns based on mapping
        df_data = df_data.rename(columns=COLUMN_MAP)
        
        # Fill NA values
        df_data = df_data.fillna('')
        
        # Convert date fields
        df_data['date_of_birth'] = df_data['date_of_birth'].apply(parse_date)
        df_data['date_joined'] = df_data['date_joined'].apply(parse_date)
        
        # Convert PDPA fields to boolean
        df_data['sms_pdpa'] = df_data['sms_pdpa'].map({'Yes': True, 'No': False})
        df_data['email_pdpa'] = df_data['email_pdpa'].map({'Yes': True, 'No': False})
        
        # Convert numeric fields
        df_data['available_credit'] = df_data['available_credit'].apply(clean_numeric)
        df_data['available_point'] = df_data['available_point'].apply(clean_numeric)
        
        # Add timestamp
        current_time = datetime.now(ZoneInfo("Asia/Bangkok")).strftime('%Y-%m-%d %H:%M:%S')
        df_data['update_time'] = current_time

        logger.info("Conversion to DataFrame completed.")
        return df_data

    except Exception as ex:
        logger.error("Error during reading CSV into pandas and formatting.", exc_info=True)
        raise ex

@retry_on_exception(retries=3, delay=1)
def push_to_supabase(df_data):
    try:
        logger.info("Pushing data to Supabase")

        # Convert DataFrame to list of dictionaries
        records = df_data.to_dict('records')
        
        # First, create a new batch_id based on current timestamp
        batch_id = datetime.now(ZoneInfo("Asia/Bangkok")).strftime('%Y%m%d_%H%M%S')
        
        # Add batch_id to each record and convert numpy types
        for record in records:
            record['batch_id'] = batch_id
            # Convert numpy types to Python types
            for key, value in record.items():
                if isinstance(value, np.integer):
                    record[key] = int(value)
                elif isinstance(value, np.floating):
                    record[key] = float(value)
                elif isinstance(value, np.bool_):
                    record[key] = bool(value)

        # Clear existing data from Supabase
        data = supabase.table('customers').select('id').execute()
        if data.data:  # Only attempt to delete if there is data
            logger.info("Truncating existing data from customers table")
            result = supabase.table('customers').delete().execute()
            logger.info("Table truncated successfully")

        # Insert new data
        result = supabase.table('customers').insert(records).execute()
        
        logger.info(f"Inserted {len(records)} records with batch_id: {batch_id}")
        return batch_id

    except Exception as ex:
        logger.error(f"Unexpected error during Supabase update: {str(ex)}", exc_info=True)
        raise ex

def run_job():
    """Run the actual job logic"""
    logger.info("APP START")
    
    try:
        get_file()
        files = list_download_dir()
        results = []
        for file_path in files:
            body = convert_file_to_data(file_path)
            batch_id = push_to_supabase(body)
            results.append({
                "file": str(file_path),
                "batch_id": batch_id,
                "status": "success"
            })
            logger.info(f"Successfully processed file {file_path} with batch_id {batch_id}")
        
        return {"status": "success", "results": results}
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Critical error in main execution: {error_msg}", exc_info=True)
        return {"status": "error", "message": error_msg}
    finally:
        logger.info("APP END")

@app.route('/healthz', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now(ZoneInfo("Asia/Bangkok")).isoformat(),
        "service": "lengolf-crm"
    }), 200

@app.route('/', methods=['GET'])
def trigger_job():
    """Endpoint to trigger the sync job"""
    result = run_job()
    if result["status"] == "success":
        return jsonify(result), 200
    else:
        return jsonify(result), 500

if __name__ == "__main__":
    # Ensure required directories exist
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    os.makedirs(SCREENSHOT_FOLDER, exist_ok=True)
    
    # Get port from environment variable or default to 8080
    port = int(os.environ.get('PORT', 8080))
    
    # Run Flask app
    app.run(host='0.0.0.0', port=port)