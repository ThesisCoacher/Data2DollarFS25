# Scrapy settings for tiktok_spd project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "tiktok_spd"

SPIDER_MODULES = ["tiktok_spd.spiders"]
NEWSPIDER_MODULE = "tiktok_spd.spiders"

# Crawl responsibly by identifying yourself
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests
CONCURRENT_REQUESTS = 1
DOWNLOAD_DELAY = 3
RANDOMIZE_DOWNLOAD_DELAY = True

# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'tiktok_spd.middlewares.RotateUserAgentMiddleware': 400,
    'tiktok_spd.middlewares.TikTokAPIMiddleware': 401,
    'scrapy.downloadermiddlewares.retry.RetryMiddleware': 500,
    'scrapy.downloadermiddlewares.redirect.RedirectMiddleware': 600,
    'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
}

# Configure item pipelines
ITEM_PIPELINES = {
    'tiktok_spd.pipelines.TiktokSpdPipeline': 300,
}

# Enable and configure the AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 5
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = 3

# Enable and configure HTTP caching
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [503, 403, 429, 302, 307]

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 10  # Increased retry attempts
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]

# Additional settings for TikTok
DOWNLOAD_TIMEOUT = 180
COOKIES_ENABLED = True
COOKIES_DEBUG = False
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# Feed export settings
FEED_EXPORT_ENCODING = 'utf-8'

# Log settings
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
