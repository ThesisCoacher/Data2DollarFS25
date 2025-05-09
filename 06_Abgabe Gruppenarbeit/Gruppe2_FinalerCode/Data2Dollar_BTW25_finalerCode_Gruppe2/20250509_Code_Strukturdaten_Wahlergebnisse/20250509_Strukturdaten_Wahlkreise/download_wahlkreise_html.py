import requests
import os
from pathlib import Path

def download_html_files():
    """
    Download HTML files from the Bundeswahlleiterin website for Baden-Württemberg Wahlkreise
    and save them to a local directory.
    """
    # Dictionary of Wahlkreise in Baden-Württemberg with their numbers and names
    baden_wuerttemberg_wahlkreise = {
        "258": "Stuttgart 1",
        "259": "Stuttgart 2",
        "260": "Böblingen",
        "261": "Esslingen",
        "262": "Nürtingen", 
        "263": "Göppingen",
        "264": "Waiblingen", 
        "265": "Ludwigsburg",
        "266": "Neckar-Zaber", 
        "267": "Heilbronn", 
        "268": "Schwäbisch Hall - Hohenlohe",
        "269": "Backnang - Schwäbisch Gmünd", 
        "270": "Aalen - Heidenheim", 
        "271": "Karlsruhe-Stadt", 
        "272": "Karlsruhe-Land", 
        "273": "Rastatt", 
        "274": "Heidelberg", 
        "275": "Mannheim", 
        "276": "Odenwald - Tauber", 
        "277": "Rhein-Neckar", 
        "278": "Bruchsal - Schwetzingen", 
        "279": "Pforzheim", 
        "280": "Calw", 
        "281": "Freiburg", 
        "282": "Lörrach - Müllheim", 
        "283": "Emmendingen - Lahr", 
        "284": "Offenburg", 
        "285": "Rottweil - Tuttlingen", 
        "286": "Schwarzwald-Baar", 
        "287": "Konstanz", 
        "288": "Waldshut", 
        "289": "Reutlingen", 
        "290": "Tübingen", 
        "291": "Ulm", 
        "292": "Biberach", 
        "293": "Bodensee", 
        "294": "Ravensburg", 
        "295": "Zollernalb - Sigmaringen"
    }
    
    # Create output directory
    output_dir = Path("downloaded_wahlkreise_html")
    output_dir.mkdir(exist_ok=True)
    
    # URL template for Wahlkreise in Baden-Württemberg (land-8)
    url_template = "https://www.bundeswahlleiterin.de/bundestagswahlen/2025/strukturdaten/bund-99/land-8/wahlkreis-{}.html"
    
    for wk_number, wk_name in baden_wuerttemberg_wahlkreise.items():
        try:
            # Construct the URL for this Wahlkreis
            url = url_template.format(wk_number)
            
            # Download the HTML content
            response = requests.get(url)
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            # Save the HTML content to a file (using number to keep order)
            output_file = output_dir / f"{wk_number}_{wk_name.replace(' ', '_').replace('-', '_')}.html"
            with open(output_file, "wb") as f:
                f.write(response.content)
            
            print(f"Successfully downloaded Wahlkreis {wk_number} ({wk_name}) data to {output_file}")
            
        except requests.RequestException as e:
            print(f"Error downloading Wahlkreis {wk_number} ({wk_name}): {e}")

if __name__ == "__main__":
    download_html_files()