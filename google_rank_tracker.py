# google_rank_tracker.py

import logging
import random
import time
import urllib.parse
from datetime import datetime
import pandas as pd # برای ذخیره سازی نتایج در انتهای اسکریپت

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
    from selenium.webdriver.chrome.service import Service as ChromeService # برای مدیریت بهتر درایور
    # from webdriver_manager.chrome import ChromeDriverManager # راه دیگر برای مدیریت خودکار درایور
except ImportError:
    print("خطا: لطفاً کتابخانه‌های لازم را نصب کنید. `pip install selenium pandas openpyxl`")
    exit()

# --- تنظیمات اصلی ربات (کاربران اینجا را ویرایش کنند) ---
TARGET_DOMAIN = "wikipedia.org"  # دامنه وب‌سایت مورد نظر شما (بدون http یا www)
KEYWORDS_TO_TRACK = [
    "پایتون (زبان برنامه‌نویسی)", 
    "یادگیری ماشین", 
    "گوگل",
    "هوش مصنوعی چیست" # یک کلمه کلیدی که ممکن است رتبه خوبی نداشته باشد برای تست "Not Found"
]
MAX_PAGES_TO_CHECK = 3  # حداکثر تعداد صفحات نتایج گوگل برای بررسی هر کلمه کلیدی
RESULTS_PER_PAGE_ESTIMATE = 10 # تخمینی برای محاسبه رتبه کلی (گوگل ممکن است کمتر یا بیشتر نشان دهد)

# مسیر ChromeDriver:
# 1. اگر ChromeDriver در PATH سیستم شما قرار دارد، می‌توانید این را خالی بگذارید یا روی None تنظیم کنید.
#    (Selenium 4.6.0 و بالاتر به صورت خودکار سعی در دانلود و مدیریت ChromeDriver دارد اگر در PATH نباشد)
# 2. مسیر کامل فایل اجرایی ChromeDriver را مشخص کنید، مثال:
#    CHROME_DRIVER_PATH = "C:/WebDriver/chromedriver.exe" # برای ویندوز
#    CHROME_DRIVER_PATH = "/usr/local/bin/chromedriver"   # برای مک/لینوکس
CHROME_DRIVER_PATH = None # توصیه می‌شود برای استفاده از Selenium Manager (از نسخه ۴.۶ به بعد)

# تنظیمات پیشرفته (معمولاً نیازی به تغییر نیست)
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36" # یک User-Agent معقول
RANDOM_DELAY_BETWEEN_KEYWORDS = (5, 10)  # تاخیر تصادفی (ثانیه) بین بررسی هر کلمه کلیدی
RANDOM_DELAY_BETWEEN_PAGES = (2, 5)    # تاخیر تصادفی (ثانیه) بین پیمایش صفحات نتایج
IMPLICIT_WAIT_TIME = 10 # حداکثر زمان (ثانیه) برای انتظار ضمنی هنگام یافتن المان
EXPLICIT_WAIT_TIME = 15 # حداکثر زمان (ثانیه) برای انتظار صریح برای المان‌های خاص
TAKE_SCREENSHOTS_ON_ERROR = True # گرفتن اسکرین‌شات در صورت بروز خطاهای مهم
LOG_LEVEL = logging.INFO # سطح لاگ‌گیری: DEBUG, INFO, WARNING, ERROR, CRITICAL
OUTPUT_FILENAME_PREFIX = "google_rank_report"
# --- پایان بخش تنظیمات ---

