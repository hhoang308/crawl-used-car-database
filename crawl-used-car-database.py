from selenium import webdriver
from selenium.webdriver.remote.webdriver import (
    WebDriver,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
from selenium_stealth import stealth

import os
import csv
import logging
import re
import time
import datetime
from enum import Enum

# input: 
# brand : toyota,...
# model : yaris,...
# year : 2019,...
# TODO: user doesn't need to insert pages limit

# output:
# car data : brand, model, year, vin id in excel format

## START: USER INPUT (lower case only)
# TODO: allow user inputs upper case
BRAND = "ford"
MODEL = "fiesta"
YEAR = 2015
BASE_URL = "https://checkcar.vin/vin-decoder/"
PAGE = 1

## END: USER INPUT
FULL_URL = f"{BASE_URL}{BRAND}/{MODEL}/{YEAR}"

class LogType(Enum):
    INFO = "INFO"
    WARNNING = "WARNNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    DEBUG = "DEBUG"

class Category:
    def __init__(self, brand: str, model: str, year: int = -1, page: int = 1):
        self.brand: str = brand
        self.model: str = model
        self.year: int = year
        self.page: int = page
        self.url: str = f"{FULL_URL}?page={self.page}"
        print(f'Category URL {self.url}')

    def to_dict(self):
        return {
            "brand": self.brand,
            "model": self.model,
            "year": self.year,
            "page": self.page,
            "url": self.url,
        }

class Extactor:
    def __init__(self):
        self.base_path = (
            f"extracter_{BRAND}_{MODEL}_{YEAR}_{PAGE}_{datetime.datetime.now().isoformat().replace(':', '-')}"
        )
        self.sleep_interval = 1

        self.initialize_result_directory()
        # self.initialize_logging()
        self.initalize_csv()

        self.driver_options = webdriver.ChromeOptions()
        self.driver_options.add_argument("start-maximized")
        self.driver_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        self.driver_options.add_experimental_option('useAutomationExtension', False)

        self.driver = webdriver.Chrome(options=self.driver_options)

        stealth(self.driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )

        self.wait = WebDriverWait(self.driver, 10)

        # self.apply_header()

        # INITIALIZE
        time.sleep(self.sleep_interval)

    def initialize_result_directory(self):
        try:
            os.makedirs(self.base_path)
            print(f"Directory '{self.base_path}' created successfully.")
        except FileExistsError:
            print(f"Directory '{self.base_path}' already exists.")
        except Exception as e:
            print(f"An error occurred: {e}")

    def initialize_logging(self):
        logging.basicConfig(
            # Log file path
            filename=os.path.join(self.base_path, f"{self.base_path}.log"),
            level=logging.INFO,  # Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

    def initalize_csv(self):
        self.csv_filename = os.path.join(self.base_path, f"{self.base_path}.csv")

        try:
            with open(
                self.csv_filename, "x", newline=""
            ) as file:  # 'x' mode creates a file, fails if the file exists
                self.csv_writer = csv.writer(file)
                self.csv_writer.writerow(
                    [
                        "Model",
                        "Brand",
                        "Year",
                        "VIN ID",
                    ]
                )
        except FileExistsError:
            # File already exists, no need to write the header
            print("File already exists")

    def apply_header(self):
        self.user_agents = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"

        self.driver.execute_cdp_cmd(
            "Network.setUserAgentOverride",
            {"userAgent": self.user_agents},
        )

        self.driver.execute_script("return navigator.userAgent;")

    def get_url(self, url: str):
        if not url or len(url) == 0:
            return

        self.driver.get(url)

        time.sleep(3)

        # self.handle_request_was_throttled()

    def create_soup(self):
        self.soup = BeautifulSoup(self.driver.page_source, "html.parser")

    def get_all_products_and_nested_sub_catgories_of_current_category(
        self, category: Category
    ):
        if not category:
            self.log(LogType.ERROR, "Input must be a Category object")
            return

        if not category.url or len(category.url) == 0:
            self.log(LogType.ERROR, "Url of category must not be empty string")

        # Access to url of category
        self.get_url(category.url)

        # self.scroll_to_the_end_of_page_slowly()

        self.create_soup()

        # Check if category has any products
        text = self.soup_try_to_find_all(
            name="span",
            attribute={"data-v-d33b2a58": True},
            raw=False
        )

        valid_vins = []
        for item in text:
            if self.is_valid_vin(item):
                valid_vins.append(item)
                self.append_item_to_csv(item)

        print(valid_vins)

    def soup_try_to_find_all(
        self,
        name: str,
        attribute: dict = {},
        get_value_from_attribute: str = None,
        raw: bool = False,
    ):
        try:
            item_list = self.soup.find_all(name, attribute)
            if raw:
                return [item for item in item_list]
            else:
                if get_value_from_attribute:
                    return [item.get(get_value_from_attribute) for item in item_list]
                else:
                    return [item.text.strip() for item in item_list]
        except:
            return None

    def is_valid_vin(self, vin: str) -> bool:
        return bool(re.fullmatch(r"^[A-HJ-NPR-Z0-9]{17}$", vin))

    def append_item_to_csv(self, vin: str):
        if vin:
            with open(
                self.csv_filename, "a", newline=""
            ) as file:  # 'x' mode creates a file, fails if the file exists
                self.csv_writer = csv.writer(file)
                self.csv_writer.writerow(
                    [
                        MODEL,
                        BRAND,
                        YEAR,
                        vin,
                    ]
                )

    def scroll_to_the_end_of_page_slowly(self):
        if not self.driver:
            return

        scroll_increment = 400  # Number of pixels to scroll each time
        scroll_pause_time = 0.5  # Pause time between scrolls (in seconds)

        # Get the total height of the page
        total_height = self.driver.execute_script("return document.body.scrollHeight")

        current_position = 0
        while current_position < total_height:
            # Scroll down by 'scroll_increment' pixels
            self.driver.execute_script(f"window.scrollBy(0, {scroll_increment});")

            # Update the current position
            current_position += scroll_increment

            # Wait for a short time before scrolling again
            time.sleep(scroll_pause_time)

            # Update total height in case the content loads dynamically (infinite scrolling)
            total_height = self.driver.execute_script(
                "return document.body.scrollHeight"
            )

def main():
    extractor = Extactor()

    car_category = Category(
        brand=BRAND,
        model=MODEL,
        year=YEAR,
        page=PAGE,
    )

    extractor.get_all_products_and_nested_sub_catgories_of_current_category(
        car_category
    )

    time.sleep(2)

if __name__ == "__main__":
    start_time = time.time()

    main()

    end_time = time.time()
    elapsed_time = end_time - start_time
    print(f"Elapsed time: {elapsed_time:.5f} seconds")