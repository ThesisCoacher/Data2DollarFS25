#!/usr/bin/env python3
import praw
import pandas as pd
import concurrent.futures
import os
import json
import pickle
from datetime import datetime, timedelta
import time
from tqdm import tqdm
import logging
import sys
import re
import argparse
from praw.models import MoreComments

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("reddit_scraper.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Parse command line arguments
parser = argparse.ArgumentParser(description='Scrape Reddit posts based on keywords')
parser.add_argument('--no-cache', action='store_true', help='Ignore cached results and perform fresh searches')
parser.add_argument('--keyword', type=str, help='Scrape a single keyword instead of all')
parser.add_argument('--max-posts', type=int, default=5000, help='Maximum posts to check per keyword')
parser.add_argument('--debug', action='store_true', help='Enable debug mode with additional logging')
parser.add_argument('--comments', action='store_true', help='Scrape comments for each post (slower)')
parser.add_argument('--comment-limit', type=int, default=100, help='Maximum number of comments to scrape per post')
parser.add_argument('--comment-sort', type=str, default='top', choices=['top', 'best', 'new', 'controversial', 'old', 'qa'], 
                    help='Comment sort method')
args = parser.parse_args()

if args.debug:
    logging.getLogger().setLevel(logging.DEBUG)
    logger.debug("Debug mode enabled with verbose logging")

# Configuration
SUBREDDIT = "de"
START_DATE = datetime(2024, 11, 1)
END_DATE = datetime(2025, 4, 1)
START_TS = int(START_DATE.timestamp())
END_TS = int(END_DATE.timestamp())
MAX_POSTS_PER_KEYWORD = args.max_posts
CACHE_DIR = "scraper_cache"
USE_CACHE = not args.no_cache
COMMENTS_DIR = "comments_cache"

# Reddit API credentials
CLIENT_ID = "56pMmac9Mba5D1vtMP-AnQ"
CLIENT_SECRET = "MN0aqmex0btUr88uqF0e1Ts48h65nw"
USER_AGENT = "ElectionScraper/0.11 by noobi147"

# Keywords to search for
KEYWORDS = [
    'wahl', 'bundestag', 'politik', 'wahlen', 'söder', 'soeder', 'habeck', 
    'weidel', 'bsw', 'wagenknecht', 'buschmann', 'kuikens', 'faseer', 
    'wissing', 'heil', 'lambrecht', 'pistorius', 'özdemir', 'oezdemir', 
    'spiegel', 'paus', 'lauterbach', 'leuke', 'wattiger', 'klingel', 
    'brinkhaus', 'göring-eckhardt', 'hofreiter', 'dröge', 'droeg', 'dürr', 
    'duerr', 'gauland', 'höcke', 'hoecke', 'von storch', 'reichinnek', 
    'gysi', 'nazi', 'extreme rechte', 'rechtsextrem', 'flüchtlingspolitik', 
    'rentenpolitik', 'sozialpolitik'
]

# If a specific keyword is provided, only use that one
if args.keyword:
    if args.keyword in KEYWORDS:
        KEYWORDS = [args.keyword]
        logger.info(f"Searching for single keyword: {args.keyword}")
    else:
        logger.warning(f"Keyword '{args.keyword}' not in predefined list, but will search for it anyway")
        KEYWORDS = [args.keyword]

# Allowed flairs - more lenient now to catch more posts
ALLOWED_FLAIRS = {
    'Nachrichten DE', 'Gesellschaft', 'Kultur', 'Politik', 'Kriminalität',
    'Medien', 'Umwelt', 'Wirtschaft', 'News DE', 'Politik DE', 'News', 'Politik/News',
    'Diskussion', 'Frage', 'Fragen', 'Diskussion/Frage'
}

# Allow posts with no flair or None flair
ALLOW_NO_FLAIR = True

# Setup cache directories
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(COMMENTS_DIR, exist_ok=True)

def init_reddit():
    """Initialize Reddit API client"""
    return praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT
    )

