# google_rank_tracker.py

import logging
import random
import time
import urllib.parse
from datetime import datetime
import pandas as pd

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
    from selenium.webdriver.chrome.service import Service as ChromeService
except ImportError:
    print("ERROR: Yo, install the damn libraries first! `pip install selenium pandas openpyxl`")
    exit()

# --- BOT CONFIG - TWEAK THIS STUFF! ---
TARGET_DOMAIN = "wikipedia.org"  # Your site (no http/www, just example.com)
KEYWORDS_TO_TRACK = [
    "python (programming language)",
    "machine learning",
    "google",
    "what is artificial intelligence" # A keyword that might not rank well, for "Not Found" testing
]
MAX_PAGES_TO_CHECK = 2 # How many Google SERP pages to crawl per keyword (keep it low to be nice)
RESULTS_PER_PAGE_ESTIMATE = 10 # Google's usually around 10, but can vary

# ChromeDriver Path:
# 1. If chromedriver is in your system PATH, leave this as None.
#    (Selenium 4.6.0+ is pretty good at auto-managing this if it's not in PATH)
# 2. OR, give the full path to your chromedriver executable:
#    CHROME_DRIVER_PATH = "C:/WebDriver/chromedriver.exe" # Windows example
#    CHROME_DRIVER_PATH = "/usr/local/bin/chromedriver"   # Mac/Linux example
CHROME_DRIVER_PATH = None # Recommended: Let Selenium Manager do its thing (v4.6+)

# Advanced Settings (usually fine as is)
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
RANDOM_DELAY_BETWEEN_KEYWORDS = (7, 12)  # (seconds)
RANDOM_DELAY_BETWEEN_PAGES = (3, 6)    # (seconds)
IMPLICIT_WAIT_TIME = 10 # (seconds)
EXPLICIT_WAIT_TIME = 15 # (seconds)
TAKE_SCREENSHOTS_ON_ERROR = True
LOG_LEVEL = logging.INFO # DEBUG, INFO, WARNING, ERROR, CRITICAL
OUTPUT_FILENAME_PREFIX = "google_rank_report"
# --- END OF CONFIG ---

