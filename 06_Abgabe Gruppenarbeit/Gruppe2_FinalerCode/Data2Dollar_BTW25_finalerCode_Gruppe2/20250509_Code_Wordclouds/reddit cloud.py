import csv
import re
from collections import Counter
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import os

# Whitelist (aktualisiert)
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

print("Looking for Reddit data files...")

# Check if the Reddit data files exist
comments_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r_de_comments_20241101_20250401_v11.csv")
posts_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "r_de_posts_20241101_20250401_v11.csv")

if not os.path.exists(comments_file):
    print(f"Warning: Comments file not found: {comments_file}")
    
if not os.path.exists(posts_file):
    print(f"Warning: Posts file not found: {posts_file}")

if not os.path.exists(comments_file) and not os.path.exists(posts_file):
    raise FileNotFoundError("Reddit data files not found. Please make sure the files are in the correct directory.")

# 1) Häufigkeiten aus r/de-Kommentaren und -Posts zählen
freq = Counter()
pattern = re.compile(r"\[.*?\]")
comment_count = 0
post_count = 0

# Kommentare
if os.path.exists(comments_file):
    print(f"Reading comments from: {comments_file}")
    with open(comments_file, encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            comment_count += 1
            text = row.get('body', '') or ''
            clean = pattern.sub('', text).lower()
            for w in re.findall(r"\b[a-zäöüß]{3,}\b", clean):
                if w in whitelist:
                    freq[w] += 1
    print(f"Processed {comment_count} comments")

# Posts
if os.path.exists(posts_file):
    print(f"Reading posts from: {posts_file}")
    with open(posts_file, encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for row in reader:
            post_count += 1
            text = (row.get('selftext', '') or '') + ' ' + (row.get('title', '') or '')
            clean = pattern.sub('', text).lower()
            for w in re.findall(r"\b[a-zäöüß]{3,}\b", clean):
                if w in whitelist:
                    freq[w] += 1
    print(f"Processed {post_count} posts")

print(f"Processed a total of {comment_count} comments and {post_count} posts")
print(f"Found {len(freq)} matching terms in whitelist")

if len(freq) == 0:
    raise ValueError("No matching terms found in Reddit data. Cannot generate wordcloud.")

# 2) WordCloud erzeugen (16:9) mit Reddit-Orange
reddit_orange = "#FF4500"
def orange_color(word, font_size, position, orientation, random_state=None, **kwargs):
    return reddit_orange

wc = WordCloud(
    width=1600,
    height=900,
    background_color="white",
    color_func=orange_color,
    collocations=False,
    max_words=100
).generate_from_frequencies(freq)

# 3) Darstellung
plt.figure(figsize=(16, 9))
plt.imshow(wc, interpolation='bilinear')
plt.axis('off')
plt.tight_layout(pad=0)
plt.savefig('reddit_wordcloud.png')  # Save to file
print("Wordcloud saved as 'reddit_wordcloud.png'")
plt.show()

# 4) Häufigkeitsliste ausgeben
print("\nTop word frequencies:")
for word, count in freq.most_common(10):  # Show top 10 for readability
    print(f"{word}: {count}")
