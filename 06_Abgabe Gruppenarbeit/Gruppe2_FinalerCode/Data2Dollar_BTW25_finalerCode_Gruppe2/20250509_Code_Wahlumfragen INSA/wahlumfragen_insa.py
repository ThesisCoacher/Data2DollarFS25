import scrapy
from datetime import datetime


class WahlumfragenInsaSpider(scrapy.Spider):
    name = "wahlumfragen_insa"
    allowed_domains = ["www.wahlrecht.de"]
    start_urls = ["https://www.wahlrecht.de/umfragen/insa.htm"]

    def parse(self, response):
        # Define the target parties
        target_parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "LINKE", "AfD", "BSW"]
        
        # Define the target date range (as strings for comparison)
        start_date = "31.08.2024"
        end_date = "23.02.2025"
        
        # Find the table containing the polling data
        table = response.xpath('//body/table')
        
        # Get all rows except the header rows
        rows = table.xpath('./tbody/tr')
        
        # Store all extracted data
        all_data = []
        
        for row in rows:
            # Extract date from the first column
            date_str = row.xpath('./td[1]/text()').get()
            if not date_str:
                continue
                
            date_str = date_str.strip()
            
            # Skip rows outside our date range
            # We need to check if the date falls within our target range
            try:
                # Parse the date to compare (DD.MM.YYYY format)
                date_obj = datetime.strptime(date_str, "%d.%m.%Y")
                start_date_obj = datetime.strptime(start_date, "%d.%m.%Y")
                end_date_obj = datetime.strptime(end_date, "%d.%m.%Y")
                
                # Skip if outside our range
                if not (start_date_obj <= date_obj <= end_date_obj):
                    continue
            except ValueError:
                # Skip if the date is not in the expected format
                continue
            
            # Create a data object for this row
            poll_data = {
                "date": date_str
            }
            
            # Extract institute name
            institute = row.xpath('./td[2]/text()').get()
            if institute:
                poll_data["institute"] = institute.strip()
            
            # Loop through the target parties and extract their percentages
            # Corrected column mapping: CDU/CSU is in column 3, SPD in column 4, etc.
            # AfD is in column 9, not 8, and BSW is in column 10, not 9
            party_columns = {
                "CDU/CSU": 3,
                "SPD": 4,
                "GRÜNE": 5,
                "FDP": 6,
                "LINKE": 7,
                "AfD": 9,
                "BSW": 10
            }
            
            for party, col_index in party_columns.items():
                if party in target_parties:
                    percentage = row.xpath(f'./td[{col_index}]/text()').get()
                    if percentage:
                        poll_data[party] = percentage.strip().replace(",", ".")
            
            # Add the data for this row to our collection
            all_data.append(poll_data)
            
            # Output the data to the console
            self.log(f"Found data: {poll_data}")
            
            # Yield the data for Scrapy to collect
            yield poll_data
        
        self.log(f"Total records collected: {len(all_data)}")