logging.basicConfig(level=LOG_LEVEL,
                    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class GoogleRankTracker:
    def __init__(self, driver_path=None, target_domain="", user_agent=None):
        self.driver_path = driver_path
        if not target_domain:
            raise ValueError("Target domain can't be empty, dude.")
        self.target_domain = target_domain.lower().replace("www.", "").replace("http://", "").replace("https://", "")
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.driver = None
        self._setup_driver()

    def _get_webdriver_options(self):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f"user-agent={self.user_agent}")
        chrome_options.add_argument("--headless=new") # New headless mode for Chrome
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--lang=en-US,en;q=0.9") # Request English results for consistency
        chrome_options.add_argument("--blink-settings=imagesEnabled=false") # No images, faster
        return chrome_options

    def _setup_driver(self):
        try:
            options = self._get_webdriver_options()
            if self.driver_path:
                service = ChromeService(executable_path=self.driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                logging.info("ChromeDriver path not set. Selenium Manager will try to handle it (Selenium 4.6+)...")
                self.driver = webdriver.Chrome(options=options)
            self.driver.implicitly_wait(IMPLICIT_WAIT_TIME)
            logging.info("Chrome browser fired up (headless). Let's do this.")
        except WebDriverException as e:
            logging.error(f"Damn, ChromeDriver setup failed: {e}")
            logging.error("Make sure ChromeDriver is installed and in your PATH, or the CHROME_DRIVER_PATH is correct.")
            logging.error("Get ChromeDriver: https://chromedriver.chromium.org/downloads")
            raise

    def _normalize_url(self, url_string):
        if not url_string: return ""
        try:
            parsed_url = urllib.parse.urlparse(url_string)
            domain = parsed_url.netloc.lower().replace("www.", "")
            return domain
        except Exception:
            return ""

    def _handle_cookie_consent(self, wait):
        # These XPaths are a crapshoot, Google changes 'em. Good luck.
        consent_selectors = [
            "//button[.//div[contains(text(),'Accept all')]]", "//button[.//div[contains(text(),'Reject all')]]",
            "//button[@id='L2AGLb']", "//button[@id='W0wltc']", "//div[text()='I agree']",
            "//button[contains(., 'Agree') or contains(., 'Accept') or contains(., 'Alles akzeptieren') or contains(., 'Tout accepter') or contains(., 'Accetta tutto') or contains(., 'Aceptar todo')]"
        ]
        for selector in consent_selectors:
            try:
                consent_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                consent_button.click()
                logging.info(f"Cookie consent button clicked (selector: '{selector[:30]}...').")
                time.sleep(0.5)
                return True
            except TimeoutException:
                continue
        logging.info("No cookie consent pop-up found or needed to smash.")
        return False

    def _extract_search_results(self):
        # Google's SERP structure is like shifting sands. These selectors are a starting point.
        # The '.yuRUbf > a' was solid for a while. Keeping fingers crossed.
        result_selectors = [
            "div.g .yuRUbf > a", "div.g div[data-hveid] > div > a", # Common organic
            "div.Gx5Zad.fP1Qef.xpd.ETM_NB .kCrYT a", # Another structure seen
            "//div[h3 and ./a[@href and @ping]]//a[@href]" # More generic XPath if others fail
        ]
        all_links_in_page = []
        for selector_idx, selector in enumerate(result_selectors):
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR if not selector.startswith("//") else By.XPATH, selector)
                if elements:
                    for elem in elements:
                        href = elem.get_attribute("href")
                        title = ""
                        try:
                            # Try to find an H3 directly within or as a sibling/nephew
                            h3_candidates = [
                                ".//h3", # Direct child
                                "ancestor::div[.//h3][1]//h3", # Ancestor's H3
                                "parent::div//h3" # Sibling's H3 via parent
                            ]
                            for h3_xpath in h3_candidates:
                                try:
                                    title_elem = elem.find_element(By.XPATH, h3_xpath)
                                    if title_elem.is_displayed(): # Only visible titles
                                        title = title_elem.text.strip()
                                        if title: break # Found a good title
                                except NoSuchElementException:
                                    continue
                            if not title: title = "Title not grabbed"
                        except Exception:
                             title = "Title grab error"

                        if href and not href.startswith("http://webcache.googleusercontent.com"): # Valid, non-cache links
                           all_links_in_page.append({"url": href, "title": title})
                    if all_links_in_page:
                        logging.debug(f"Found {len(all_links_in_page)} links with selector #{selector_idx+1}.")
                        return all_links_in_page
            except Exception as e:
                logging.debug(f"Selector #{selector_idx+1} ('{selector[:30]}...') failed or no results: {e}")
                continue
        if not all_links_in_page: logging.warning("No results found with any defined selectors on this page. Uh oh.")
        return all_links_in_page

    def _click_next_page(self, wait):
        # "Next" button selectors. Also a moving target.
        next_page_selectors = [
            "//a[@id='pnnext']", "//a[@aria-label='Next page']", "//a[@aria-label='Page suivante']",
            "//span[text()='Next']/parent::a", "//footer//a[contains(@aria-label, 'Next') or contains(@aria-label, 'Suivant')]"
        ]
        for selector in next_page_selectors:
            try:
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button) # Make sure it's in view
                time.sleep(0.2) # Tiny pause before click
                next_button.click()
                logging.info(f"Hopped to next page (selector: '{selector[:30]}...').")
                return True
            except TimeoutException:
                continue
            except Exception as e: # Other errors like ElementClickInterceptedException
                logging.warning(f"Problem clicking 'Next' with selector '{selector[:30]}...': {e}")
                # Could try JS click: self.driver.execute_script("arguments[0].click();", next_button)
                continue
        logging.warning("Can't find the 'Next' page button. End of the line?")
        return False

    def _check_for_captcha(self):
        captcha_indicators = [
            "//iframe[contains(@src, 'recaptcha')]", "//div[text()='reCAPTCHA']",
            "//form[@id='captcha-form']", "//h1[contains(text(),'unusual traffic')]",
            "//p[contains(text(),'systems have detected unusual traffic')]"
        ]
        current_url = self.driver.current_url
        if "ipv4.google.com/sorry" in current_url or "consent.google.com" in current_url and "continue" in current_url: # Google's CAPTCHA/consent wall
            logging.error(f"Hit Google's CAPTCHA/sorry wall at URL: {current_url}")
            return True

        for indicator in captcha_indicators:
            try:
                if self.driver.find_elements(By.XPATH, indicator):
                    logging.error(f"CAPTCHA detected with indicator: '{indicator}'!")
                    if TAKE_SCREENSHOTS_ON_ERROR:
                        filename = f"captcha_detected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        self.driver.save_screenshot(filename)
                        logging.info(f"CAPTCHA screenshot saved to '{filename}'")
                    return True
            except Exception:
                continue
        return False

    def get_rank_for_keyword(self, keyword, max_pages=3, retries=1):
        if not self.driver:
            logging.error("Browser driver's MIA. Can't search.")
            return {"keyword": keyword, "rank": "Error - No Driver", "url": "", "title": "", "page": 0, "status": "Error"}

        for attempt in range(retries + 1):
            if attempt > 0:
                logging.info(f"Retrying ({attempt}/{retries}) for '{keyword}' after a nap...")
                time.sleep(random.uniform(10, 25) * attempt)

            try:
                logging.info(f"🔍 Hunting for '{keyword}' (Attempt {attempt + 1})")
                # Use `num` for more results, `hl` (language) and `gl` (geo) for consistency.
                # Google can still override these.
                search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(keyword)}&num={RESULTS_PER_PAGE_ESTIMATE * max_pages}&hl=en&gl=us&filter=0&start=0"
                self.driver.get(search_url)
                wait = WebDriverWait(self.driver, EXPLICIT_WAIT_TIME)

                if self._check_for_captcha():
                    return {"keyword": keyword, "rank": "CAPTCHA", "url": "", "title": "", "page": 0, "status": "CAPTCHA"}

                self._handle_cookie_consent(wait)

                WebDriverWait(self.driver, EXPLICIT_WAIT_TIME).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div#search, div.g, div.hlcw0c, div.Gx5Zad"))
                )
                time.sleep(random.uniform(1.5, 2.5)) # Let things settle

                absolute_rank_counter = 0
                found_on_page = 0
                for page_num_actual in range(1, max_pages + 1): # Actual page we are on
                    logging.info(f"---- Scanning SERP page {page_num_actual} for '{keyword}' ----")
                    if self._check_for_captcha():
                         return {"keyword": keyword, "rank": "CAPTCHA", "url": "", "title": "", "page": page_num_actual, "status": "CAPTCHA"}

                    page_results = self._extract_search_results()

                    for result_item in page_results:
                        absolute_rank_counter += 1
                        link_domain = self._normalize_url(result_item.get("url"))

                        if self.target_domain in link_domain:
                            logging.info(f"🎉 BINGO! Found '{self.target_domain}' for '{keyword}'!")
                            logging.info(f"Rank: {absolute_rank_counter}, Title: '{result_item.get('title')}', URL: {result_item.get('url')}")
                            return {"keyword": keyword, "rank": absolute_rank_counter, "url": result_item.get("url"),
                                    "title": result_item.get("title"), "page": page_num_actual, "status": "Found"}

                    if page_num_actual < max_pages:
                        logging.debug(f"Target not on page {page_num_actual}. Trying next page...")
                        if self._click_next_page(wait):
                            time.sleep(random.uniform(RANDOM_DELAY_BETWEEN_PAGES[0], RANDOM_DELAY_BETWEEN_PAGES[1]))
                        else:
                            logging.info(f"No 'Next' button from page {page_num_actual} for '{keyword}'. Guess that's it.")
                            break
                    else:
                        logging.info(f"Hit max pages ({max_pages}) for '{keyword}'.")

                logging.info(f"Domain '{self.target_domain}' NOT FOUND for '{keyword}' in top {absolute_rank_counter} results (checked {max_pages} pages).")
                return {"keyword": keyword, "rank": f"Not Found in top {absolute_rank_counter}", "url": "", "title": "", "page": max_pages, "status": "Not Found"}

            except TimeoutException as e:
                logging.warning(f"Timeout on attempt {attempt + 1} for '{keyword}': {e}")
                if TAKE_SCREENSHOTS_ON_ERROR: self.driver.save_screenshot(f"error_timeout_{keyword.replace(' ','_')}_{attempt}.png")
            except WebDriverException as e:
                logging.error(f"WebDriver busted on attempt {attempt + 1} for '{keyword}': {type(e).__name__} - {e}")
                if TAKE_SCREENSHOTS_ON_ERROR: self.driver.save_screenshot(f"error_webdriver_{keyword.replace(' ','_')}_{attempt}.png")
                if "session id is null" in str(e).lower() or "target window already closed" in str(e).lower():
                    logging.error("Browser probably crashed. Attempting driver restart...")
                    self.close()
                    try: self._setup_driver()
                    except Exception as setup_err:
                         logging.critical(f"Driver restart FAILED: {setup_err}")
                         return {"keyword": keyword, "rank": "Error - Driver Crash, Restart Fail", "url": "", "title": "", "page": 0, "status": "Error"}
            except Exception as e:
                logging.error(f"Unexpected screw-up on attempt {attempt + 1} for '{keyword}': {type(e).__name__} - {e}", exc_info=False)
                if TAKE_SCREENSHOTS_ON_ERROR and self.driver:
                     try: self.driver.save_screenshot(f"error_unexpected_{keyword.replace(' ','_')}_{attempt}.png")
                     except: pass # Might fail if driver truly borked

            if attempt >= retries: # This was the last retry
                logging.error(f"Max retries ({retries}) hit for '{keyword}'. Giving up on this one.")
                error_status = "Error - Max Retries (Timeout)" if isinstance(e, TimeoutException) else \
                               "Error - Max Retries (WebDriver)" if isinstance(e, WebDriverException) else \
                               "Error - Max Retries (Unexpected)"
                return {"keyword": keyword, "rank": error_status, "url": "", "title": "", "page": 0, "status": "Error"}
        # Should not be reached if logic is correct for retries
        return {"keyword": keyword, "rank": "Error - Logic Flaw in Retries", "url": "", "title": "", "page": 0, "status": "Error"}


    def close(self):
        if self.driver:
            try:
                self.driver.quit()
                logging.info("Browser shut down. Peace out.")
            except Exception as e:
                logging.warning(f"Problem closing browser: {e}")
            self.driver = None

