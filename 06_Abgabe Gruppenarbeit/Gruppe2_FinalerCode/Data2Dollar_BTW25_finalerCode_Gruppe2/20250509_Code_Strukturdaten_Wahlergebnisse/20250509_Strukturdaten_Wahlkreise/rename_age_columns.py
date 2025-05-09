import pandas as pd

def rename_age_columns():
    """
    Rename the age columns in bundesland_strukturdaten.csv according to requirements:
    - "Alter unter 16" -> "Alter unter 18"
    - "Alter 16-17" -> "Alter 18-24"
    - "Alter 18-24" -> "Alter 25-34"
    - "Alter 25-34" -> "Alter 35-59"
    - "Alter 35-59" -> "Alter 60-74"
    - "Alter 60-74" -> "Alter über 75"
    - Delete "Alter über 75" column
    """
    # Load the CSV file
    df = pd.read_csv("bundesland_strukturdaten.csv")
    
    # Define the column renaming mapping
    columns_to_rename = {
        "Alter unter 16": "Alter unter 18",
        "Alter 16-17": "Alter 18-24",
        "Alter 18-24": "Alter 25-34",
        "Alter 25-34": "Alter 35-59",
        "Alter 35-59": "Alter 60-74",
        "Alter 60-74": "Alter über 75"
    }
    
    # Rename the columns
    df = df.rename(columns=columns_to_rename)
    
    # Drop the "Alter über 75" column
    df = df.drop(columns=["Alter über 75"], errors="ignore")
    
    # Save the updated CSV
    df.to_csv("bundesland_strukturdaten.csv", index=False)
    
    print("Age columns have been renamed and the 'Alter über 75' column has been deleted.")

if __name__ == "__main__":
    rename_age_columns()