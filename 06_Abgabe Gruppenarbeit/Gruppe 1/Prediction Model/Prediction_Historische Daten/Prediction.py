#!/usr/bin/env python3
import pandas as pd

# 1. Load historical data
df = pd.read_excel(
    '/Users/pivda/Gruppenprojekt Data2Dollar/Bundesliga_Prognosen & Ergebnisse/Oddsportal_Historische Daten/Historische Daten.xlsx',
    sheet_name='oddsportal_bundesliga_results_o'
)

# 2. Create a result column: 'H' = home win, 'D' = draw, 'A' = away win
df['result'] = df.apply(
    lambda x: 'H' if x['Score_Home Team'] > x['Score_Away Team']
              else ('A' if x['Score_Home Team'] < x['Score_Away Team'] else 'D'),
    axis=1
)

# 3. Calculate home and away win/draw/loss rates for each team
def get_team_stats(df):
    teams = set(df['Home Team']).union(set(df['Away Team']))
    stats = {}
    for team in teams:
        # Home stats
        home_games = df[df['Home Team'] == team]
        home_total = len(home_games)
        home_win = (home_games['result'] == 'H').sum()
        home_draw = (home_games['result'] == 'D').sum()
        home_loss = (home_games['result'] == 'A').sum()
        # Avoid division by zero
        if home_total > 0:
            home_win_rate = home_win / home_total
            home_draw_rate = home_draw / home_total
            home_loss_rate = home_loss / home_total
        else:
            home_win_rate = home_draw_rate = home_loss_rate = 0
        # Away stats
        away_games = df[df['Away Team'] == team]
        away_total = len(away_games)
        away_win = (away_games['result'] == 'A').sum()
        away_draw = (away_games['result'] == 'D').sum()
        away_loss = (away_games['result'] == 'H').sum()
        if away_total > 0:
            away_win_rate = away_win / away_total
            away_draw_rate = away_draw / away_total
            away_loss_rate = away_loss / away_total
        else:
            away_win_rate = away_draw_rate = away_loss_rate = 0
        stats[team] = {
            'home': {'W': home_win_rate, 'D': home_draw_rate, 'L': home_loss_rate},
            'away': {'W': away_win_rate, 'D': away_draw_rate, 'L': away_loss_rate}
        }
    return stats

team_stats = get_team_stats(df)

# 4. Prepare upcoming fixtures
upcoming = pd.DataFrame({
    'Home Team': [
        'Stuttgart',
        'Bayer Leverkusen',
        'Bayern Munich',
        'Holstein Kiel',
        'Hoffenheim',
        'Wolfsburg',
        'Eintracht Frankfurt',
        'Bochum',
        'Werder Bremen'
    ],
    'Away Team': [
        'Heidenheim',
        'Augsburg',
        'Mainz',
        'B. Monchengladbach',
        'Dortmund',
        'Freiburg',
        'RB Leipzig',
        'Union Berlin',
        'St. Pauli'
    ]
})

# 5. Predict probabilities for each match
def predict_probabilities(home_team, away_team, stats):
    # Home team at home, away team away
    home = stats.get(home_team, {'home': {'W':0, 'D':0, 'L':0}})['home']
    away = stats.get(away_team, {'away': {'W':0, 'D':0, 'L':0}})['away']
    # Average the probabilities
    prob_home_win = (home['W'] + away['L']) / 2
    prob_draw = (home['D'] + away['D']) / 2
    prob_away_win = (home['L'] + away['W']) / 2
    # Normalize to sum to 1
    total = prob_home_win + prob_draw + prob_away_win
    if total > 0:
        prob_home_win /= total
        prob_draw /= total
        prob_away_win /= total
    return prob_home_win, prob_draw, prob_away_win

print("\n=== Upcoming Matches: Historic Win/Draw/Loss Probabilities ===")
results = []
for idx, row in upcoming.iterrows():
    home, away = row['Home Team'], row['Away Team']
    pH, pD, pA = predict_probabilities(home, away, team_stats)
    print(f"\n{home} vs {away}:")
    print(f"  Home win:  {pH:.2%}")
    print(f"  Draw:      {pD:.2%}")
    print(f"  Away win:  {pA:.2%}")
    results.append({
        'Home Team': home,
        'Away Team': away,
        'Home Win Probability': pH,
        'Draw Probability': pD,
        'Away Win Probability': pA
    })

# Export to Excel
df_results = pd.DataFrame(results)
df_results.to_excel('upcoming_predictions.xlsx', index=False)
print("\nPredictions exported to upcoming_predictions.xlsx")