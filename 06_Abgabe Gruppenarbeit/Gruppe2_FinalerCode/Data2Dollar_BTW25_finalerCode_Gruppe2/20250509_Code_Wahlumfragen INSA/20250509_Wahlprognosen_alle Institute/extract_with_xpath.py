import os
import pandas as pd
from bs4 import BeautifulSoup
import datetime
import re
import sys

def parse_date(date_str):
    """Parse date string to datetime object, handling various formats."""
    # Clean up the date string
    date_str = date_str.strip()
    
    # Match dd.mm.yyyy format
    if re.match(r'\d{1,2}\.\d{1,2}\.20\d{2}', date_str):
        return datetime.datetime.strptime(date_str, '%d.%m.%Y')
    
    # Match dd.mm.yy format
    elif re.match(r'\d{1,2}\.\d{1,2}\.\d{2}', date_str):
        return datetime.datetime.strptime(date_str, '%d.%m.%y')
    
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
                return datetime.datetime(year, month_num, day)
    
    # Special case for the format like "29.04.2025"
    try:
        if len(date_str) >= 10 and date_str[2] == '.' and date_str[5] == '.':
            parts = date_str.split('.')
            if len(parts) >= 3:
                day = int(parts[0])
                month = int(parts[1])
                year = int(parts[2][:4])
                return datetime.datetime(year, month, day)
    except (ValueError, IndexError):
        pass
    
    return None

def extract_data_from_html(html_file, institute_name):
    """Extract polling data from HTML file using BeautifulSoup."""
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
    
    try:
        with open(html_file, 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        # Parse the HTML with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all tables in the document
        tables = soup.find_all('table')
        print(f"  Found {len(tables)} tables in {html_file}")
        
        # Process each table to find polling data
        for table_index, table in enumerate(tables):
            print(f"  Checking table {table_index + 1}")
            
            # Skip tables that are likely not polling data
            if not table.find_all('tr'):
                continue
            
            # Check if this table contains party names in header
            headers = table.find_all('th')
            header_texts = [h.get_text().strip() for h in headers]
            
            # Check if this looks like a polling data table
            contains_parties = any(party in " ".join(header_texts) for party in target_parties + list(party_aliases.keys()))
            
            if not contains_parties and len(tables) > 1:
                # May not be a polling table, skip to the next one
                continue
            
            # Find column indices for parties
            party_indices = {}
            date_index = None
            
            header_row = table.find('tr')
            if not header_row:
                continue
                
            header_cells = header_row.find_all(['th', 'td'])
            
            # Try to identify date column and party columns
            for i, cell in enumerate(header_cells):
                cell_text = cell.get_text().strip()
                
                # Look for date column
                if any(date_word in cell_text.lower() for date_word in ["datum", "date", "zeit", "time"]):
                    date_index = i
                    continue
                
                # Check if this is a party column
                for party_name, std_name in party_aliases.items():
                    if party_name in cell_text and std_name in target_parties:
                        party_indices[i] = std_name
                        break
            
            # If we didn't find any party columns, this might not be the right table
            if not party_indices and len(tables) > 1:
                continue
                
            # If date column wasn't found, assume it's the first column
            if date_index is None:
                date_index = 0
            
            # If we still don't have party indices, try to infer from common patterns
            if not party_indices:
                print("  Attempting to infer party columns from typical patterns...")
                # These are typical positions for parties in wahlrecht.de tables
                party_map = {
                    "CDU/CSU": [2],
                    "SPD": [3],
                    "GRÜNE": [4],
                    "FDP": [5],
                    "LINKE": [6],
                    "AfD": [7],
                    "BSW": [9, 10]  # BSW might be in either position
                }
                
                # Check if these indices match header cells that might be party headers
                for party, possible_indices in party_map.items():
                    for idx in possible_indices:
                        if idx < len(header_cells):
                            # Add this mapping unless we already found this party
                            if not any(p == party for p in party_indices.values()):
                                party_indices[idx] = party
            
            # Process each data row
            rows = table.find_all('tr')[1:]  # Skip header row
            print(f"  Processing {len(rows)} rows with parties at indices: {party_indices}")
            
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) <= date_index:
                    continue
                
                # Extract date
                date_text = cells[date_index].get_text().strip()
                
                # Skip headers or election results rows
                if 'wahl' in date_text.lower() or 'datum' in date_text.lower():
                    continue
                
                # Parse the date
                date_obj = parse_date(date_text)
                if not date_obj:
                    print(f"  Could not parse date: {date_text}")
                    continue
                
                # Create row data with institute and date
                row_data = {
                    "Institute": institute_name,
                    "Date": date_obj.strftime('%Y-%m-%d')
                }
                
                # Extract values for each party
                for col_idx, party_name in party_indices.items():
                    if col_idx < len(cells):
                        val_text = cells[col_idx].get_text().strip()
                        # Remove % sign and handle comma as decimal separator
                        val_text = val_text.replace('%', '').replace(',', '.').strip()
                        
                        # Handle special cases
                        if val_text in ["–", "-", "", "n.e."] or not val_text:
                            continue
                        
                        # Try to convert to float
                        try:
                            value = float(val_text)
                            row_data[party_name] = value
                        except ValueError:
                            # Skip non-numeric values
                            pass
                
                # Only add the row if we found at least one party value
                if len(row_data) > 2:
                    data.append(row_data)
                    
            # If we found data, break out of the loop (assuming the first table with data is the right one)
            if data:
                print(f"  Found {len(data)} polls in table {table_index + 1}")
                break
                
    except Exception as e:
        print(f"  Error processing {html_file}: {str(e)}")
        
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
            file_data = extract_data_from_html(filepath, institute_name)
            if file_data:
                print(f"  - Found {len(file_data)} polls from {institute_name}")
                all_data.extend(file_data)
            else:
                print(f"  - No data found for {institute_name}")
        except Exception as e:
            print(f"Error processing {filename}: {e}")
    
    return all_data

