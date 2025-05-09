import scrapy
from scrapy_playwright.page import PageMethod
from ..items import TiktokCommentItem
import logging

class TiktokCommentsSpider(scrapy.Spider):
    name = 'tiktok_comments'
    
    def __init__(self, *args, **kwargs):
        super(TiktokCommentsSpider, self).__init__(*args, **kwargs)
        self.start_urls = ["https://www.tiktok.com/@fch_achtzehn_46/video/7463516170193308950"]

    def start_requests(self):
        for url in self.start_urls:
            yield scrapy.Request(
                url,
                meta={
                    "playwright": True,
                    "playwright_include_page": True,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "domcontentloaded"),
                    ],
                    "errback": self.errback,
                },
                dont_filter=True
            )

    async def parse(self, response):
        page = response.meta["playwright_page"]
        
        try:
            # Wait for initial load
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(3000)

            # Scroll down to load comments
            for _ in range(3):
                await page.evaluate("window.scrollBy(0, 500)")
                await page.wait_for_timeout(1000)

            # Find comments container
            comments = await page.query_selector_all("div[data-e2e='comment-item'], div[class*='DivCommentItemContainer']")
            
            self.logger.info(f"Found {len(comments)} comments")

            for comment in comments:
                try:
                    # Extract text
                    text_el = await comment.query_selector("p[dir='auto'], span[class*='comment-text']")
                    if not text_el:
                        continue
                    
                    text = await text_el.inner_text()
                    
                    # Extract username
                    username_el = await comment.query_selector("a[data-e2e*='comment-username-link'], a[class*='user-link']")
                    username = await username_el.inner_text() if username_el else None

                    # Extract likes
                    likes_el = await comment.query_selector("span[data-e2e*='like-count']")
                    likes = await likes_el.inner_text() if likes_el else "0"

                    yield TiktokCommentItem(
                        text=text,
                        author=username,
                        likes=likes
                    )

                except Exception as e:
                    self.logger.error(f"Error extracting comment: {str(e)}")
                    continue

        except Exception as e:
            self.logger.error(f"Error during parsing: {str(e)}")
        
        finally:
            await page.close()

    async def errback(self, failure):
        self.logger.error(f"Request failed: {failure.value}")
        page = failure.request.meta.get("playwright_page")
        if page:
            await page.close()