# پیکربندی لاگ‌گیری
logging.basicConfig(level=LOG_LEVEL,
                    format='%(asctime)s - %(levelname)s - %(module)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

class GoogleRankTracker:
    def __init__(self, driver_path=None, target_domain="", user_agent=None):
        self.driver_path = driver_path
        if not target_domain:
            raise ValueError("دامنه هدف (target_domain) نباید خالی باشد.")
        self.target_domain = target_domain.lower().replace("www.", "").replace("http://", "").replace("https://", "")
        self.user_agent = user_agent or DEFAULT_USER_AGENT
        self.driver = None
        self._setup_driver()

    def _get_webdriver_options(self):
        """تنظیمات ChromeOptions را برمی‌گرداند."""
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f"user-agent={self.user_agent}")
        chrome_options.add_argument("--headless")  # اجرای بدون نمایش مرورگر
        chrome_options.add_argument("--disable-gpu") # گاهی برای headless لازم است
        chrome_options.add_argument("--no-sandbox") # برای اجرای روی لینوکس به عنوان روت (با احتیاط)
        chrome_options.add_argument("--disable-dev-shm-usage") # برای رفع مشکلات حافظه اشتراکی در کانتینرهای داکر
        chrome_options.add_argument("--lang=en-US,en;q=0.9") # درخواست نتایج به زبان انگلیسی برای یکسان سازی ساختار
        chrome_options.add_argument("--blink-settings=imagesEnabled=false") # غیرفعال کردن بارگذاری تصاویر برای سرعت بیشتر
        # chrome_options.add_argument("--proxy-server=ip:port") # در صورت نیاز به پروکسی
        # prefs = {"profile.managed_default_content_settings.cookies": 2} # بلاک کردن کوکی ها (می تواند منجر به کپچا شود)
        # chrome_options.add_experimental_option("prefs", prefs)
        return chrome_options

    def _setup_driver(self):
        """راه‌اندازی WebDriver."""
        try:
            options = self._get_webdriver_options()
            if self.driver_path:
                service = ChromeService(executable_path=self.driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
            else:
                # Selenium 4.6+ از Selenium Manager برای مدیریت خودکار درایور استفاده می‌کند
                logging.info(" مسیر ChromeDriver مشخص نشده است. تلاش برای استفاده از Selenium Manager...")
                self.driver = webdriver.Chrome(options=options)
            
            self.driver.implicitly_wait(IMPLICIT_WAIT_TIME)
            logging.info("مرورگر Chrome با موفقیت راه‌اندازی شد (در حالت Headless).")
        except WebDriverException as e:
            logging.error(f"خطا در راه‌اندازی ChromeDriver: {e}")
            logging.error("لطفاً مطمئن شوید ChromeDriver نصب شده و در PATH سیستم قرار دارد، یا مسیر آن به درستی در CHROME_DRIVER_PATH مشخص شده است.")
            logging.error("می‌توانید آخرین نسخه ChromeDriver را از https://chromedriver.chromium.org/downloads دانلود کنید.")
            logging.error("همچنین، اگر از Selenium نسخه ۴.۶ به بالا استفاده می‌کنید، ممکن است خودش آن را مدیریت کند اگر ابزارهای لازم نصب باشند.")
            raise  # خطا را مجددا پرتاب می‌کنیم تا برنامه متوقف شود

    def _normalize_url(self, url_string):
        """ URL را برای مقایسه بهتر، نرمال و دامنه اصلی آن را استخراج می‌کند. """
        if not url_string: return ""
        try:
            parsed_url = urllib.parse.urlparse(url_string)
            domain = parsed_url.netloc.lower().replace("www.", "")
            return domain
        except Exception:
            return "" # در صورت بروز خطا در پارس URL

    def _handle_cookie_consent(self, wait):
        """ تلاش برای پذیرش یا رد کردن پاپ‌آپ کوکی‌ها. """
        consent_selectors = [
            "//button[.//div[contains(text(),'Accept all')]]",
            "//button[.//div[contains(text(),'Reject all')]]", # گاهی گزینه رد کردن هم وجود دارد و بهتر است
            "//button[@id='L2AGLb']", # معمولا Accept
            "//button[@id='W0wltc']", # معمولا Reject
            "//div[text()='I agree']",
            "//button[contains(., 'Agree') or contains(., 'Accept')]", # عمومی تر
        ]
        for selector in consent_selectors:
            try:
                consent_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                consent_button.click()
                logging.info(f"دکمه کوکی با سلکتور '{selector}' کلیک شد.")
                time.sleep(0.5) # کمی صبر برای اعمال
                return True
            except TimeoutException:
                continue
        logging.info("پاپ‌آپ کوکی پیدا نشد یا نیازی به مدیریت آن نبود.")
        return False

    def _extract_search_results(self):
        """استخراج نتایج جستجو از صفحه فعلی."""
        # سلکتورهای رایج برای بلاک‌های نتایج اصلی گوگل. این‌ها ممکن است تغییر کنند.
        # اولویت با سلکتورهایی است که مستقیما لینک اصلی را هدف قرار می‌دهند.
        # سلکتور ".yuRUbf > a" برای نتایج ارگانیک استاندارد بسیار رایج بوده است.
        # سلکتور "div.g a h3" نیز اغلب عنوان‌ها را در بر می‌گیرد.
        # در اینجا ما به دنبال خود تگ <a> که دارای href است هستیم.
        result_selectors = [
            "div.g .yuRUbf > a",                            # رایج ترین برای نتایج ارگانیک
            "div.g div[role='link']",                       # گاهی اوقات لینک ها در این ساختار هستند
            "div.hlcw0c .yuRUbf > a",                       # ساختار دیگر
            "div.Gx5Zad.fP1Qef.xpd.ETM_NB .kCrYT a",        # ساختار پیچیده تر
            "//div[contains(@class, 'g ')]//a[@data-ved and @href and not(contains(@class, 'fl')) and count(h3)>0]" # XPath انعطاف‌پذیرتر
        ]
        
        all_links_in_page = []
        for selector in result_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR if not selector.startswith("//") else By.XPATH, selector)
                if elements:
                    for elem in elements:
                        href = elem.get_attribute("href")
                        # دریافت عنوان می‌تواند بهینه‌تر شود، گاهی h3 فرزند مستقیم a نیست
                        title = ""
                        try:
                            # تلاش برای یافتن h3 مرتبط با لینک
                            h3_element = elem.find_element(By.XPATH, ".//h3")
                            title = h3_element.text.strip()
                        except NoSuchElementException:
                            # اگر h3 مستقیم پیدا نشد، سعی در یافتن از ساختارهای دیگر
                            try:
                                parent_with_h3 = elem.find_element(By.XPATH, "./ancestor::div[.//h3][1]")
                                title = parent_with_h3.find_element(By.XPATH, ".//h3").text.strip()
                            except NoSuchElementException:
                                title = "عنوان یافت نشد"
                        
                        if href: # فقط لینک های معتبر
                           all_links_in_page.append({"url": href, "title": title})
                    if all_links_in_page:
                        # logging.debug(f"با سلکتور '{selector}' تعداد {len(all_links_in_page)} لینک یافت شد.")
                        return all_links_in_page # با اولین سلکتور موفق، خارج می‌شویم
            except Exception as e:
                logging.debug(f"خطا یا عدم یافتن نتیجه با سلکتور '{selector}': {e}")
                continue
        
        if not all_links_in_page:
             logging.warning("هیچ نتیجه‌ای با سلکتورهای تعریف شده در این صفحه یافت نشد.")
        return all_links_in_page

    def _click_next_page(self, wait):
        """ تلاش برای کلیک روی دکمه 'صفحه بعد'. """
        next_page_selectors = [
            "//a[@id='pnnext']",
            "//a[@aria-label='Next page']",
            "//a[@aria-label='Page suivante']", # برای زبان‌های دیگر
            "//span[text()='Next']/parent::a",
            "//span[text()='بعدی']/parent::a"
        ]
        for selector in next_page_selectors:
            try:
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                # self.driver.execute_script("arguments[0].scrollIntoView(true);", next_button) # اسکرول به دکمه اگر لازم باشد
                # time.sleep(0.3)
                next_button.click()
                logging.info(f"به صفحه بعد رفتیم (با سلکتور '{selector}').")
                return True
            except TimeoutException:
                continue
        logging.warning("دکمه 'صفحه بعد' پیدا نشد.")
        return False

    def _check_for_captcha(self):
        """بررسی وجود کپچا در صفحه."""
        # این یک روش ساده است و ممکن است برای انواع کپچاها کافی نباشد.
        captcha_indicators = [
            "//iframe[contains(@src, 'recaptcha')]",
            "//div[text()='reCAPTCHA']",
            "//form[@id='captcha-form']",
            "//h1[contains(text(),'unusual traffic')]",
            "//p[contains(text(),'systems have detected unusual traffic')]"
        ]
        for indicator in captcha_indicators:
            try:
                if self.driver.find_elements(By.XPATH, indicator):
                    logging.error("کپچا شناسایی شد!")
                    if TAKE_SCREENSHOTS_ON_ERROR:
                        filename = f"captcha_detected_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        self.driver.save_screenshot(filename)
                        logging.info(f"اسکرین‌شات کپچا در '{filename}' ذخیره شد.")
                    return True
            except Exception: # ممکن است خود find_elements خطا بدهد
                continue
        return False


    def get_rank_for_keyword(self, keyword, max_pages=3, retries=1):
        """
        رتبه دامنه هدف را برای یک کلمه کلیدی خاص جستجو می‌کند.
        در صورت بروز خطا، تا تعداد retries تلاش مجدد انجام می‌دهد.
        """
        if not self.driver:
            logging.error("درایور مرورگر راه‌اندازی نشده است. نمی‌توان جستجو کرد.")
            return {"keyword": keyword, "rank": "Error - Driver not initialized", "url": "", "title": "", "page": 0, "status": "Error"}

        attempt = 0
        while attempt <= retries:
            if attempt > 0:
                logging.info(f"تلاش مجدد ({attempt}/{retries}) برای کلمه کلیدی '{keyword}' پس از چند ثانیه...")
                time.sleep(random.uniform(10, 20) * attempt) # تاخیر بیشتر در هر تلاش

            try:
                logging.info(f"🔍 در حال جستجوی کلمه کلیدی: '{keyword}' (تلاش {attempt+1})")
                # پارامتر num=100 برای درخواست ۱۰۰ نتیجه (گوگل تصمیم نهایی را می‌گیرد)
                # پارامتر gl و hl برای تعیین کشور و زبان نتایج برای یکنواختی
                # ممکن است گوگل این پارامترها را نادیده بگیرد یا رفتار متفاوتی نشان دهد.
                search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(keyword)}&num={RESULTS_PER_PAGE_ESTIMATE * max_pages}&hl=en&gl=us"
                self.driver.get(search_url)
                
                wait = WebDriverWait(self.driver, EXPLICIT_WAIT_TIME)
                
                # بررسی کپچا بلافاصله پس از بارگذاری صفحه
                if self._check_for_captcha():
                    # اگر در تلاش اول کپچا بود، می‌توان تلاش‌های بعدی را متوقف کرد
                    # مگر اینکه بخواهیم با سشن جدید یا پروکسی دیگر تلاش کنیم (منطق پیچیده‌تر)
                    if attempt == 0 : # فقط در تلاش اول اگر کپچا بود سریعا برگردان
                         return {"keyword": keyword, "rank": "CAPTCHA", "url": "", "title": "", "page": 0, "status": "CAPTCHA"}
                    # اگر در تلاش های بعدی بود، شاید مشکل موقتی بوده
                    # فعلا با ادامه دادن به تلاش بعدی ریسک میکنیم

                self._handle_cookie_consent(wait) # مدیریت پاپ آپ کوکی
                
                # منتظر ماندن برای اولین نتیجه جستجو به عنوان نشانه بارگذاری صفحه
                WebDriverWait(self.driver, EXPLICIT_WAIT_TIME).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.g, div.hlcw0c, div.Gx5Zad")) 
                )
                time.sleep(random.uniform(1,2)) # کمی صبر برای اطمینان از بارگذاری کامل اولیه

                absolute_rank_counter = 0
                for page_num in range(1, max_pages + 1):
                    logging.info(f"---- بررسی صفحه {page_num} نتایج برای '{keyword}' ----")
                    
                    if self._check_for_captcha(): # بررسی کپچا قبل از استخراج نتایج هر صفحه
                         return {"keyword": keyword, "rank": "CAPTCHA", "url": "", "title": "", "page": page_num, "status": "CAPTCHA"}

                    page_results = self._extract_search_results()
                    if not page_results:
                        logging.warning(f"هیچ نتیجه‌ای در صفحه {page_num} برای '{keyword}' یافت نشد.")
                        # شاید لازم باشد به صفحه بعد برویم یا جستجو را متوقف کنیم
                        # فعلا ادامه می‌دهیم شاید در صفحات بعدی نتیجه باشد.

                    for result_item in page_results:
                        absolute_rank_counter += 1
                        link_domain = self._normalize_url(result_item.get("url"))
                        
                        # logging.debug(f"رتبه {absolute_rank_counter}: {result_item.get('url')} (دامنه نرمال شده: {link_domain})")

                        if self.target_domain in link_domain:
                            logging.info(f"🎉 دامنه '{self.target_domain}' برای '{keyword}' پیدا شد!")
                            logging.info(f"رتبه: {absolute_rank_counter}, عنوان: '{result_item.get('title')}', URL: {result_item.get('url')}")
                            return {"keyword": keyword, "rank": absolute_rank_counter, "url": result_item.get("url"), 
                                    "title": result_item.get("title"), "page": page_num, "status": "Found"}
                    
                    # رفتن به صفحه بعد (اگر هنوز دامنه پیدا نشده و آخرین صفحه نیست)
                    if page_num < max_pages:
                        logging.debug(f"دامنه هدف در صفحه {page_num} یافت نشد، تلاش برای رفتن به صفحه بعد...")
                        if self._click_next_page(wait):
                            time.sleep(random.uniform(RANDOM_DELAY_BETWEEN_PAGES[0], RANDOM_DELAY_BETWEEN_PAGES[1]))
                        else:
                            logging.info(f"نمی‌توان به صفحه بعد از {page_num} برای '{keyword}' رفت. پایان جستجو برای این کلمه.")
                            break # از حلقه صفحات خارج شو، چون دکمه بعدی نیست
                    else:
                        logging.info(f"به حداکثر تعداد صفحات ({max_pages}) برای بررسی '{keyword}' رسیدیم.")

                logging.info(f"دامنه '{self.target_domain}' برای '{keyword}' در {max_pages} صفحه اول ({absolute_rank_counter} نتیجه بررسی شده) یافت نشد.")
                return {"keyword": keyword, "rank": f"Not Found in top {absolute_rank_counter}", "url": "", "title": "", "page": max_pages, "status": "Not Found"}

            except TimeoutException as e:
                logging.warning(f"Timeout در تلاش {attempt + 1} برای '{keyword}': {e}")
                if TAKE_SCREENSHOTS_ON_ERROR: self.driver.save_screenshot(f"error_timeout_{keyword.replace(' ','_')}_{attempt}.png")
                if attempt >= retries: 
                    return {"keyword": keyword, "rank": "Error - Timeout", "url": "", "title": "", "page": 0, "status": "Error"}
            except WebDriverException as e: # خطاهای عمومی‌تر درایور
                logging.error(f"خطای WebDriver در تلاش {attempt + 1} برای '{keyword}': {type(e).__name__} - {e}")
                if TAKE_SCREENSHOTS_ON_ERROR: self.driver.save_screenshot(f"error_webdriver_{keyword.replace(' ','_')}_{attempt}.png")
                # اگر خطای session id is null یا مشابه آن بود، ممکن است مرورگر کرش کرده باشد.
                if "session id is null" in str(e).lower() or "target window already closed" in str(e).lower():
                    logging.error("مرورگر احتمالاً کرش کرده یا بسته شده است. تلاش برای راه‌اندازی مجدد درایور...")
                    self.close() # بستن درایور فعلی (اگر هنوز وجود دارد)
                    try:
                        self._setup_driver() # راه‌اندازی مجدد
                    except Exception as setup_err:
                         logging.critical(f"امکان راه‌اندازی مجدد درایور وجود ندارد: {setup_err}")
                         # اگر نتوانستیم مجددا راه اندازی کنیم، باید از این کلمه کلیدی صرفنظر کنیم یا کل برنامه را متوقف کنیم.
                         return {"keyword": keyword, "rank": "Error - Driver Crash, Restart Failed", "url": "", "title": "", "page": 0, "status": "Error"}
                if attempt >= retries:
                    return {"keyword": keyword, "rank": f"Error - WebDriver ({type(e).__name__})", "url": "", "title": "", "page": 0, "status": "Error"}
            except Exception as e:
                logging.error(f"یک خطای غیرمنتظره در تلاش {attempt + 1} برای '{keyword}': {type(e).__name__} - {e}", exc_info=False)
                if TAKE_SCREENSHOTS_ON_ERROR and self.driver:
                     try: self.driver.save_screenshot(f"error_unexpected_{keyword.replace(' ','_')}_{attempt}.png")
                     except: pass
                if attempt >= retries:
                    return {"keyword": keyword, "rank": f"Error - Unexpected ({type(e).__name__})", "url": "", "title": "", "page": 0, "status": "Error"}
            attempt += 1
        
        # اگر حلقه تمام شد و نتیجه‌ای برنگشت (نباید اتفاق بیفتد اگر منطق درست باشد)
        return {"keyword": keyword, "rank": "Error - Max Retries Reached (Logic Error?)", "url": "", "title": "", "page": 0, "status": "Error"}


    def close(self):
        """مرورگر را می‌بندد."""
        if self.driver:
            try:
                self.driver.quit()
                logging.info("مرورگر با موفقیت بسته شد.")
            except Exception as e:
                logging.warning(f"خطا در بستن مرورگر: {e}")
            self.driver = None

