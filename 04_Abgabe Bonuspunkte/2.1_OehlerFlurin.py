import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
import csv
import time
import random
from datetime import datetime
import os

class AbnbScraperA2Spider(scrapy.Spider):
    name = "ABnB_Scraper_A2"
    allowed_domains = ["airbnb.com"]
    
    def __init__(self):
        super(AbnbScraperA2Spider, self).__init__()
        
        # Setup Chrome options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--window-size=1920,1080")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        # Create CSV file with V8 in name
        self.output_dir = r"C:\Users\fluri\OneDrive\Desktop\D2D\airbnb_scraper\AirBnB_Advanced_Scraper"
        self.csv_filename = 'airbnb_listings_V8.csv'
        self.csv_path = os.path.join(self.output_dir, self.csv_filename)
        
        # Set to track unique listings
        self.scraped_listings = set()
        
        try:
            self.csv_file = open(self.csv_path, 'w', newline='', encoding='utf-8')
            self.csv_writer = csv.writer(self.csv_file)
            self.csv_writer.writerow(['Date Range', 'Location Name', 'Price per Night'])
            self.logger.info(f"CSV file created successfully at: {self.csv_path}")
        except Exception as e:
            self.logger.error(f"Error creating CSV file: {str(e)}")
            raise
        
        self.date_ranges = [
            {
                'start': '2025-06-26',
                'end': '2025-06-29',
                'description': '26.06.2025-29.06.2025'
            },
            {
                'start': '2025-10-09',
                'end': '2025-10-19',
                'description': '09.10.2025-19.10.2025'
            }
        ]

        # Updated XPaths and CSS selectors
        self.name_xpath = ".//span[@data-testid='listing-card-name']"
        self.price_xpath = ".//span[contains(@class, 'a8jt5op') and contains(text(), 'CHF')]"
        
        # Next button selectors
        self.next_button_css = "#site-content > div > div.pbmlr01.atm_h3_t9kd1m.atm_gq_n9wab5.dir.dir-ltr > div > div > div > nav > div > a.l1ovpqvx"
        self.next_button_xpaths = [
            "//a[contains(@class, 'l1ovpqvx')]",  # Class-based
            "//a[@aria-label='Next']",
            "//a[@aria-label='Weiter']",
            "//button[@aria-label='Next']",
            "//button[@aria-label='Weiter']",
            "//a[contains(@aria-label, 'next')]",
            "//a[contains(@aria-label, 'Next')]",
            "//a[.//path[@d='m12 4 11.3 11.3a1 1 0 0 1 0 1.4L12 28']]",
            "/html/body/div[5]/div/div/div[1]/div/div[3]/div[1]/main/div[2]/div/div[3]/div/div/div/nav/div/a[5]"
        ]
        self.container_xpath = "//div[@data-testid='card-container']"
        self.pagination_xpath = "//nav[@aria-label='Search results pagination']"
        
        # Maximum pages to scrape
        self.max_pages = 6

    def random_delay(self):
        """Add random delay between actions"""
        time.sleep(random.uniform(3, 5))  # Increased delay

    def wait_for_element(self, selector, by=By.XPATH, timeout=30):  # Increased timeout
        """Wait for an element with basic retry logic"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
            return element
        except TimeoutException:
            self.logger.error(f"Timeout waiting for element: {selector}")
            return None

    def wait_for_clickable(self, selector, by=By.XPATH, timeout=30):
        """Wait for an element to be clickable"""
        try:
            element = WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
            return element
        except TimeoutException:
            self.logger.error(f"Timeout waiting for clickable element: {selector}")
            return None

    def save_html(self, date_range, page_num):
        """Save the page HTML locally"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'airbnb_page_{date_range["description"]}_page{page_num}_{timestamp}.html'
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.driver.page_source)
        
        return filepath

    def start_requests(self):
        for date_range in self.date_ranges:
            url = (f"https://www.airbnb.com/s/St.-Gallen--Switzerland/homes?"
                  f"tab_id=home_tab&"
                  f"refinement_paths%5B%5D=%2Fhomes&"
                  f"flexible_trip_lengths%5B%5D=one_week&"
                  f"price_filter_input_type=0&"
                  f"checkin={date_range['start']}&"
                  f"checkout={date_range['end']}&"
                  f"source=structured_search_input_header&"
                  f"search_type=filter_change")
            
            yield scrapy.Request(
                url=url,
                callback=self.parse,
                meta={'date_range': date_range}
            )

    def scroll_to_bottom(self):
        """Scroll to bottom of page gradually"""
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # Scroll down gradually
            for i in range(3):
                self.driver.execute_script(f"window.scrollTo(0, {(i + 1) * last_height / 3});")
                time.sleep(1)
            
            # Wait for page to load
            time.sleep(2)
            
            # Calculate new scroll height and compare with last scroll height
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

    def click_next_page(self):
        """Click next page button with improved retry logic"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Store current listings before clicking
                current_listings = set(elem.text for elem in self.driver.find_elements(By.XPATH, self.name_xpath))
                
                # First try CSS selector
                try:
                    next_button = self.driver.find_element(By.CSS_SELECTOR, self.next_button_css)
                    if next_button and next_button.is_displayed() and next_button.is_enabled():
                        self.logger.info("Found next button using CSS selector")
                    else:
                        next_button = None
                except:
                    next_button = None

                # If CSS selector failed, try XPath alternatives
                if not next_button:
                    for xpath in self.next_button_xpaths:
                        try:
                            buttons = self.driver.find_elements(By.XPATH, xpath)
                            for button in buttons:
                                if button.is_displayed() and button.is_enabled():
                                    next_button = button
                                    self.logger.info(f"Found next button using XPath: {xpath}")
                                    break
                            if next_button:
                                break
                        except:
                            continue

                if not next_button:
                    self.logger.error("Next button not found with any selector")
                    return False

                # Scroll the button into view with offset
                self.driver.execute_script("""
                    arguments[0].scrollIntoView({block: 'center'});
                    window.scrollBy(0, -100);  // Scroll up slightly to avoid any overlays
                """, next_button)
                time.sleep(3)

                # Try multiple click methods
                click_successful = False
                
                # Method 1: JavaScript click with retry
                for _ in range(2):
                    try:
                        self.driver.execute_script("arguments[0].click();", next_button)
                        click_successful = True
                        break
                    except:
                        time.sleep(1)

                if not click_successful:
                    # Method 2: ActionChains click with move and pause
                    try:
                        actions = ActionChains(self.driver)
                        actions.move_to_element(next_button)
                        actions.pause(1)
                        actions.click()
                        actions.perform()
                        click_successful = True
                    except:
                        pass

                if not click_successful:
                    # Method 3: Regular click
                    try:
                        next_button.click()
                        click_successful = True
                    except:
                        pass

                if not click_successful:
                    raise Exception("All click methods failed")

                # Wait longer for page transition
                time.sleep(5)

                # Wait for new content and verify it's different
                if self.wait_for_element(self.container_xpath):
                    new_listings = set(elem.text for elem in self.driver.find_elements(By.XPATH, self.name_xpath))
                    if len(new_listings.difference(current_listings)) < 3:  # At least 3 new listings
                        self.logger.warning("Not enough new listings after navigation")
                        continue
                    
                    self.logger.info(f"Successfully navigated to next page, found {len(new_listings.difference(current_listings))} new listings")
                    return True

            except ElementClickInterceptedException:
                self.logger.warning(f"Click intercepted, retry {attempt + 1}/{max_retries}")
                time.sleep(3)
                continue
            except Exception as e:
                self.logger.error(f"Error clicking next page: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(3)
                continue
        
        return False

    def parse(self, response):
        date_range = response.meta['date_range']
        self.logger.info(f"Starting scraping for date range: {date_range['description']}")
        
        # Load the first page
        self.driver.get(response.url)
        self.random_delay()
        
        total_processed = 0
        page_num = 1
        results_this_date = 0
        
        while page_num <= self.max_pages:
            try:
                self.logger.info(f"Processing page {page_num} of {self.max_pages} for {date_range['description']}")
                
                # Wait for content and scroll
                if not self.wait_for_element(self.container_xpath):
                    self.logger.error(f"Could not find listing containers on page {page_num}")
                    break
                
                # Scroll through the page
                self.scroll_to_bottom()
                time.sleep(2)  # Additional wait after scrolling
                
                # Save HTML locally
                html_file = self.save_html(date_range, page_num)
                self.logger.info(f"Saved HTML for page {page_num} to: {html_file}")
                
                # Find all listing containers
                listing_containers = self.driver.find_elements(By.XPATH, self.container_xpath)
                container_count = len(listing_containers)
                self.logger.info(f"Found {container_count} listing containers on page {page_num}")
                
                if container_count == 0:
                    self.logger.error(f"No listing containers found on page {page_num}!")
                    break
                
                page_results = 0
                for listing in listing_containers:
                    # Check if we've reached 100 results for this date range
                    if results_this_date >= 100:
                        self.logger.info(f"Reached exactly 100 results for {date_range['description']}")
                        break

                    try:
                        # Get name
                        name_elem = listing.find_element(By.XPATH, self.name_xpath)
                        name = name_elem.text.strip()
                        
                        # Get price
                        price_elem = listing.find_element(By.XPATH, self.price_xpath)
                        price_text = price_elem.text.strip()
                        
                        self.logger.info(f"Found listing: {name} with price {price_text}")

                        # Create unique identifier including page number
                        listing_id = f"{name}_{price_text}_{date_range['description']}_page{page_num}"
                        
                        if listing_id in self.scraped_listings:
                            self.logger.info(f"Skipping duplicate listing: {name}")
                            continue
                        
                        if name and price_text and 'CHF' in price_text:
                            try:
                                # Extract price before "CHF"
                                price_parts = price_text.split('CHF')[0].strip()
                                price_clean = ''.join(c for c in price_parts if c.isdigit() or c == '.' or c == ' ')
                                price_final = price_clean.strip().split()[0]
                                price = float(price_final)
                                
                                if price > 10000:
                                    self.logger.warning(f"Unrealistic price detected: {price} CHF for {name}")
                                    continue
                                
                                self.scraped_listings.add(listing_id)
                                self.csv_writer.writerow([
                                    date_range['description'],
                                    name,
                                    f"{price:.2f}"
                                ])
                                self.csv_file.flush()
                                total_processed += 1
                                results_this_date += 1
                                page_results += 1
                                self.logger.info(f"Successfully scraped ({results_this_date} for this date range): {name} - CHF {price:.2f}")

                                # Check again after successful scrape
                                if results_this_date >= 100:
                                    self.logger.info(f"Reached exactly 100 results for {date_range['description']}")
                                    break
                            except (ValueError, IndexError) as e:
                                self.logger.warning(f"Invalid price format: {price_text} - Error: {str(e)}")
                                continue
                    
                    except NoSuchElementException as e:
                        self.logger.warning(f"Could not find element: {str(e)}")
                        continue
                    except Exception as e:
                        self.logger.error(f"Unexpected error: {str(e)}")
                        continue

                self.logger.info(f"Processed {page_results} listings on page {page_num} for {date_range['description']}")
                self.logger.info(f"Total results for this date range so far: {results_this_date}")

                # Break the outer loop if we've reached 100 results
                if results_this_date >= 100:
                    break

                # Continue to next page if we haven't reached max pages and haven't got enough results
                if page_num < self.max_pages and results_this_date < 100:
                    self.logger.info(f"Attempting to navigate to page {page_num + 1} for {date_range['description']}")
                    
                    # Additional wait before clicking next
                    time.sleep(2)
                    
                    if not self.click_next_page():
                        self.logger.info(f"Could not navigate to next page - ending pagination for {date_range['description']}")
                        break
                    
                    page_num += 1
                    self.random_delay()
                else:
                    if results_this_date >= 100:
                        self.logger.info(f"Reached target of 100 results for {date_range['description']}")
                    else:
                        self.logger.info(f"Reached max pages ({self.max_pages}) for {date_range['description']}")
                    break
                    
            except Exception as e:
                self.logger.error(f"Error processing page {page_num} for {date_range['description']}: {str(e)}")
                break

        self.logger.info(f"Finished processing {date_range['description']} - Total results: {results_this_date}")
        self.logger.info(f"Overall total processed so far: {total_processed}")

    def closed(self, reason):
        if hasattr(self, 'csv_file'):
            self.csv_file.close()
            self.logger.info("CSV file closed successfully")
        
        if hasattr(self, 'driver'):
            self.driver.quit()