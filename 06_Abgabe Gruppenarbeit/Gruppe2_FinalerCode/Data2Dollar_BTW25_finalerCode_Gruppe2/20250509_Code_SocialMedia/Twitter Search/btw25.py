import asyncio
from twikit import Client
from datetime import datetime, timezone
import csv
import json
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

USERNAME = 'tag_btw25'
EMAIL = 'tag.bundes@web.de'
PASSWORD = 'Di2aufdie1'

PARTIES = {
    'Die_Gruenen': {'handle': 'Die_Gruenen', 'id': '14553288'},
    'CDU': {'handle': 'CDU', 'id': '20429858'},
    'SPD': {'handle': 'spdde', 'id': '26458162'},
    'AfD': {'handle': 'AfD', 'id': '844081278'},
    'FDP': {'handle': 'fdp', 'id': '39475170'},
    'dieLinke': {'handle': 'dieLinke', 'id': '44101578'}
}

# Set date range to a past period
START_DATE = datetime(2023, 12, 27, tzinfo=timezone.utc)
END_DATE = datetime(2024, 2, 23, tzinfo=timezone.utc)

# Create debug directory if it doesn't exist
debug_dir = 'debug_output'
os.makedirs(debug_dir, exist_ok=True)

def setup_driver(headless=False):
    """Setup and return a configured Chrome WebDriver"""
    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')  # Try to avoid detection
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("--window-size=1920,1080")  # Set a reasonable window size
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36")
    
    try:
        # Try to initialize with webdriver-manager
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.core.os_manager import ChromeType
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)
    except Exception as e:
        print(f"Error with ChromeDriverManager: {str(e)}")
        try:
            # If that fails, try to create driver with default behavior
            return webdriver.Chrome(options=options)
        except Exception as e:
            print(f"Error creating Chrome driver with default behavior: {str(e)}")
            # As a last resort, try Selenium Manager
            try:
                return webdriver.Chrome(options=options)
            except Exception as e:
                print(f"All Chrome driver initialization methods failed: {str(e)}")
                raise

async def safe_api_call(func, *args, **kwargs):
    """Wrapper for API calls with retries and error handling"""
    max_retries = 3
    retry_delay = 5
    last_error = None
    
    for attempt in range(max_retries):
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            last_error = e
            print(f"API call failed (attempt {attempt+1}/{max_retries}): {str(e)}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2
            else:
                print("All retry attempts failed")
    raise last_error

def process_tweet(tweet, party_name):
    """Process a tweet and extract relevant information"""
    tweet_data = {
        'party': party_name,
        'tweet_id': tweet.id,
        'created_at': tweet.created_at,
        'text': tweet.text,
        'favorite_count': getattr(tweet, 'favorite_count', 0),
        'retweet_count': getattr(tweet, 'retweet_count', 0),
        'reply_count': getattr(tweet, 'reply_count', 0),
        'quote_count': getattr(tweet, 'quote_count', 0),
        'bookmark_count': getattr(tweet, 'bookmark_count', 0),
        'view_count': getattr(tweet, 'view_count', 0),
        'lang': getattr(tweet, 'lang', ''),
        'is_quote': getattr(tweet, 'is_quote_status', False),
        'has_media': bool(getattr(tweet, 'media', [])),
        'urls': ','.join([u.get('expanded_url', '') for u in getattr(tweet, 'urls', [])]),
        'hashtags': ','.join(getattr(tweet, 'hashtags', [])),
        'conversation_id': getattr(tweet, 'conversation_id', ''),
        'possibly_sensitive': getattr(tweet, 'possibly_sensitive', False)
    }
    
    print(f"\nProcessed tweet from {tweet_data['created_at']}: {tweet_data['text'][:100]}...")
    return tweet_data

def login_to_twitter(driver):
    """Login to Twitter using Selenium"""
    try:
        print("Logging into Twitter web interface...")
        driver.get("https://twitter.com/i/flow/login")
        time.sleep(5)  # Wait longer for the page to load
        
        # Take a screenshot for debugging
        driver.save_screenshot(f"{debug_dir}/login_page.png")
        
        # Enter username/email
        try:
            # Wait for the username field - look for input field in the login form
            username_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']"))
            )
            username_input.send_keys(EMAIL)
            username_input.send_keys(Keys.RETURN)
            time.sleep(3)
        except Exception as e:
            print(f"Error entering username: {str(e)}")
            driver.save_screenshot(f"{debug_dir}/username_error.png")
            return False
        
        # Enter password
        try:
            # Wait for password field using a more specific selector
            password_input = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password']"))
            )
            password_input.send_keys(PASSWORD)
            password_input.send_keys(Keys.RETURN)
            time.sleep(5)
            
            # Check if we're successfully logged in by looking for the home icon
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[data-testid='AppTabBar_Home_Link']"))
                )
                print("Successfully logged into Twitter!")
                return True
            except:
                driver.save_screenshot(f"{debug_dir}/login_verification_failed.png")
                print("Login verification failed, may need to solve CAPTCHA or handle verification")
                return False
                
        except Exception as e:
            print(f"Error entering password: {str(e)}")
            driver.save_screenshot(f"{debug_dir}/password_error.png")
            return False
            
    except Exception as e:
        print(f"Error in Twitter login: {str(e)}")
        driver.save_screenshot(f"{debug_dir}/login_general_error.png")
        return False