def save_results_to_files(results_df, base_filename_prefix):
    """نتایج DataFrame را در فایل‌های CSV و Excel ذخیره می‌کند."""
    if results_df.empty:
        logging.info("داده‌ای برای ذخیره‌سازی وجود ندارد.")
        return

    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # ۱. ذخیره به صورت فایل CSV
    csv_filename = f"{base_filename_prefix}_{timestamp_str}.csv"
    try:
        results_df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        logging.info(f"نتایج با موفقیت در فایل CSV ذخیره شد: {csv_filename}")
    except Exception as e:
        logging.error(f"خطا در ذخیره فایل CSV '{csv_filename}': {e}")

    # ۲. ذخیره به صورت فایل Excel (نیاز به openpyxl: pip install openpyxl)
    excel_filename = f"{base_filename_prefix}_{timestamp_str}.xlsx"
    try:
        results_df.to_excel(excel_filename, index=False, sheet_name='Rankings')
        logging.info(f"نتایج با موفقیت در فایل Excel ذخیره شد: {excel_filename}")
    except Exception as e:
        logging.error(f"خطا در ذخیره فایل Excel '{excel_filename}': {e}")
        logging.warning("برای ذخیره در فرمت Excel، کتابخانه 'openpyxl' باید نصب باشد: `pip install openpyxl`")


