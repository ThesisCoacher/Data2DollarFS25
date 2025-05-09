import scrapy
import os


class AlleWahlumfragenSpider(scrapy.Spider):
    name = "alle_wahlumfragen"
    allowed_domains = ["www.wahlrecht.de"]
    
    # Define the list of all institute URLs to crawl
    start_urls = [
        "https://www.wahlrecht.de/umfragen/allensbach.htm",
        "https://www.wahlrecht.de/umfragen/emnid.htm",  # Verian (former Emnid)
        "https://www.wahlrecht.de/umfragen/forsa.htm",
        "https://www.wahlrecht.de/umfragen/politbarometer.htm",  # Forschungsgruppe Wahlen
        "https://www.wahlrecht.de/umfragen/gms.htm",
        "https://www.wahlrecht.de/umfragen/dimap.htm",  # Infratest dimap
        "https://www.wahlrecht.de/umfragen/insa.htm",
        "https://www.wahlrecht.de/umfragen/yougov.htm",
        # Also include the main page
        "https://www.wahlrecht.de/umfragen/"
    ]
    
    # Create output directory if it doesn't exist
    def __init__(self, *args, **kwargs):
        super(AlleWahlumfragenSpider, self).__init__(*args, **kwargs)
        self.output_dir = 'wahlrecht_html'
        os.makedirs(self.output_dir, exist_ok=True)
        self.logger.info(f"Created output directory: {self.output_dir}")

    def parse(self, response):
        # Get the filename from the URL
        url = response.url
        filename = url.split("/")[-1]
        
        # Handle the main page differently
        if filename == "" or filename == "umfragen/":
            filename = "index.htm"
        
        # Write the response body to an HTML file
        file_path = os.path.join(self.output_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(response.body)
        
        self.logger.info(f"Saved file: {file_path}")
        
        # Yield the file information
        yield {
            'url': url,
            'institute': filename.replace('.htm', ''),
            'file_path': file_path
        }
