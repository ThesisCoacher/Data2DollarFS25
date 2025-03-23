# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
from datetime import datetime

class AirbnbScraperPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)
        
        # Clean and convert price to numeric
        if adapter.get('price_per_night'):
            adapter['price_per_night'] = float(adapter['price_per_night'])
        
        # Ensure rating is float
        if adapter.get('rating'):
            try:
                adapter['rating'] = float(adapter['rating'])
            except (ValueError, TypeError):
                adapter['rating'] = None
        
        # Ensure review_count is integer
        if adapter.get('review_count'):
            try:
                adapter['review_count'] = int(adapter['review_count'])
            except (ValueError, TypeError):
                adapter['review_count'] = 0
        
        # Convert beds to integer
        if adapter.get('beds'):
            try:
                adapter['beds'] = int(adapter['beds'])
            except (ValueError, TypeError):
                adapter['beds'] = None
        
        # Convert bathrooms to float (can be 1.5 bathrooms)
        if adapter.get('bathrooms'):
            try:
                adapter['bathrooms'] = float(adapter['bathrooms'])
            except (ValueError, TypeError):
                adapter['bathrooms'] = None
        
        # Ensure proper datetime format
        if adapter.get('scraped_date'):
            try:
                if isinstance(adapter['scraped_date'], str):
                    adapter['scraped_date'] = datetime.fromisoformat(adapter['scraped_date'])
            except (ValueError, TypeError):
                adapter['scraped_date'] = datetime.now()
        
        # Convert superhost to boolean
        adapter['superhost'] = bool(adapter.get('superhost', False))
        
        return item
