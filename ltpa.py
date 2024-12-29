import time
import re

import undetected_chromedriver

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as Wait
import selenium.webdriver.chrome.options

ACORN_URL = 'https://acorn.utoronto.ca/sws/#/'
BYPASS_URL = 'https://bypass.utormfa.utoronto.ca/'

LTPA_COOKIE_NAME = 'LtpaToken2'

def get_LTPA_and_bypass_codes(utorid, password, timeout=10):
    driver = make_driver()
    bypass, *bypass_codes = get_bypass_codes(driver, utorid, password)
    ltpa_token = get_LTPA_token(driver, utorid, password, bypass, timeout)
    return (ltpa_token, bypass_codes)

def get_LTPA_token(driver, utorid, password, bypass_code, timeout=10) -> str:
    login(driver, ACORN_URL, utorid, password, bypass_code, timeout)
    all_cookies = driver.get_cookies()
    ltpa_cookie = next(filter(lambda c: c['name'] == LTPA_COOKIE_NAME, all_cookies))
    return ltpa_cookie['value']

def get_bypass_codes(driver, utorid, password) -> [str]:
    _login(driver, BYPASS_URL, utorid, password)
    Wait(driver, 30).until(EC.url_to_be(BYPASS_URL))
    proceed(driver, 'generate', find=By.NAME)

    # super janky but \-_-/
    Wait(driver, 10).until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, 'main .site-container'), 'Copy and paste'))
    div_innerHTML = driver.execute_script('return document.querySelector("main .site-container").innerHTML;')
    bypass_codes = re.findall(r'(\d{9})', div_innerHTML)

    return bypass_codes

def login(driver, url, utorid, password, bypass_code, timeout=10):
    _login(driver, url, utorid, password)

    proceed(driver, 'button--link', find=By.CLASS_NAME)
    proceed(driver, "[data-testid='test-id-bypass']", find=By.CSS_SELECTOR)
    input_keys(driver, "passcode-input", bypass_code, find=By.NAME)
    proceed(driver, "[data-testid='verify-button']", find=By.CSS_SELECTOR)
    try:
        proceed(driver, 'trust-browser-button', find=By.ID)
    except Exception:
        pass

    Wait(driver, timeout).until(EC.url_to_be(url))

def _login(driver, url, utorid, password):
    driver.get(url)
    input_keys(driver, "username", utorid, find=By.ID)
    input_keys(driver, "password", password, find=By.ID)
    proceed(driver, "_eventId_proceed", find=By.NAME)

def make_driver():
    chrome_options = selenium.webdriver.chrome.options.Options()
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')

    return undetected_chromedriver.Chrome(chrome_options=chrome_options)

def proceed(driver, name: str, find):
    Wait(driver, 5).until(EC.presence_of_element_located((find, name)))
    btn = driver.find_element(by=find, value=name)
    btn.click()
    time.sleep(1)

def input_keys(driver, name: str, value: str, find):
    Wait(driver, 10).until(EC.presence_of_element_located((find, name)))
    block = driver.find_element(by=find, value=name)
    block.send_keys(value)
    time.sleep(1)