import glob, json, pathlib, logging
from functools import lru_cache
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from googletrans import Translator

# Set up logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')

analyser = SentimentIntensityAnalyzer()
translator = Translator()

# Translation cache
translation_cache = {}

# Define sentiment dictionaries at module level
emoji_replacements = {
    # Positive emotions
    '🔥': 'excellent excellent',  # Doubled for emphasis
    '💪': 'very strong',
    '❤️': 'love love',  # Doubled for emphasis
    '🫶': 'love love',  # Doubled for emphasis
    '👍': 'very good',
    '🎉': 'great celebration',
    '🏆': 'amazing victory',
    '⚽': 'fantastic goal',
    '🥅': 'fantastic goal',
    '🌟': 'brilliant brilliant',  # Doubled for emphasis
    '🦁': 'very strong',
    '💯': 'perfect perfect',  # Doubled for emphasis
    '🙌': 'great celebration',
    '😊': 'very happy',
    '🫡': 'respect',
    '👏': 'excellent',
    
    # Negative emotions
    '😭': 'very very sad',  # Doubled for emphasis
    '😢': 'very sad',
    '😡': 'very angry',
    '😤': 'very frustrated',
    '💔': 'heartbroken devastated',  # Enhanced negativity
    '😩': 'very disappointed',
    '😔': 'sad disappointed',
    
    # Neutral/context (convert to empty to avoid noise)
    '⚪': '',
    '⚫': '',
    '🔴': '',
    '🔵': '',
    '🟡': '',
    '🟢': '',
}

# Football-specific sentiment boosters with enhanced emotions
football_boosters = {
    # Positive match-related terms
    'sieg': 'incredible victory amazing win spectacular',
    'tor': 'fantastic goal brilliant shot amazing',
    'gewonnen': 'brilliantly won amazing victory fantastic',
    'derby': 'crucial epic match important intense game',
    'meister': 'champions incredible achievement amazing',
    'super': 'excellent fantastic amazing',
    'geil': 'amazing fantastic spectacular',
    'stark': 'very strong excellent powerful',
    'hammer': 'incredible amazing spectacular',
    'toll': 'fantastic great wonderful',
    'klasse': 'excellent fantastic brilliant',
    'bester': 'best amazing fantastic',
    'gut': 'good excellent great',
    
    # Match attendance and support
    'stadion': 'amazing atmosphere fantastic crowd',
    'fans': 'incredible support amazing atmosphere',
    'support': 'great support amazing fans',
    'stimmung': 'great atmosphere amazing energy',
    
    # Negative terms
    'abstieg': 'terrible relegation very sad disappointing',
    'verloren': 'unfortunately lost disappointing defeat',
    'schlecht': 'very bad terrible disappointing',
    'niederlage': 'disappointing loss terrible defeat',
    'schwach': 'weak poor disappointing'
}

def preprocess_text(text):
    """Preprocess text with emoji replacements and return processed text"""
    for emoji, replacement in emoji_replacements.items():
        text = text.replace(emoji, replacement)
    return text

def preprocess_with_boosters(text):
    # First apply emoji replacements
    processed_text = preprocess_text(text)
    
    # Apply football-specific boosters
    lower_text = processed_text.lower()
    boosts = []
    
    # Check for multiple boosters and combine their effects
    for term, boost in football_boosters.items():
        if term.lower() in lower_text:
            boosts.append(boost)
    
    if boosts:
        processed_text = processed_text + ". " + " ".join(boosts)
    
    return processed_text

@lru_cache(maxsize=1000)
def translate_text(text):
    """Cache translations to avoid redundant API calls"""
    if text in translation_cache:
        return translation_cache[text]
    try:
        translation = translator.translate(text, dest='en')
        translation_cache[text] = translation.text
        return translation.text
    except Exception as e:
        logging.warning(f"Translation failed: {e}")
        return text

def analyze_text(text):
    try:
        processed_text = preprocess_with_boosters(text)
        translated_text = translate_text(processed_text)
        scores = analyser.polarity_scores(translated_text)
        
        if abs(scores['compound']) > 0.75:
            logging.info(f"Strong sentiment detected ({scores['compound']}): {text}")
        return scores
    except Exception as e:
        logging.error(f"Error in analyze_text: {str(e)}")
        return {"compound": 0.0, "pos": 0.0, "neu": 1.0, "neg": 0.0}

