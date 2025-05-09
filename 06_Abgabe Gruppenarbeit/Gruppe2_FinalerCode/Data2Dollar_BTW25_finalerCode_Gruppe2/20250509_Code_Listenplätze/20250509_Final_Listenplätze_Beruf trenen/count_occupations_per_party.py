import pandas as pd
from collections import Counter
import re

# Function to normalize job titles (combine male/female versions)
def normalize_occupation(occupation):
    if pd.isna(occupation) or occupation == '':
        return ''
    
    # Common German female suffix patterns
    patterns = [
        (r'in$', ''),           # e.g., Lehrerin -> Lehrer
        (r'innen$', ''),        # e.g., Lehrerinnen -> Lehrer
        (r'frau$', 'mann'),     # e.g., Kauffrau -> Kaufmann
        (r'frauen$', 'männer'), # e.g., Kauffrauen -> Kaufmänner
    ]
    
    # Direct mappings for special cases
    direct_mappings = {
        'Studentin': 'Student', 
        'Ärztin': 'Arzt',
        'Tierärztin': 'Tierarzt',
        'Rechtsanwältin': 'Rechtsanwalt',
        'Unternehmerin': 'Unternehmer',
        'Projektmanagerin': 'Projektmanager',
        'Softwareentwicklerin': 'Softwareentwickler',
        'Professorin': 'Professor',
        'Gewerkschaftssekretärin': 'Gewerkschaftssekretär',
        'Wissenschaftlerin': 'Wissenschaftler',
        'Politikwissenschaftlerin': 'Politikwissenschaftler',
        'Dipl.-Kauffrau': 'Dipl.-Kaufmann',
        'Wirtschaftsingenieurin': 'Wirtschaftsingenieur',
        'Ingenieurin': 'Ingenieur',
        'Angestellte': 'Angestellter',
        'Rentnerin': 'Rentner',
        'Physikerin': 'Physiker',
        'Beamtin': 'Beamter',
        'Journalistin': 'Journalist',
        'Managerin': 'Manager',
        'Freischaffende': 'Freischaffender',
        'Rentenschaffende': 'Rentenschaffender',
        'Selbstständige': 'Selbstständiger'
    }
    
    # Check direct mappings first
    if occupation in direct_mappings:
        return direct_mappings[occupation]
    
    # Try applying patterns
    normalized = occupation
    for pattern, replacement in patterns:
        if re.search(pattern, normalized):
            normalized = re.sub(pattern, replacement, normalized)
            break
            
    return normalized

# Read the updated CSV file with combined party labels
input_file = 'final_listenplatz_beruf_processed_updated.csv'
df = pd.read_csv(input_file)

# Get unique parties
parties = df['partei'].unique()

# Create a dictionary to store results
results = {}

# Process each party
for party in parties:
    # Filter dataframe for the current party
    party_df = df[df['partei'] == party]
    
    # Collect all occupations (both beruf1 and beruf2)
    occupations = []
    
    # Add non-empty beruf1 values with normalization
    occupations.extend([normalize_occupation(beruf) for beruf in party_df['beruf1'].dropna() if beruf != ''])
    
    # Add non-empty beruf2 values with normalization
    occupations.extend([normalize_occupation(beruf) for beruf in party_df['beruf2'].dropna() if beruf != ''])
    
    # Remove any empty strings that might have resulted from normalization
    occupations = [occ for occ in occupations if occ != '']
    
    # Count occupations
    occupation_counts = Counter(occupations)
    
    # Get top 5 occupations
    top_occupations = occupation_counts.most_common(5)
    
    # Store results
    results[party] = top_occupations

# Print results
print("Top 5 occupations per party (normalized gender forms):")
print("==================================================\n")

for party, occupations in results.items():
    print(f"\n{party}:")
    print("-" * len(party))
    
    if occupations:
        for i, (occupation, count) in enumerate(occupations, 1):
            print(f"{i}. {occupation}: {count}")
    else:
        print("No occupation data available")

# Save results to CSV
output_rows = []
max_occupations = 0

for party, occupations in results.items():
    row = {'party': party}
    
    for i, (occupation, count) in enumerate(occupations, 1):
        row[f'occupation_{i}'] = occupation
        row[f'count_{i}'] = count
    
    max_occupations = max(max_occupations, len(occupations))
    output_rows.append(row)

# Ensure all rows have the same columns
for row in output_rows:
    for i in range(1, max_occupations + 1):
        if f'occupation_{i}' not in row:
            row[f'occupation_{i}'] = ''
            row[f'count_{i}'] = 0

# Create and save output dataframe
output_df = pd.DataFrame(output_rows)
output_df.to_csv('updated_top_normalized_occupations_per_party.csv', index=False)

print("\nResults saved to updated_top_normalized_occupations_per_party.csv")