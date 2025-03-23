# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class AirbnbListingItem(scrapy.Item):
    name = scrapy.Field()
    price_per_night = scrapy.Field()
    location = scrapy.Field()
    rating = scrapy.Field()
    review_count = scrapy.Field()
    room_type = scrapy.Field()
    amenities = scrapy.Field()
    beds = scrapy.Field()
    bathrooms = scrapy.Field()
    url = scrapy.Field()
    host_name = scrapy.Field()
    superhost = scrapy.Field()
    scraped_date = scrapy.Field()
