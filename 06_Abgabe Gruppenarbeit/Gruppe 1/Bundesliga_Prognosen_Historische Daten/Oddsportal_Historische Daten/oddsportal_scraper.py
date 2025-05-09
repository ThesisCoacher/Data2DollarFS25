import time
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urljoin
import random

def setup_driver():
    """
    Sets up the WebDriver for scraping.

    Returns:
        selenium.webdriver.Chrome: The configured WebDriver.
    """
    try:
        print("Setting up Chrome WebDriver...")
        service = ChromeService(executable_path=ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument('--headless') # Re-enable headless mode
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('window-size=1920x1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        driver = webdriver.Chrome(service=service, options=options)
        print("WebDriver setup complete.")
        wait = WebDriverWait(driver, 20)
        return driver, wait
    except WebDriverException as e:
        print(f"Error setting up WebDriver: {e}")
        return None, None
    except Exception as e:
        print(f"An unexpected error occurred during WebDriver setup: {e}")
        return None, None

def set_decimal_odds(driver, wait):
    """Attempts to set the odds format to Decimal on the current page."""
    try:
        print("  Attempting to set odds format to Decimal...")
        odds_format_button_xpath = "//div[p[text()='Odds formats:']]/following-sibling::div[contains(@class, 'group')]/button"
        decimal_odds_option_xpath = "//div[contains(@class, 'dropdown-content')]//a[contains(span, 'Decimal Odds')]"

        odds_format_button = wait.until(EC.element_to_be_clickable((By.XPATH, odds_format_button_xpath)))
        if "Decimal Odds" not in odds_format_button.text:
            driver.execute_script("arguments[0].click();", odds_format_button) # JS click needed for potential overlays
            print("    Clicked odds format button.")
            time.sleep(0.5) # Brief pause for dropdown
            decimal_option = wait.until(EC.element_to_be_clickable((By.XPATH, decimal_odds_option_xpath)))
            driver.execute_script("arguments[0].click();", decimal_option) # JS click
            print("    Selected 'Decimal Odds'.")
            time.sleep(2) # Wait for page to update odds
        else:
            print("    Odds format is already set to Decimal.")
    except TimeoutException:
        print("    Could not find or interact with the odds format selection menu.")
    except Exception as e:
        print(f"    Error setting odds format: {e}")

def scrape_season_pages(driver, wait):
    """Scrapes all pages for the currently loaded season, handling pagination."""
    season_matches_data = []
    current_page = 1
    last_valid_date = None # Reset for each season

    while True:
        print(f"    Scraping page {current_page}...")
        try:
            # --- Wait for results container and extract data ---
            results_container_selector = "div.min-h-\\[80vh\\]" # Escaped brackets
            match_row_selector = "div.eventRow"
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, results_container_selector)))
            time.sleep(random.uniform(1.5, 2.5)) # Wait for dynamic content loading within container

            match_rows = driver.find_elements(By.CSS_SELECTOR, match_row_selector)
            print(f"      Found {len(match_rows)} match rows using '{match_row_selector}' on page {current_page}.")

            if not match_rows and current_page == 1:
                 print("      No match rows found on the first page. Skipping season.")
                 break # Exit loop for this season if page 1 is empty
            elif not match_rows:
                 print("      No match rows found on this page, likely end of season pages.")
                 break # Exit loop if subsequent page is empty

            page_data = []
            for i, row in enumerate(match_rows):
                home_team, away_team, score, odds_1, odds_x, odds_2 = "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"
                match_date = "N/A" # Default date for the row
                try:
                    # Define selectors within the loop or ensure they are accessible
                    team_selector = "p.participant-name.truncate"
                    odds_selector = "div[data-testid='add-to-coupon-button'] p"
                    score_parent_xpath = ".//div[contains(@class, 'text-gray-dark')]//div[@data-v-a4e7076e and contains(@class, 'font-bold')]" # XPath for parent of score parts
                    score_digit_xpath = "./div[@data-v-a4e7076e]" # XPath for score digits relative to parent
                    date_selector = "div.text-black-main.font-main.w-full.truncate.text-xs.font-normal.leading-5" # Selector for date

                    # Date Extraction (with carry-forward logic)
                    try:
                        date_element = row.find_element(By.CSS_SELECTOR, date_selector)
                        current_row_date = date_element.text.strip()
                        if current_row_date and current_row_date != "N/A":
                            last_valid_date = current_row_date
                            match_date = current_row_date
                        elif last_valid_date:
                            match_date = last_valid_date
                    except NoSuchElementException:
                        if last_valid_date:
                            match_date = last_valid_date

                    # Team Names
                    teams = row.find_elements(By.CSS_SELECTOR, team_selector)
                    if len(teams) >= 2:
                        home_team = teams[0].text.strip()
                        away_team = teams[1].text.strip()

                    # Score - Two-step approach
                    score_elements = []
                    try:
                        score_parent_element = row.find_element(By.XPATH, score_parent_xpath)
                        score_elements = score_parent_element.find_elements(By.XPATH, score_digit_xpath)
                    except NoSuchElementException:
                        pass

                    if len(score_elements) >= 2:
                        score = f"{score_elements[0].text.strip()}-{score_elements[1].text.strip()}"
                    elif len(score_elements) == 1:
                        score = score_elements[0].text.strip()
                    else:
                        score = "N/A"

                    # Prepend with ' to force text format in CSV
                    if isinstance(score, str) and '-' in score and not score.startswith("N/A"):
                        score_for_csv = f"'{score}"
                    else:
                        score_for_csv = score

                    # Odds
                    odds_elements = row.find_elements(By.CSS_SELECTOR, odds_selector)
                    valid_odds = [o.text.strip() for o in odds_elements if o.text.strip() and o.text.strip() != '-']
                    if len(valid_odds) >= 3:
                        odds_1, odds_x, odds_2 = valid_odds[0], valid_odds[1], valid_odds[2]
                    else:
                        odds_1, odds_x, odds_2 = "N/A", "N/A", "N/A"

                    # Append Data
                    if home_team != "N/A" and away_team != "N/A":
                        page_data.append({
                            "Date": match_date,
                            "Home Team": home_team,
                            "Away Team": away_team,
                            "Score": score_for_csv,
                            "Odds_1": odds_1,
                            "Odds_X": odds_x,
                            "Odds_2": odds_2
                        })

                except Exception as e:
                     print(f"        Error processing row {i}: {e}")
                     # Optionally add placeholder data for the failed row
                     page_data.append({"Date": "ERROR", "Home Team": f"Row {i} Error", "Away Team": str(e), "Score": "ERROR", "Odds_1": "N/A", "Odds_X": "N/A", "Odds_2": "N/A"})

            season_matches_data.extend(page_data)
            print(f"      Successfully parsed {len(page_data)} matches from page {current_page}.")

            # --- Click 'Next' button --- 
            try:
                next_button_xpath = "//a[contains(@class, 'pagination-link') and contains(text(), 'Next')]"
                next_button = driver.find_element(By.XPATH, next_button_xpath)

                # Scroll into view if necessary and click using JavaScript
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(0.5)
                # Use JavaScript click to potentially avoid interception issues
                driver.execute_script("arguments[0].click();", next_button)
                print("    Clicked 'Next' button.")
                current_page += 1
                time.sleep(random.uniform(2, 4)) # Wait for next page to load
            except NoSuchElementException:
                print("    'Next' button not found or not clickable. Reached the last page for this season.")
                break # Exit pagination loop for the current season
            except Exception as e:
                print(f"    Error clicking 'Next' button: {e}. Stopping pagination for this season.")
                break
        except TimeoutException:
             print(f"    Timeout waiting for container on page {current_page}. Skipping rest of season.")
             break
        except Exception as e:
            print(f"    Error scraping page {current_page}: {e}")
            # Decide whether to break or continue to next page attempt
            # For now, let's break to avoid potential infinite loops on errors
            print(f"    Stopping scraping for this season due to error on page {current_page}.")
            break

    return season_matches_data

