import pandas as pd
from collections import defaultdict

# Daten einlesen
df = pd.read_csv('predictions_FCB-M05.csv')

# Dictionary für gewichtete Zählung der Vorhersagen
weighted_predictions = defaultdict(int)

# Durch jede Zeile iterieren
for _, row in df.iterrows():
    prediction = row['prediction']
    likes = row['likes']
    
    # Gewichtete Zählung (jede Vorhersage zählt so viel wie ihre Likes)
    weighted_predictions[prediction] += likes + 1  # +1 um auch Vorhersagen mit 0 Likes zu berücksichtigen

# Ergebnisse sortieren
sorted_predictions = sorted(weighted_predictions.items(), key=lambda x: x[1], reverse=True)

# Ergebnisse ausgeben
print("Häufigste Ergebnisvorhersagen (gewichtet nach Likes):")
for pred, weight in sorted_predictions[:10]:  # Top 10 anzeigen
    print(f"{pred}: {weight} Punkte (Gewichtung)")

# Gesamtzahl der Vorhersagen analysieren
total_weight = sum(weighted_predictions.values())
print(f"\nGesamtgewicht aller Vorhersagen: {total_weight}")

# Prozentuale Verteilung der Top-Vorhersagen
print("\nProzentuale Verteilung der Top-Vorhersagen:")
for pred, weight in sorted_predictions[:5]:
    percentage = (weight / total_weight) * 100
    print(f"{pred}: {percentage:.1f}%")