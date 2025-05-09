import requests
import os
import time
from pathlib import Path

def download_bundesland_html():
    # Dictionary mapping of Bundesland IDs to their names
    bundeslaender = {
        '8': 'Baden-Württemberg',
        '9': 'Bayern',
        '11': 'Berlin',
        '12': 'Brandenburg',
        '4': 'Bremen',
        '2': 'Hamburg',
        '6': 'Hessen',
        '13': 'Mecklenburg-Vorpommern',
        '3': 'Niedersachsen',
        '5': 'Nordrhein-Westfalen',
        '7': 'Rheinland-Pfalz',
        '10': 'Saarland',
        '14': 'Sachsen',
        '15': 'Sachsen-Anhalt',
        '1': 'Schleswig-Holstein',
        '16': 'Thüringen',
    }
    
    # Create a directory to store the downloaded HTML files
    output_dir = Path("bundesland_html")
    output_dir.mkdir(exist_ok=True)
    
    # Download the HTML content for each Bundesland
    for land_id, land_name in bundeslaender.items():
        url = f"https://www.bundeswahlleiterin.de/bundestagswahlen/2025/ergebnisse/bund-99/land-{land_id}.html"
        print(f"Downloading {land_name} from {url}")
        
        try:
            # Add headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            # Send the request
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            # Generate a filename for the downloaded content
            # Replace spaces and special characters for clean filenames
            clean_name = land_name.replace(' ', '_').replace('-', '_').replace('ü', 'ue').replace('ä', 'ae').replace('ö', 'oe')
            filename = output_dir / f"{clean_name}.html"
            
            # Save the HTML content to a file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(response.text)
            
            print(f"Successfully saved {land_name} HTML to {filename}")
            
            # Add a small delay between requests to avoid overwhelming the server
            time.sleep(1)
            
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {land_name}: {e}")
    
    print("Download completed!")

if __name__ == "__main__":
    download_bundesland_html()