def scrape_oddsportal_results(url):
    """
    Scrapes match results and 1x2 odds for a given Oddsportal results URL,
    handling pagination.

    Args:
        url (str): The URL of the Oddsportal results page (e.g., for a specific season).

    Returns:
        pandas.DataFrame: DataFrame with Home Team, Away Team, Score, Odds_1, Odds_X, Odds_2.
    """
    all_matches_data = []
    page_num = 1
    last_valid_date = None # Variable to store the last encountered valid date

    # --- Setup Selenium WebDriver ---
    driver, wait = setup_driver()
    if not driver:
        return pd.DataFrame()

    # --- Navigate, Scrape, and Paginate ---
    current_page = 1
    try:
        print(f"Navigating to {url}...")
        driver.get(url)

        # --- Handle Consent/Cookie Banner (Example) ---
        try:
            consent_button_xpath = "//button[contains(., 'Consent') or contains(., 'Agree') or contains(., 'Accept') or @id='onetrust-accept-btn-handler']"
            consent_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, consent_button_xpath)))
            consent_button.click()
            print("Clicked consent button.")
            time.sleep(1)
        except TimeoutException:
            print("No consent button found or needed.")
        except Exception as e:
            print(f"Error clicking consent button: {e}")

        # --- Set Odds Format to Decimal --- 
        set_decimal_odds(driver, wait)

        while True:
            print(f"Scraping page {current_page}...")

            # --- Wait for results container and extract data ---
            # Updated container selector:
            results_container_selector = "div.min-h-\\[80vh\\]" # Try again with escaped brackets
            # Updated row selector:
            match_row_selector = "div.eventRow"
            
            page_data = []
            try:
                # Wait for the main container to be present
                results_container = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, results_container_selector)))
                # Add a wait for at least one event row to be present within the container
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, f"{results_container_selector} {match_row_selector}")))
                time.sleep(1) # Allow rows to render within

                # Find rows using the correct selector within the container
                match_rows = results_container.find_elements(By.CSS_SELECTOR, match_row_selector)

                print(f"  Found {len(match_rows)} match rows using '{match_row_selector}' on page {current_page}.")

                for i, row in enumerate(match_rows):
                    home_team, away_team, score, odds_1, odds_x, odds_2 = "N/A", "N/A", "N/A", "N/A", "N/A", "N/A"
                    match_date = "N/A" # Default date for the row
                    try:
                        # --- Use updated selectors from user feedback ---
                        team_selector = "p.participant-name.truncate"
                        odds_selector = "div[data-testid='add-to-coupon-button'] p"
                        # score_parts_selector = "div.text-gray-dark div[data-v-a4e7076e].font-bold > div[data-v-a4e7076e]" # Old selector
                        # score_parts_selector = "div[data-v-a4e7076e].min-mt\:\!flex.hidden.text-red-dark.font-bold" # Try single backslash escape - FAILED
                        # score_parts_xpath = "//div[contains(@class, 'text-red-dark') and contains(@class, 'font-bold') and @data-v-a4e7076e]" # XPath for score parts - Absolute (Failed)
                        # score_parts_xpath = ".//div[contains(@class, 'text-red-dark') and contains(@class, 'font-bold') and @data-v-a4e7076e]" # Relative XPath for score parts (Failed)
                        score_parent_xpath = ".//div[contains(@class, 'text-gray-dark')]//div[@data-v-a4e7076e and contains(@class, 'font-bold')]" # XPath for parent of score parts
                        score_digit_xpath = "./div[@data-v-a4e7076e]" # XPath for score digits relative to parent
                        date_selector = "div.text-black-main.font-main.w-full.truncate.text-xs.font-normal.leading-5" # New selector for date


                        teams = row.find_elements(By.CSS_SELECTOR, team_selector)
                        odds_elements = row.find_elements(By.CSS_SELECTOR, odds_selector)
                        # --- Date Extraction (with carry-forward logic) ---
                        try:
                            date_element = row.find_element(By.CSS_SELECTOR, date_selector)
                            current_row_date = date_element.text.strip()
                            if current_row_date and current_row_date != "N/A": # Check if it's a valid new date string
                                last_valid_date = current_row_date # Update last known date
                                match_date = current_row_date # Use the new date for this row
                            elif last_valid_date: # If current date is empty/N/A but we have a previous date
                                match_date = last_valid_date # Use the last valid date
                        except NoSuchElementException:
                            if last_valid_date: # If date element doesn't exist, use last valid date if available
                                match_date = last_valid_date
                        # --- End updated selectors ---

                        # Process Teams
                        if len(teams) >= 2:
                            home_team = teams[0].text.strip()
                            away_team = teams[1].text.strip()

                        # Process Score - Two-step approach
                        score_elements = [] # Initialize
                        try:
                            score_parent_element = row.find_element(By.XPATH, score_parent_xpath)
                            score_elements = score_parent_element.find_elements(By.XPATH, score_digit_xpath)
                        except NoSuchElementException:
                            pass # score_elements remains empty, will default to N/A

                        if len(score_elements) >= 2:
                            score = f"{score_elements[0].text.strip()}-{score_elements[1].text.strip()}"
                        elif len(score_elements) == 1: # Handle cases like postponed/cancelled?
                            score = score_elements[0].text.strip()
                            if score == '-': score = "N/A" # If score is just placeholder
                        else: # Try fallback if specific selector fails
                            try:
                                score_fallback = row.find_element(By.CSS_SELECTOR, ".event__score")
                                score = score_fallback.text.strip()
                            except NoSuchElementException:
                                score = "N/A"

                        # Prepend with ' to force text format in CSV if score is X-Y format
                        if isinstance(score, str) and '-' in score and not score.startswith("N/A"): # Check if it's a typical score format
                            score_for_csv = f"'{score}"
                        else:
                            score_for_csv = score # Keep N/A or other formats as is

                        # Process Odds
                        valid_odds = [o.text.strip() for o in odds_elements if o.text.strip() and o.text.strip() != '-']
                        if len(valid_odds) >= 3:
                            odds_1 = valid_odds[0]
                            odds_x = valid_odds[1]
                            odds_2 = valid_odds[2]
                        
                        # Basic validation (require teams)
                        if home_team != "N/A" and away_team != "N/A":
                            page_data.append({
                                "Date": match_date,
                                "Home Team": home_team,
                                "Away Team": away_team,
                                "Score": score_for_csv,
                                "Odds_1": odds_1,
                                "Odds_X": odds_x,
                                "Odds_2": odds_2
                            })
                        # else: 
                            # print(f"    Skipping row {i+1} due to missing teams.") # Debug

                    except StaleElementReferenceException:
                         print(f"    Stale element reference in row {i+1}. Skipping row.")
                         continue
                    except NoSuchElementException:
                         print(f"    Missing element during extraction in row {i+1}. Skipping row.") 
                         continue
                    except Exception as e:
                        print(f"    Error processing row {i+1}: {e}")
                        continue
                
                all_matches_data.extend(page_data)
                print(f"  Successfully parsed {len(page_data)} matches from page {current_page}.")

            except TimeoutException:
                print(f"Timeout waiting for results container ('{results_container_selector}') or rows within it on page {current_page}. Stopping.")
                break
            except Exception as e:
                print(f"Error scraping page {current_page}: {e}")
                break # Stop if scraping fails fundamentally on a page

            # --- Find and click 'Next' button using XPath ---
            next_button_xpath = "//a[contains(@class, 'pagination-link') and contains(text(), 'Next')]"
            try:
                next_button = wait.until(EC.element_to_be_clickable((By.XPATH, next_button_xpath)))
                
                # Scroll to button if needed and click
                driver.execute_script("arguments[0].scrollIntoView(true);", next_button)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", next_button) # JS click can be more robust
                print("Clicked 'Next' button.")
                current_page += 1
                time.sleep(3) # Wait for next page to load

            except TimeoutException:
                 print("'Next' button not found or not clickable. Reached the last page.")
                 break # Exit loop if no next button
            except Exception as e:
                print(f"Error clicking 'Next' button: {e}. Stopping.")
                break

    except Exception as e:
        print(f"An unexpected error occurred during the main scraping process: {e}")
    finally:
        # --- Cleanup ---
        if driver:
            try:
                print("Closing WebDriver...")
                driver.quit()
                print("WebDriver closed.")
            except Exception as e:
                print(f"Error closing WebDriver: {e}")

    # --- Finalize Data ---
    print("Scraping process finished.")
    if all_matches_data:
        # Define column order explicitly including Date
        column_order = ["Date", "Home Team", "Away Team", "Score", "Odds_1", "Odds_X", "Odds_2"]
        df = pd.DataFrame(all_matches_data)
        df = df[column_order] # Reorder columns
        return df
    else:
        print("No data was successfully scraped.")
        return pd.DataFrame()