def get_sentiment_category(compound_score):
    if compound_score >= 0.35:  # Lowered threshold for very positive
        return "very positive"
    elif compound_score >= 0.05:  # Lowered threshold for positive
        return "positive"
    elif compound_score <= -0.35:  # Adjusted threshold for very negative
        return "very negative"
    elif compound_score <= -0.05:  # Adjusted threshold for negative
        return "negative"
    else:
        return "neutral"

def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

records = []
total_comments = 0
error_count = 0

for f in glob.glob("comments_*.json"):
    club = pathlib.Path(f).stem.replace("comments_", "").replace("_", " ").title()
    logging.info(f"Processing comments for {club}")
    
    try:
        comments = load(f)
        total_comments += len(comments)
        
        for item in comments:
            try:
                text = item["text"]
                scores = analyze_text(text)
                compound_score = scores["compound"]
                
                records.append({
                    "club": club,
                    "comment": text,
                    "compound": compound_score,
                    "pos": scores["pos"],
                    "neu": scores["neu"],
                    "neg": scores["neg"],
                    "sentiment": get_sentiment_category(compound_score)
                })
            except Exception as e:
                error_count += 1
                logging.error(f"Error processing comment for {club}: {str(e)}")
                continue
    except Exception as e:
        logging.error(f"Error loading file for {club}: {str(e)}")
        continue

logging.info(f"Processed {total_comments} comments with {error_count} errors")

df = pd.DataFrame(records)

# ---- high-level dashboard ----
# Print distribution of sentiment categories
print("\nOverall Sentiment Distribution:")
print(df['sentiment'].value_counts(normalize=True).round(3) * 100)

# Calculate statistics with explicit float handling
def safe_mean(x):
    return float(x.mean())

summary = df.groupby('club').agg({
    'compound': ['size', 'mean'],
    'pos': 'mean',
    'neg': 'mean',
    'neu': 'mean',
}).round(3)

# Flatten the multi-index columns
summary.columns = ['n_comments', 'avg_compound', 'avg_pos_score', 'avg_neg_score', 'avg_neu_score']

# Calculate sentiment category percentages
all_sentiments = ["very positive", "positive", "neutral", "negative", "very negative"]
sentiment_stats = df.groupby('club')['sentiment'].value_counts(normalize=True).unstack(fill_value=0)
sentiment_stats = sentiment_stats.reindex(columns=all_sentiments, fill_value=0)
sentiment_stats = sentiment_stats.round(3)
sentiment_stats.columns = ['pct_' + col.lower().replace(' ', '_') for col in sentiment_stats.columns]

# Combine the statistics
summary = pd.concat([summary, sentiment_stats], axis=1)

# Ensure all numeric columns except n_comments are float
numeric_columns = summary.columns.drop('n_comments')
summary[numeric_columns] = summary[numeric_columns].astype(float)

# Convert percentages and round
for col in sentiment_stats.columns:
    summary[col] = (summary[col] * 100).round(3)

# Sort by compound score
summary = summary.sort_values("avg_compound", ascending=False)

# Format the DataFrame for display and CSV output
pd.set_option('display.float_format', '{:.3f}'.format)
summary = summary.sort_values('avg_compound', ascending=False)

# Save to CSV with proper decimal formatting
summary.to_csv('club_sentiment_summary.csv', float_format='%.3f')

# Save full details
df.to_csv("all_comment_sentiments.csv", index=False, float_format='%.3f')
# Format the summary for display
print("\nSentiment Analysis Summary:")
with pd.option_context('display.float_format', '{:.3f}'.format):
    print(summary)

# show top 5 most positive / negative per club
for club, grp in df.groupby("club"):
    best = grp.nlargest(5, "compound")[["comment", "compound", "sentiment"]]
    worst = grp.nsmallest(5, "compound")[["comment", "compound", "sentiment"]]
    print(f"\n—— {club.upper()} ——")
    print("Top 5 positive comments:")
    print(best.to_string(index=False))
    print("\nTop 5 negative comments:")
    print(worst.to_string(index=False))