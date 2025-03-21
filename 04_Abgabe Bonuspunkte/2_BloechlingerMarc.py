# Note: Ich habe nicht das gesamte scrapy Projekt hochgeladen, da es zu gross ist
# - dieses Skript ("airbnb_spider.py") ist der Hauptbestandteil des Projekts. LG Marc B.


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from time import sleep
import scrapy
from challenge2proj.items import AirbnbListingItem
from urllib.parse import urlparse, parse_qs

# how to run: scrapy crawl airbnb_spider -o listings.json

class AirbnbSpider(scrapy.Spider):
    name = "airbnb_spider"
    allowed_domains = ["airbnb.com"]
    
    source_links = [
    "https://www.airbnb.com/s/St.-Gallen/homes?refinement_paths%5B%5D=%2Fhomes&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2025-04-01&monthly_length=3&monthly_end_date=2025-07-01&price_filter_input_type=2&channel=EXPLORE&place_id=ChIJVdgzdikem0cRFGH-HwhQIpo&location_bb=Qj3P8kEW9sZCPZSjQRSqDQ%3D%3D&acp_id=dbe08aaf-a8e2-4a78-8b40-601f9f718efc&date_picker_type=calendar&checkin=2025-06-26&checkout=2025-06-29&source=structured_search_input_header&search_type=autocomplete_click",
    "https://www.airbnb.com/s/St.-Gallen/homes?refinement_paths%5B%5D=%2Fhomes&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2025-04-01&monthly_length=3&monthly_end_date=2025-07-01&price_filter_input_type=2&channel=EXPLORE&place_id=ChIJVdgzdikem0cRFGH-HwhQIpo&acp_id=dbe08aaf-a8e2-4a78-8b40-601f9f718efc&date_picker_type=calendar&checkin=2025-10-09&checkout=2025-10-19&source=structured_search_input_header&search_type=filter_change&query=St.%20Gallen&search_mode=regular_search&price_filter_num_nights=3"
    ]

    start_urls = source_links

    items_per_url = 60  # Target number of listings per URL
    max_pages_per_url = 4  # Safety limit to avoid endless pagination
    
    # Dictionary to track listings per URL
    listings_count = {}
    current_page = {}
    
    FEED_FORMAT = "json"
    FEED_URI = "listings.json"

    # clear content of listings.json
    open("listings.json", "w").close()
    
    # Define listing selectors for different possible Airbnb layouts
    listing_selectors = [
        "div[itemprop='itemListElement']",
        "div[data-testid='card-container']",
        "div.c4mnd7m",
        "div.cy5jw6o",
        "div.c1l1h97y",
        "div.gsgwcjk",
        "div._8ssblpx"
    ]

    def __init__(self):
        super().__init__()
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        # More realistic browser settings
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # More realistic user agent
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36'})
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.driver.set_page_load_timeout(30)

    def get_base_url(self, url):
        """Extract base URL without query parameters to track pagination properly"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

    def parse(self, response):
        # Use base URL as key for tracking
        base_url = self.get_base_url(response.url)
        
        # Initialize counters for this URL if not already set
        if base_url not in self.listings_count:
            self.listings_count[base_url] = 0
            self.current_page[base_url] = 1
        
        # Check if we've already reached our target for this URL
        if self.listings_count[base_url] >= self.items_per_url:
            self.logger.info(f"Already reached target of {self.items_per_url} listings for {base_url}")
            # Move to next source URL if available
            return self._process_next_source_url(response.url)
        
        self.driver.get(response.url)
        sleep(2)
        
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        sleep(1)
        
        rendered_html = self.driver.page_source
        sel = scrapy.Selector(text=rendered_html)
        
        # Track if we need to stop processing this URL
        should_stop = False
        
        # Process listings using your existing selectors
        for selector in self.listing_selectors:
            if should_stop:
                break
                
            listings = sel.css(selector)
            self.logger.info(f"URL: {response.url}, Page: {self.current_page[base_url]}, Selector: {selector}, Found: {len(listings)} listings")
            
            if listings:
                for listing in listings:
                    # Check if we've reached our target
                    if self.listings_count[base_url] >= self.items_per_url:
                        self.logger.info(f"Reached target of {self.items_per_url} listings for {base_url}")
                        should_stop = True
                        break
                    
                    # Extract title and price
                    title = (
                        listing.css("div[data-testid='listing-card-title']::text").get() or
                        listing.css("div.t1jojoys::text").get() or
                        listing.css("span[itemprop='name']::text").get() or
                        listing.css("div.mj1o7ki::text").get() or
                        "Title not found"
                    )
                    
                    price = (
                        listing.css("span._hb913q::text").get() or
                        listing.css("span.a8jt5op::text").get() or
                        listing.css("._1qgfaxb1 span::text").get() or
                        listing.css("span[data-testid='price-and-total']::text").get() or
                        "Price not found"
                    )
                    
                    item = AirbnbListingItem()
                    item["title"] = title.strip() if isinstance(title, str) else "Title not found"
                    item["price"] = price.strip() if isinstance(price, str) else "Price not found"
                    
                    # Increment counter only if actual data was found
                    if "not found" not in item["title"] and "not found" not in item["price"]:
                        self.listings_count[base_url] += 1
                        yield item  # Only yield if we're counting it
                
                # Break after finding listings with first working selector
                break
        
        # If we should stop, move to the next source URL
        if should_stop:
            return self._process_next_source_url(response.url)
        
        # Otherwise check if we need to paginate for this URL
        if self.listings_count[base_url] < self.items_per_url and self.current_page[base_url] < self.max_pages_per_url:
            try:
                next_button = self.driver.find_element(By.CSS_SELECTOR, "a[aria-label='Next']")
                if next_button:
                    next_url = next_button.get_attribute('href')
                    if next_url:
                        self.current_page[base_url] += 1
                        self.logger.info(f"Pagination: {self.current_page[base_url]} for {base_url}")
                        sleep(1)
                        yield scrapy.Request(url=next_url, callback=self.parse)
                    else:
                        self.logger.info(f"No href found in next button for {response.url}")
                        return self._process_next_source_url(response.url)
            except Exception as e:
                self.logger.error(f"Error finding next page: {e}")
                return self._process_next_source_url(response.url)
        else:
            return self._process_next_source_url(response.url)

    def _process_next_source_url(self, current_url):
        """Helper method to process the next source URL if available"""
        self.logger.info(f"Completed URL {current_url} with {self.listings_count[self.get_base_url(current_url)]} listings")
        
        # Check if there are more source URLs to process
        current_index = self.source_links.index(current_url) if current_url in self.source_links else -1
        if current_index != -1 and current_index + 1 < len(self.source_links):
            next_source_url = self.source_links[current_index + 1]
            self.logger.info(f"Moving to next source URL: {next_source_url}")
            return scrapy.Request(url=next_source_url, callback=self.parse)
        return None

    def closed(self, reason):
        # First close the browser
        self.driver.quit()
        
        # Clean the JSON output
        self.clean_json_output('listings.json')
    
    def clean_json_output(self, filename):
        """Clean the JSON file by removing duplicate data and fixing JSON format issues"""
        try:
            # Read the current file
            with open(filename, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find first opening brace and keep everything from there
            start_pos = content.find('{')
            if (start_pos > 0):
                content = content[start_pos:]
            
            # Fix duplicate data issue - look for duplicate sets of listings
            # First, find any invalid patterns like "][" which indicate duplicates
            if "][" in content:
                # Split at this boundary
                parts = content.split("][")
                # Keep only the first part and add closing bracket
                content = parts[0] + "]"
                
            # Remove any standalone "]" lines that aren't properly part of JSON structure
            lines = content.split('\n')
            cleaned_lines = [line for line in lines if line.strip() != "]" or line == lines[-1]]
            content = '\n'.join(cleaned_lines)
            
            # Ensure the JSON is properly formatted by parsing and re-serializing
            try:
                import json
                data = json.loads(content)
                # Remove duplicate entries
                unique_data = []
                seen = set()
                for item in data:
                    item_hash = hash(frozenset(item.items()))
                    if item_hash not in seen:
                        seen.add(item_hash)
                        unique_data.append(item)
                    
                # Limit to 100 entries
                if len(unique_data) > 100:
                    unique_data = unique_data[:100]
                    self.logger.info(f"Limited output to 100 entries (removed {len(data) - 100} entries)")
                    
                # Write back as properly formatted JSON
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(unique_data, f, indent=2)
                    
                self.logger.info(f"Successfully cleaned JSON output file: {filename}")

                
            except json.JSONDecodeError as e:
                # If there's a JSON parsing error, try a simpler approach
                self.logger.warning(f"JSON parsing error: {e}. Using fallback cleaning method.")
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
        except Exception as e:
            self.logger.error(f"Error cleaning JSON file: {e}")