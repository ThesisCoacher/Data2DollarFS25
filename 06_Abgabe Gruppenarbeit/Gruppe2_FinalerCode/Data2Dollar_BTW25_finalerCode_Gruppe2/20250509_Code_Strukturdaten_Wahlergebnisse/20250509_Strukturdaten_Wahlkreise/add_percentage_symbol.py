import pandas as pd

def add_percentage_symbol():
    """
    Add a percentage sign (%) at the end of column headers for columns containing percentage values
    in the baden_wuerttemberg_wahlkreise_strukturdaten.csv file.
    """
    # Load the CSV file
    df = pd.read_csv("baden_wuerttemberg_wahlkreise_strukturdaten.csv")
    
    # List of columns that should be marked as percentages
    percentage_columns = [
        "Ausländer*innenanteil",
        "PKW Elektro oder Hybrid",
        "Schulabgänger*innen ohne Hauptschulabschluss",
        "Schulabgänger*innen mit Hauptschulabschluss",
        "Schulabgänger*innen mit Realschulabschluss",
        "Schulabgänger*innen mit allgemeiner und Fachhochschulreife",
        "Quote betreute Kinder unter 3 Jahre",
        "Quote betreute Kinder 3-5 Jahre",
        "Anteil Sozialversicherungspflichtiger in Land-, Forstwirtschaft & Fisherei",
        "Anteil Sozialversicherungspflichtiger im produzierenden Gewerbe",
        "Anteil Sozialversicherungspflichtiger im Handel, Gastgewerbe, Verkehr",
        "Anteil Sozialversicherungspflichtige öffentliche und private Dienstleister",
        "Anteil Sozialversicherungspflichtige übrige Dienstleister",
        "Anteil SGB II Empfänger*innen nichterwerbsfähige Hilfebedürftige",
        "Anteil SGB II Empfänger*innen Ausländer*innen",
        "Arbeitslosenquote insgesamt",
        "Arbeitslosenquote Männer",
        "Arbeitslosenquote Frauen",
        "Arbeitslosenquote 15-24",
        "Arbeitslosenquote 55-64",
        "Alter unter 18",
        "Alter 18-24",
        "Alter 25-34",
        "Alter 35-59",
        "Alter 60-74",
        "Alter über 75"
    ]
    
    # Create a dictionary for renaming columns
    rename_dict = {}
    for col in df.columns:
        if col in percentage_columns:
            rename_dict[col] = f"{col} %"
    
    # Rename columns
    df = df.rename(columns=rename_dict)
    
    # Save the updated CSV
    df.to_csv("baden_wuerttemberg_wahlkreise_strukturdaten.csv", index=False)
    
    print("Percentage sign (%) added to percentage column headers.")

if __name__ == "__main__":
    add_percentage_symbol()