import json
import time
import re
import os

import imaplib
import email
import schedule
import traceback

from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver import FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import airtable

load_dotenv()
BASE_ID = os.environ.get('BASE_ID')
API_KEY = os.environ.get('API_KEY')

at1 = airtable.Airtable(BASE_ID, API_KEY)
at2 = airtable.Airtable(BASE_ID, API_KEY)

CONFIRMATION_SUBJECT = 'Your Twitter confirmation code'
WAIT_TIME = 10


def get_code(emails, password):
    # Login to the email account
    with imaplib.IMAP4_SSL('imap.gmail.com') as mailbox:
        try:
            mailbox.login(emails, password)
        except imaplib.IMAP4.error as login_error:
            print(f"Login failed: {login_error}")
            return None

        # Select the inbox folder and search for emails containing the twitter code
        mailbox.select('inbox')
        _, search_data = mailbox.search(None, 'SUBJECT', f'"{CONFIRMATION_SUBJECT}"', '(UNSEEN)')
        code = None

        # Get the latest email with the twitter code
        for num in search_data[0].split()[::-1]:
            _, data = mailbox.fetch(num, '(RFC822)')

            msg = email.message_from_bytes(data[0][1])
            subject = msg['Subject']

            if CONFIRMATION_SUBJECT in subject:
                code_match = re.search(r'Your Twitter confirmation code is\s*(\W+)', subject)
                if code_match:
                    code = code_match.group(1)
                    print(f"Found Twitter confirmation code: {code}")
            else:
                code = None

            mailbox.store(num, '+FLAGS', '\\Seen')

    return code


def set_up_firefox_options(path_to_dir):
    # Set up Firefox options based on the existence of cookies directory
    firefox_options = FirefoxOptions()
    # firefox_options.add_argument("--headless")
    firefox_options.add_argument("--width=300") if os.path.exists(path_to_dir) else firefox_options.add_argument(
        "--width=700")
    firefox_options.add_argument("--height=300") if os.path.exists(path_to_dir) else firefox_options.add_argument(
        "--height=700")
    return firefox_options


def set_up_proxy(firefox_options, proxy):
    # Set up proxy settings if provided
    if proxy:
        firefox_options.set_preference('network.proxy.type', 1)
        firefox_options.set_preference('network.proxy.http', proxy.split(':')[0])
        firefox_options.set_preference('network.proxy.http_port', int(proxy.split(':')[1]))


def set_up_authentication(firefox_options, auth):
    # Set up proxy authentication if provided
    if auth:
        firefox_options.set_preference('network.proxy.auth_username', str(auth).split(':')[0])
        firefox_options.set_preference('network.proxy.auth_password', str(auth).split(':')[1])


def initialize_webdriver(firefox_options):
    # Initialize and return a new WebDriver instance
    return webdriver.Firefox(options=firefox_options)


def restore_cookies(driver, path_to_dir):
    # Restore cookies from the saved file
    driver.get("https://twitter.com/")
    WebDriverWait(driver, WAIT_TIME).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

    with open(path_to_dir, "r") as f:
        cookies = eval(f.read())

    for cookie in cookies:
        driver.add_cookie(cookie)

    driver.refresh()
    WebDriverWait(driver, WAIT_TIME).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

    print(f"Cookies Restored..")


def login_and_save_cookies(driver, username, password, email_address, g_pass, path_to_dir):
    # Login to Twitter, handle confirmation code if necessary, and save cookies
    driver.get("https://twitter.com/login")
    WebDriverWait(driver, WAIT_TIME).until(EC.presence_of_element_located((By.NAME, 'text')))

    user = driver.find_element(by=By.NAME, value="text")
    user.send_keys(username)
    user.send_keys(Keys.RETURN)

    WebDriverWait(driver, WAIT_TIME).until(EC.presence_of_element_located((By.NAME, 'password')))
    passwords = driver.find_element(by=By.NAME, value="password")
    passwords.send_keys(password)
    driver.find_element(by=By.XPATH, value='//*[@data-testid="LoginForm_Login_Button"]').click()

    WebDriverWait(driver, WAIT_TIME).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

    if "Confirmation code" in driver.page_source:
        time.sleep(20)
        c = get_code(email_address, g_pass)
        print(f'[{username}]')
        conf = driver.find_element(by=By.NAME, value="text")
        conf.send_keys(c)
        driver.find_element(by=By.XPATH, value='//*[@data-testid="ocfEnterTextNextButton"]').click()

    print(f"Logged In Successfully..")

    # Save cookies
    time.sleep(10)
    cookies = driver.get_cookies()
    with open(path_to_dir, "w") as f:
        f.write(str(cookies))
    print(f"Cookies Saved Successfully..")


