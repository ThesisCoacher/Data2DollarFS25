import pandas as pd

# Read the processed CSV file
df = pd.read_csv('final_listenplatz_beruf_processed.csv')

# Get unique parties and sort them alphabetically
unique_parties = sorted(df['partei'].unique())

# Print the result
print("Unique parties in the dataset:")
print("=============================")
for party in unique_parties:
    print(party)

print(f"\nTotal unique parties: {len(unique_parties)}")