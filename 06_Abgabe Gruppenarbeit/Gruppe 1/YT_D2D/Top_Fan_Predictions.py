import pandas as pd
from collections import defaultdict
import glob

def analyze_predictions(file_pattern):
    # Alle CSV-Dateien finden
    files = glob.glob(file_pattern)
    
    # Dictionary für alle Ergebnisse
    all_results = {}
    
    for file in files:
        # Match-Namen aus Dateiname extrahieren
        match_name = file.split('_')[-1].split('.')[0].replace('-', ' vs ')
        
        try:
            # Daten einlesen
            df = pd.read_csv(file)
            
            # Dictionary für gewichtete Zählung der Vorhersagen
            weighted_predictions = defaultdict(int)
            
            # Durch jede Zeile iterieren
            for _, row in df.iterrows():
                prediction = str(row['prediction']).strip()
                likes = row['likes']
                
                # Gewichtete Zählung (jede Vorhersage zählt so viel wie ihre Likes + 1)
                weighted_predictions[prediction] += likes + 1
            
            # Ergebnisse sortieren
            sorted_predictions = sorted(weighted_predictions.items(), key=lambda x: x[1], reverse=True)
            
            # Top 3 Vorhersagen speichern
            top_predictions = []
            for pred, weight in sorted_predictions[:6]:
                percentage = (weight / sum(weighted_predictions.values())) * 100
                top_predictions.append(f"{pred} ({percentage:.1f}%)")
            
            # Gesamtzahl der Stimmen
            total_votes = sum(weighted_predictions.values())
            
            # In all_results speichern
            all_results[match_name] = {
                'Top Predictions': " | ".join(top_predictions),
                'Total Votes': total_votes,
                'Most Liked Prediction': sorted_predictions[0][0],
                'Most Liked Score': sorted_predictions[0][1]
            }
            
        except Exception as e:
            print(f"Fehler bei der Verarbeitung von {file}: {str(e)}")
            continue
    
    # DataFrame erstellen und speichern
    result_df = pd.DataFrame.from_dict(all_results, orient='index')
    result_df.index.name = 'Match'
    result_df.to_csv('topfan_predictions.csv', encoding='utf-8-sig')
    
    return result_df

# Alle CSV-Dateien analysieren
file_pattern = 'predictions_*.csv'
results = analyze_predictions(file_pattern)

# Ergebnisse anzeigen
print("Analyse abgeschlossen. Ergebnisse wurden in 'topfan_predictions.csv' gespeichert.")
print("\nZusammenfassung der Ergebnisse:")
print(results)