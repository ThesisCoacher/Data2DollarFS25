import scrapy
import os
import csv
from bs4 import BeautifulSoup


class BundeslandWahlergebnisseSpider(scrapy.Spider):
    name = "bundesland_wahlergebnisse"
    allowed_domains = ["www.bundeswahlleiterin.de"]
    start_urls = ["https://www.bundeswahlleiterin.de/bundestagswahlen/2025/ergebnisse/bund-99/land-8.html"]

    def parse(self, response):
        pass


# Party name mappings to handle variations
PARTY_MAPPINGS = {
    # CDU/CSU variations
    'CDU': 'CDU/CSU',
    'CSU': 'CDU/CSU',
    'Christlich Demokratische Union Deutschlands': 'CDU/CSU',
    
    # SPD variations
    'SPD': 'SPD',
    'Sozialdemokratische Partei Deutschlands': 'SPD',
    
    # Grüne variations
    'GRÜNE': 'Grüne',
    'GRÃNE': 'Grüne',
    'Die Grünen': 'Grüne',
    'BÜNDNIS 90/DIE GRÜNEN': 'Grüne',
    'BÃNDNIS 90/DIE GRÃNEN': 'Grüne',
    'Grüne/B 90': 'Grüne',
    
    # AfD variations
    'AfD': 'AfD',
    'Alternative für Deutschland': 'AfD',
    'Alternative fÃ¼r Deutschland': 'AfD',
    
    # Die Linke variations
    'Die Linke': 'Die Linke',
    'Die Linken': 'Die Linke',
    
    # BSW variations
    'BSW': 'BSW',
    'Bündnis Sahra Wagenknecht': 'BSW',
    'Bündnis Sahra Wagenknecht - Vernunft und Gerechtigkeit': 'BSW',
    'BÃ¼ndnis Sahra Wagenknecht - Vernunft und Gerechtigkeit': 'BSW',
    
    # FDP variations
    'FDP': 'FDP',
    'Freie Demokratische Partei': 'FDP',
}

# List of parties we want to collect data for
TARGET_PARTIES = ['CDU/CSU', 'SPD', 'Grüne', 'AfD', 'Die Linke', 'BSW', 'FDP']

def normalize_party_name(name):
    """Normalize party names using the mapping dictionary"""
    for key, value in PARTY_MAPPINGS.items():
        if key.lower() in name.lower():
            return value
    return name