def create_formatted_table():
    """Create a formatted table with dates in rows and parties/institutes in columns."""
    # Get the raw data
    data = process_html_files()
    
    if not data:
        print("No data found.")
        return
    
    print(f"\nFound a total of {len(data)} polling entries.")
    
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Ensure all party columns are present
    target_parties = ["CDU/CSU", "SPD", "GRÜNE", "FDP", "LINKE", "AfD", "BSW"]
    for party in target_parties:
        if party not in df.columns:
            df[party] = None
    
    # Save the raw data
    raw_csv_path = "wahlumfragen_raw_data.csv"
    df.to_csv(raw_csv_path, index=False)
    print(f"Raw data saved to {raw_csv_path}")
    
    # Create the formatted table
    # Group by date and institute
    all_dates = sorted(df['Date'].unique())
    all_institutes = sorted(df['Institute'].unique())
    
    # Create a multiindex DataFrame
    formatted_data = {}
    
    # For each party, create columns for each institute
    for party in target_parties:
        for institute in all_institutes:
            col_name = f"{party} - {institute}"
            formatted_data[col_name] = [None] * len(all_dates)
    
    # Fill in the data
    for i, date in enumerate(all_dates):
        date_rows = df[df['Date'] == date]
        for _, row in date_rows.iterrows():
            institute = row['Institute']
            for party in target_parties:
                if party in row and not pd.isna(row[party]):
                    col_name = f"{party} - {institute}"
                    formatted_data[col_name][i] = row[party]
    
    # Create the DataFrame with dates as index
    formatted_df = pd.DataFrame(formatted_data, index=all_dates)
    formatted_df.index.name = 'Date'
    
    # Save the formatted table
    formatted_csv_path = "wahlumfragen_formatted_table.csv"
    formatted_df.to_csv(formatted_csv_path)
    print(f"Formatted table saved to {formatted_csv_path}")
    
    # Also create an Excel file for better visualization
    excel_path = "wahlumfragen_formatted_table.xlsx"
    formatted_df.to_excel(excel_path)
    print(f"Formatted table also saved to {excel_path}")

if __name__ == "__main__":
    create_formatted_table()