def save_results_to_files(results_df, base_filename_prefix):
    if results_df.empty:
        logging.info("No data to save. Bummer.")
        return

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"{base_filename_prefix}_{timestamp_str}.csv"
    try:
        results_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        logging.info(f"Results dumped to CSV: {csv_filename}")
    except Exception as e:
        logging.error(f"Failed to save CSV '{csv_filename}': {e}")

    excel_filename = f"{base_filename_prefix}_{timestamp_str}.xlsx"
    try:
        results_df.to_excel(excel_filename, index=False, sheet_name='Rankings')
        logging.info(f"Results also dumped to Excel: {excel_filename}")
    except Exception as e:
        logging.error(f"Failed to save Excel '{excel_filename}': {e}")
        logging.warning("Need 'openpyxl' for Excel export: `pip install openpyxl`")

if __name__ == "__main__":
    logging.info("--- Sajjad Akbari's Google Rank Tracker - Kicking Off ---")
    logging.info(f"Targeting domain: {TARGET_DOMAIN}")
    logging.info(f"Keywords on the hit list: {len(KEYWORDS_TO_TRACK)}")
    logging.info(f"Max SERP pages per keyword: {MAX_PAGES_TO_CHECK}")

    all_results_data = []
    tracker_instance = None

    try:
        tracker_instance = GoogleRankTracker(driver_path=CHROME_DRIVER_PATH,
                                             target_domain=TARGET_DOMAIN)
        for i, keyword in enumerate(KEYWORDS_TO_TRACK):
            result = tracker_instance.get_rank_for_keyword(keyword, max_pages=MAX_PAGES_TO_CHECK, retries=1)
            result['timestamp_executed'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result['target_domain_checked'] = TARGET_DOMAIN
            all_results_data.append(result)
            logging.info(f"Result for '{keyword}': Rank {result.get('rank', 'N/A')}, Status: {result.get('status', 'N/A')}")

            if i < len(KEYWORDS_TO_TRACK) - 1:
                delay = random.uniform(RANDOM_DELAY_BETWEEN_KEYWORDS[0], RANDOM_DELAY_BETWEEN_KEYWORDS[1])
                logging.info(f"Chilling for {delay:.1f}s before next keyword...")
                time.sleep(delay)
    except KeyboardInterrupt:
        logging.warning("User pulled the plug (Ctrl+C). Shutting down.")
    except WebDriverException as e:
        logging.critical(f"WebDriver crapped out hard during init. Can't continue: {e}")
    except Exception as e:
        logging.critical(f"Something went sideways in the main block: {e}", exc_info=True)
    finally:
        if tracker_instance:
            tracker_instance.close()

        logging.info("\n--- FINAL SCORE ---")
        if all_results_data:
            results_df = pd.DataFrame(all_results_data)
            column_order = ['timestamp_executed', 'keyword', 'target_domain_checked', 'rank', 'status', 'url', 'title', 'page']
            results_df = results_df.reindex(columns=column_order, fill_value='')
            # For console output, can be a bit much for many keywords
            # pd.set_option('display.max_rows', None); pd.set_option('display.max_colwidth', None); pd.set_option('display.width', 120)
            logging.info(f"\n{results_df.to_string(index=False)}")
            save_results_to_files(results_df, OUTPUT_FILENAME_PREFIX)
        else:
            logging.info("Welp, no results were gathered.")
        logging.info("--- Bot signing off. ---")
