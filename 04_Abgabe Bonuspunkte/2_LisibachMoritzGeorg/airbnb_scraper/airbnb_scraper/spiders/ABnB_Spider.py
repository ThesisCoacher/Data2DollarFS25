import scrapy
from scrapy import signals
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import os
import csv
import time
import random
import logging
from datetime import datetime

class AirbnbSpider(scrapy.Spider):
    name = 'airbnb'
    allowed_domains = ['airbnb.com']
    
    custom_settings = {
        'ROBOTSTXT_OBEY': False,
        'DOWNLOAD_DELAY': random.uniform(2, 4),  # Randomized delay
        'CONCURRENT_REQUESTS': 1
    }

    def __init__(self):
        super().__init__()
        self.setup_chrome()
        self.output_dir = "airbnb_data"
        self.html_dir = os.path.join(self.output_dir, "html_pages")
        
        for directory in [self.output_dir, self.html_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
        
        self.date_ranges = [
            {"check_in": "2025-06-26", "check_out": "2025-06-29"},
            {"check_in": "2025-10-09", "check_out": "2025-10-19"}
        ]
        
        self.location = "St. Gallen, Switzerland"
        self.target_listings = 100
        
        self.all_listings = {
            f"{date_range['check_in']}_to_{date_range['check_out']}": []
            for date_range in self.date_ranges
        }
        
        # Updated selectors using more resilient patterns
        self.listing_container = "div[itemprop='itemListElement'], div[role='group']"
        self.name_selector = "div[style*='line-height'] span, div[data-testid*='title'], div[aria-labelledby*='title']"
        self.price_selector = "span[style*='font-weight: 600'], span[data-testid*='price'], span[aria-label*='price']"
        self.next_button_selector = "a[aria-label*='Next'], button[aria-label*='Next'], a[data-testid*='next']"

    def setup_chrome(self):
        """Set up Chrome with enhanced anti-bot measures"""
        options = Options()
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # Enhanced browser fingerprinting
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument("--disable-notifications")
        options.add_argument("--lang=en-US,en")
        
        # Randomized viewport size
        width = random.randint(1280, 1920)
        height = random.randint(800, 1080)
        options.add_argument(f"--window-size={width},{height}")
        
        # Realistic user agent with platform-specific details
        user_agents = [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        self.driver = webdriver.Chrome(options=options)
        
        # Additional anti-detection measures
        self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
            "userAgent": random.choice(user_agents),
            "platform": random.choice(["Windows", "MacIntel", "Linux x86_64"]),
            "acceptLanguage": "en-US,en;q=0.9"
        })
        
        # Spoof webdriver
        self.driver.execute_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
        """)

    def natural_scroll(self):
        """Perform more natural scrolling with random pauses"""
        screen_height = self.driver.execute_script("return window.innerHeight")
        scroll_height = self.driver.execute_script("return document.documentElement.scrollHeight")
        
        current_position = 0
        while current_position < scroll_height:
            # Random scroll amount between 100-300 pixels
            scroll_amount = random.randint(100, 300)
            current_position += scroll_amount
            
            # Natural easing function
            self.driver.execute_script(f"""
                window.scrollTo({{
                    top: {current_position},
                    behavior: 'smooth'
                }});
            """)
            
            # Random pause between scrolls (1-3 seconds)
            time.sleep(random.uniform(1, 3))
            
            # Occasional longer pause (10% chance)
            if random.random() < 0.1:
                time.sleep(random.uniform(3, 5))
            
            # Small up/down movements (20% chance)
            if random.random() < 0.2:
                jitter = random.randint(-50, 50)
                self.driver.execute_script(f"window.scrollBy(0, {jitter})")
                time.sleep(random.uniform(0.5, 1))

        # Smooth scroll back to top
        self.driver.execute_script("window.scrollTo({ top: 0, behavior: 'smooth' })")
        time.sleep(random.uniform(2, 4))

    def wait_for_element(self, selector, by=By.CSS_SELECTOR, timeout=30, parent=None):
        """Enhanced wait function with retry logic"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                element = WebDriverWait(parent or self.driver, 5).until(
                    EC.presence_of_element_located((by, selector))
                )
                # Add random delay after finding element
                time.sleep(random.uniform(0.5, 1.5))
                return element
            except TimeoutException:
                # Retry with small scroll jitter
                self.driver.execute_script(f"window.scrollBy(0, {random.randint(-100, 100)})")
                time.sleep(random.uniform(1, 2))
        
        raise TimeoutException(f"Element {selector} not found after {timeout} seconds")

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    def spider_closed(self, spider):
        """Clean up when spider is closed"""
        self.driver.quit()
        self.save_results()

    def start_requests(self):
        """Start the scraping process for each date range"""
        for date_range in self.date_ranges:
            url = self.build_url(date_range)
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={
                    'date_range': date_range,
                    'page': 1
                },
                dont_filter=True
            )

    def build_url(self, date_range):
        """Build the Airbnb search URL"""
        location_query = self.location.replace(" ", "-").replace(",", "--")
        return f"https://www.airbnb.com/s/{location_query}/homes?checkin={date_range['check_in']}&checkout={date_range['check_out']}"

    def save_page_html(self, page_num, date_range):
        """Save the current page's HTML"""
        date_key = f"{date_range['check_in']}_to_{date_range['check_out']}"
        filename = f"page_{page_num}_{date_key}.html"
        filepath = os.path.join(self.html_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        
        self.logger.info(f"Saved HTML for page {page_num} to {filepath}")

    def parse(self, response):
        """Parse each page with improved loading and retry logic"""
        date_range = response.meta['date_range']
        page = response.meta['page']
        date_key = f"{date_range['check_in']}_to_{date_range['check_out']}"
        
        # Initial page load with longer wait time
        self.driver.get(response.url)
        time.sleep(random.uniform(8, 12))  # Increased initial wait
        
        # Natural scrolling behavior
        self.natural_scroll()
        
        # Save the page HTML
        self.save_page_html(page, date_range)
        
        # Extract listings with retry logic
        retry_count = 0
        max_retries = 3
        listings = []
        
        while retry_count < max_retries:
            try:
                listings = self.extract_listings()
                if listings:
                    break
            except Exception as e:
                self.logger.warning(f"Attempt {retry_count + 1} failed: {str(e)}")
                retry_count += 1
                time.sleep(random.uniform(5, 8))
        
        if listings:
            self.all_listings[date_key].extend(listings)
            self.logger.info(f"Found {len(listings)} listings on page {page} for {date_key}")
            
            if len(self.all_listings[date_key]) < self.target_listings:
                try:
                    next_button = self.wait_for_element(self.next_button_selector)
                    if next_button and next_button.is_enabled():
                        next_url = next_button.get_attribute('href')
                        time.sleep(random.uniform(3, 5))  # Natural pause before next page
                        yield scrapy.Request(
                            url=next_url,
                            callback=self.parse,
                            meta={
                                'date_range': date_range,
                                'page': page + 1
                            },
                            dont_filter=True
                        )
                except (TimeoutException, NoSuchElementException):
                    self.logger.info(f"No more pages available for {date_key}")
        else:
            self.logger.warning(f"No listings found on page {page} for {date_key}")

    def extract_listings(self):
        """Extract listing information from the current page using more robust selectors"""
        listings = []
        retry_count = 0
        max_retries = 3
        
        while retry_count < max_retries:
            try:
                # Wait for listings container with increased timeout
                WebDriverWait(self.driver, 30).until(  # Increased timeout to 30 seconds
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.listing_container))
                )
                
                # Additional wait after container is found
                time.sleep(random.uniform(2, 4))
                
                # Find all listing containers
                listing_containers = self.driver.find_elements(By.CSS_SELECTOR, self.listing_container)
                self.logger.info(f"Found {len(listing_containers)} listing containers")
                
                for container in listing_containers:
                    listing = {}
                    
                    try:
                        # Extract name
                        name_element = WebDriverWait(container, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, self.name_selector))
                        )
                        if name_element:
                            listing['name'] = name_element.text.strip()
                    except (NoSuchElementException, TimeoutException):
                        self.logger.debug("Could not find name element")
                        continue
                        
                    try:
                        # Extract price with retry logic
                        price_element = WebDriverWait(container, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, self.price_selector))
                        )
                        if price_element:
                            price_text = price_element.text.strip()
                            # Extract only digits from price
                            listing['price'] = ''.join(filter(str.isdigit, price_text))
                    except (NoSuchElementException, TimeoutException):
                        self.logger.debug("Could not find price element")
                        continue
                    
                    if listing.get('name') and listing.get('price'):
                        listings.append(listing)
                        self.logger.debug(f"Added listing: {listing['name']} - {listing['price']}")
                    
                    # Break if we have enough listings
                    if len(listings) >= self.target_listings:
                        break
                
                break  # Break the retry loop if successful
                
            except TimeoutException:
                retry_count += 1
                self.logger.warning(f"Timeout waiting for listings (attempt {retry_count}/{max_retries})")
                time.sleep(random.uniform(3, 5))  # Longer wait before retry
                
                if retry_count == max_retries:
                    self.logger.error("Failed to load listings after maximum retries")
                    return []
            except Exception as e:
                self.logger.error(f"Error extracting listings: {e}")
                return []
        
        self.logger.info(f"Successfully extracted {len(listings)} listings on current page")
        return listings

    def save_results(self):
        """Save all results to CSV files"""
        # Save individual files for each date range
        for date_range in self.date_ranges:
            date_key = f"{date_range['check_in']}_to_{date_range['check_out']}"
            file_path = os.path.join(self.output_dir, f"airbnb_listings_{date_key}.csv")
            
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Name', 'Price per Night'])
                
                # Write exactly 100 listings or all available if less than 100
                for listing in self.all_listings[date_key][:self.target_listings]:
                    writer.writerow([
                        listing.get('name', ''),
                        listing.get('price', '')
                    ])
            
            self.logger.info(f"Saved {min(len(self.all_listings[date_key]), self.target_listings)} listings to {file_path}")
        
        # Create summary file
        self.create_summary()

    def create_summary(self):
        """Create a summary file combining all results"""
        summary_path = os.path.join(self.output_dir, "airbnb_all_listings.csv")
        
        with open(summary_path, 'w', newline='', encoding='utf-8') as summary_file:
            writer = csv.writer(summary_file)
            writer.writerow(['Name', 'Price per Night', 'Date Range'])
            
            for date_range in self.date_ranges:
                date_key = f"{date_range['check_in']}_to_{date_range['check_out']}"
                listings = self.all_listings[date_key][:self.target_listings]
                
                for listing in listings:
                    writer.writerow([
                        listing.get('name', ''),
                        listing.get('price', ''),
                        date_key
                    ])
        
        self.logger.info(f"Summary created at {summary_path}")
        
        # Print summary
        for date_key, listings in self.all_listings.items():
            self.logger.info(f"Date range {date_key}: {min(len(listings), self.target_listings)} listings")