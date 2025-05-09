import pandas as pd
import re

# Definition der Spiele des 31. Spieltags
matches = [
    {"home": "Bayer 04 Leverkusen", "away": "FC Augsburg", "short": "LEV-FCA"},
    {"home": "VfB Stuttgart", "away": "1. FC Heidenheim", "short": "VFB-FCH"},
    {"home": "Bayern München", "away": "1. FSV Mainz 05", "short": "FCB-M05"},
    {"home": "Eintracht Frankfurt", "away": "RB Leipzig", "short": "SGE-RBL"},
    {"home": "TSG Hoffenheim", "away": "Borussia Dortmund", "short": "TSG-BVB"},
    {"home": "Werder Bremen", "away": "FC St. Pauli", "short": "SVW-STP"},
    {"home": "VfL Wolfsburg", "away": "SC Freiburg", "short": "WOB-SCF"},
    {"home": "VfL Bochum", "away": "1. FC Union Berlin", "short": "BOC-FCU"},
    {"home": "Holstein Kiel", "away": "Borussia Mönchengladbach", "short": "KSV-BMG"}
]

# Aliase für die Teams zur besseren Erkennung
team_aliases = {
    "Bayer 04 Leverkusen": ["Leverkusen", "B04", "LEV"],
    "FC Augsburg": ["Augsburg", "FCA"],
    "VfB Stuttgart": ["Stuttgart", "VfB", "VFB"],
    "1. FC Heidenheim": ["Heidenheim", "FCH"],
    "Bayern München": ["Bayern", "FCB", "München"],
    "1. FSV Mainz 05": ["Mainz", "M05"],
    "Eintracht Frankfurt": ["Frankfurt", "SGE"],
    "RB Leipzig": ["Leipzig", "RBL"],
    "TSG Hoffenheim": ["Hoffenheim", "TSG"],
    "Borussia Dortmund": ["Dortmund", "BVB"],
    "Werder Bremen": ["Bremen", "SVW"],
    "FC St. Pauli": ["St. Pauli", "Pauli"],
    "VfL Wolfsburg": ["Wolfsburg", "WOB"],
    "SC Freiburg": ["Freiburg", "SCF"],
    "VfL Bochum": ["Bochum", "BOC"],
    "1. FC Union Berlin": ["Union", "Union Berlin", "FCU"],
    "Holstein Kiel": ["Kiel", "KSV"],
    "Borussia Mönchengladbach": ["Gladbach", "M'gladbach", "BMG"]
}

# Regex-Muster für Ergebnisvorhersagen
pattern = re.compile(
    r'(?:^|\s)(\b[\w\s\.]+\b)\s*[-:vs]+\s*(\b[\w\s\.]+\b)\s*(\d+)[:\-](\d+)(?:\s|$)',
    flags=re.IGNORECASE
)

def extract_predictions(comment):
    predictions = []
    for match in pattern.finditer(comment):
        team1, team2, score1, score2 = match.groups()
        predictions.append({
            'team1': team1.strip(),
            'team2': team2.strip(),
            'prediction': f"{score1}:{score2}"
        })
    return predictions

def is_relevant_comment(comment):
    if not comment or len(comment) < 10:
        return False
    if any(word in comment.lower() for word in ["http", "www", "instagram", "telegram", "youtube"]):
        return False
    return True

# Daten laden und bereinigen
df = pd.read_csv('YT_Comments_Roh.csv')
df['comment'] = df['comment'].astype(str)
df = df[df['comment'].apply(is_relevant_comment)]

# Für jedes Spiel eine separate CSV erstellen
for match in matches:
    home = match["home"]
    away = match["away"]
    short = match["short"]
    
    # Alle Aliases für die Teams
    home_aliases = [home] + team_aliases.get(home, [])
    away_aliases = [away] + team_aliases.get(away, [])
    
    # DataFrame für dieses Spiel
    match_data = []
    
    for _, row in df.iterrows():
        comment = row['comment']
        predictions = extract_predictions(comment)
        
        for pred in predictions:
            # Prüfe ob die Vorhersage zu diesem Spiel gehört
            team1_match = any(alias.lower() in pred['team1'].lower() for alias in home_aliases)
            team2_match = any(alias.lower() in pred['team2'].lower() for alias in away_aliases)
            
            if team1_match and team2_match:
                match_data.append({
                    'comment': comment,
                    'prediction': pred['prediction'],
                    'likes': row['num_of_likes']
                })
    
    if match_data:
        match_df = pd.DataFrame(match_data)
        filename = f"predictions_{short.replace(' ', '_')}.csv"
        match_df.to_csv(filename, index=False)
        print(f"✅ {len(match_df)} Vorhersagen für {home} vs {away} gespeichert als {filename}")
    else:
        print(f"⚠️ Keine Vorhersagen gefunden für {home} vs {away}")

print("Alle Vorhersagen wurden verarbeitet.")