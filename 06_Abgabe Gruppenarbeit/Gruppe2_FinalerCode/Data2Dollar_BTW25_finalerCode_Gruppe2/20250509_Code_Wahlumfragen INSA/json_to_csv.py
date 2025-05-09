import json
import csv

# Read the JSON data from the updated file
json_file = "insa_polling_data_updated.json"
csv_file = "insa_polling_data.csv"

# Open and load the JSON data
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Check if we have any data
if not data:
    print("No data found in the JSON file.")
    exit(1)

# Fill in "INSA" as the institute for all records
# and clean up the polling data to be decimal numbers (remove % sign)
for item in data:
    item['institute'] = "INSA"
    
    # Process each party's poll value
    for key, value in list(item.items()):
        if key not in ['date', 'institute'] and value:
            # Remove the percentage sign and any whitespace
            cleaned_value = value.replace('%', '').strip()
            
            # If it's a number (not "–"), convert to decimal
            if cleaned_value and cleaned_value != "–":
                try:
                    # Convert to float and divide by 100 to get the decimal value
                    # The comma is already being used as decimal separator in the data
                    decimal_value = float(cleaned_value.replace(',', '.')) / 100
                    # Format to show with decimal dot for CSV (no need to replace dots with commas)
                    item[key] = str(decimal_value)
                except ValueError:
                    # If conversion fails, keep as string
                    pass

# Determine the fieldnames (column headers) from the first item
# First ensure we have consistent fields across all items
all_keys = set()
for item in data:
    all_keys.update(item.keys())

# Sort the fields to make sure they appear in a sensible order
# Putting 'date' first, followed by 'institute', then all parties
fieldnames = ['date', 'institute']
party_names = [key for key in all_keys if key not in ['date', 'institute']]
# Sort party names to ensure consistent order
party_names.sort()
fieldnames.extend(party_names)

# Write the data to a CSV file
with open(csv_file, 'w', encoding='utf-8', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)

print(f"Successfully converted {json_file} to {csv_file}")
print(f"The CSV file contains {len(data)} records with the following fields: {', '.join(fieldnames)}")
print("All records have 'INSA' set as the institute.")
print("Percentage values have been converted to decimal numbers with dots as separators (e.g., 30% → 0.3).")