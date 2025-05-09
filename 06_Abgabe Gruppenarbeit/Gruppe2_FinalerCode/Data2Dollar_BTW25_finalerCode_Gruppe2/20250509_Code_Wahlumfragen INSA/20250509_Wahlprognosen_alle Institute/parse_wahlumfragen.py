import os
import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime
import re

def parse_date(date_str):
    """Parse date string to datetime object, handling various formats."""
    # Clean up the date string
    date_str = date_str.strip()
    
    # Match dd.mm.yyyy format
    if re.match(r'\d{1,2}\.\d{1,2}\.20\d{2}', date_str):
        return datetime.strptime(date_str, '%d.%m.%Y')
    
    # Match dd.mm.yy format
    elif re.match(r'\d{1,2}\.\d{1,2}\.\d{2}', date_str):
        return datetime.strptime(date_str, '%d.%m.%y')
    
    # Match formats like DD. Monthname YYYY or similar
    month_patterns = {
        'Jan': 1, 'Feb': 2, 'März': 3, 'Mär': 3, 'Mar': 3, 'Apr': 4, 'Mai': 5, 'May': 5,
        'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Okt': 10, 'Oct': 10,
        'Nov': 11, 'Dez': 12, 'Dec': 12
    }
    
    for month_name, month_num in month_patterns.items():
        if month_name in date_str:
            day_match = re.search(r'(\d{1,2})\.?\s*', date_str)
            year_match = re.search(r'20\d{2}', date_str)
            
            if day_match and year_match:
                day = int(day_match.group(1))
                year = int(year_match.group(0))
                return datetime(year, month_num, day)
    
    # Special case for the format like "29.04.2025"
    try:
        if len(date_str) >= 10 and date_str[2] == '.' and date_str[5] == '.':
            parts = date_str.split('.')
            if len(parts) >= 3:
                day = int(parts[0])
                month = int(parts[1])
                year = int(parts[2][:4])
                return datetime(year, month, day)
    except (ValueError, IndexError):
        pass
    
    return None

def extract_data_from_table(table, institute_name):
    """Extract polling data from a table."""
    data = []
    
    # Define the parties we're interested in and their possible aliases
    target_parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "LINKE", "AfD", "BSW"]
    party_aliases = {
        "Union": "CDU/CSU",
        "CDU": "CDU/CSU",
        "CSU": "CDU/CSU",
        "Grüne": "GRÜNE",
        "GRÜNE": "GRÜNE",
        "Linke": "LINKE",
        "LINKE": "LINKE",
        "Die Linke": "LINKE",
        "Die LINKE": "LINKE",
        "FDP": "FDP",
        "AfD": "AfD",
        "BSW": "BSW",
        "Bündnis Sahra Wagenknecht": "BSW",
    }
    
    # Check if this is likely to be a polling data table
    if not table.find_all('tr'):
        return []
    
    # Find column positions for date and parties
    header_row = table.find('tr')
    if not header_row:
        return []
    
    # Since table structure might vary, try to identify columns from both header and row structure
    date_column = None
    party_columns = {}
    
    # First, try to identify from header text
    headers = header_row.find_all(['th', 'td'])
    for i, th in enumerate(headers):
        text = th.get_text().strip().upper()
        
        # Look for date column
        if any(date_word in text.lower() for date_word in ["datum", "date", "zeit", "time"]):
            date_column = i
        else:
            # Look for party columns
            for party, std_name in party_aliases.items():
                if party.upper() in text:
                    party_columns[i] = std_name
                    break
    
    # If we didn't find date column in header, it might be the first column
    if date_column is None:
        # In many tables, the first column is the date
        date_column = 0
    
    # If we didn't identify party columns from header, try to infer from a typical row
    if not party_columns:
        # Get the second row (usually the first data row)
        if len(table.find_all('tr')) > 1:
            sample_row = table.find_all('tr')[1]
            cells = sample_row.find_all(['td', 'th'])
            
            # Check if this is the Bundestagswahl row which often has all parties
            row_text = sample_row.get_text().lower()
            if 'bundestagswahl' in row_text or 'wahl' in row_text:
                # This is likely the election result row which has party percentages
                for i, cell in enumerate(cells):
                    cell_text = cell.get_text().strip()
                    # Look for percentage values like "28,5 %" which would indicate a party column
                    if re.search(r'\d+[,\.]\d+\s*%', cell_text):
                        # Try to identify which party based on the position
                        if i == 2:  # Usually CDU/CSU position
                            party_columns[i] = "CDU/CSU"
                        elif i == 3:  # Usually SPD position
                            party_columns[i] = "SPD"
                        elif i == 4:  # Usually GRÜNE position
                            party_columns[i] = "GRÜNE"
                        elif i == 5:  # Usually FDP position
                            party_columns[i] = "FDP"
                        elif i == 6:  # Usually LINKE position
                            party_columns[i] = "LINKE"
                        elif i == 7:  # Usually AfD position
                            party_columns[i] = "AfD"
                        elif i == 9 and "BSW" in target_parties:  # BSW often appears here
                            party_columns[i] = "BSW"
    
    # If still no party columns identified, use fixed positions from typical wahlrecht.de tables
    if not party_columns:
        party_columns = {
            2: "CDU/CSU",  # Index 2 is typically CDU/CSU
            3: "SPD",      # Index 3 is typically SPD
            4: "GRÜNE",    # Index 4 is typically GRÜNE
            5: "FDP",      # Index 5 is typically FDP
            6: "LINKE",    # Index 6 is typically LINKE
            7: "AfD",      # Index 7 is typically AfD
            9: "BSW"       # Index 9 is typically BSW if present
        }
    
    # Process data rows
    for row in table.find_all('tr')[1:]:  # Skip header row
        cells = row.find_all(['td', 'th'])
        if len(cells) <= date_column:
            continue
        
        # Extract date from the date column
        date_cell = cells[date_column]
        date_text = date_cell.get_text().strip()
        
        # Check if it's a date or a label like "Bundestagswahl"
        if 'wahl' in date_text.lower():
            continue  # Skip election result rows
        
        date_obj = parse_date(date_text)
        if not date_obj:
            continue
        
        # Check if date is within our time range (Dec 1, 2024 - Feb 23, 2025)
        start_date = datetime(2024, 12, 1)
        end_date = datetime(2025, 2, 23)
        
        if date_obj >= start_date and date_obj <= end_date:
            row_data = {
                "Institute": institute_name,
                "Date": date_obj.strftime('%Y-%m-%d')
            }
            
            # Extract polling values for each party
            for col_idx, party_name in party_columns.items():
                if col_idx < len(cells):
                    val_text = cells[col_idx].get_text().strip()
                    # Remove % sign and handle comma as decimal separator
                    val_text = val_text.replace('%', '').replace(',', '.').strip()
                    # Handle special cases like "–" or empty cells
                    if val_text == "–" or val_text == "-" or not val_text:
                        continue
                    
                    # Try to convert to float
                    try:
                        value = float(val_text)
                        if party_name in target_parties:
                            row_data[party_name] = value
                    except ValueError:
                        # Skip non-numeric values
                        pass
            
            # Only add the row if we found at least one party value
            if len(row_data) > 2:
                data.append(row_data)
    
    return data

