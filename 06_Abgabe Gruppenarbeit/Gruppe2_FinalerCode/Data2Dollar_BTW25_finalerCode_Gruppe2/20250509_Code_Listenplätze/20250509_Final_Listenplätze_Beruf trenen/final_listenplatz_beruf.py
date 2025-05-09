import pandas as pd
import re

# Read the CSV file
input_file = 'final_listenplatz_mit_alter.csv'
output_file = 'final_listenplatz_beruf_processed.csv'

# Read the CSV file
df = pd.read_csv(input_file)

# Create new columns
df['beruf1'] = ''
df['beruf2'] = ''
df['mdb'] = False

# Process each row
for index, row in df.iterrows():
    beruf = str(row['beruf']) if not pd.isna(row['beruf']) else ""
    
    # Check if MdB or Mitglied des Deutschen Bundestages is present
    is_mdb = False
    if "MdB" in beruf or "Mitglied des Deutschen Bundestages" in beruf:
        is_mdb = True
    
    # Remove MdB and Mitglied des Deutschen Bundestages from the beruf string
    beruf = beruf.replace("MdB", "").replace("Mitglied des Deutschen Bundestages", "")
    
    # Clean up the remaining string (remove commas at beginning/end, multiple commas, extra spaces)
    beruf = re.sub(r'^[,\s]+|[,\s]+$', '', beruf)
    beruf = re.sub(r',\s*,', ',', beruf)
    beruf = re.sub(r'\s+', ' ', beruf)
    
    # Split the remaining occupations by comma
    berufe = [b.strip() for b in beruf.split(',') if b.strip()]
    
    # Assign beruf1 and beruf2 if available
    if len(berufe) >= 1:
        df.at[index, 'beruf1'] = berufe[0]
    if len(berufe) >= 2:
        df.at[index, 'beruf2'] = berufe[1]
    
    # Set mdb flag
    df.at[index, 'mdb'] = is_mdb

# Save the result
df.to_csv(output_file, index=False)

print(f"Processing complete. Results saved to {output_file}")