def get_cache_filename(keyword, method_name):
    """Generate a cache filename for a keyword and method"""
    safe_keyword = re.sub(r'[^\w]', '_', keyword)
    return f"{CACHE_DIR}/{safe_keyword}_{method_name}_{START_DATE.strftime('%Y%m%d')}_{END_DATE.strftime('%Y%m%d')}.pkl"

def get_comments_cache_filename(post_id):
    """Generate a cache filename for comments of a post"""
    return f"{COMMENTS_DIR}/comments_{post_id}.pkl"

def load_from_cache(keyword, method_name):
    """Load posts from cache if available and cache usage is enabled"""
    if not USE_CACHE:
        return None
        
    cache_file = get_cache_filename(keyword, method_name)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            logger.error(f"Error loading cache for {keyword}, {method_name}: {e}")
    return None

def save_to_cache(keyword, method_name, data):
    """Save posts to cache"""
    cache_file = get_cache_filename(keyword, method_name)
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(data, f)
    except Exception as e:
        logger.error(f"Error saving cache for {keyword}, {method_name}: {e}")

def load_comments_from_cache(post_id):
    """Load comments from cache if available"""
    if not USE_CACHE:
        return None
        
    cache_file = get_comments_cache_filename(post_id)
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
                logger.debug(f"Successfully loaded comments from {cache_file}")
                return data
        except Exception as e:
            logger.error(f"Error loading comments cache for post {post_id}: {str(e)}")
    else:
        # Try alternative filenames that might exist
        # This helps with compatibility with older versions or different cache approaches
        alternative_patterns = [
            f"{COMMENTS_DIR}/comments_{post_id}.pkl",
            f"{COMMENTS_DIR}/{post_id}_comments.pkl",
            f"{COMMENTS_DIR}/comment_{post_id}.pkl"
        ]
        
        for alt_file in alternative_patterns:
            if os.path.exists(alt_file):
                try:
                    with open(alt_file, 'rb') as f:
                        data = pickle.load(f)
                        logger.debug(f"Successfully loaded comments from alternative file {alt_file}")
                        return data
                except Exception as e:
                    logger.error(f"Error loading alternative comments cache for post {post_id}: {str(e)}")
                    
    return None

def save_comments_to_cache(post_id, comments_data):
    """Save comments to cache"""
    cache_file = get_comments_cache_filename(post_id)
    try:
        with open(cache_file, 'wb') as f:
            pickle.dump(comments_data, f)
    except Exception as e:
        logger.error(f"Error saving comments cache for post {post_id}: {e}")

