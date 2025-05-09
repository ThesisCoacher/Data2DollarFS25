import csv
import re
from collections import Counter
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import os

# 1) Whitelist (wie zuvor definiert)
whitelist = {
    "parlament", "bundestag", "landtag", "eu-parlament", "regierung",
    "bundesregierung", "minister", "ministerium", "abgeordnete",
    "koalition", "opposition", "gesetz", "gesetzesentwurf", "beschluss",
    "haushalt", "etats", "finanzierung", "wahlen", "wahlkampf", "referendum",
    "petition", "wahl", "bildung", "gesundheit", "wirtschaft", "arbeit",
    "soziales", "rente", "migration", "integration", "umwelt", "klima",
    "energie", "digitalisierung", "verkehr", "heizung", "infrastruktur",
    "spd", "cdu", "csu", "fdp", "gruene", "grünen", "afd", "linke", "linken",
    "bsw", "parteien", "politiker", "wähler", "wählen", "scholz", "merz",
    "habeck", "weidel", "wagenknecht", "chrupalla", "lindner", "pistorius",
    "baerbock", "wissing", "musk", "trump", "putin", "demokratie", "freiheit",
    "gerechtigkeit", "solidarität", "chancengleichheit", "nachhaltigkeit",
    "innovationen", "investitionen", "wettbewerb", "globalisierung",
    "populismus", "kritik", "geschichte", "entscheidung", "kanzler", "kabinet",
    "ampel", "bundestagswahl", "neuwahlen", "usa", "europa", "russland",
    "ukraine", "deutschen", "deutsche", "berlin", "bayern", "steuern",
    "schulden", "schuldenbremse", "inflation", "euro", "geld", "sicherheit",
    "polizei", "verteidigung", "bundeswehr", "krieg", "menschen", "bürger",
    "gesellschaft", "familie", "kinder", "bevölkerung", "arbeitnehmer",
    "unternehmen", "projekt", "region", "stadt", "land", "deutschland",
    "staat", "ausländer", "arbeitslosigkeit", "flüchtlinge", "asyl",
    "wohlergehen"
}

# Get the full path to the CSV file in the current directory
csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Reden_mit_Session_und_Korrektur.csv")

# 2) Häufigkeiten für CDU- und CSU-Politiker zählen
freq = Counter()
pattern = re.compile(r"\[.*?\]")
with open(csv_path, encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        party = (row.get('partei') or "").upper()
        if 'CDU' in party or 'CSU' in party:
            text = (row.get('text') or '')
            clean = pattern.sub('', text).lower()
            for w in re.findall(r"\b[a-zäöüß]{3,}\b", clean):
                if w in whitelist:
                    freq[w] += 1

print(f"Processed speeches from CDU/CSU. Found {len(freq)} matching terms.")

# 3) WordCloud konfigurieren (16:9) mit einheitlichem CDU-Schwarz
cdu_black = "#000000"
def black_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
    return cdu_black

wc = WordCloud(
    width=1600,
    height=900,
    background_color="white",
    color_func=black_color_func,
    collocations=False,
    max_words=100
).generate_from_frequencies(freq)

# 4) Darstellung mit 16:9 Seitenverhältnis
plt.figure(figsize=(16, 9))
plt.imshow(wc, interpolation='bilinear')
plt.axis('off')
plt.tight_layout(pad=0)
plt.savefig('cducsu_wordcloud.png')  # Save to file
print("Wordcloud saved as 'cducsu_wordcloud.png'")
plt.show()
