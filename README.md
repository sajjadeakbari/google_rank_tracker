# ربات بررسی رتبه گوگل با Python + Selenium (پروژه سجاد اکبری)

[![GitHub stars](https://img.shields.io/github/stars/sajjadeakbari/google_rank_tracker.svg?style=social&label=Star&maxAge=2592000)](https://github.com/sajjadeakbari/google_rank_tracker/stargazers/)
[![GitHub forks](https://img.shields.io/github/forks/sajjadeakbari/google_rank_tracker.svg?style=social&label=Fork&maxAge=2592000)](https://github.com/sajjadeakbari/google_rank_tracker/network/members)

این پروژه یک ربات پایتونی برای بررسی و ردیابی خودکار رتبه یک وب‌سایت خاص برای مجموعه‌ای از کلمات کلیدی در نتایج جستجوی گوگل است. این ابزار با استفاده از کتابخانه Selenium برای کنترل مرورگر و استخراج اطلاعات ساخته شده است. این ریپازیتوری کد منبع مربوط به مقاله آموزشی جامع در این زمینه است.

**لینک به مقاله:** *(در صورت وجود، لینک مقاله خود را اینجا قرار دهید)*

## 🚀 قابلیت‌ها

*   بررسی رتبه برای چندین کلمه کلیدی.
*   تعیین دامنه هدف برای ردیابی.
*   تنظیم حداکثر تعداد صفحات نتایج گوگل برای بررسی.
*   استفاده از User-Agent سفارشی و تاخیرهای تصادفی برای کاهش احتمال شناسایی شدن.
*   اجرای مرورگر در حالت Headless (بدون نمایش پنجره).
*   مدیریت خطاهای رایج و تلاش مجدد (Retry).
*   ذخیره نتایج در فرمت‌های CSV و Excel به همراه تاریخ و زمان.
*   لاگ‌گیری دقیق از عملیات.

## 🛠️ پیش‌نیازها

*   Python 3.7 یا بالاتر.
*   مرورگر Google Chrome نصب شده روی سیستم.
*   (اختیاری اما شدیدا توصیه شده) Git برای کلون کردن مخزن.

## ⚙️ راه‌اندازی و نصب

1.  **کلون کردن مخزن:**
    ```bash
    git clone https://github.com/sajjadeakbari/google_rank_tracker.git
    cd google_rank_tracker
    ```

2.  **ایجاد و فعال‌سازی یک محیط مجازی (بسیار توصیه می‌شود):**
    ```bash
    # برای پایتون نسخه ۳
    python -m venv venv 
    # یا اگر از python3 به طور صریح استفاده می‌کنید:
    # python3 -m venv venv

    # فعال‌سازی در ویندوز:
    venv\Scripts\activate
    # فعال‌سازی در macOS/Linux:
    source venv/bin/activate
    ```

3.  **نصب کتابخانه‌های مورد نیاز:**
    فایل `requirements.txt` شامل کتابخانه‌های اصلی برای اجرای ربات است.
    ```bash
    pip install -r requirements.txt
    ```

4.  **راه‌اندازی ChromeDriver:**
    *   **روش توصیه شده (Selenium 4.6.0 به بالا):** Selenium Manager معمولاً به صورت خودکار ChromeDriver مناسب را دانلود و مدیریت می‌کند اگر در `PATH` سیستم نباشد. در اکثر موارد، نیازی به تنظیم دستی `CHROME_DRIVER_PATH` در اسکریپت `google_rank_tracker.py` نیست و می‌توانید آن را روی `None` (مقدار پیش‌فرض در اسکریپت) باقی بگذارید.
    *   **روش دستی (اگر روش خودکار کار نکرد یا از نسخه‌های قدیمی‌تر Selenium استفاده می‌کنید):**
        1.  آخرین نسخه ChromeDriver متناسب با نسخه Google Chrome خود را از [ChromeDriver WebDriver for Chrome](https://chromedriver.chromium.org/downloads) دانلود کنید.
        2.  فایل اجرایی `chromedriver.exe` (برای ویندوز) یا `chromedriver` (برای مک/لینوکس) را در مکانی روی سیستم خود قرار دهید.
        3.  مسیر کامل این فایل را در متغیر `CHROME_DRIVER_PATH` در ابتدای اسکریپت `google_rank_tracker.py` تنظیم کنید.
            *مثال برای ویندوز:* `CHROME_DRIVER_PATH = "C:/WebDriver/chromedriver.exe"`
            *مثال برای مک/لینوکس:* `CHROME_DRIVER_PATH = "/usr/local/bin/chromedriver"`
            (راه دیگر: فایل `chromedriver` را در پوشه‌ای قرار دهید که در متغیر `PATH` سیستمتان لیست شده است.)

## 🔧 پیکربندی ربات

قبل از اجرای اسکریپت، فایل `google_rank_tracker.py` را باز کرده و مقادیر زیر را در **بخش تنظیمات (ابتدای فایل)** مطابق نیاز خود ویرایش کنید:

*   `TARGET_DOMAIN`: دامنه وب‌سایتی که می‌خواهید رتبه آن را بررسی کنید (مثال: `"wikipedia.org"`). **مهم:** بدون `http://` یا `www.` وارد کنید.
*   `KEYWORDS_TO_TRACK`: لیستی از کلمات کلیدی مورد نظر شما (مثال: `["قیمت گوشی سامسونگ", "آموزش پایتون"]`).
*   `MAX_PAGES_TO_CHECK`: حداکثر تعداد صفحات نتایج گوگل که برای هر کلمه کلیدی بررسی می‌شود (مثال: `3`).
*   `CHROME_DRIVER_PATH`: (در صورت نیاز به تنظیم دستی، طبق توضیحات بخش راه‌اندازی ChromeDriver).

سایر تنظیمات پیشرفته مانند `DEFAULT_USER_AGENT`، تاخیرها (`RANDOM_DELAY_BETWEEN_KEYWORDS`, `RANDOM_DELAY_BETWEEN_PAGES`) و سطح لاگ‌گیری (`LOG_LEVEL`) نیز در همان بخش قابل ویرایش هستند.

## ▶️ اجرای ربات

پس از انجام تنظیمات، اسکریپت را از طریق ترمینال یا خط فرمان (در محیط مجازی فعال شده) اجرا کنید:

```bash
python google_rank_tracker.py
```

ربات شروع به کار کرده و لاگ عملیات را در کنسول نمایش می‌دهد. در پایان، نتایج در فایل‌های CSV و Excel (در صورت نصب بودن `openpyxl`) در همان پوشه اسکریپت ذخیره خواهند شد. نام فایل‌ها شامل تاریخ و زمان اجرا خواهد بود.

## 📊 تحلیل نتایج

فایل‌های CSV یا Excel خروجی شامل اطلاعات زیر برای هر کلمه کلیدی هستند:
*   `timestamp_executed`: زمان دقیق بررسی.
*   `keyword`: کلمه کلیدی بررسی شده.
*   `target_domain_checked`: دامنه هدف که برای آن جستجو انجام شده.
*   `rank`: رتبه عددی یافت شده یا وضعیت (مانند "Not Found...", "CAPTCHA", "Error...").
*   `status`: وضعیت نهایی (Found, Not Found, CAPTCHA, Error).
*   `url`: آدرس URL صفحه رتبه‌بندی شده (در صورت یافتن).
*   `title`: عنوان صفحه رتبه‌بندی شده (در صورت یافتن).
*   `page`: شماره صفحه‌ای از نتایج گوگل که دامنه در آن یافت شده (تخمینی بر اساس نتایج هر صفحه).

برای تحلیل‌های پیشرفته‌تر و بصری‌سازی روندها، می‌توانید از داده‌های این فایل‌ها در ابزارهایی مانند Microsoft Excel, Google Sheets یا با استفاده از کتابخانه‌های پایتون مانند Pandas, Matplotlib و Seaborn (همانطور که در مقاله همراه توضیح داده شده) استفاده کنید.

## ✨ ابزارها و کتابخانه‌های تکمیلی (پیشنهادی)

### کتابخانه `seokar`

برای انجام تحلیل‌های تخصصی‌تر سئو و کار با داده‌های مرتبط، می‌توانید از کتابخانه `seokar` استفاده کنید. این کتابخانه می‌تواند در کنار خروجی این ربات، به شما در درک بهتر وضعیت سئوی وب‌سایتتان کمک کند.

**نصب `seokar` (در صورت نیاز):**
```bash
pip install seokar
```
*(در صورت وجود، لینک به مستندات یا مخزن `seokar` را اینجا قرار دهید)*

## ⚠️ ملاحظات مهم

*   **شرایط خدمات گوگل:** اسکرپینگ خودکار نتایج جستجوی گوگل برخلاف شرایط خدمات این شرکت است. از این ابزار با مسئولیت خود و با رعایت جوانب احتیاط (استفاده محدود، تاخیر مناسب) استفاده کنید. این ابزار بیشتر برای اهداف آموزشی و استفاده شخصی در مقیاس کوچک طراحی شده است.
*   **CAPTCHA:** در صورت ارسال درخواست‌های زیاد یا تشخیص رفتار مشکوک توسط گوگل، ممکن است با CAPTCHA مواجه شوید. ربات فعلی قابلیت حل خودکار CAPTCHA را ندارد و در صورت شناسایی، آن کلمه کلیدی را با وضعیت CAPTCHA رها می‌کند.
*   **تغییرات ساختار گوگل:** گوگل ممکن است ساختار HTML صفحات نتایج خود را تغییر دهد که می‌تواند باعث از کار افتادن سلکتورهای CSS/XPath در ربات شود. در این صورت، نیاز به به‌روزرسانی سلکتورها در کد (`_extract_search_results` و `_click_next_page`) خواهد بود.
*   **User-Agent:** استفاده از User-Agent معقول و به‌روز و حتی چرخشی (با کدنویسی بیشتر) می‌تواند به کاهش احتمال شناسایی شدن کمک کند.

## 🤝 مشارکت و گزارش خطا

از مشارکت شما استقبال می‌شود! اگر پیشنهادی برای بهبود دارید یا خطایی پیدا کردید، لطفاً یک "Issue" در این مخزن ثبت کنید یا یک "Pull Request" ارسال نمایید.

## 📝 نویسنده

**سجاد اکبری**

*   GitHub: [sajjadeakbari](https://github.com/sajjadeakbari)
*   *(می‌توانید لینک به وب‌سایت شخصی، لینکدین یا سایر پروفایل‌های خود را اینجا اضافه کنید)*

## 📜 مجوز

این پروژه تحت مجوز MIT منتشر شده است. برای جزئیات بیشتر فایل `LICENSE` را (در صورت وجود) مشاهده کنید. *(اگر فایل LICENSE ندارید، می‌توانید این خط را حذف کنید یا یک فایل LICENSE به پروژه اضافه کنید. MIT یک مجوز رایج و ساده است.)*
