import scrapy
import os
import glob
import pandas as pd
import time
import sys
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import chromedriver_autoinstaller


class GetGenderSpider(scrapy.Spider):
    name = "get_gender"
    allowed_domains = ["genderize.io"]
    start_urls = ["https://genderize.io"]

    def parse(self, response):
        pass


def setup_webdriver():
    """Set up a headless Chrome browser for scraping"""
    # Auto-install ChromeDriver
    chromedriver_autoinstaller.install()
    
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Create a new webdriver
    driver = webdriver.Chrome(options=chrome_options)
    
    return driver


def get_gender_web(name, driver):
    """Scrape genderize.io website to get gender and probability for a given name"""
    try:
        # Navigate to the site
        driver.get("https://genderize.io")
        
        # Find the input field
        input_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div/div/main/div[1]/div[1]/div/div/form/div/input"))
        )
        
        # Clear any existing text and enter the name
        input_field.clear()
        input_field.send_keys(name)
        
        # Find and click the search button
        search_button = driver.find_element(By.XPATH, "/html/body/div/div/main/div[1]/div[1]/div/div/form/button")
        search_button.click()
        
        # Wait for results to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div/div/main/div[1]/div[1]/div/p/b[2]"))
        )
        
        # Get gender and probability
        gender_element = driver.find_element(By.XPATH, "/html/body/div/div/main/div[1]/div[1]/div/p/b[2]")
        probability_element = driver.find_element(By.XPATH, "/html/body/div/div/main/div[1]/div[1]/div/p/b[3]")
        
        gender = gender_element.text.strip()
        probability = probability_element.text.strip()
        
        # Convert probability from string to float
        try:
            probability = float(probability)
        except ValueError:
            probability = None
            
        # Add a small delay to avoid overloading the site
        time.sleep(1)
        
        return gender, probability
    
    except TimeoutException:
        print(f"Timeout while processing name: {name}")
        time.sleep(2)  # Wait a bit longer on timeout
        return None, None
    except NoSuchElementException as e:
        print(f"Element not found for {name}: {e}")
        return None, None
    except Exception as e:
        print(f"Error getting gender for {name}: {e}")
        return None, None


def process_chunk(combined_df, start_idx, end_idx, output_file, driver=None):
    """Process a chunk of the dataframe and save progress"""
    # Initialize WebDriver if not provided
    if driver is None:
        driver = setup_webdriver()
    
    try:
        for i in range(start_idx, min(end_idx, len(combined_df))):
            if i % 5 == 0:
                print(f"Processing name {i+1}/{len(combined_df)}")
            
            try:
                vorname = combined_df.at[i, 'vorname']
                if pd.isnull(vorname) or not vorname:
                    print(f"Row {i} has no first name, skipping")
                    continue
                    
                name = str(vorname).split()[0]  # Take only the first name if multiple
                gender, probability = get_gender_web(name, driver)
                
                combined_df.at[i, 'gender'] = gender
                combined_df.at[i, 'gender_probability'] = probability
                
            except Exception as e:
                print(f"Error processing row {i}: {e}")
        
        # Save after processing the chunk
        combined_df.to_csv(output_file, index=False)
        print(f"Progress saved at index {end_idx}")
        return combined_df
    
    except Exception as e:
        print(f"Error in process_chunk: {e}")
        # Save progress before returning
        combined_df.to_csv(output_file, index=False)
        return combined_df


def main(start_index=1800):
    try:
        # Check if output file already exists
        output_file = "candidates_with_gender.csv"
        
        # Get all CSV files in the directory (excluding any potential output file)
        csv_files = [f for f in glob.glob("*.csv") if "candidates_" in f and "with_gender" not in f]
        print(f"Found {len(csv_files)} CSV files to process")
        
        # Initialize an empty list to store all dataframes
        all_dfs = []
        
        # Read and combine all CSV files
        for file in csv_files:
            try:
                df = pd.read_csv(file)
                print(f"Processing {file}: {len(df)} rows")
                all_dfs.append(df)
            except Exception as e:
                print(f"Error reading {file}: {e}")
        
        # Concatenate all dataframes into one
        if all_dfs:
            combined_df = pd.concat(all_dfs, ignore_index=True)
            print(f"Combined dataframe has {len(combined_df)} rows")
            
            # Check if output file already exists
            if os.path.exists(output_file):
                print(f"Found existing output file {output_file}, will continue from where we left off")
                existing_df = pd.read_csv(output_file)
                print(f"Existing file has {len(existing_df)} rows")
                
                # Copy existing data if the file structure matches
                if len(existing_df) <= len(combined_df):
                    # Add gender columns if they don't exist
                    if 'gender' not in combined_df.columns:
                        combined_df['gender'] = None
                    if 'gender_probability' not in combined_df.columns:
                        combined_df['gender_probability'] = None
                    
                    # Copy already processed gender data
                    for i in range(min(start_index, len(combined_df))):
                        if i < len(existing_df):
                            if 'gender' in existing_df.columns:
                                combined_df.at[i, 'gender'] = existing_df.at[i, 'gender']
                            if 'gender_probability' in existing_df.columns:
                                combined_df.at[i, 'gender_probability'] = existing_df.at[i, 'gender_probability']
                else:
                    print("Warning: Existing file has more rows than combined data, will create new file")
            else:
                # Add new columns for gender and probability
                combined_df['gender'] = None
                combined_df['gender_probability'] = None
            
            # Process each name starting from start_index
            total = len(combined_df)
            chunk_size = 10  # Process in smaller chunks for web scraping
            
            print(f"Starting to process names from index {start_index} out of {total}")
            
            # Create a persistent WebDriver
            driver = setup_webdriver()
            
            try:
                # Process in chunks
                current_start = start_index
                while current_start < total:
                    current_end = min(current_start + chunk_size, total)
                    print(f"Processing chunk from {current_start} to {current_end}")
                    
                    try:
                        combined_df = process_chunk(
                            combined_df, 
                            current_start, 
                            current_end, 
                            output_file,
                            driver
                        )
                        current_start = current_end
                    except KeyboardInterrupt:
                        print("\nProcess interrupted by user. Saving progress...")
                        combined_df.to_csv(output_file, index=False)
                        print(f"Progress saved at index {current_start}")
                        break
                    except Exception as e:
                        print(f"Error processing chunk: {e}")
                        # Save progress and move to next chunk
                        combined_df.to_csv(output_file, index=False)
                        current_start = current_end
            
            finally:
                # Close the browser
                try:
                    if driver:
                        driver.quit()
                except Exception:
                    pass
                
                # Save the final result to the CSV file
                combined_df.to_csv(output_file, index=False)
                print(f"Final results saved to {output_file}")
        else:
            print("No data to process")
    
    except Exception as e:
        print(f"An error occurred in the main process: {e}")

if __name__ == "__main__":
    try:
        # Allow specifying start index as command line argument
        if len(sys.argv) > 1:
            start_index = int(sys.argv[1])
        else:
            start_index = 1800
            
        main(start_index=start_index)
    except KeyboardInterrupt:
        print("\nScript terminated by user. Any saved progress is preserved in the output file.")
    except Exception as e:
        print(f"Fatal error: {e}")
