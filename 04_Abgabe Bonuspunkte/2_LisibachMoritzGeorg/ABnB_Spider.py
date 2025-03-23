import scrapy
from scrapy.crawler import CrawlerProcess
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv
import platform
import random
from urllib.parse import quote
import logging
import os
from datetime import datetime

class AirbnbSpider(scrapy.Spider):
    name = "airbnb_spider"
    allowed_domains = ["airbnb.com"]
    
    def __init__(self):
        super().__init__()
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.FileHandler("airbnb_spider.log"), logging.StreamHandler()]
        )
        self.logger = logging.getLogger(self.name)
        
        # Configure Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # Set binary location based on operating system
        if platform.system() == "Darwin":  # macOS
            chrome_options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            self.logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
        
        # Create output directory if it doesn't exist
        self.output_dir = "output"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        # Define search parameters
        self.check_in = "2025-06-26"
        self.check_out = "2025-06-29"
        self.location = "St. Gallen, Switzerland"
        
    def start_requests(self):
        # Format the location for URL
        encoded_location = quote(self.location)
        
        # Construct URL with location and dates
        url = f"https://www.airbnb.com/s/{encoded_location}/homes?checkin={self.check_in}&checkout={self.check_out}"
        
        self.logger.info(f"Starting request to URL: {url}")
        yield scrapy.Request(url=url, callback=self.parse)
    
    def parse(self, response):
        try:
            self.logger.info(f"Navigating to: {response.url}")
            self.driver.get(response.url)
            
            # Initial wait for page load
            time.sleep(5)
            
            # Scroll down slowly to simulate human behavior and load all content
            self.logger.info("Scrolling down to load all content...")
            for i in range(5):
                self.driver.execute_script(f"window.scrollTo(0, {i * 800})")
                time.sleep(random.uniform(1.5, 3))
            
            # Scroll back to top
            self.driver.execute_script("window.scrollTo(0, 0)")
            time.sleep(2)
            
            # Save the page source for debugging
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = os.path.join(self.output_dir, f"airbnb_page_{timestamp}.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            self.logger.info(f"Saved HTML to {html_path}")
            
            # Take a screenshot for debugging
            screenshot_path = os.path.join(self.output_dir, f"screenshot_{timestamp}.png")
            self.driver.save_screenshot(screenshot_path)
            self.logger.info(f"Saved screenshot to {screenshot_path}")
            
            # Extract listings
            self.extract_listings()
            
        except Exception as e:
            self.logger.error(f"Error in parse method: {e}")
            self.driver.save_screenshot(os.path.join(self.output_dir, "error_screenshot.png"))
    
    def extract_listings(self):
        csv_path = os.path.join(self.output_dir, f"airbnb_listings_{self.check_in}_to_{self.check_out}.csv")
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Name', 'Price per Night', 'URL'])
            
            try:
                # Wait for the main content to load
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-section-id='EXPLORE_STRUCTURED_PAGE_TITLE']"))
                )
                
                # Better selectors based on Airbnb's structure
                listing_cards = self.driver.find_elements(By.CSS_SELECTOR, "div[itemprop='itemListElement']")
                self.logger.info(f"Found {len(listing_cards)} listing cards")
                
                # If no listing cards found with the above selector, try alternative selectors
                if not listing_cards:
                    self.logger.info("Trying alternative selectors...")
                    listing_cards = self.driver.find_elements(By.CSS_SELECTOR, "div[data-testid='card-container']")
                    self.logger.info(f"Found {len(listing_cards)} listing cards with alternative selector")
                
                if not listing_cards:
                    # Try one more alternative selector
                    listing_cards = self.driver.find_elements(By.XPATH, "//div[contains(@style, 'displayGrid')]//div[contains(@class, 'c4mnd7m')]")
                    self.logger.info(f"Found {len(listing_cards)} listing cards with second alternative selector")
                
                # Process found listings
                for i, card in enumerate(listing_cards, 1):
                    try:
                        # Try different selectors for the name
                        name = None
                        for selector in [
                            ".//div[contains(@class, 'fcab3ed')]/div[1]/div[1]/div/div/div/div/span",
                            ".//div[@class='t1jojoys dir dir-ltr']",
                            ".//span[contains(@class, 't6mzqp7')]"
                        ]:
                            try:
                                name_elem = card.find_element(By.XPATH, selector)
                                name = name_elem.text.strip()
                                if name:
                                    break
                            except:
                                continue
                        
                        # Try different selectors for the price
                        price = None
                        for selector in [
                            ".//span[contains(@class, '_tyxjp1')]/span",
                            ".//span[contains(@class, '_14y1gc')]/span",
                            ".//span[contains(@class, 'a8jt5op')]//span"
                        ]:
                            try:
                                price_elem = card.find_element(By.XPATH, selector)
                                price_text = price_elem.text.strip()
                                # Clean price text (remove currency symbol and extra text)
                                price = ''.join(filter(str.isdigit, price_text))
                                if price:
                                    break
                            except:
                                continue
                        
                        # Get the URL
                        url = ''
                        try:
                            link_elem = card.find_element(By.XPATH, ".//a")
                            url = link_elem.get_attribute('href')
                        except:
                            pass
                        
                        # Log and write data if both name and price were found
                        if name and price:
                            writer.writerow([name, price, url])
                            self.logger.info(f"Listing {i}: {name} - {price}")
                        else:
                            self.logger.warning(f"Listing {i}: Missing data - Name: {name}, Price: {price}")
                            
                    except Exception as e:
                        self.logger.error(f"Error processing listing {i}: {e}")
                
                self.logger.info(f"Completed extraction. Data saved to {csv_path}")
                
            except Exception as e:
                self.logger.error(f"Error extracting listings: {e}")
                self.driver.save_screenshot(os.path.join(self.output_dir, "extraction_error.png"))
    
    def closed(self, reason):
        self.logger.info(f"Spider closed: {reason}")
        if hasattr(self, 'driver'):
            self.driver.quit()

# Run the spider if script is executed directly
if __name__ == "__main__":
    process = CrawlerProcess({
        'USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })
    process.crawl(AirbnbSpider)
    process.start()