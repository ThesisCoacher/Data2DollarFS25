import pandas as pd
import re

# Einfache Tokenisierungsfunktion
def count_tokens(text):
    if not isinstance(text, str):
        return 0
    # Einfache Tokenisierung (Wörter und Interpunktion)
    tokens = re.findall(r'\b\w+\b|[^\w\s]', text)
    return len(tokens)

# CSV-Datei einlesen
print("Lese 001.csv ein...")
df = pd.read_csv("001.csv")

# Prüfen, ob die Spalte 'text' existiert
if 'text' not in df.columns:
    print("Fehler: Die Spalte 'text' wurde nicht in der CSV-Datei gefunden.")
    exit()

# Anzahl der Tokens für jeden Text berechnen
print("Zähle Tokens in jedem Text...")
df['token_count'] = df['text'].apply(count_tokens)

# Filter für Texte mit mehr als 512 Tokens
long_texts = df[df['token_count'] > 512]

# Ergebnisse ausgeben
print(f"\nAnzahl Texte insgesamt: {len(df)}")
print(f"Anzahl Texte mit mehr als 512 Tokens: {len(long_texts)}")
print(f"Prozentsatz: {(len(long_texts) / len(df)) * 100:.2f}%")

# Detaillierte Statistiken
print("\nStatistik zur Tokenlänge:")
print(f"Minimum: {df['token_count'].min()}")
print(f"Maximum: {df['token_count'].max()}")
print(f"Durchschnitt: {df['token_count'].mean():.2f}")
print(f"Median: {df['token_count'].median()}")

# Einige Beispiele für lange Texte
if not long_texts.empty:
    print("\nBeispiele für lange Texte (>512 Tokens):")
    samples = long_texts.sample(min(3, len(long_texts)))
    for i, (idx, row) in enumerate(samples.iterrows()):
        print(f"\nBeispiel {i+1}: {row['token_count']} Tokens")
        if 'speaker' in row:
            print(f"Sprecher: {row['speaker']}")
        print(f"Text (gekürzt): {row['text'][:150]}...")

# Die Ergebnisse in einer CSV-Datei speichern
output_file = "token_analysis.csv"
df[['text', 'token_count']].to_csv(output_file, index=False)
print(f"\nVollständige Analyse wurde in '{output_file}' gespeichert.")
