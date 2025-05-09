import asyncio
import scrapy.utils.reactor
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from twisted.internet import asyncio as twisted_asyncio

# Install AsyncioSelectorReactor
twisted_asyncio.install()

def run_spider():
    process = CrawlerProcess(get_project_settings())
    process.crawl('tiktok_comments')
    process.start()

if __name__ == "__main__":
    run_spider()