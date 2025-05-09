import asyncio
from playwright.async_api import async_playwright
import json
import logging
import sys
from datetime import datetime

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
        
    async def extract_comments(self, page):
        try:
            logger.info("Waiting for page to load...")
            await page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)
            
            logger.info("Scrolling to load comments...")
            for i in range(5):
                await page.evaluate("window.scrollBy(0, 500)")
                await asyncio.sleep(1)
                logger.info(f"Scroll {i+1}/5 completed")
            
            # Find all comments
            comments = await page.query_selector_all("div[data-e2e='comment-item'], div[class*='CommentItem']")
            logger.info(f"Found {len(comments)} comments")
            
            for index, comment in enumerate(comments, 1):
                try:
                    # Extract text
                    text_el = await comment.query_selector("p[dir='auto'], span[class*='comment-text'], span[class*='DivComment']")
                    if not text_el:
                        logger.warning(f"No text found for comment {index}")
                        continue
                        
                    text = await text_el.inner_text()
                    logger.debug(f"Comment {index} text: {text[:50]}...")
                    
                    # Extract username
                    username_el = await comment.query_selector("a[data-e2e*='comment-username-link'], a[class*='user-link'], a[class*='UserLink']")
                    username = await username_el.inner_text() if username_el else None
                    
                    # Extract likes
                    likes_el = await comment.query_selector("span[data-e2e*='like-count'], span[class*='like-count']")
                    likes = await likes_el.inner_text() if likes_el else "0"
                    
                    self.comments.append({
                        'text': text,
                        'author': username,
                        'likes': likes,
                        'scraped_at': datetime.now().isoformat()
                    })
                    
                    if index % 5 == 0:
                        logger.info(f"Processed {index}/{len(comments)} comments")
                    
                except Exception as e:
                    logger.error(f"Error extracting comment {index}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error during parsing: {str(e)}")
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
                        '--disable-blink-features=AutomationControlled'
                    ]
                )
                
                context = await browser.new_context(
                    viewport=None,
                    java_script_enabled=True,
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
                )
                
                page = await context.new_page()
                logger.info("Navigating to page...")
                
                try:
                    await page.goto(url, wait_until='domcontentloaded')
                    logger.info("Page loaded, extracting comments...")
                    await self.extract_comments(page)
                    
                    # Save results
                    output_file = 'comments.json'
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(self.comments, f, ensure_ascii=False, indent=2)
                    
                    logger.info(f"Successfully saved {len(self.comments)} comments to {output_file}")
                    
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
        url = "https://www.tiktok.com/@fch_achtzehn_46/video/7463516170193308950"
        await scraper.run(url)
    except Exception as e:
        logger.error(f"Script failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())