def parse_tweet_date(date_str):
    """Parse Twitter date format to datetime object"""
    try:
        # Twitter dates are in format like "Wed Apr 09 13:51:17 +0000 2025"
        return datetime.strptime(date_str, "%a %b %d %H:%M:%S %z %Y")
    except Exception as e:
        print(f"Error parsing date '{date_str}': {str(e)}")
        return None

def scrape_tweets_from_profile(driver, party_name, party_handle):
    """Scrape tweets directly from Twitter profile page with improved selectors"""
    tweets = []
    processed_ids = set()
    scroll_count = 0
    max_scroll_attempts = 20
    
    try:
        # Navigate to profile
        profile_url = f"https://twitter.com/{party_handle}"
        driver.get(profile_url)
        print(f"Navigating to profile: {profile_url}")
        time.sleep(5)
        
        # Take screenshot for debugging
        driver.save_screenshot(f"{debug_dir}/{party_name}_profile.png")
        
        print("Checking if profile page loaded correctly...")
        
        # Check if we need to handle any prompts or overlays first
        try:
            # Look for common overlays and dismiss them
            overlays = driver.find_elements(By.CSS_SELECTOR, "div[role='dialog']")
            if overlays:
                print(f"Found {len(overlays)} potential overlays, attempting to dismiss")
                for overlay in overlays:
                    try:
                        # Look for dismiss buttons
                        dismiss_buttons = overlay.find_elements(By.CSS_SELECTOR, "div[role='button']")
                        for button in dismiss_buttons:
                            try:
                                if "Not now" in button.text or "Skip" in button.text or "Close" in button.text:
                                    button.click()
                                    print("Dismissed overlay")
                                    time.sleep(1)
                                    break
                            except:
                                pass
                    except:
                        pass
        except:
            pass
        
        # Wait for tweets to load
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='cellInnerDiv']"))
            )
        except:
            print("Could not find tweet containers")
            
        # Keep scrolling and collecting tweets until we have enough or reach our limit
        while scroll_count < max_scroll_attempts:
            scroll_count += 1
            print(f"Scroll attempt #{scroll_count}...")
            
            # Find all tweet containers
            tweet_containers = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='cellInnerDiv']")
            if not tweet_containers:
                print(f"No tweet containers found on {party_name}'s profile page")
                
                # Try alternative selector
                tweet_containers = driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
                if not tweet_containers:
                    print(f"No tweet articles found either. Taking screenshot for debugging.")
                    driver.save_screenshot(f"{debug_dir}/{party_name}_no_tweets.png")
                    
                    # One more try with a different approach
                    tweet_containers = driver.find_elements(By.XPATH, "//div[contains(@class, 'tweet')]")
                    if not tweet_containers:
                        if scroll_count > 5:
                            break
                        else:
                            # Scroll and try again
                            driver.execute_script("window.scrollTo(0, window.scrollY + 1000);")
                            time.sleep(3)
                            continue
            
            print(f"Found {len(tweet_containers)} potential tweet containers")
                
            # Process each tweet container
            new_tweets_found = 0
            for container in tweet_containers:
                try:
                    # Look for the actual tweet article within the container
                    tweet_articles = container.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
                    if not tweet_articles:
                        continue
                    
                    for tweet_el in tweet_articles:
                        try:
                            # Extract tweet data
                            tweet_id = None
                            
                            # Find all links and look for status links
                            links = tweet_el.find_elements(By.TAG_NAME, "a")
                            for link in links:
                                try:
                                    href = link.get_attribute("href")
                                    if href and "/status/" in href:
                                        tweet_id = href.split("/status/")[1].split("?")[0].split("/")[0]
                                        break
                                except:
                                    continue
                            
                            if not tweet_id or tweet_id in processed_ids:
                                continue
                                
                            processed_ids.add(tweet_id)
                            new_tweets_found += 1
                            
                            # Get tweet text
                            text = ""
                            try:
                                # Try to find the text element
                                text_el = tweet_el.find_element(By.CSS_SELECTOR, "div[data-testid='tweetText']")
                                text = text_el.text
                            except:
                                # Try alternative approach
                                try:
                                    paragraphs = tweet_el.find_elements(By.TAG_NAME, "span")
                                    text_parts = []
                                    for p in paragraphs:
                                        if p.text and len(p.text) > 5:  # Ignore short spans that might be metadata
                                            text_parts.append(p.text)
                                    text = " ".join(text_parts)
                                except:
                                    pass
                            
                            # Get timestamp
                            timestamp = None
                            date_str = ""
                            try:
                                time_els = tweet_el.find_elements(By.TAG_NAME, "time")
                                for time_el in time_els:
                                    datetime_attr = time_el.get_attribute("datetime")
                                    if datetime_attr:
                                        timestamp = datetime.fromisoformat(datetime_attr.replace("Z", "+00:00"))
                                        date_str = timestamp.strftime("%a %b %d %H:%M:%S %z %Y")
                                        break
                            except Exception as e:
                                print(f"Error parsing date: {str(e)}")
                            
                            # If we couldn't get a proper timestamp, try to get the text
                            if not timestamp:
                                try:
                                    time_spans = tweet_el.find_elements(By.XPATH, "//span[contains(text(), 'h') or contains(text(), 'd') or contains(text(), 'm')]")
                                    for span in time_spans:
                                        if span.text and (('h' in span.text) or ('d' in span.text) or ('m' in span.text)):
                                            date_str = span.text
                                            break
                                except:
                                    pass
                            
                            # For browser-scraped tweets, we might need to estimate dates from relative times
                            # For now, we'll collect all tweets and filter later
                            is_in_range = True
                            if timestamp:
                                is_in_range = START_DATE <= timestamp <= END_DATE
                            
                            if not is_in_range:
                                continue
                            
                            # Get engagement metrics
                            metrics = {
                                'favorite_count': 0,
                                'retweet_count': 0,
                                'reply_count': 0,
                                'quote_count': 0
                            }
                            
                            try:
                                # Look for engagement elements
                                engagement_group = tweet_el.find_elements(By.CSS_SELECTOR, "div[role='group']")
                                if engagement_group:
                                    for group in engagement_group:
                                        spans = group.find_elements(By.TAG_NAME, "span")
                                        for span in spans:
                                            text_content = span.get_attribute("innerHTML")
                                            if text_content:
                                                if "repl" in text_content.lower():
                                                    metrics['reply_count'] = extract_number_from_text(span.text)
                                                elif "retweet" in text_content.lower():
                                                    metrics['retweet_count'] = extract_number_from_text(span.text)
                                                elif "like" in text_content.lower():
                                                    metrics['favorite_count'] = extract_number_from_text(span.text)
                            except:
                                pass
                                
                            # Check for media
                            has_media = False
                            try:
                                media_els = tweet_el.find_elements(By.CSS_SELECTOR, "div[data-testid='tweetPhoto'], video, img")
                                has_media = len(media_els) > 0
                            except:
                                pass
                            
                            # Create tweet data dictionary
                            tweet_data = {
                                'party': party_name,
                                'tweet_id': tweet_id,
                                'created_at': date_str,
                                'text': text,
                                'favorite_count': metrics['favorite_count'],
                                'retweet_count': metrics['retweet_count'],
                                'reply_count': metrics['reply_count'],
                                'quote_count': metrics['quote_count'],
                                'bookmark_count': 0,
                                'view_count': 0,
                                'lang': 'de',  # Assuming German as default
                                'is_quote': False,
                                'has_media': has_media,
                                'urls': '',
                                'hashtags': extract_hashtags(text),
                                'conversation_id': tweet_id,
                                'possibly_sensitive': False
                            }
                            
                            tweets.append(tweet_data)
                            print(f"Scraped tweet {tweet_id[:8]}...: {text[:50]}{'...' if len(text) > 50 else ''}")
                            
                        except Exception as e:
                            print(f"Error processing tweet element: {str(e)}")
                except Exception as e:
                    print(f"Error processing container: {str(e)}")
            
            print(f"Found {new_tweets_found} new tweets in this scroll")
            
            # If we've processed a lot of tweets or haven't found any new ones in this iteration
            if len(processed_ids) > 200 or new_tweets_found == 0:
                if scroll_count > 3:  # Give it a few scrolls before giving up
                    print(f"Reached likely end of relevant tweets for {party_name}")
                    break
            
            # Scroll down to load more tweets
            try:
                # Try different scroll techniques
                if scroll_count % 3 == 0:
                    # Scroll to bottom
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                else:
                    # Scroll a fixed amount
                    driver.execute_script("window.scrollTo(0, window.scrollY + 2000);")
                
                # Take a screenshot after scrolling
                if scroll_count % 5 == 0:
                    driver.save_screenshot(f"{debug_dir}/{party_name}_scroll_{scroll_count}.png")
                
                # Wait for content to load
                time.sleep(3)
                
            except Exception as e:
                print(f"Error scrolling: {str(e)}")
    
    except Exception as e:
        print(f"Error scraping tweets for {party_name}: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Sort tweets by date if possible
    valid_tweets = []
    for tweet in tweets:
        try:
            if tweet['created_at'] and len(tweet['text']) > 0:
                valid_tweets.append(tweet)
        except:
            pass
    
    print(f"\nFound {len(valid_tweets)} valid tweets for {party_name}")
    return valid_tweets

def extract_number_from_text(text):
    """Extract number from text like '42K', '1.5M', etc."""
    if not text:
        return 0
        
    try:
        text = text.strip().replace(',', '')
        if 'K' in text:
            return int(float(text.replace('K', '')) * 1000)
        elif 'M' in text:
            return int(float(text.replace('M', '')) * 1000000)
        else:
            # Try to extract just the number
            num_match = re.search(r'\d+(\.\d+)?', text)
            if num_match:
                return int(float(num_match.group(0)))
            return 0
    except:
        return 0

def extract_hashtags(text):
    """Extract hashtags from tweet text"""
    if not text:
        return ''
        
    hashtags = re.findall(r'#(\w+)', text)
    return ','.join(hashtags)

async def fetch_party_tweets(client, party_name, party_info, driver):
    """Fetch all tweets for a party within the date range"""
    tweets = []
    
    try:
        print(f"\n{'='*50}")
        print(f"Fetching tweets for {party_name} (@{party_info['handle']})...")
        
        # Convert dates to ISO 8601 format for the API
        start_time = START_DATE.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_time = END_DATE.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        print(f"Fetching tweets from {start_time} to {end_time}")
        
        # First try with the API
        api_success = False
        try:
            # Try to get tweets using user_id
            print("\nFetching tweets using Twitter API...")
            user_tweets = await safe_api_call(
                client.get_user_tweets,
                user_id=party_info['id'],
                tweet_type='tweets'
            )
            
            if user_tweets:
                tweet_list = list(user_tweets)
                print(f"Retrieved {len(tweet_list)} tweets via API")
                
                for tweet in tweet_list:
                    try:
                        tweet_date = tweet.created_at_datetime
                        if START_DATE <= tweet_date <= END_DATE:
                            tweet_data = process_tweet(tweet, party_name)
                            tweets.append(tweet_data)
                    except Exception as e:
                        print(f"Error processing tweet: {str(e)}")
                        continue
                
                print(f"Found {len(tweets)} tweets in date range via API")
                if tweets:
                    api_success = True
        except Exception as e:
            print(f"Error getting user tweets via API: {str(e)}")
            
        # If API method didn't yield results, try direct browser scraping
        if not api_success:
            print("\nFalling back to direct browser scraping...")
            browser_tweets = scrape_tweets_from_profile(driver, party_name, party_info['handle'])
            tweets.extend(browser_tweets)
        
        print(f"\nTotal tweets found for {party_name}: {len(tweets)}")
        
    except Exception as e:
        print(f"Error fetching tweets for {party_name}: {str(e)}")
        import traceback
        print(traceback.format_exc())
    
    return tweets

async def main():
    client = Client('en-US')
    all_tweets = []
    
    try:
        print("Setting up Chrome WebDriver...")
        driver = setup_driver(headless=False)  # Use non-headless mode for better reliability
        
        print("Logging in to Twitter...")
        # First login using the browser
        login_success = login_to_twitter(driver)
        
        if not login_success:
            print("Browser login failed. Trying API login...")
        
        # Also try API login
        try:
            await client.login(
                auth_info_1=USERNAME,
                auth_info_2=EMAIL,
                password=PASSWORD,
                cookies_file='cookies.json'
            )
            print("Successfully logged in via API!")
        except Exception as e:
            print(f"API login failed: {str(e)}")
            
            # If both login methods failed, we can't proceed
            if not login_success:
                print("Both login methods failed. Cannot proceed with scraping.")
                driver.quit()
                return
        
        print(f"Fetching tweets from {START_DATE.strftime('%Y-%m-%d')} to {END_DATE.strftime('%Y-%m-%d')}")
        
        # Fetch tweets for each party
        for party_name, party_info in PARTIES.items():
            party_tweets = await fetch_party_tweets(client, party_name, party_info, driver)
            all_tweets.extend(party_tweets)
            
            # Save partial results
            if party_tweets:
                partial_csv = f'tweets_{party_name}.csv'
                fieldnames = party_tweets[0].keys()
                with open(partial_csv, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(party_tweets)
                print(f"Saved {len(party_tweets)} tweets to {partial_csv}")
            
            await asyncio.sleep(3)  # Delay between parties
        
        # Save all tweets to CSV
        if all_tweets:
            csv_filename = 'political_parties_tweets.csv'
            fieldnames = all_tweets[0].keys()
            
            with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(all_tweets)
            
            print(f"\nSuccessfully saved {len(all_tweets)} tweets to {csv_filename}")
        else:
            print("\nNo tweets found in the specified date range")
            
        # Clean up
        driver.quit()
            
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        print(traceback.format_exc())

if __name__ == '__main__':
    asyncio.run(main())