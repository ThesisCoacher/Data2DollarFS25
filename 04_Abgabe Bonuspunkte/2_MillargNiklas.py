import time
import csv
from datetime import datetime
from scrapy import Spider, Request
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("airbnb_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GetdataSpider(Spider):
    name = 'getdata'
    allowed_domains = ["www.airbnb.ch"]
    
    def __init__(self):
        super(GetdataSpider, self).__init__()
        chrome_options = Options()
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
        chrome_options.add_argument(f"--user-agent={user_agent}")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )
        
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.listings_count = 0
        self.max_listings = 100
        self.items = []
        self.current_page = 1

    def start_requests(self):
        check_in = "2025-06-26"
        check_out = "2025-06-29"
        location = "St.%20Gallen%2C%20Switzerland"
        
        url = f"https://www.airbnb.ch/s/{location}/homes?checkin={check_in}&checkout={check_out}&adults=1"
        
        logger.info(f"Starting scrape with URL: {url}")
        print("\n=== Airbnb Accommodation Scraper ===")
        print("="*70)
        print(f"{'TITLE':<40} | {'PRICE':<15} | {'PAGE':<5}")
        print("="*70)
        
        yield Request(
            url=url,
            callback=self.parse_listings_page,
            dont_filter=True
        )

    def parse_listings_page(self, response):
        logger.info(f"Processing page {self.current_page}: {response.url}")
        
        try:
            if self.current_page > 1:
                current_url = self.driver.current_url
                logger.info(f"Already on page {self.current_page}: {current_url}")
            else:
                self.driver.get(response.url)
            
            logger.info("Waiting for page to load...")
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[itemprop='itemListElement']"))
            )
            
            time.sleep(5)
            
            logger.info("Scrolling to load content...")
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight * 0.7);")
            time.sleep(3)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            
            listing_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[itemprop='itemListElement']")
            
            if not listing_elements:
                listing_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[data-testid='card-container']")
            
            logger.info(f"Found {len(listing_elements)} listing elements on page {self.current_page}")
            
            for i, listing_element in enumerate(listing_elements):
                if self.listings_count >= self.max_listings:
                    break
                
                try:
                    listing = {
                        'page': self.current_page,
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    try:
                        title_element = listing_element.find_element(By.CSS_SELECTOR, "div[data-testid='listing-card-title']")
                        listing['name'] = title_element.text.strip()
                    except:
                        listing['name'] = None
                    
                    try:
                        price_element = listing_element.find_element(By.CSS_SELECTOR, "._hb913q")
                        listing['price_per_night'] = price_element.text.strip()
                    except:
                        listing['price_per_night'] = None
                    
                    if listing['name'] and listing['price_per_night']:
                        self.items.append(listing)
                        self.listings_count += 1
                        
                        # Print to console
                        title_display = listing['name'][:37] + "..." if len(listing['name']) > 40 else listing['name']
                        print(f"{title_display:<40} | {listing['price_per_night']:<15} | {self.current_page:<5}")
                    
                except Exception as e:
                    logger.error(f"Error processing listing element: {e}")
            
            if self.listings_count < self.max_listings:
                try:
                    next_button = None
                    next_selectors = [
                        "a[aria-label='Next']",
                        "a[aria-label='Next page']",
                        "a.l1ovpqvx[aria-busy='false']",
                        "button[aria-label='Next']",
                        "a[data-testid='pagination-next-btn']"
                    ]
                    
                    for selector in next_selectors:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements and elements[0].is_displayed():
                            next_button = elements[0]
                            break
                    
                    if next_button:
                        logger.info(f"Found next button on page {self.current_page}, navigating...")
                        self.current_page += 1
                        next_button.click()
                        time.sleep(5)
                        yield Request(
                            url=self.driver.current_url,
                            callback=self.parse_listings_page,
                            dont_filter=True
                        )
                    else:
                        logger.info(f"No next button found on page {self.current_page}")
                        print(f"\nNo more pages available. Reached {self.current_page} pages.")
                except Exception as e:
                    logger.error(f"Error navigating to next page: {e}")
                    
        except Exception as e:
            logger.error(f"Error in parse_listings_page: {e}")
    
    def closed(self, reason):
        logger.info(f"Spider closed: {reason}")
        
        print("="*70)
        print(f"Total listings: {self.listings_count} across {self.current_page} pages")
        print("="*70)
        
        if self.items:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'airbnb_st_gallen_june2025_{timestamp}.csv'
            
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=['name', 'price_per_night', 'page', 'scraped_at'])
                    writer.writeheader()
                    for item in self.items:
                        writer.writerow(item)
                
                logger.info(f"Successfully saved {len(self.items)} listings to {filename}")
                print(f"\nData saved to {filename}")
            except Exception as e:
                logger.error(f"Error saving to CSV: {e}")
        
        self.driver.quit()