def process_html_files():
    """Process all HTML files in the wahlrecht_html directory."""
    all_data = []
    html_dir = "wahlrecht_html"
    
    # Map file names to institute names
    institute_mapping = {
        "allensbach.htm": "Allensbach",
        "dimap.htm": "Infratest dimap",
        "emnid.htm": "Verian",
        "forsa.htm": "Forsa",
        "gms.htm": "GMS",
        "insa.htm": "INSA",
        "politbarometer.htm": "Forschungsgruppe Wahlen",
        "yougov.htm": "YouGov",
        "index.htm": "Wahlrecht.de"
    }
    
    # Process each HTML file
    for filename in os.listdir(html_dir):
        # Skip files we're not interested in
        if filename not in institute_mapping:
            continue
        
        institute_name = institute_mapping[filename]
        filepath = os.path.join(html_dir, filename)
        
        print(f"Processing {institute_name} from {filename}...")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                html_content = file.read()
                
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find all tables in the HTML
            tables = soup.find_all('table')
            print(f"Found {len(tables)} tables in {filename}")
            
            for i, table in enumerate(tables):
                # Extract data from this table
                table_data = extract_data_from_table(table, institute_name)
                if table_data:
                    print(f"  - Found {len(table_data)} relevant polls in table {i+1}")
                    all_data.extend(table_data)
        
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    return all_data

def create_csv():
    """Create CSV file from the extracted data."""
    data = process_html_files()
    
    if not data:
        print("No data found within the specified date range.")
        return
    
    print(f"\nFound a total of {len(data)} polls within the specified date range.")
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Ensure all party columns are present
    target_parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "LINKE", "AfD", "BSW"]
    for party in target_parties:
        if party not in df.columns:
            df[party] = None
    
    # Sort by date and institute
    df = df.sort_values(by=['Date', 'Institute'])
    
    # Save to CSV
    csv_path = "wahlumfragen_dec2024_feb2025.csv"
    df.to_csv(csv_path, index=False)
    
    print(f"Data saved to {csv_path}")
    print(f"Found {len(df)} polling entries from {len(df['Institute'].unique())} institutes")
    
    # Print a summary of the data
    print("\nData summary:")
    for institute in sorted(df['Institute'].unique()):
        count = len(df[df['Institute'] == institute])
        dates = df[df['Institute'] == institute]['Date'].tolist()
        print(f"  - {institute}: {count} polls ({', '.join(dates)})")

if __name__ == "__main__":
    create_csv()