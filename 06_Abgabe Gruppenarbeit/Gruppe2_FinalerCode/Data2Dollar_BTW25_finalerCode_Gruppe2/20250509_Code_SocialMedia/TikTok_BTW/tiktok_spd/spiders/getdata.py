import scrapy
from scrapy.http import Request
from datetime import datetime
import json
import re
import time
import random
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message
import logging
from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.signalmanager import dispatcher
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class TikTokRetryMiddleware(RetryMiddleware):
    def __init__(self, settings):
        super().__init__(settings)
        self.retry_http_codes = set([403, 429, 503, 302, 406, 408, 500, 502, 520, 522])

    def process_response(self, request, response, spider):
        if request.meta.get('dont_retry', False):
            return response
        if response.status in self.retry_http_codes:
            self.logger.warning(f'Retrying {request.url} (status code: {response.status})')
            return self._retry(request, response.status, spider) or response
        return response

    def process_exception(self, request, exception, spider):
        spider.logger.warning(f"Exception for {request.url}: {exception}")
        return super().process_exception(request, exception, spider)

class GetdataSpider(scrapy.Spider):
    name = "getdata"
    allowed_domains = ["www.tiktok.com"]
    start_urls = ["https://www.tiktok.com/@deinespd"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        options = uc.ChromeOptions()
        
        # Basic configuration
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--headless=new')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1')
        
        # Create undetected ChromeDriver instance
        self.driver = uc.Chrome(
            options=options,
            use_subprocess=True,
            version_main=None  # Auto-detect Chrome version
        )
        
        self.start_date = datetime(2024, 12, 27)
        self.end_date = datetime(2025, 2, 23)
        self.wait = WebDriverWait(self.driver, 15)

    def parse(self, response):
        try:
            self.logger.info("Starting to scrape TikTok profile")
            
            # Use mobile URL
            self.driver.get("https://www.tiktok.com/@deinespd")
            time.sleep(random.uniform(3, 5))
            
            # Inject custom JavaScript to mask automation
            self.driver.execute_script('''
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            ''')
            
            # Wait for profile to load
            try:
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-e2e="user-post-item"],[class*="DivItemContainer"]')))
                self.logger.info("Profile page loaded successfully")
            except Exception as e:
                self.logger.warning(f"Profile page load timeout: {str(e)}")
            
            # Initial scroll to trigger video loading
            self.driver.execute_script("window.scrollTo(0, 500);")
            time.sleep(2)
            
            # Scroll and collect videos
            scroll_attempts = 0
            max_attempts = 20
            processed_videos = set()
            last_height = self.driver.execute_script("return document.documentElement.scrollHeight")
            
            while scroll_attempts < max_attempts:
                # Try multiple selectors for video containers
                selectors = [
                    "//div[@data-e2e='user-post-item']",
                    "//div[contains(@class, 'DivItemContainer')]",
                    "//div[contains(@class, 'video-feed-item')]",
                    "//div[contains(@class, 'tiktok-x6y88p-DivItemContainerV2')]"
                ]
                
                for selector in selectors:
                    try:
                        videos = self.driver.find_elements(By.XPATH, selector)
                        if videos:
                            self.logger.info(f"Found {len(videos)} videos with selector: {selector}")
                            
                            for video in videos:
                                try:
                                    # Get video URL from various possible elements
                                    video_url = None
                                    for url_elem in video.find_elements(By.XPATH, ".//a"):
                                        href = url_elem.get_attribute('href')
                                        if href and '@deinespd/video/' in href:
                                            video_url = href
                                            break
                                    
                                    if video_url and video_url not in processed_videos:
                                        processed_videos.add(video_url)
                                        
                                        # Extract views using JavaScript
                                        view_count = self.driver.execute_script("""
                                            var elem = arguments[0];
                                            var viewElems = elem.querySelectorAll('[data-e2e*="video-views"], [data-e2e*="video-count"], .video-count, .video-stats strong');
                                            for(var i = 0; i < viewElems.length; i++) {
                                                if(viewElems[i].textContent) return viewElems[i].textContent;
                                            }
                                            return null;
                                        """, video)
                                        
                                        # Extract date using JavaScript
                                        date_text = self.driver.execute_script("""
                                            var elem = arguments[0];
                                            var dateElems = elem.querySelectorAll('time, [data-e2e*="post-time"]');
                                            for(var i = 0; i < dateElems.length; i++) {
                                                var dt = dateElems[i].getAttribute('datetime') || dateElems[i].textContent;
                                                if(dt) return dt;
                                            }
                                            return null;
                                        """, video)
                                        
                                        if date_text:
                                            try:
                                                if 'T' in date_text:
                                                    post_date = datetime.strptime(date_text.split('T')[0], '%Y-%m-%d')
                                                else:
                                                    # Try different date formats
                                                    for fmt in ['%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y']:
                                                        try:
                                                            post_date = datetime.strptime(date_text, fmt)
                                                            break
                                                        except:
                                                            continue
                                                
                                                if view_count and post_date and self.start_date <= post_date <= self.end_date:
                                                    clean_views = self.clean_view_count(view_count)
                                                    self.logger.info(f"Found video: Date={post_date.strftime('%Y-%m-%d')}, Views={clean_views}")
                                                    
                                                    yield {
                                                        'date': post_date.strftime('%Y-%m-%d'),
                                                        'views': clean_views,
                                                        'url': video_url
                                                    }
                                            except Exception as e:
                                                self.logger.error(f"Error parsing date {date_text}: {str(e)}")
                                except Exception as e:
                                    self.logger.error(f"Error processing individual video: {str(e)}")
                                    continue
                            
                            break  # Break out of selector loop if videos were found
                    except Exception as e:
                        self.logger.error(f"Error with selector {selector}: {str(e)}")
                        continue
                
                # Scroll with random offset and delay
                scroll_height = random.randint(500, 1000)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_height});")
                time.sleep(random.uniform(2, 3))
                
                # Check if we've reached the bottom
                new_height = self.driver.execute_script("return document.documentElement.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                else:
                    last_height = new_height
                    scroll_attempts = 0  # Reset counter if we found new content
                
                self.logger.info(f"Scroll attempt {scroll_attempts}/{max_attempts}, processed {len(processed_videos)} videos")
                
                # Break if we've found enough videos
                if len(processed_videos) >= 50:  # Adjust this number as needed
                    self.logger.info("Reached target number of videos")
                    break
        
        except Exception as e:
            self.logger.error(f"Error during scraping: {str(e)}")
        
        finally:
            if hasattr(self, 'driver'):
                self.driver.quit()

    def clean_view_count(self, view_count):
        if not view_count:
            return 0
            
        try:
            # Remove any non-numeric characters except K, M, B, comma and dot
            view_count = ''.join(c for c in view_count if c.isdigit() or c in 'kmb,.')
            view_count = view_count.strip().lower()
            
            multiplier = 1
            if 'k' in view_count:
                multiplier = 1000
                view_count = view_count.replace('k', '')
            elif 'm' in view_count:
                multiplier = 1000000
                view_count = view_count.replace('m', '')
            elif 'b' in view_count:
                multiplier = 1000000000
                view_count = view_count.replace('b', '')
            
            # Handle comma as decimal separator
            view_count = view_count.replace(',', '.')
            
            return int(float(view_count) * multiplier)
        except (ValueError, TypeError) as e:
            self.logger.error(f"Error cleaning view count {view_count}: {str(e)}")
            return 0

def run_spider():
    """Spider as a process"""
    process = CrawlerProcess({
        'LOG_LEVEL': 'INFO',
        'FEEDS': {
            'spd_tiktok_data.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 4,
                'overwrite': True,
            },
        },
    })
    
    process.crawl(GetdataSpider)
    process.start()

if __name__ == "__main__":
    run_spider()