def process_comment(comment, level=0):
    """Process a single comment"""
    try:
        if isinstance(comment, MoreComments):
            return None
            
        comment_data = {
            "id": comment.id,
            "author": str(comment.author) if comment.author else "[deleted]",
            "body": comment.body,
            "created_utc": comment.created_utc,
            "created_date": datetime.fromtimestamp(comment.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
            "score": comment.score,
            "is_submitter": comment.is_submitter,
            "level": level,
            "permalink": comment.permalink
        }
        return comment_data
    except Exception as e:
        logger.error(f"Error processing comment {comment.id if hasattr(comment, 'id') else 'unknown'}: {str(e)}")
        return None

def get_comments_for_post(reddit, post_id, limit=100, sort='top'):
    """Get comments for a post"""
    # First check if we have cached comments
    cached_comments = load_comments_from_cache(post_id)
    if cached_comments is not None:
        logger.debug(f"Loaded {len(cached_comments)} comments from cache for post {post_id}")
        return cached_comments
    
    comments_data = []
    try:
        logger.info(f"Fetching comments for post {post_id}")
        submission = reddit.submission(id=post_id)
        submission.comment_sort = sort
        
        # Log number of comments before replacing more
        logger.info(f"Post {post_id} has {len(submission.comments)} comments before replace_more")
        
        # Don't load additional comments to avoid heavy API usage
        submission.comments.replace_more(limit=0)
        
        # Log number of comments after replacing more
        logger.info(f"Post {post_id} has {len(submission.comments)} comments after replace_more")
        
        # Process top-level comments first
        for i, top_comment in enumerate(submission.comments):
            if i >= limit:
                break
                
            comment_data = process_comment(top_comment, level=0)
            if comment_data:
                comments_data.append(comment_data)
                
                # Process replies to this comment (first level only to avoid excessive API calls)
                for j, reply in enumerate(top_comment.replies):
                    if j >= 5:  # Limit replies per comment
                        break
                    reply_data = process_comment(reply, level=1)
                    if reply_data:
                        comments_data.append(reply_data)
            
            # Add small delay to avoid rate limiting
            time.sleep(0.05)
        
        logger.info(f"Successfully processed {len(comments_data)} comments for post {post_id}")
    except Exception as e:
        logger.error(f"Error getting comments for post {post_id}: {str(e)}")
    
    # Save to cache
    if comments_data:
        save_comments_to_cache(post_id, comments_data)
        logger.info(f"Saved {len(comments_data)} comments to cache for post {post_id}")
    else:
        logger.warning(f"No comments found for post {post_id}")
        
    return comments_data

def process_submission(submission, keyword, include_comments=False):
    """Process a single submission"""
    try:
        # Get the selftext, handle deleted posts
        selftext = submission.selftext
        if selftext == "[removed]" or selftext == "[deleted]":
            selftext = ""
        
        processed = {
            "keyword": keyword,
            "id": submission.id,
            "title": submission.title,
            "selftext": selftext,
            "created_utc": submission.created_utc,
            "created_date": datetime.fromtimestamp(submission.created_utc).strftime('%Y-%m-%d %H:%M:%S'),
            "score": submission.score,
            "num_comments": submission.num_comments,
            "permalink": submission.permalink,
            "url": submission.url,
            "author": str(submission.author) if submission.author else "[deleted]",
            "flair": submission.link_flair_text,
            "upvote_ratio": submission.upvote_ratio,
            "is_original_content": submission.is_original_content,
            "is_self": submission.is_self,
            "scraped_time": datetime.now().isoformat()
        }
        
        # If comments are requested, add them to the post data
        if include_comments and submission.num_comments > 0:
            processed["has_comments_file"] = True
        
        return processed
    except Exception as e:
        logger.error(f"Error processing submission {submission.id}: {str(e)}")
        return None

def check_flair(submission):
    """Check if submission flair is allowed"""
    # If we allow posts with no flair and this post has no flair, accept it
    if ALLOW_NO_FLAIR and (submission.link_flair_text is None or submission.link_flair_text == ""):
        return True
    
    # Otherwise check if the flair is in our allowed list
    return submission.link_flair_text in ALLOWED_FLAIRS

def search_with_method(reddit, keyword, method_name, method_func, start_ts, end_ts):
    """Search using a specific method with caching"""
    # Try to load from cache if enabled
    cache_data = load_from_cache(keyword, method_name)
    if cache_data is not None:
        logger.info(f"Loaded {len(cache_data)} posts from cache for {method_name}_{keyword}")
        return cache_data
    
    posts = []
    posts_checked = 0
    seen_ids = set()
    
    logger.info(f"Performing fresh search with {method_name} for keyword '{keyword}'")
    
    try:
        with tqdm(total=MAX_POSTS_PER_KEYWORD, desc=f"{method_name}_{keyword}") as pbar:
            # For the simple case, just use the method directly
            for submission in method_func():
                posts_checked += 1
                pbar.update(1)
                
                # Skip if already seen
                if submission.id in seen_ids:
                    continue
                seen_ids.add(submission.id)
                
                # Debug: log every 100th post to see what's being checked
                if args.debug and posts_checked % 100 == 0:
                    logger.debug(f"Checking post {posts_checked}: {submission.title[:50]}... (created: {datetime.fromtimestamp(submission.created_utc)})")
                
                created = int(submission.created_utc)
                # Filter by date range
                if start_ts <= created <= end_ts:
                    # Check keyword match (case insensitive)
                    if (keyword.lower() in submission.title.lower() or 
                        (submission.selftext and keyword.lower() in submission.selftext.lower())):
                        
                        # Check if flair is allowed
                        if check_flair(submission):
                            processed = process_submission(submission, keyword, include_comments=args.comments)
                            if processed:
                                posts.append(processed)
                                
                                # If comments are requested, get them now
                                if args.comments and submission.num_comments > 0:
                                    # Get comments for this post
                                    get_comments_for_post(
                                        reddit, 
                                        submission.id, 
                                        limit=args.comment_limit,
                                        sort=args.comment_sort
                                    )
                                
                                if len(posts) % 10 == 0:
                                    logger.info(f"Found {len(posts)} matching posts for '{keyword}' with {method_name}")
                
                # Respect Reddit's rate limits
                sleep_time = 0.03 if len(posts) > 0 else 0.05
                time.sleep(sleep_time)
                
                if posts_checked >= MAX_POSTS_PER_KEYWORD:
                    break
    except Exception as e:
        logger.error(f"Error in {method_name} for '{keyword}': {str(e)}")
    
    logger.info(f"Checked {posts_checked} posts for '{keyword}' using {method_name}, found {len(posts)}")
    
    # Save to cache
    save_to_cache(keyword, method_name, posts)
    
    return posts

def process_keyword(keyword):
    """Process a single keyword with multiple search methods using time-based filtering"""
    reddit = init_reddit()
    subreddit = reddit.subreddit(SUBREDDIT)
    all_keyword_posts = []
    
    # Format timestamps for Reddit search
    # For direct time filtering in newer Reddit API:
    timestamp_filter = f"timestamp:{START_TS}..{END_TS}"
    
    # For older Reddit API versions that might not support timestamp - use alternative method
    time_period = "year"  # can be hour, day, week, month, year, all
    
    # Define search methods with time range filtering
    search_methods = [
        ('search', lambda: subreddit.search(
            f'{keyword}',  # Simplified query to catch more results
            sort='relevance',
            time_filter=time_period,
            limit=MAX_POSTS_PER_KEYWORD
        )),
        ('top', lambda: subreddit.top(
            time_filter=time_period,
            limit=MAX_POSTS_PER_KEYWORD
        )),
        ('hot', lambda: subreddit.hot(
            limit=MAX_POSTS_PER_KEYWORD
        )),
        ('new', lambda: subreddit.new(
            limit=MAX_POSTS_PER_KEYWORD
        ))
    ]
    
    # Add flair-specific searches for important flairs
    important_flairs = {'Politik', 'Nachrichten DE', 'News DE', 'Politik DE'}
    for flair in important_flairs:
        flair_query = f'{keyword} flair:"{flair}"'
        
        # Create a closure to capture the current flair value correctly
        def make_search_func(query=flair_query):
            return lambda: subreddit.search(
                query,
                sort='relevance',
                time_filter=time_period,
                limit=MAX_POSTS_PER_KEYWORD
            )
        
        search_methods.append((
            f'search_flair_{flair}',
            make_search_func()
        ))
    
    # Execute all search methods
    for method_name, method_func in search_methods:
        posts = search_with_method(
            reddit, keyword, method_name, method_func, START_TS, END_TS
        )
        all_keyword_posts.extend(posts)
    
    # Deduplicate posts
    seen_ids = set()
    unique_posts = []
    for post in all_keyword_posts:
        if post['id'] not in seen_ids:
            seen_ids.add(post['id'])
            unique_posts.append(post)
    
    logger.info(f"Found {len(unique_posts)} unique posts for keyword '{keyword}'")
    return unique_posts

def save_comments_to_csv(posts_df):
    """Save all comments for the posts to a separate CSV file"""
    if not args.comments:
        return
        
    all_comments = []
    post_ids_with_comments = 0
    total_comments = 0
    
    logger.info(f"Preparing to export comments for {len(posts_df)} posts")
    
    # List all comment cache files to see what we actually have
    comment_cache_files = os.listdir(COMMENTS_DIR) if os.path.exists(COMMENTS_DIR) else []
    logger.info(f"Found {len(comment_cache_files)} comment cache files in {COMMENTS_DIR}")
    
    with tqdm(total=len(posts_df), desc="Exporting comments") as pbar:
        for post_id in posts_df['id']:
            comments = load_comments_from_cache(post_id)
            if comments:
                for comment in comments:
                    comment['post_id'] = post_id
                    all_comments.append(comment)
                post_ids_with_comments += 1
                total_comments += len(comments)
                logger.info(f"Loaded {len(comments)} comments for post {post_id}")
            else:
                logger.warning(f"No comments found in cache for post {post_id}")
            pbar.update(1)
    
    if all_comments:
        comments_df = pd.DataFrame(all_comments)
        output_file = f"r_de_comments_{START_DATE.strftime('%Y%m%d')}_{END_DATE.strftime('%Y%m%d')}_v11.csv"
        comments_df.to_csv(output_file, index=False, encoding='utf-8')
        logger.info(f"Successfully saved {total_comments} comments from {post_ids_with_comments} posts to {output_file}")
    else:
        logger.warning("No comments were found.")

def main():
    start_time = time.time()
    logger.info(f"Starting search for posts between {START_DATE.date()} and {END_DATE.date()}")
    logger.info(f"Using timestamps: {START_TS} to {END_TS}")
    logger.info(f"Cache usage is {'DISABLED' if not USE_CACHE else 'ENABLED'}")
    logger.info(f"Maximum posts to check per keyword: {MAX_POSTS_PER_KEYWORD}")
    logger.info(f"Allow posts with no flair: {ALLOW_NO_FLAIR}")
    logger.info(f"Comments scraping: {'ENABLED' if args.comments else 'DISABLED'}")
    if args.comments:
        logger.info(f"  Comment limit per post: {args.comment_limit}")
        logger.info(f"  Comment sort method: {args.comment_sort}")
    
    # Use parallel processing for keywords
    all_posts = []
    
    # Use ThreadPoolExecutor for concurrent processing
    max_workers = min(3, len(KEYWORDS))  # Reduced workers to avoid rate limiting
    logger.info(f"Using {max_workers} parallel workers for {len(KEYWORDS)} keywords")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_keyword = {
            executor.submit(process_keyword, keyword): keyword 
            for keyword in KEYWORDS
        }
        
        for future in tqdm(concurrent.futures.as_completed(future_to_keyword), 
                           total=len(KEYWORDS), 
                           desc="Processing keywords"):
            keyword = future_to_keyword[future]
            try:
                posts = future.result()
                all_posts.extend(posts)
                logger.info(f"Completed processing for '{keyword}', found {len(posts)} posts")
            except Exception as e:
                logger.error(f"Error processing '{keyword}': {str(e)}")
    
    # Remove duplicates based on post ID
    seen_ids = set()
    unique_posts = []
    for post in all_posts:
        if post['id'] not in seen_ids:
            seen_ids.add(post['id'])
            unique_posts.append(post)
    
    logger.info(f"Total unique posts found across all keywords: {len(unique_posts)}")
    
    # Save to CSV if we got any posts
    if unique_posts:
        df = pd.DataFrame(unique_posts)
        output_file = f"r_de_posts_{START_DATE.strftime('%Y%m%d')}_{END_DATE.strftime('%Y%m%d')}_v11.csv"
        df.to_csv(output_file, index=False, encoding='utf-8')
        logger.info(f"Successfully saved {len(df)} posts to {output_file}")
        
        # Save comments if they were requested
        if args.comments:
            save_comments_to_csv(df)
    else:
        logger.warning("No posts were found. Please check the parameters and try again.")
    
    elapsed_time = time.time() - start_time
    logger.info(f"Total scraping time: {timedelta(seconds=elapsed_time)}")

if __name__ == "__main__":
    main()