def login(username, password, email_address, g_pass, proxy, auth):
    # Constants
    cookies_file = f"{username}_cookies.txt"
    path_to_dir = f"./Cookies/{cookies_file}"

    # Set up Firefox options
    firefox_options = set_up_firefox_options(path_to_dir)

    # Set up proxy
    set_up_proxy(firefox_options, proxy)

    # Set up authentication
    set_up_authentication(firefox_options, auth)

    # Initialize webdriver
    driver = initialize_webdriver(firefox_options)

    try:
        if os.path.exists(path_to_dir):
            # Restore cookies
            restore_cookies(driver, path_to_dir)
        else:
            # Login and save cookies
            login_and_save_cookies(driver, username, password, email_address, g_pass, path_to_dir)
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        return driver


def target_user(driver, target_username, source_username):
    try:
        search_url = (f"https://twitter.com/search?q=(from%3A{target_username})%20-filter%3Areplies&src=typed_query&f"
                      f"=live")
        driver.get(search_url)

        # Give some time for the tweets to fully load
        time.sleep(25)

        # Now, try to extract the post URLs
        post_urls = re.findall(r'<div\s+class="css-175oi2r\s+r-18u37iz\s+r-1q142lx"><a\s+href="([\s\S]+?)"\s+dir="ltr"',
                               str(driver.page_source))

        blacklist_file_path = f"Data/{source_username}_Blacklist.txt"

        with open(blacklist_file_path, 'a+', encoding='utf-8') as blacklist_file:
            # Read existing blacklist entries
            blacklist = blacklist_file.read().splitlines()

            if post_urls:
                post_url = post_urls.pop(0)
                if post_url not in blacklist:
                    driver.get(f"https://twitter.com{post_url}")

                    like_button_xpath = '//*[@data-testid="like"]'
                    like_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, like_button_xpath)))

                    try:
                        print(f'Attempting to like tweet for {target_username}...')
                        like_button.click()
                        print(f"[{source_username}] - Liked {target_username}'s Tweet : {post_url}")
                    except Exception as like_exception:
                        print(f"Error while liking tweet for {target_username}: {like_exception}")

                    time.sleep(10)

                    # Append the liked post to the blacklist file
                    blacklist_file.write(f"{post_url}\n")

    except Exception as target_user_exception:
        print(f"Error in target_user for {target_username}: {target_user_exception}")


def targets(driver, username):
    try:
        data = at1.get(table_name='tbllMwi49IydDHcTz', view='viwFE0eygV7NHbf6H')
        for d in data['records']:
            fields = d['fields']
            target_username = fields['username']
            source_accounts = fields["account (from accounts)"]
            if source_accounts[0] == username:
                try:
                    target_user(driver, target_username, username)
                    print(f"Processed target user: {target_username} for source user: {username}")
                except Exception as target_user_exception:
                    print(f"Error in target_user for {target_username}: {target_user_exception}")
    except Exception as targets_exception:
        print(f"Error in targets function: {targets_exception}")


def main():
    drivers = None

    try:
        data = at2.get(table_name='tblGCxi9uw0IkrIA9', view='viwyJ17dSyXbpsO02')
        for d in data['records']:
            username = d['fields']['name']
            password = d['fields']['Password']
            email_address = d['fields']['Email']
            # num = d['fields'].get('Mobile', '')
            g_pass = d['fields']['IMAP']
            ip = f"{d['fields']['IP address']}:{d['fields']['Port']}"
            auth = f"{d['fields']['Proxy Login']}:{d['fields']['Proxy Password']}"

            try:
                print(f'Attempting to login user: {username}')
                drivers = login(username, password, email_address, g_pass, ip, auth)
                targets(drivers, username)
            except Exception as login_exception:
                print(f"Error during login for {username}: {login_exception}")
            finally:
                drivers.close()

    except Exception as source_table_exception:
        print(f"Error retrieving data from the source table: {source_table_exception}")


max_retries = 3  # Adjust as needed
retry_delay = 300  # seconds (adjust as needed)

for attempt in range(1, max_retries + 1):
    try:
        main()
        break  # Exit the loop if successful
    except Exception as e:
        print(f"Error in main execution (Attempt {attempt}/{max_retries}): {e}")
        print(traceback.format_exc())  # Log the full traceback for better debugging
        time.sleep(retry_delay)

try:
    schedule.every(90).minutes.do(main)
except Exception as e:
    print(f"Error in scheduling: {e}")

# Run the scheduled tasks
while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as e:
        print(f"Error in scheduled task execution: {e}")
