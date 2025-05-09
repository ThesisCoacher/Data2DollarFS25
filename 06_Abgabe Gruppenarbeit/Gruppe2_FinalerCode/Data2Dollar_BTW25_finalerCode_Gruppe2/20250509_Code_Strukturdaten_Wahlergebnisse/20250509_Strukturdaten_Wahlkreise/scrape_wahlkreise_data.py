import os
from pathlib import Path
import csv
import re
from lxml import html

def extract_numeric_value(text):
    """Extract numeric value from text, handling different formats including negative values."""
    if text is None:
        return None
    
    # Remove spaces and replace comma with dot for decimal values
    text = text.strip()
    
    # Check if the value is negative (contains a minus sign)
    is_negative = '-' in text
    
    # Extract numbers with possible comma as decimal separator
    match = re.search(r'([\d.,]+)', text)
    if match:
        value = match.group(1).replace('.', '').replace(',', '.')
        try:
            numeric_value = float(value)
            # Apply negative sign if found in the original text
            if is_negative:
                numeric_value = -numeric_value
            return numeric_value
        except ValueError:
            return text
    return text

def extract_wahlkreis_info(filename):
    """Extract Wahlkreis number and name from filename."""
    # Extract the number and name from the filename pattern: 258_Stuttgart_1.html
    match = re.match(r'(\d+)_(.+)\.html', filename)
    if match:
        wahlkreis_number = match.group(1)
        wahlkreis_name = match.group(2).replace('_', ' ')
        return wahlkreis_number, wahlkreis_name
    return None, None

