from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time
import json
from datetime import datetime
import re

def extract_price(text):
    """Extract price value from text containing CHF"""
    # Remove any spaces between digits and commas
    text = re.sub(r'(\d)\s+(\d)', r'\1\2', text)
    # Find all numbers in the text (including those with commas)
    matches = re.findall(r'CHF\s*([\d,]+)', text)
    if matches:
        # Take the first match and remove any commas
        price_str = matches[0].replace(',', '')
        try:
            return float(price_str)
        except ValueError:
            return None
    return None

def parse_page(driver, stay_length, waittime=3):
    results = []
    time.sleep(waittime)
    
    elements = driver.find_elements(By.CSS_SELECTOR, ".dir[data-testid]")
    for e in elements:
        try:
            id = e.get_dom_attribute("id")
            if id is not None and id.startswith("title_"):
                parent = e.find_element(By.XPATH, "./..")
                
                # Skip carousel items
                try:
                    carousel_parent = parent
                    is_carousel = False
                    while carousel_parent is not None:
                        label = carousel_parent.get_dom_attribute("aria-labelledby")
                        if label == "carousel-label":
                            is_carousel = True
                            break
                        carousel_parent = carousel_parent.find_element(By.XPATH, "./..")
                    if is_carousel:
                        continue
                except:
                    pass

                name = parent.find_element(By.CSS_SELECTOR, "[data-testid=listing-card-name]").text
                price = ""
                
                siblings = parent.find_elements(By.CSS_SELECTOR, ".dir")
                for s in siblings:
                    if "CHF" in s.text:
                        price = s.text.split(" ")[0]
                        break

                if name and price:
                    # The price we get is already per night, so no need to divide
                    price_value = float(''.join(filter(str.isdigit, price)))
                    results.append({
                        'name': name,
                        'price_per_night': f"CHF {price_value}"
                    })
        except:
            continue

    return results

def main():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 10)
    actions = ActionChains(driver)
    
    search_params = [
        {
            'checkin': '2025-06-26',
            'checkout': '2025-06-29',
            'nights': 3,
            'period': 'june'
        },
        {
            'checkin': '2025-10-09',
            'checkout': '2025-10-19',
            'nights': 10,
            'period': 'october'
        }
    ]
    
    all_results = {
        'june_listings': [],
        'october_listings': [],
        'scraped_date': datetime.now().isoformat()
    }
    
    try:
        for params in search_params:
            period_results = []
            
            url = (
                f"https://www.airbnb.ch/s/St.-Gallen--Schweiz/homes?"
                f"tab_id=home_tab&"
                f"checkin={params['checkin']}&"
                f"checkout={params['checkout']}&"
                f"source=structured_search_input_header&"
                f"search_type=filter_change"
            )
            
            driver.get(url)
            time.sleep(5)  # Initial page load wait
            
            print(f"Getting listings for {params['period']}")
            
            # Get first page results
            results = parse_page(driver, params['nights'], 5)
            period_results.extend(results)
            
            # Get next pages until we have enough listings
            page = 2
            while len(period_results) < 100 and page <= 6:
                try:
                    print(f"Processing page {page}")
                    
                    # Scroll to bottom of page first
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                    
                    # Scroll back up a bit to make sure the next button is in view
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight - 800);")
                    time.sleep(1)
                    
                    # Try to find the next button
                    next_button = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "[aria-label='Weiter']"))
                    )
                    
                    # Move to the button and click it
                    actions.move_to_element(next_button).perform()
                    time.sleep(1)
                    
                    # Try JavaScript click if regular click doesn't work
                    try:
                        next_button.click()
                    except:
                        driver.execute_script("arguments[0].click();", next_button)
                    
                    # Wait for new listings to load
                    time.sleep(3)
                    
                    results = parse_page(driver, params['nights'], 3)
                    period_results.extend(results)
                    page += 1
                    
                except Exception as e:
                    print(f"Error navigating to next page: {str(e)}")
                    break
            
            # Store results for this period
            if params['period'] == 'june':
                all_results['june_listings'] = period_results[:100]
            else:
                all_results['october_listings'] = period_results[:100]
                
            print(f"Collected {len(period_results[:100])} listings for {params['period']}")
            
            time.sleep(3)  # Add delay between periods
            
    except Exception as e:
        print(f"Error during scraping: {str(e)}")
    
    finally:
        driver.quit()
        
        # Save results to JSON file
        with open('stgallen_listings.json', 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        
        print("Results saved to stgallen_listings.json")

if __name__ == "__main__":
    main()