def extract_party_data(html_path):
    """Extract party election data from an HTML file"""
    with open(html_path, 'r', encoding='utf-8', errors='ignore') as file:
        content = file.read()
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # Get the Bundesland name from the title
    title_element = soup.find('title')
    bundesland = "Unknown"
    if title_element:
        title_text = title_element.text
        if "Ergebnisse" in title_text:
            parts = title_text.split("Ergebnisse")[1].strip().split("-")[0].strip()
            bundesland = parts.replace("WÃ¼rttemberg", "Württemberg").replace("ThÃ¼ringen", "Thüringen")
    
    # Find the results table
    results_table = soup.find(id=lambda x: x and x.startswith('stimmentabelle'))
    
    if not results_table:
        print(f"Could not find results table in {html_path}")
        return None, None
    
    # Find all rows in the table body (the second tbody contains the party data)
    try:
        tbody_elements = results_table.find_all('tbody')
        if len(tbody_elements) >= 2:
            rows = tbody_elements[1].find_all('tr')
        else:
            rows = []
            print(f"Could not find party data rows in {html_path}")
    except Exception as e:
        print(f"Error finding party rows: {e}")
        return None, None
    
    party_data = {}
    debug_parties = []
    
    # Process each row
    for row in rows:
        cells = row.find_all(['th', 'td'])
        if len(cells) < 6:
            continue
        
        # Extract party name from first cell
        party_cell = cells[0]
        party_name = party_cell.text.strip()
        
        # Debug - print every party name to find Grüne
        original_party_name = party_name
        
        # Check if the cell has an abbr tag and use its title if available
        abbr_tag = party_cell.find('abbr')
        if abbr_tag and 'title' in abbr_tag.attrs:
            party_name = abbr_tag['title']
        
        # Store for debugging
        debug_parties.append(f"{party_name} (original: {original_party_name})")
        
        # Special case for Grüne
        if "GR" in party_name.upper() or "GRÜNE" in party_name or "GRÃNE" in party_name or "BÜNDNIS" in party_name or "BÃNDNIS" in party_name:
            normalized_party = 'Grüne'
            # Extract vote data, ensure we handle empty cells
            erststimmen_total = cells[1].text.strip().replace('.', '') if cells[1].text.strip() != '-' else ''
            erststimmen_percent = cells[2].text.strip().replace(',', '.') if cells[2].text.strip() != '-' else ''
            zweitstimmen_total = cells[4].text.strip().replace('.', '') if cells[4].text.strip() != '-' else ''
            zweitstimmen_percent = cells[5].text.strip().replace(',', '.') if cells[5].text.strip() != '-' else ''
            
            # Store the data
            party_data[normalized_party] = {
                'Erststimmen_total': erststimmen_total,
                'Erststimmen_percent': erststimmen_percent,
                'Zweitstimmen_total': zweitstimmen_total,
                'Zweitstimmen_percent': zweitstimmen_percent
            }
            continue
        
        # Normalize the party name for other parties
        normalized_party = normalize_party_name(party_name)
        
        if normalized_party in TARGET_PARTIES:
            # Extract vote data, ensure we handle empty cells
            erststimmen_total = cells[1].text.strip().replace('.', '') if cells[1].text.strip() != '-' else ''
            erststimmen_percent = cells[2].text.strip().replace(',', '.') if cells[2].text.strip() != '-' else ''
            zweitstimmen_total = cells[4].text.strip().replace('.', '') if cells[4].text.strip() != '-' else ''
            zweitstimmen_percent = cells[5].text.strip().replace(',', '.') if cells[5].text.strip() != '-' else ''
            
            # Store the data
            party_data[normalized_party] = {
                'Erststimmen_total': erststimmen_total,
                'Erststimmen_percent': erststimmen_percent,
                'Zweitstimmen_total': zweitstimmen_total,
                'Zweitstimmen_percent': zweitstimmen_percent
            }
    
    # Debug output to check which parties were found
    print(f"{bundesland}: Found {len(party_data)} parties: {', '.join(party_data.keys())}")
    
    # Debug for Grüne issue
    if 'Grüne' not in party_data:
        print(f"Could not find Grüne in {bundesland}. All parties found: {'; '.join(debug_parties)}")
    
    return bundesland, party_data

def process_all_html_files():
    """Process all HTML files in the bundesland_html directory"""
    html_dir = 'bundesland_html'
    results = []
    
    for filename in os.listdir(html_dir):
        if filename.endswith('.html'):
            file_path = os.path.join(html_dir, filename)
            print(f"Processing {filename}...")
            bundesland, party_data = extract_party_data(file_path)
            
            if bundesland and party_data:
                # Create a row for this Bundesland
                row = {'Bundesland': bundesland}
                
                # Add data for each party
                for party in TARGET_PARTIES:
                    if party in party_data:
                        for key, value in party_data[party].items():
                            row[f'{party}_{key}'] = value
                    else:
                        # Party not found, add empty values
                        row[f'{party}_Erststimmen_total'] = ''
                        row[f'{party}_Erststimmen_percent'] = ''
                        row[f'{party}_Zweitstimmen_total'] = ''
                        row[f'{party}_Zweitstimmen_percent'] = ''
                
                results.append(row)
    
    return results

def write_csv(results, output_file='wahlergebnisse.csv'):
    """Write the results to a CSV file"""
    if not results:
        print("No results to write")
        return
    
    # Create header
    fieldnames = ['Bundesland']
    for party in TARGET_PARTIES:
        fieldnames.extend([
            f'{party}_Erststimmen_total',
            f'{party}_Erststimmen_percent',
            f'{party}_Zweitstimmen_total',
            f'{party}_Zweitstimmen_percent'
        ])
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"Results written to {output_file}")

if __name__ == "__main__":
    # Process all HTML files and get the results
    results = process_all_html_files()
    
    # Write results to CSV
    write_csv(results)
