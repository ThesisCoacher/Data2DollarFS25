import time
import pandas as pd
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

def scrape_bundesliga_prognose_selenium(start_spieltag=1, end_spieltag=34):
    """
    Scrapes match predictions (ERG and PROG) for the Bundesliga 2024/25 season
    from bundesliga-prognose.de using Selenium for the specified range of matchdays.

    Args:
        start_spieltag (int): The first matchday to scrape.
        end_spieltag (int): The last matchday to scrape.

    Returns:
        pandas.DataFrame: A DataFrame containing the scraped match data,
                          including Spieltag, Date, Time, Home Team, Away Team,
                          Actual Result (ERG), and Predicted Result (PROG).
                          Returns an empty DataFrame if scraping fails.
    """
    base_url = "https://www.bundesliga-prognose.de/1/2024/{spieltag}/"
    all_matches_data = []

    # --- Setup Selenium WebDriver ---
    driver = None # Initialize driver to None
    try:
        print("Setting up Chrome WebDriver...")
        service = ChromeService(executable_path=ChromeDriverManager().install())
        options = webdriver.ChromeOptions()
        options.add_argument('--headless') # Run in background without opening a browser window
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
        driver = webdriver.Chrome(service=service, options=options)
        print("WebDriver setup complete.")
        wait = WebDriverWait(driver, 10) # Wait up to 10 seconds for elements
    except WebDriverException as e:
        print(f"Error setting up WebDriver: {e}")
        print("Please ensure Chrome is installed and accessible.")
        return pd.DataFrame()
    except Exception as e:
        print(f"An unexpected error occurred during WebDriver setup: {e}")
        return pd.DataFrame()


    print(f"Starting scraping from Spieltag {start_spieltag} to {end_spieltag}...")

    for spieltag in range(start_spieltag, end_spieltag + 1):
        url = base_url.format(spieltag=spieltag)
        print(f"Scraping Spieltag {spieltag}...", end='\r') # Use end='\r' to update line

        try:
            driver.get(url)
            time.sleep(0.5) # Reduced sleep time slightly

            # --- Find the relevant table ---
            target_table = None
            # print("  Attempting to find table...") # Debug line removed
            try:
                # Try finding the specific header first
                header_xpath = f"//*[contains(text(), 'Prognose 1. Bundesliga') and contains(text(), 'Saison') and contains(text(), 'am {spieltag}. Spieltag')]"
                # print(f"  Looking for header with XPath: {header_xpath}") # Debug line removed
                prognose_header = wait.until(EC.presence_of_element_located((By.XPATH, header_xpath)))
                # print("  Found header element.") # Debug line removed

                # New primary approach: Find first table *after* header that contains "PROG"
                # print("  Looking for first table after header containing 'PROG'...") # Debug line removed
                table_after_header_xpath = "following::table[.//th[normalize-space()='PROG'] | .//td[normalize-space()='PROG']][1]"
                target_table = prognose_header.find_element(By.XPATH, table_after_header_xpath)
                # print("  Found table after header containing 'PROG'.") # Debug line removed

            except (NoSuchElementException, TimeoutException):
                # print(f"  Could not find specific header OR table containing 'PROG' after header for Spieltag {spieltag}. Trying fallbacks...") # Debug line removed
                target_table = None # Ensure target_table is None before fallbacks

                # Fallback 1: Try the immediate next table, but verify it has "PROG"
                if 'prognose_header' in locals() and prognose_header: # Check if header was found before the exception
                    try:
                        # print("  Fallback 1: Checking immediate next table for 'PROG'...") # Debug line removed
                        potential_table = prognose_header.find_element(By.XPATH, "following::table[1]")
                        potential_table.find_element(By.XPATH, ".//th[normalize-space()='PROG'] | .//td[normalize-space()='PROG']")
                        target_table = potential_table
                        # print("  Fallback 1: Found immediate next table and it contains 'PROG'.") # Debug line removed
                    except (NoSuchElementException, TimeoutException):
                        # print("  Fallback 1: Immediate next table does not contain 'PROG'.") # Debug line removed
                        target_table = None

                # Fallback 2: Search the whole page if header wasn't found or Fallback 1 failed
                if not target_table:
                    try:
                        # print("  Fallback 2: Searching entire page for first table with 'PROG'...") # Debug line removed
                        fallback_xpath = "//table[.//th[normalize-space()='PROG'] | .//td[normalize-space()='PROG']][1]"
                        target_table = wait.until(EC.presence_of_element_located((By.XPATH, fallback_xpath)))
                        # print("  Fallback 2: Found table using global search for 'PROG'.") # Debug line removed
                    except (NoSuchElementException, TimeoutException):
                        print(f"\n  Error: Could not find any predictions table with 'PROG' for Spieltag {spieltag}. Skipping.")
                        time.sleep(0.5)
                        continue # Skip to the next spieltag

            if not target_table:
                 print(f"\n  Error: All attempts failed: Could not locate the target table for Spieltag {spieltag}. Skipping.")
                 time.sleep(0.5)
                 continue
            # else:
                 # print("  Successfully located target table.") # Debug line removed


            # --- Extract data from the table ---
            current_date_str = None
            # print("  Finding rows in the table...") # Debug line removed
            rows = target_table.find_elements(By.TAG_NAME, 'tr')
            # print(f"  Found {len(rows)} rows in the table.") # Debug line removed

            for i, row in enumerate(rows):
                cells = row.find_elements(By.TAG_NAME, 'td')
                # print(f"  Row {i+1}: Found {len(cells)} cells.") # Debug line removed
                if not cells:
                    # print(f"  Row {i+1}: Skipping header or empty row.") # Debug line removed
                    continue

                cell_texts = [cell.text.strip() for cell in cells]
                # print(f"  Row {i+1}: Cell texts: {cell_texts}") # Debug line removed

                # Try to parse date from the first cell
                first_cell_text = cell_texts[0]
                date_match = re.match(r"^\s*(\d{2}\.\d{2}\.\d{4})\s*$", first_cell_text)
                if date_match:
                    current_date_str = date_match.group(1)
                    # print(f"  Row {i+1}: Parsed date: {current_date_str}") # Debug line removed
                    if len(cells) < 8:
                        # print(f"  Row {i+1}: Identified as likely date-only row.") # Debug line removed
                        continue

                # Identify match rows (check specific indices for score pattern)
                if len(cell_texts) >= 8:
                    erg_text = cell_texts[6]
                    prog_text = cell_texts[7]

                    is_match_row = re.match(r"^\d+:\d+$|^:$", erg_text) and \
                                   re.match(r"^\d+:\d+$|^:$", prog_text)

                    if is_match_row:
                        # print(f"  Row {i+1}: Identified as match row by checking indices 6 and 7.") # Debug line removed
                        time_str = cell_texts[1] if len(cell_texts) > 1 else "N/A"
                        home_team = cell_texts[2] if len(cell_texts) > 2 else "N/A"
                        away_team = cell_texts[4].replace('- ', '') if len(cell_texts) > 4 else "N/A"
                        erg = erg_text if erg_text != ':' else 'N/A'
                        prog = prog_text if prog_text != ':' else 'N/A'

                        if current_date_str:
                            match_data = {
                                "Spieltag": spieltag,
                                "Date": current_date_str,
                                "Time": time_str,
                                "Home Team": home_team,
                                "Away Team": away_team,
                                "ERG": erg,
                                "PROG": prog
                            }
                            # print(f"  Row {i+1}: Extracted data: {match_data}") # Debug line removed
                            all_matches_data.append(match_data)
                        else:
                            # This might happen for the first match(es) if date row parsing fails or structure is odd
                            print(f"\n  Warning: Match found on Spieltag {spieltag} row {i+1} without preceding date.")
                    # else:
                        # print(f"  Row {i+1}: Did not match score pattern in cells at index 6 ('{erg_text}') and 7 ('{prog_text}').") # Debug line removed
                # else:
                    # print(f"  Row {i+1}: Skipping row, does not have >= 8 cells.") # Debug line removed

        except TimeoutException:
            print(f"\n  Error: Timeout waiting for elements on Spieltag {spieltag} page. Skipping.")
        except NoSuchElementException:
            print(f"\n  Error: Could not find expected elements on Spieltag {spieltag} page. Skipping.")
        except Exception as e:
            print(f"\n  An unexpected error occurred while processing Spieltag {spieltag}: {e}. Skipping.")

        # Small delay between requests - keep this to be polite to the server
        time.sleep(0.2)

    print("\nScraping finished.") # Add newline to clear the progress line

    # --- Cleanup ---
    if driver:
        try:
            print("Closing WebDriver...")
            driver.quit()
            print("WebDriver closed.")
        except Exception as e:
            print(f"Error closing WebDriver: {e}")


    # Convert the list of dictionaries to a pandas DataFrame
    if all_matches_data:
        df = pd.DataFrame(all_matches_data)
        return df
    else:
        print("No data was scraped.")
        return pd.DataFrame()

# --- Main execution ---
if __name__ == "__main__":
    # Make sure you have libraries installed: pip install selenium pandas webdriver-manager
    # --- Run for all Spieltage --- 
    results_df_selenium = scrape_bundesliga_prognose_selenium(start_spieltag=1, end_spieltag=34) # Scrape all 34 matchdays

    if not results_df_selenium.empty:
        print("\n--- Scraped Data (Selenium) ---")
        pd.set_option('display.max_rows', None) # Display all rows
        pd.set_option('display.max_columns', None) # Display all columns
        print(results_df_selenium.to_string())

        # --- Optional: Save to CSV ---
        try:
            output_filename = "bundesliga_prognosen_2024_2025_selenium.csv"
            results_df_selenium.to_csv(output_filename, index=False, encoding='utf-8-sig')
            print(f"\nData saved successfully to {output_filename}")
        except Exception as e:
            print(f"\nError saving data to CSV: {e}") 