# --- Main execution ---
if __name__ == "__main__":
    start_url = "https://www.oddsportal.com/football/germany/bundesliga/results/"
    all_seasons_data = []

    driver = None # Initialize driver variable
    try:
        driver, wait = setup_driver()

        print(f"Navigating to initial page: {start_url}")
        driver.get(start_url)
        time.sleep(2)

        # --- Handle Consent Button (once) --- 
        try:
            consent_button_id = "onetrust-accept-btn-handler"
            wait.until(EC.element_to_be_clickable((By.ID, consent_button_id))).click()
            print("Clicked consent button.")
            time.sleep(1)
        except TimeoutException:
            print("No consent button found or needed.")
        except Exception as e:
            print(f"Error clicking consent button: {e}")


        # --- Find Season Links --- 
        season_links = []
        try:
             season_container_xpath = "//div[contains(@class, 'flex-wrap') and contains(@class, 'gap-2') and contains(@class, 'py-3') and .//a[contains(@href, 'bundesliga')]]"
             print("Finding season links...")
             season_container = wait.until(EC.presence_of_element_located((By.XPATH, season_container_xpath)))
             links = season_container.find_elements(By.TAG_NAME, "a")
             for link in links:
                 season_name = link.text.strip()
                 href = link.get_attribute('href')
                 if season_name and href:
                     # Ensure URL is absolute
                     absolute_href = urljoin(driver.current_url, href)
                     season_links.append((season_name, absolute_href))
             print(f"Found {len(season_links)} season links.")
             # Optional: Reverse the order to scrape oldest first if desired
             # season_links.reverse()
        except TimeoutException:
             print("Could not find the season links container. Scraping only current page.")
             # Fallback: Use the start_url as the only "season"
             season_links.append(("Current Season", start_url))
        except Exception as e:
            print(f"Error finding season links: {e}. Scraping only current page.")
            season_links.append(("Current Season", start_url))


        # --- Loop Through Seasons --- 
        for season_name, season_url in season_links:
            print(f"\n--- Starting scraping for season: {season_name} --- ({season_url})")
            try:
                if driver.current_url != season_url:
                    print(f"  Navigating to season URL: {season_url}")
                    driver.get(season_url)
                    time.sleep(random.uniform(2, 4)) # Wait for page navigation
                else:
                    print("  Already on the correct season URL.")

                # Set odds format for this season
                set_decimal_odds(driver, wait)

                # Scrape all pages for this season
                season_data = scrape_season_pages(driver, wait)

                # Add season identifier to the data
                for match in season_data:
                     match['Season'] = season_name

                all_seasons_data.extend(season_data)
                print(f"--- Finished scraping for season: {season_name}. Found {len(season_data)} matches. ---")

                # Polite pause between seasons
                pause_duration = random.uniform(5, 10)
                print(f"Pausing for {pause_duration:.1f} seconds before next season...")
                time.sleep(pause_duration)

            except Exception as e:
                 print(f"!! Error scraping season {season_name}: {e}")
                 print(f"!! Skipping rest of season {season_name}.")
                 # Consider adding a longer pause or stopping if a season fails critically
                 time.sleep(5) # Pause even after error
                 continue # Move to the next season

    except Exception as e:
         print(f"A critical error occurred: {e}")
    finally:
         if driver:
            print("Closing WebDriver...")
            driver.quit()
            print("WebDriver closed.")

    # --- Finalize and Save All Data ---
    print("\nScraping process finished for all seasons.")
    if all_seasons_data:
        # Combine data into DataFrame
        results_df_oddsportal = pd.DataFrame(all_seasons_data)

        # Define final column order
        column_order = ["Season", "Date", "Home Team", "Away Team", "Score", "Odds_1", "Odds_X", "Odds_2"]
        # Ensure all columns exist, adding missing ones with N/A if necessary (though unlikely with this structure)
        for col in column_order:
            if col not in results_df_oddsportal.columns:
                results_df_oddsportal[col] = "N/A"
        results_df_oddsportal = results_df_oddsportal[column_order] # Reorder/select columns

        print("\n--- Combined Scraped Oddsportal Results Data (All Seasons) ---")
        # Optionally print head/tail instead of full df for large data
        # pd.set_option('display.max_rows', None)
        print(results_df_oddsportal.head())
        print("...")
        print(results_df_oddsportal.tail())
        print(f"Total matches scraped: {len(results_df_oddsportal)}")

        # Save the combined DataFrame to a new CSV file
        try:
            output_filename = 'oddsportal_bundesliga_results_odds_all_seasons.csv'
            results_df_oddsportal.to_csv(output_filename, index=False)
            print(f"\nData saved successfully to {output_filename}")
        except Exception as e:
            print(f"\nError saving combined data to CSV: {e}")
    else:
        print("No data was successfully scraped across all seasons.") 