# Siehe Public Repository von silvandario:
# https://github.com/silvandario/AirbnbAdvanced
# Idee
# Alles scrapen. Danach Kontrolle der CSV Datei. Bei fehlenden Preisen, diese nochmals scrapen.
# D.h. zeurst gtdata.py ausführen, dann get_remaining_data.py
# cleandata.py ist nicht mehr relevant, da in get_remaining_data.py integriert.

# -*- coding: utf-8 -*-
import time
import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import re


# Chrome START ###############################################################################################################

# Configure Chrome options
options = Options()
options.add_argument("--start-maximized")  # Start with browser maximized
options.add_argument("--disable-blink-features=AutomationControlled")  # Disable automation flag
options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
options.add_argument("--headless")  # Browser im Hintergrund laufen lassen

# Initialize the browser
driver = webdriver.Chrome(options=options)

# Modify navigator.webdriver flag to prevent detection
driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

# Chrome END ###############################################################################################################


# CSV File Start ###############################################################################################################

# Configure CSV file for output
print("Creating CSV file...")
csv_file = open('airbnb_listings_olm.csv', 'w', newline='', encoding='utf-8')
csv_writer = csv.writer(csv_file)
csv_writer.writerow(['Name', 'Preis', 'Link'])
print("CSV file created")

# Csv file for links
print("Creating CSV file for links...")
csv_file_links = open('airbnb_links.csv', 'w', newline='', encoding='utf-8')
csv_writer_links = csv.writer(csv_file_links)
csv_writer_links.writerow(['Link'])
print("CSV file for links created")

# CSV END ###############################################################################################################


# Main scraping logic ###############################################################################################################

