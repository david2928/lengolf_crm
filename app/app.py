from playwright.sync_api import Page, expect, sync_playwright
import os
from pathlib import Path

from googleapiclient import discovery
from google.oauth2 import service_account
from pprint import pprint
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from datetime import datetime
import pandas as pd
import gspread
from  settings import *

def screenshot(filename, page):
    if DEBUG:
        page.screenshot(path=os.path.join(SCREENSHOT_FOLDER, filename))

def get_file():
    print("Getting files from CMS")
    with sync_playwright() as p:
        if DEBUG:
            print(f"HEADLESS = {HEADLESS}")
            print(f"APP_LOGIN = {APP_LOGIN}")
            print(f"APP_PASSWORD = {APP_PASSWORD}")
            print(f"URL = {URL}")
            print(f"URL_CUST_MAGEMENT = {URL_CUST_MAGEMENT}")
            
        browser = p.chromium.launch(headless=HEADLESS)
        page = browser.new_page()
        print(f"Opening main page: {URL}")
        page.goto(URL)
        page.wait_for_load_state()
        print(f"Opened main page {page.title()}")

        screenshot(filename="LoginPageBefore.png", page=page)

        page.get_by_label('Username').fill(APP_LOGIN)
        page.get_by_label('Password').fill(APP_PASSWORD)

        print(f"Input log/pass")
        print(f"Pressing LOGIN...")

        screenshot(filename="LoginPageAfter.png", page=page)
        page.locator('button:has-text("Login")').click()
        print(f"Pressed LOGIN")
        
        page.wait_for_timeout(2000)
        page.wait_for_load_state()
        print(f"Login finished")

        print(f"Opening cust management url: {URL_CUST_MAGEMENT}")
        page.goto(URL_CUST_MAGEMENT)

        page.wait_for_timeout(2000)
        page.wait_for_load_state()

        screenshot(filename="CustManagementUrl.png", page=page)
        print(f"Opened cust management")
        
        page.locator('button:has-text("Export")').click()
        page.wait_for_timeout(2000)
        page.wait_for_load_state()
        
        with page.expect_download() as download_info:
            # Perform the action that initiates download
            page.locator('button:has-text("Confirm")').click()
            page.wait_for_timeout(2000)
            download = download_info.value

            # Wait for the download process to complete and save the downloaded file somewhere
            download.save_as(os.path.join(DOWNLOAD_FOLDER, download.suggested_filename))

        browser.close()

def list_download_dir():
    print("List of downloaded csv files locally")
    files = []
    for child in [i for i in Path(DOWNLOAD_FOLDER).iterdir() if ".csv" in str(i)]:
        print(child)
        files.append(child)

    return files

def convert_file_to_sheets_data(file_path):
    try:
        print("Converting files into pandas")
        df_data = pd.read_csv(file_path)
        df_data_cleaned = df_data.fillna('')
        
        # Add a column with the current timestamp
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        df_data_cleaned['UpdateTime'] = current_time

        print("Done")
        return df_data_cleaned

    except Exception as ex:
        print("Error during reading csv into pandas and formatting to structure")
        raise ex

def push_to_google_sheets(df_data):
    try:
        # set up credentials
        credentials = service_account.Credentials.from_service_account_file(PATH_TO_GOOGLE_KEY)

        # set up filename
        time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        file_name = f"{FILE_NAME_PREFIX}"
        # _{time_str}"

        # set up gspread lib
        gc = gspread.service_account(filename=PATH_TO_GOOGLE_KEY)
        # create file
        # worksheet = gc.create(file_name)
        # print(f"File created: {worksheet}")
        worksheet = gc.open(file_name)
        # update file
        worksheet.sheet1.update([df_data.columns.values.tolist()] + df_data.values.tolist())
        print(f"File populated")
        # init google disk
        service_drive = discovery.build("drive", "v3", credentials=credentials)

        # move file to folder
        # file = service_drive.files().get(fileId=worksheet.id, fields='parents').execute()

        file = service_drive.files().update(
                fileId=worksheet.id,
                addParents=DRIVE_FOLDER_ID,
                removeParents="root",
                fields="id, parents",
            ).execute()
        print(f"File copied to folder: {DRIVE_FOLDER_ID}")

    except HttpError as error:
        print(f"An error occurred during creation file in gsheets: {error}")
        file = None

def main():
    print("APP START")
    
    get_file()
    files = list_download_dir()
    for i in files:
        body = convert_file_to_sheets_data(i)
        push_to_google_sheets(body)

    print("APP END")

if __name__=="__main__":
    main()
