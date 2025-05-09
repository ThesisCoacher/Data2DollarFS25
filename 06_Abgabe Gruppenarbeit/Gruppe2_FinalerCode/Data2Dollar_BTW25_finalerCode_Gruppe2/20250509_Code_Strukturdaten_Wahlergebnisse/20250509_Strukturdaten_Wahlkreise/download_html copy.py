import requests
import os
from pathlib import Path

def download_html_files():
    """
    Download HTML files from the Bundeswahlleiterin website for specific states
    and save them to a local directory.
    """
    # URLs for the different states
    urls = {
        "Baden_Wuerttemberg": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-8.html",
        "Bayern": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-9.html",
        "Berlin": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-11.html",
        "Brandenburg": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-12.html",
        "Bremen": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-4.html",
        "Hamburg": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-2.html",
        "Hessen": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-6.html",
        "Mecklenburg_Vorpommern": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-13.html",
        "Niedersachsen": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-3.html",
        "Nordrhein_Westfalen": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-5.html",
        "Rheinland_Pfalz": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-7.html",
        "Saarland": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-10.html",
        "Sachsen": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-14.html",
        "Sachsen_Anhalt": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-15.html",
        "Schleswig_Holstein": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-1.html",
        "Thueringen": "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-16.html"
    }
    
    # Create output directory
    output_dir = Path("downloaded_html")
    output_dir.mkdir(exist_ok=True)
    
    for state_name, url in urls.items():
        try:
            # Download the HTML content
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            # Save the HTML content to a file
            output_file = output_dir / f"{state_name}.html"
            with open(output_file, "wb") as f:
                f.write(response.content)
            
            print(f"Successfully downloaded {state_name} data to {output_file}")
            
        except requests.RequestException as e:
            print(f"Error downloading {state_name}: {e}")

if __name__ == "__main__":
    download_html_files()