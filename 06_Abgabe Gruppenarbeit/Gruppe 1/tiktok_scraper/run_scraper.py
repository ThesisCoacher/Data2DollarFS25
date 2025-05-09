import asyncio
from playwright.async_api import async_playwright
import json
import logging
import sys
from datetime import datetime
import os

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('scraper.log')
    ]
)
logger = logging.getLogger(__name__)

class TikTokScraper:
    def __init__(self):
        self.comments = []
        
    async def handle_cookie_banner(self, page):
        """Handle cookie consent banner if it appears"""
        try:
            # Updated selectors with German button text
            cookie_buttons = [
                "button:has-text('Optionale Cookies ablehnen')",
                "button:text('Optionale Cookies ablehnen')",
                "button:has-text('Decline optional cookies')",
                "button[data-e2e='cookie-banner-deny']",
                "button[data-e2e='modal-deny-button']"
            ]
            
            for button_selector in cookie_buttons:
                try:
                    # Wait longer for the cookie banner to appear and be clickable
                    cookie_button = await page.wait_for_selector(button_selector, timeout=10000, state="visible")
                    if cookie_button:
                        await cookie_button.click()
                        logger.info(f"Clicked cookie button with selector: {button_selector}")
                        await asyncio.sleep(3)
                        return True
                except Exception:
                    continue
                    
            logger.info("No cookie banner found with current selectors")
            return False
            
        except Exception as e:
            logger.warning(f"Error handling cookie banner: {str(e)}")
            return False

    async def wait_for_captcha(self, page):
        """Wait for manual captcha solving"""
        logger.info("Checking for captcha...")
        
        captcha_selectors = [
            "div[class*='captcha_verify']",
            "iframe[title*='captcha']",
            "div[class*='verify-bar']"
        ]
        
        for selector in captcha_selectors:
            try:
                if await page.query_selector(selector):
                    logger.info("⚠️ CAPTCHA detected! Please solve it manually...")
                    await page.wait_for_selector(selector, state="hidden", timeout=180000)  # 3 minutes
                    logger.info("Captcha appears to be solved!")
                    await asyncio.sleep(5)  # Wait longer after captcha
                    return True
            except Exception:
                continue
                
        return False

    async def wait_for_comments_to_load(self, page):
        """Wait for comments section to be fully loaded"""
        logger.info("Waiting for comments section to load...")
        try:
            await page.wait_for_selector("div[class*='CommentItem'], div[data-e2e='comment-item']", timeout=30000)
            return True
        except Exception as e:
            logger.error(f"Error waiting for comments: {str(e)}")
            return False

    async def click_comment_section(self, page):
        """Click to open the comments section if needed"""
        logger.info("Attempting to open comments section...")
        try:
            # Wait for the video page to be properly loaded
            await page.wait_for_selector('div[class*="DivVideoWrapper"]', timeout=10000)
            await asyncio.sleep(2)

            # Use exact button structure from the TikTok page
            button = await page.wait_for_selector('button[class*="css-1ok4pbl-ButtonActionItem"][aria-label*="Kommentare lesen oder hinzufügen"]', timeout=10000)
            
            if button:
                try:
                    # Try direct click
                    await button.click()
                except Exception:
                    # If direct click fails, try JavaScript click
                    await page.evaluate("(button) => button.click()", button)
                
                logger.info("Clicked comment button")
                await asyncio.sleep(3)
                
                # Verify comments are visible
                comment_list_selectors = [
                    'div[class*="DivCommentListContainer"]',
                    'div[class*="CommentScrollContainer"]',
                    'div[data-e2e="comment-list"]'
                ]
                
                for list_selector in comment_list_selectors:
                    if await page.query_selector(list_selector):
                        logger.info("Comment section is now visible")
                        return True
            
            # If button wasn't found, check if comments are already visible
            already_visible_selectors = [
                'div[class*="DivCommentListContainer"]',
                'div[class*="CommentScrollContainer"]',
                'div[data-e2e="comment-list"]'
            ]
            
            for selector in already_visible_selectors:
                if await page.query_selector(selector):
                    logger.info("Comments section was already visible")
                    return True

            logger.warning("Could not find or click comment button, and comments are not visible")
            return False
            
        except Exception as e:
            logger.error(f"Error opening comments section: {str(e)}")
            return False

    async def extract_comment_data(self, comment):
        """Extract data from a single comment"""
        try:
            # Get comment text - updated selectors for current TikTok structure
            text_selectors = [
                'p[class*="DivComment"] span',         # Main comment text
                'p[class*="comment-text"] span',       # Alternative text format
                'span[class*="comment-text"]',         # Direct text span
                '[data-e2e="comment-level-1"]'         # First level comments
            ]
            
            text = None
            for selector in text_selectors:
                try:
                    text_el = await comment.query_selector(selector)
                    if text_el:
                        text = await text_el.inner_text()
                        if text and text.strip():
                            break
                except Exception:
                    continue

            if not text or not text.strip():
                return None

            # Get username with updated selectors for new layout
            username_selectors = [
                'a[data-e2e="comment-username"]',          # New primary selector
                'a[data-e2e="comment-username-1"]',        # Alternate selector
                'div[class*="DivCommentItemHeader"] a',    # Header username
                'p[class*="AuthorTitle"] a',              # Author element
                'a[class*="UserLink"]',                   # Generic user link
            ]
            
            username = None
            for selector in username_selectors:
                try:
                    username_el = await comment.query_selector(selector)
                    if username_el:
                        username = await username_el.inner_text()
                        if username and username.strip():
                            break
                except Exception:
                    continue

            # Format the comment data
            comment_data = {
                'text': text.strip() if text else None,
                'author': username.strip() if username else 'Anonymous',
                'scraped_at': datetime.now().isoformat()
            }
            
            if comment_data['text']:
                logger.info(f"Extracted comment: {comment_data['text'][:50]}... by {comment_data['author']}")
                return comment_data
            return None

        except Exception as e:
            logger.error(f"Error extracting comment data: {str(e)}")
            return None

    async def scroll_to_load_comments(self, page):
        """Scroll gradually to load all comments"""
        logger.info("Starting to scroll for comments...")
        previous_comment_count = 0
        no_new_comments_count = 0
        max_attempts_without_new = 3
        total_scrolls = 0
        max_total_scrolls = 15

        # First locate the comment container
        container_selectors = [
            'div[class*="DivCommentListContainer"]',   # Primary container
            'div[class*="CommentList"]',               # Alternative container
            'div[data-e2e="comment-list"]'            # Data attribute container
        ]

        # Find the scrollable container
        container_selector = None
        for selector in container_selectors:
            try:
                container = await page.query_selector(selector)
                if container:
                    # Verify it's a comment container
                    comments = await container.query_selector_all('div[class*="DivCommentItem"], div[data-e2e="comment-item"], [data-e2e="comment-level-1"]')
                    if len(comments) > 0:
                        container_selector = selector
                        logger.info(f"Found comment container with selector: {selector}")
                        break
            except Exception:
                continue

        if not container_selector:
            logger.error("Could not find comment container")
            return 0

        # Scroll the container
        while total_scrolls < max_total_scrolls and no_new_comments_count < max_attempts_without_new:
            try:
                # More aggressive scrolling
                await page.evaluate(f"""() => {{
                    const container = document.querySelector('{container_selector}');
                    if (container) {{
                        // Scroll in steps
                        const currentScroll = container.scrollTop;
                        container.scrollTo({{
                            top: currentScroll + 1000,
                            behavior: 'smooth'
                        }});
                        // Also scroll window as fallback
                        window.scrollTo(0, document.body.scrollHeight);
                    }}
                }}""")
                
                await asyncio.sleep(2)

                # Count comments with updated selectors
                comments = await page.query_selector_all('div[class*="DivCommentItem"], div[data-e2e="comment-item"], [data-e2e="comment-level-1"]')
                current_count = len(comments)
                logger.info(f"Found {current_count} comments after scroll {total_scrolls + 1}")
                
                if current_count > previous_comment_count:
                    no_new_comments_count = 0
                    logger.info(f"Found {current_count - previous_comment_count} new comments")
                    await asyncio.sleep(1)
                else:
                    no_new_comments_count += 1
                    logger.info(f"No new comments found (attempt {no_new_comments_count}/{max_attempts_without_new})")
                
                previous_comment_count = current_count
                total_scrolls += 1

            except Exception as e:
                logger.warning(f"Error during scroll: {str(e)}")
                no_new_comments_count += 1

        return previous_comment_count

    async def save_comments(self, output_file='comments.json'):
        """Save comments with verification"""
        if not self.comments:
            logger.error("No comments to save!")
            return False
            
        try:
            # Ensure we have a valid path
            output_path = os.path.abspath(output_file)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save with pretty printing
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.comments, f, ensure_ascii=False, indent=2)
            
            # Verify the save
            if os.path.exists(output_path):
                with open(output_path, 'r', encoding='utf-8') as f:
                    saved_data = json.load(f)
                    if len(saved_data) == len(self.comments):
                        logger.info(f"Successfully saved {len(self.comments)} comments to {output_path}")
                        # Print first few comments as verification
                        for i, comment in enumerate(saved_data[:3]):
                            logger.info(f"Sample comment {i+1}: {comment['text'][:50]}...")
                        return True
                    else:
                        logger.error(f"Save verification failed! Found {len(saved_data)} comments in file but expected {len(self.comments)}")
                        return False
            else:
                logger.error(f"Failed to save comments! File {output_path} does not exist")
                return False
                
        except Exception as e:
            logger.error(f"Error saving comments: {str(e)}")
            return False

    async def extract_comments(self, page):
        try:
            logger.info("Waiting for page to load...")
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)
            
            # Handle cookie banner if present
            await self.handle_cookie_banner(page)
            
            # Check for and handle captcha
            await self.wait_for_captcha(page)
            
            # Wait for manually opened comments section
            logger.info("Waiting for comments to be visible (please open comments manually)...")
            comment_selectors = [
                "div[class*='CommentItem']", 
                "div[data-e2e='comment-item']", 
                "div[class*='DivCommentItemContainer']"
            ]
            
            comment_container_found = False
            for selector in comment_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=60000)  # Wait up to 1 minute
                    comment_container_found = True
                    logger.info("Comments are now visible!")
                    break
                except Exception:
                    continue

            if not comment_container_found:
                logger.error("Could not find visible comments! Please make sure comments are opened.")
                return
            
            # Scroll to load all comments
            total_comments = await self.scroll_to_load_comments(page)
            if total_comments == 0:
                logger.error("No comments found after scrolling!")
                return
            
            # Get all comments after scrolling is complete
            comments = await page.query_selector_all("div[data-e2e='comment-item'], div[class*='CommentItem'], div[class*='DivCommentItemContainer']")
            logger.info(f"Found {len(comments)} total comments")
            
            # Extract data from each comment
            self.comments = []  # Reset comments list before extraction
            for index, comment in enumerate(comments, 1):
                comment_data = await self.extract_comment_data(comment)
                if comment_data and comment_data['text']:  # Only add if we have valid text
                    self.comments.append(comment_data)
                    logger.info(f"Processed comment {index}: {comment_data['text'][:50]}...")
            
            logger.info(f"Successfully extracted {len(self.comments)} comments")
            
            # Save comments
            if self.comments:
                await self.save_comments('comments.json')
            else:
                logger.error("No valid comments were extracted to save!")
                
        except Exception as e:
            logger.error(f"Error during comment extraction: {str(e)}")
            raise

    async def run(self, url):
        logger.info(f"Starting scraper for URL: {url}")
        async with async_playwright() as p:
            try:
                logger.info("Launching browser...")
                browser = await p.chromium.launch(
                    headless=False,
                    args=[
                        '--no-sandbox',
                        '--disable-dev-shm-usage',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-site-isolation-trials'
                    ]
                )
                
                context = await browser.new_context(
                    viewport=None,
                    java_script_enabled=True,
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
                )
                
                page = await context.new_page()
                
                try:
                    await page.goto(url, wait_until='networkidle')  # Wait for network to be idle
                    await self.extract_comments(page)
                except Exception as e:
                    logger.error(f"Error during scraping: {str(e)}")
                    raise
                finally:
                    await context.close()
                    await browser.close()
                    
            except Exception as e:
                logger.error(f"Fatal error: {str(e)}")
                raise

async def main():
    try:
        scraper = TikTokScraper()
        url = "https://www.tiktok.com/@werderbremen/video/7497250601093451030"
        
        # Extract video ID from URL
        video_id = url.split('/')[-1]
        output_file = f'comments_{video_id}.json'
        
        await scraper.run(url)
        # Save to the specific output file
        await scraper.save_comments(output_file)
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())