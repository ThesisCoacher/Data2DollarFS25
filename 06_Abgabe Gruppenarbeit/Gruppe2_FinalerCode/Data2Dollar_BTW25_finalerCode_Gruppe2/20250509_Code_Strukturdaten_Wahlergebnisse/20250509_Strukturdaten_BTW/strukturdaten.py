import scrapy
import os


class StrukturdatenSpider(scrapy.Spider):
    name = "strukturdaten"
    allowed_domains = ["www.bundeswahlleiterin.de"]
    start_urls = [
        "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-8.html",  # Baden-Württemberg
        "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-9.html",  # Bayern
        "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-11.html", # Berlin
    ]
    
    def __init__(self, *args, **kwargs):
        super(StrukturdatenSpider, self).__init__(*args, **kwargs)
        # Create a directory to save the HTML files
        self.output_dir = "downloaded_html"
        os.makedirs(self.output_dir, exist_ok=True)
    
    def parse(self, response):
        # Extract the state name from the URL
        state_id = response.url.split("/")[-1].split(".")[0]  # Extract "land-X" from the URL
        state_name = self.get_state_name(state_id)
        
        # Save the HTML content to a file
        filename = f"{state_name}.html"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(response.body)
        
        self.log(f"Saved HTML for {state_name} to {filepath}")
    
    def get_state_name(self, state_id):
        state_mapping = {
            "land-8": "Baden_Wuerttemberg",
            "land-9": "Bayern",
            "land-11": "Berlin",
        }
        return state_mapping.get(state_id, state_id)
