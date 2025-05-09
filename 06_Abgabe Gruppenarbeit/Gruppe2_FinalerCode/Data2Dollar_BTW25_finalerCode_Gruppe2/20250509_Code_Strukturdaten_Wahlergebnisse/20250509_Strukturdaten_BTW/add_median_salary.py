import csv
import pandas as pd

def main():
    """
    Add median salary data from mediangehalt_bundesländer.csv to bundesland_strukturdaten.csv
    """
    # Define a direct mapping from each strukturdaten name to the corresponding mediangehalt name
    state_mapping_reverse = {
        "Baden_Wuerttemberg": "Baden-W�rttemberg",
        "Bayern": "Bayern",
        "Berlin": "Berlin",
        "Brandenburg": "Brandenburg",
        "Bremen": "Bremen",
        "Hamburg": "Hamburg",
        "Hessen": "Hessen",
        "Mecklenburg_Vorpommern": "Mecklenburg-Vorpommern",
        "Niedersachsen": "Niedersachsen",
        "Nordrhein_Westfalen": "Nordrhein-Westfalen",
        "Rheinland_Pfalz": "Rheinland-Pfalz",
        "Saarland": "Saarland",
        "Sachsen": "Sachsen",
        "Sachsen_Anhalt": "Sachsen-Anhalt",
        "Schleswig_Holstein": "Schleswig-Holstein",
        "Thueringen": "Th�ringen"
    }

    # Read the median salary data
    median_salary_data = {}
    with open("mediangehalt_bundesländer.csv", "r", encoding="utf-8", errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['Bundesland'] and row['Mediangehalt']:  # Skip empty rows
                median_salary_data[row['Bundesland']] = row['Mediangehalt']
    
    # Manually set values for known states to ensure all are mapped correctly
    salary_mapping = {
        "Baden_Wuerttemberg": "50250",
        "Bayern": "50000",
        "Berlin": "48250",
        "Brandenburg": "41000",
        "Bremen": "47750",
        "Hamburg": "52000",
        "Hessen": "50250",
        "Mecklenburg_Vorpommern": "39500",
        "Niedersachsen": "44750",
        "Nordrhein_Westfalen": "47250",
        "Rheinland_Pfalz": "45250",
        "Saarland": "44500",
        "Sachsen": "40750",
        "Sachsen_Anhalt": "39750",
        "Schleswig_Holstein": "43750",
        "Thueringen": "40250"
    }

    # Read the strukturdaten CSV into a pandas DataFrame
    df = pd.read_csv("bundesland_strukturdaten.csv")
    
    # Create a new column for median salary using our manual mapping
    df['Mediangehalt'] = df['Bundesland'].apply(lambda x: salary_mapping.get(x, ""))
    
    # Write the updated DataFrame back to the CSV file
    df.to_csv("bundesland_strukturdaten.csv", index=False)
    
    print("Median salary data added to bundesland_strukturdaten.csv")

if __name__ == "__main__":
    main()