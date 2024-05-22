import os 
import base64
import os


URL = os.getenv("URL", "https://hq.qashier.com/#/login")    
URL_CUST_MAGEMENT = os.getenv("URL_CUST_MAGEMENT", "https://hq.qashier.com/#/customer-management") 
DOWNLOAD_FOLDER = os.getenv("FILE_NAME_PREFIX", "/tmp/browserdownload")   
HEADLESS = True 

PATH_TO_GOOGLE_KEY = "/tmp/service_account.json" 
SCREENSHOT_FOLDER = "/tmp/browserscreenshots"

DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "1gJJn48WyvrYWjq7pcZ1qGZDNQsDYjMME") 
FILE_NAME_PREFIX = os.getenv("FILE_NAME_PREFIX", "LENGOLF_CRM")  

DEBUG = os.getenv("DEBUG", False)

try:
    if not ( "LOGIN" in os.environ and "PASSWORD" in os.environ and "GOOGLE_KEY" in os.environ):
        print("APP_LOGIN, APP_PASSWORD, GOOGLE_KEY is not specified. Exit")
        exit(1)

    APP_LOGIN_ENCODED    = os.getenv("LOGIN")
    APP_LOGIN            = base64.b64decode(APP_LOGIN_ENCODED).decode('utf-8')

    APP_PASSWORD_ENCODED = os.getenv("PASSWORD")
    APP_PASSWORD         = base64.b64decode(APP_PASSWORD_ENCODED).decode('utf-8')

    GOOGLE_KEY = os.getenv("GOOGLE_KEY")
    decoded = base64.b64decode(GOOGLE_KEY).decode('utf-8')

    with open(PATH_TO_GOOGLE_KEY,"wt") as f:
        f.write(decoded)
        print(f"Key decoded and placed in {PATH_TO_GOOGLE_KEY}")

except Exception as ex:
    print("ERROR during parsing ENV variables. make sure: APP_LOGIN, APP_PASSWORD,GOOGLE_KEY is specified in correct format")
    exit(1)
    raise ex
   
