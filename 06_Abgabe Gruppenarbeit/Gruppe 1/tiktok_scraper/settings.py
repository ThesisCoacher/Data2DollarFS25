BOT_NAME = "tiktok"

SPIDER_MODULES = ["tiktok.spiders"]
NEWSPIDER_MODULE = "tiktok.spiders"

# Scraping settings
ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 1
DOWNLOAD_DELAY = 2

# Playwright settings
DOWNLOAD_HANDLERS = {
    "http": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
    "https": "scrapy_playwright.handler.ScrapyPlaywrightDownloadHandler",
}

# ARM Mac optimized browser configuration
PLAYWRIGHT_BROWSER_TYPE = "chromium"
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": False,
    "channel": "chromium",
    "args": [
        "--no-sandbox",
        "--disable-dev-shm-usage"
    ]
}

# Additional settings
DOWNLOAD_TIMEOUT = 30
PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 30000

# Output configuration
FEED_EXPORT_ENCODING = "utf-8"
FEEDS = {
    'comments.json': {
        'format': 'json',
        'encoding': 'utf8',
        'overwrite': True
    }
}