try:
    # Navigate to the Airbnb search page
    print("Starting scraping process by loading search page...")
    # Fill in link with the link to the search page
    driver.get("https://www.airbnb.ch/s/St.-Gallen--Schweiz/homes?refinement_paths%5B%5D=%2Fhomes&place_id=ChIJVdgzdikem0cRFGH-HwhQIpo&checkin=2025-10-10&checkout=2025-10-19&adults=1&query=St.%20Gallen%2C%20Schweiz&flexible_trip_lengths%5B%5D=one_week&monthly_start_date=2025-04-01&monthly_length=3&monthly_end_date=2025-07-01&search_mode=regular_search&price_filter_input_type=2&price_filter_num_nights=3&channel=EXPLORE&search_type=filter_change&date_picker_type=calendar&source=structured_search_input_header")
    
    # Wait for the page to load
    print("Waiting for page to load...")
    time.sleep(5)
    print("10")
    time.sleep(5)
    print("5")
    time.sleep(5)
    print("Page loaded")
    
    
    # Main scraping loop
    page_num = 1
    listing_count = 0
    
    while page_num <= 6:  # Limit to x pages for testing (for 100 -> 6 x 18 offers)
        print(f"Processing page {page_num}")
        
        # Wait for listings to load
        if page_num > 1:
            time.sleep(15)
        
        # Alle cookies akzeptieren indem nach button mit Alle gesucht wird
        try:
            cookies_button = driver.find_element(By.XPATH, "//button[contains(., 'Alle akzeptieren')]")
            if cookies_button:
                cookies_button.click()
                time.sleep(2)
                print("Accepted cookies")
        except:
            print("No cookies button found")
            pass
        
        print("Collecting listing URLs...")
        time.sleep(2)
        
        # Zuerst listing URLS sammeln
        listing_urls = []
        
        # Find all links that might be listings
        #links = driver.find_elements(By.XPATH, "//body/div[@id='react-application']/div[@dir='ltr']/div[1]/div[1]/div[1]/div[3]/div[1]/main[1]/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/div[1]/div[2]/div[1]/div[2]/div[1]/div[1]/div[1]/div[1]/a[1]")
        # find links by <a rel="noopener noreferrer nofollow" target=...
        links = driver.find_elements(By.XPATH, "//a[@rel='noopener noreferrer nofollow']")


        # scroll down
        print("Scrolling down...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        for link in links:
            url = link.get_attribute("href")
            if url and "airbnb.ch/rooms/" in url and url not in listing_urls:
                listing_urls.append(url)
        
        print(f"Found {len(listing_urls)} potential listing URLs on page {page_num}")
        # write to csv
        for url in listing_urls:
            csv_writer_links.writerow([url])
            csv_file_links.flush()
        
        # Process each listing URL
        for url in listing_urls[:18]:  # Limit to first x listings per page for testing (18-> all)
            print(f"Processing listing URL: {url}")
            
            # Open URL in a new tab
            driver.execute_script(f"window.open('{url}');")
            time.sleep(5)
            
            # Switch to the new tab
            driver.switch_to.window(driver.window_handles[1])
            time.sleep(15)  # Wait for page to load
            
            # If there's a popup, close it
            try:
                popup_close_button = driver.find_element(By.XPATH, "//button[@aria-label='Schliessen']")
                if popup_close_button:
                    popup_close_button.click()
                    time.sleep(2)
                    print("Closed popup")
            except:
                print("No popup found")
                pass
            print("Extracting listing details...")
            # Extract listing details
            name = None
            price = None
            
            # Try to get listing name
            try:
                # <h1 tabindex="-1" class="hpipapi atm_7l_1kw7nm4 atm_c8_1x4eueo atm_cs_1kw7nm4 atm_g3_1kw7nm4 atm_gi_idpfg4 atm_l8_idpfg4 atm_kd_idpfg4_pfnrn2 i1pmzyw7 atm_9s_1nu9bjl dir dir-ltr" elementtiming="LCP-target">Charmante Altbauwohnung ruhig und doch zentral</h1>
                name_element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'hpipapi')]"))
                )
                name = name_element.text.strip()
                print(f"Found name: {name}")
                
                # GET PRICE
                price_element = WebDriverWait(driver, 1).until(
                    EC.visibility_of_element_located((By.XPATH, "(//span[contains(@class,'_18x3iiu')])[1]"))
                )
                
                print("Raw HTML price element:", price_element.get_attribute("innerHTML"))
                
                price = price_element.get_attribute("innerHTML").replace("&nbsp;", " ")
                
                
                print(f"Found price: {price}")
            except:
                print("Could not find listing name")
            
            # Output data to CSV
            if name or price:
                csv_writer.writerow([name, price, url])
                csv_file.flush()  # Ensure data is written immediately
                listing_count += 1
                print(f"Added listing #{listing_count} to CSV")
            
            # Close tab and return to main window
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
            time.sleep(2)
        
        # Try to go to the next page
        try:
            next_button = None
            
            # Scroll to the bottom of the page to reveal the next button
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            
            # Try different selectors for the next button
            next_button_selectors = [
                "//a[@aria-label='Weiter']",
                "//a[contains(., 'Weiter')]",
            ]
            
            for selector in next_button_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements and elements[0].is_displayed() and elements[0].is_enabled():
                        next_button = elements[0]
                        break
                except:
                    continue
            
            if next_button:
                print("Found next button, clicking...")
                next_button.click()
                time.sleep(7)  # Wait for the next page to load
                page_num += 1
            else:
                print("No next button found or it's disabled")
                break
        except Exception as e:
            print(f"Error navigating to next page: {str(e)}")
            break
    
    print(f"Scraping complete. Processed {page_num} pages and {listing_count} listings.")

except Exception as e:
    print(f"An error occurred: {str(e)}")

finally:
    # Clean up
    csv_file.close()
    driver.quit()
    print("Browser closed and CSV file saved.")
    


# Datei einlesen
df = pd.read_csv("airbnb_listings_olm.csv", names=["Name", "Preis", "Links"], skiprows=1)

# Funktion zur Bereinigung der Preisangaben
def clean_price(price):
    if isinstance(price, str):
        # Entferne HTML-Tags
        clean_text = re.sub(r'<.*?>', '', price).strip()
        # Extrahiere den reinen Preiswert vor dem "x"
        match = re.search(r'(\d+\s*CHF)', clean_text)
        if match:
            return match.group(1)  # Gibt nur den Preis mit "CHF" zurück
    return price

# "Preis" Spalte bereinigen
df["Preis"] = df["Preis"].apply(clean_price)

# Bereinigte Datei speichern
df.to_csv("airbnb_listings_olm_clean.csv", index=False)

print("Bereinigung abgeschlossen. Datei gespeichert als airbnb_clean.csv")

# Starten mit:
# caffeinate -i python getdata.py