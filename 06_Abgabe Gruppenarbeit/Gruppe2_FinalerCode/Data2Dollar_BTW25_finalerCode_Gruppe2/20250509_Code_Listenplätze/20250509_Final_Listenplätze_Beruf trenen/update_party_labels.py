import pandas as pd

# Read the processed CSV file
input_file = 'final_listenplatz_beruf_processed.csv'
output_file = 'final_listenplatz_beruf_processed_updated.csv'

df = pd.read_csv(input_file)

# Update party labels
df['partei'] = df['partei'].replace({
    'CDU': 'CDU/CSU', 
    'CSU': 'CDU/CSU',
    'GRÜNE': 'GRÜNE', 
    'GRÜNE/B 90': 'GRÜNE'
})

# Save the updated file
df.to_csv(output_file, index=False)

print(f"Updated CSV file saved as {output_file}")
print("\nUnique parties in the updated file:")
for party in sorted(df['partei'].unique()):
    print(f"- {party}")