if __name__ == "__main__":
    logging.info("--- ربات بررسی رتبه گوگل سجاد اکبری ---")
    logging.info(f"دامنه هدف: {TARGET_DOMAIN}")
    logging.info(f"تعداد کلمات کلیدی برای بررسی: {len(KEYWORDS_TO_TRACK)}")
    logging.info(f"حداکثر صفحات برای بررسی هر کلمه: {MAX_PAGES_TO_CHECK}")

    all_results_data = []
    tracker_instance = None

    try:
        tracker_instance = GoogleRankTracker(driver_path=CHROME_DRIVER_PATH, 
                                             target_domain=TARGET_DOMAIN)
        
        for i, keyword in enumerate(KEYWORDS_TO_TRACK):
            result = tracker_instance.get_rank_for_keyword(keyword, max_pages=MAX_PAGES_TO_CHECK, retries=1)
            result['timestamp_executed'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result['target_domain_checked'] = TARGET_DOMAIN # اضافه کردن دامنه برای وضوح در خروجی
            all_results_data.append(result)
            
            logging.info(f"نتیجه برای '{keyword}': رتبه {result.get('rank', 'N/A')}, وضعیت: {result.get('status', 'N/A')}")

            # تاخیر بین کلمات کلیدی برای جلوگیری از بلاک شدن (مگر اینکه آخرین کلمه کلیدی باشد)
            if i < len(KEYWORDS_TO_TRACK) - 1:
                delay = random.uniform(RANDOM_DELAY_BETWEEN_KEYWORDS[0], RANDOM_DELAY_BETWEEN_KEYWORDS[1])
                logging.info(f"تاخیر {delay:.2f} ثانیه‌ای قبل از بررسی کلمه کلیدی بعدی...")
                time.sleep(delay)

    except KeyboardInterrupt: # اگر کاربر Ctrl+C بزند
        logging.warning("عملیات توسط کاربر متوقف شد.")
    except WebDriverException as e: # خطاهای مربوط به درایور که در init رخ می‌دهد
        logging.critical(f"امکان ادامه کار به دلیل خطای WebDriver وجود ندارد: {e}")
    except Exception as e:
        logging.critical(f"یک خطای پیش‌بینی نشده در اجرای اصلی رخ داد: {e}", exc_info=True)
    finally:
        if tracker_instance:
            tracker_instance.close()
        
        logging.info("\n--- خلاصه نتایج ---")
        if all_results_data:
            results_df = pd.DataFrame(all_results_data)
            # تنظیم ترتیب ستون ها برای خوانایی بهتر
            column_order = ['timestamp_executed', 'keyword', 'target_domain_checked', 'rank', 'status', 'url', 'title', 'page']
            # اطمینان از اینکه همه ستون‌ها وجود دارند، اگر نه با خالی پر شوند
            results_df = results_df.reindex(columns=column_order, fill_value='')
            
            # نمایش نتایج در کنسول (می‌توان این بخش را برای تعداد زیاد کلمه کلیدی خلاصه تر کرد)
            # pd.set_option('display.max_rows', None)
            # pd.set_option('display.max_colwidth', None)
            # pd.set_option('display.width', 1000)
            logging.info(f"\n{results_df.to_string(index=False)}")
            
            # ذخیره نتایج در فایل‌ها
            save_results_to_files(results_df, OUTPUT_FILENAME_PREFIX)

        else:
            logging.info("هیچ نتیجه‌ای جمع‌آوری نشد.")
        
        logging.info("--- پایان عملیات ربات ---")