def scrape_wahlkreise_data():
    """Scrape data from downloaded Wahlkreise HTML files."""
    # Path to directory containing downloaded HTML files
    html_dir = Path("downloaded_wahlkreise_html")
    
    # CSV file to write the data to
    csv_file = Path("baden_wuerttemberg_wahlkreise_strukturdaten.csv")
    
    # Define the XPaths we want to scrape (same as for Bundesländer)
    xpaths = {
        "Anzahl Gemeinden": "/html/body/div[1]/div/main/figure[1]/table/tbody/tr[1]/td",
        "Fläche km2": "/html/body/div[1]/div/main/figure[1]/table/tbody/tr[2]/td",
        "Bevölkerung in Tsd": "/html/body/div[1]/div/main/figure[2]/table/tbody/tr[2]/td",
        "davon Deutsche in Tsd": "/html/body/div[1]/div/main/figure[2]/table/tbody/tr[3]/td",
        "Ausländer*innenanteil": "/html/body/div[1]/div/main/figure[2]/table/tbody/tr[4]/td",
        "Bevölkerungsdichte je km2": "/html/body/div[1]/div/main/figure[2]/table/tbody/tr[6]/td",
        "Geburtensaldo": "/html/body/div[1]/div/main/figure[2]/table/tbody/tr[8]/td",
        "Wanderungssaldo": "/html/body/div[1]/div/main/figure[2]/table/tbody/tr[9]/td",
        "Alter unter 16": "/html/body/div[1]/div/main/figure[2]/table/tbody/tr[11]/td",
        "Alter 16-17": "/html/body/div[1]/div/main/figure[2]/table/tbody/tr[12]/td",
        "Alter 18-24": "/html/body/div[1]/div/main/figure[2]/table/tbody/tr[13]/td",
        "Alter 25-34": "/html/body/div[1]/div/main/figure[2]/table/tbody/tr[14]/td",
        "Alter 35-59": "/html/body/div[1]/div/main/figure[2]/table/tbody/tr[15]/td",
        "Alter 60-74": "/html/body/div[1]/div/main/figure[2]/table/tbody/tr[16]/td",
        "Alter über 75": "/html/body/div[1]/div/main/figure[2]/table/tbody/tr[17]/td",
        "Bodenfläche Siedlung und Verkehr": "/html/body/div[1]/div/main/figure[3]/table/tbody/tr[2]/td",
        "Bodenfläche Vegetation & Gewässer": "/html/body/div[1]/div/main/figure[3]/table/tbody/tr[3]/td",
        "Fertiggestellte Wohnungen 2021 je Tsd Einwohner*innen": "/html/body/div[1]/div/main/figure[4]/table/tbody/tr[1]/td",
        "Bestand an Wohnungen 2021 je Tsd Einwohner*innen": "/html/body/div[1]/div/main/figure[4]/table/tbody/tr[2]/td",
        "Wohnfläche je Wohnnung 2021": "/html/body/div[1]/div/main/figure[4]/table/tbody/tr[3]/td",
        "Wohnfläche 2021 je Tsd Einwohner*innen": "/html/body/div[1]/div/main/figure[4]/table/tbody/tr[4]/td",
        "PKW insgesamt je Tsd Einwohner*innen": "/html/body/div[1]/div/main/figure[5]/table/tbody/tr[2]/td",
        "PKW Elektro oder Hybrid": "/html/body/div[1]/div/main/figure[5]/table/tbody/tr[3]/td",
        "Unternehmen 2021 je Tsd Einwohner*innen": "/html/body/div[1]/div/main/figure[6]/table/tbody/tr[1]/td",
        "Handwerksunternehmen 2021 je Tsd Einwohner*innen": "/html/body/div[1]/div/main/figure[6]/table/tbody/tr[2]/td",
        "Schulabgänger*innen beruflicher Schulen 2022 je Tsd Einwohner*innen": "/html/body/div[1]/div/main/figure[7]/table/tbody/tr/td",
        "Schulabgänger*innen insgesamt ohne Externe je Tsd Einwohner*innen": "/html/body/div[1]/div/main/figure[8]/table/tbody/tr[2]/td",
        "Schulabgänger*innen ohne Hauptschulabschluss": "/html/body/div[1]/div/main/figure[8]/table/tbody/tr[3]/td",
        "Schulabgänger*innen mit Hauptschulabschluss": "/html/body/div[1]/div/main/figure[8]/table/tbody/tr[4]/td",
        "Schulabgänger*innen mit Realschulabschluss": "/html/body/div[1]/div/main/figure[8]/table/tbody/tr[5]/td",
        "Schulabgänger*innen mit allgemeiner und Fachhochschulreife": "/html/body/div[1]/div/main/figure[8]/table/tbody/tr[6]/td",
        "Quote betreute Kinder unter 3 Jahre": "/html/body/div[1]/div/main/figure[9]/table/tbody/tr[2]/td",
        "Quote betreute Kinder 3-5 Jahre": "/html/body/div[1]/div/main/figure[9]/table/tbody/tr[3]/td",
        "Verfügbares Einkommen der privaten Haushalte 2021 EUR je Einwohner*in": "/html/body/div[1]/div/main/figure[10]/table/tbody/tr[1]/td",
        "BIP je Einwohner*in 2021": "/html/body/div[1]/div/main/figure[10]/table/tbody/tr[2]/td",
        "Sozialversicherungspflichtig je Tsd Einwohner*innen": "/html/body/div[1]/div/main/figure[11]/table/tbody/tr[2]/td",
        "Anteil Sozialversicherungspflichtiger in Land-, Forstwirtschaft & Fisherei": "/html/body/div[1]/div/main/figure[11]/table/tbody/tr[3]/td",
        "Anteil Sozialversicherungspflichtiger im produzierenden Gewerbe": "/html/body/div[1]/div/main/figure[11]/table/tbody/tr[4]/td",
        "Anteil Sozialversicherungspflichtiger im Handel, Gastgewerbe, Verkehr": "/html/body/div[1]/div/main/figure[11]/table/tbody/tr[5]/td",
        "Anteil Sozialversicherungspflichtige öffentliche und private Dienstleister": "/html/body/div[1]/div/main/figure[11]/table/tbody/tr[6]/td",
        "Anteil Sozialversicherungspflichtige übrige Dienstleister": "/html/body/div[1]/div/main/figure[11]/table/tbody/tr[7]/td",
        "Empfänger*innen Leistungen SGB II je Tsd Einwohner*innen": "/html/body/div[1]/div/main/figure[12]/table/tbody/tr[2]/td",
        "Anteil SGB II Empfänger*innen nichterwerbsfähige Hilfebedürftige": "/html/body/div[1]/div/main/figure[12]/table/tbody/tr[3]/td",
        "Anteil SGB II Empfänger*innen Ausländer*innen": "/html/body/div[1]/div/main/figure[12]/table/tbody/tr[4]/td",
        "Arbeitslosenquote insgesamt": "/html/body/div[1]/div/main/figure[13]/table/tbody/tr[2]/td",
        "Arbeitslosenquote Männer": "/html/body/div[1]/div/main/figure[13]/table/tbody/tr[3]/td",
        "Arbeitslosenquote Frauen": "/html/body/div[1]/div/main/figure[13]/table/tbody/tr[4]/td",
        "Arbeitslosenquote 15-24": "/html/body/div[1]/div/main/figure[13]/table/tbody/tr[5]/td",
        "Arbeitslosenquote 55-64": "/html/body/div[1]/div/main/figure[13]/table/tbody/tr[6]/td",
    }
    
    # Create a list to store the data
    data = []
    
    # Check if directory exists
    if not html_dir.exists():
        print(f"Directory {html_dir} does not exist. Please run download_wahlkreise_html.py first.")
        return
    
    # Process each HTML file
    for html_file in sorted(html_dir.glob("*.html")):
        # Extract Wahlkreis number and name from filename
        wahlkreis_number, wahlkreis_name = extract_wahlkreis_info(html_file.name)
        
        if not wahlkreis_number or not wahlkreis_name:
            print(f"Could not extract Wahlkreis info from {html_file.name}, skipping...")
            continue
        
        # Read the HTML file
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # Parse the HTML
        tree = html.fromstring(html_content)
        
        # Create data record with Bundesland, Wahlkreis number, and name
        wahlkreis_data = {
            "Bundesland": "Baden-Württemberg",
            "Wahlkreis Nummer": wahlkreis_number,
            "Wahlkreis Name": wahlkreis_name
        }
        
        # Extract the values using XPaths
        for field, xpath in xpaths.items():
            elements = tree.xpath(xpath)
            
            if elements:
                # Get the text content of the element
                value = elements[0].text_content().strip()
                # Store the extracted value
                wahlkreis_data[field] = extract_numeric_value(value)
            else:
                # If the element doesn't exist, store None
                wahlkreis_data[field] = None
        
        # Add the Wahlkreis data to our list
        data.append(wahlkreis_data)
        print(f"Scraped data for Wahlkreis {wahlkreis_number} ({wahlkreis_name})")
    
    # Write the data to a CSV file
    if data:
        # Get all field names to use as CSV headers
        fieldnames = ["Bundesland", "Wahlkreis Nummer", "Wahlkreis Name"] + list(xpaths.keys())
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        print(f"Data has been written to {csv_file}")
    else:
        print("No data was found to write to the CSV file.")

if __name__ == "__main__":
    scrape_wahlkreise_data()