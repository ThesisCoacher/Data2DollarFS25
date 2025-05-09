import pandas as pd
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.sentiment import SentimentIntensityAnalyzer
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import re

# Download NLTK data
nltk.download('punkt')
nltk.download('stopwords')
nltk.download('vader_lexicon')

def load_data(file_path):
    """Load CSV file with YouTube comments, handling formatting issues."""
    try:
        df = pd.read_csv(file_path, encoding='utf-8', on_bad_lines='skip')
        if df.empty:
            raise ValueError("The CSV file is empty.")
        return df
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}. Please check the file path.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Error loading data: {e}")
        return pd.DataFrame()

def clean_text(text):
    """Clean text by removing special characters, numbers, and stopwords."""
    if not isinstance(text, str):
        return ''
    
    # Remove score predictions like 2:1, 3-0 etc.
    text = re.sub(r'\b\d+[:;-]\d+\b', '', text)
    
    # Remove single numbers
    text = re.sub(r'\b\d+\b', '', text)
    
    # Remove special characters except basic punctuation and German umlauts
    text = re.sub(r'[^\w\säöüßÄÖÜ]', '', text)
    
    # German stopwords
    stop_words = set(stopwords.words('german'))
    tokens = word_tokenize(text.lower())
    tokens = [word for word in tokens if word.isalpha() and word not in stop_words]
    
    return ' '.join(tokens)

def analyze_sentiment(df):
    """Perform sentiment analysis on comments."""
    sia = SentimentIntensityAnalyzer()
    
    # Enhance VADER with German sentiment words
    german_lexicon = {
        'gut': 2, 'super': 3, 'toll': 2, 'stark': 2, 'geil': 3, 'liebe': 2,
        'schlecht': -2, 'schwach': -2, 'schlimm': -2, 'mies': -3, 'ärgern': -2
    }
    sia.lexicon.update(german_lexicon)
    
    df['sentiment'] = df['comment'].apply(lambda x: sia.polarity_scores(str(x))['compound'])
    df['sentiment_label'] = df['sentiment'].apply(
        lambda x: 'positive' if x > 0.05 else ('negative' if x < -0.05 else 'neutral')
    )
    return df

def generate_wordcloud(df, save_path="wordcloud.png"):
    """Generate and save a word cloud."""
    text = ' '.join(df['comment'].astype(str))
    wordcloud = WordCloud(width=800, height=400, 
                         background_color='white',
                         colormap='viridis',
                         max_words=100).generate(text)
    
    plt.figure(figsize=(12, 6))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()
    print(f"Word cloud saved to {save_path}")

def analyze_comments(df):
    """Perform full analysis and save results."""
    # Basic stats
    print(f"\nTotal comments analyzed: {len(df)}")
    
    # Sentiment distribution
    if 'sentiment_label' in df.columns:
        sentiment_dist = df['sentiment_label'].value_counts(normalize=True) * 100
        print("\nSentiment Distribution (%):")
        print(sentiment_dist)
    else:
        print("\nSentiment analysis failed - no sentiment labels generated")
    
    # Save results
    output_file = "analyzed_comments.csv"
    df.to_csv(output_file, index=False)
    print(f"\nResults saved to {output_file}")

def main():
    try:
        file_path = 'YT_Comments_Roh.csv'
        print("Loading data...")
        df = load_data(file_path)
        
        if df.empty:
            print("Error: No data loaded. Check your CSV file format.")
            return
        
        # Ensure we have the expected columns
        if 'comment' not in df.columns:
            print("Error: 'comment' column not found in the data.")
            return
        
        print("Cleaning comments...")
        df['cleaned_comment'] = df['comment'].apply(clean_text)
        
        print("Analyzing sentiment...")
        df = analyze_sentiment(df)
        
        print("Generating word clouds...")
        if 'sentiment' in df.columns:
            generate_wordcloud(df[df['sentiment'] > 0.2], "positive_wordcloud.png")
            generate_wordcloud(df[df['sentiment'] < -0.2], "negative_wordcloud.png")
        generate_wordcloud(df, "all_comments_wordcloud.png")
        
        analyze_comments(df)
        
    except Exception as e:
        print(f"\nError during processing: {e}")

if __name__ == "__main__":
    main()