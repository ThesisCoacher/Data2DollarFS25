import asyncio
from scrapy.utils.log import configure_logging
from scrapy.utils.project import get_project_settings
from scrapy.crawler import CrawlerProcess
from spiders.tiktok_spider import TiktokCommentsSpider
from twisted.internet import asyncio as twisted_asyncio

def run_spider():
    # Install asyncio reactor
    twisted_asyncio.install()
    
    # Configure Scrapy
    settings = get_project_settings()
    settings.update({
        'FEEDS': {
            'comments.json': {
                'format': 'json',
                'encoding': 'utf8',
                'overwrite': True,
            },
        },
    })
    configure_logging(settings)
    
    # Create crawler process
    process = CrawlerProcess(settings)
    
    # Add our spider to crawl
    process.crawl(TiktokCommentsSpider)
    
    # Start the crawling process
    process.start()

if __name__ == "__main__":
    run_spider()