# Youtube Videos:
# https://www.youtube.com/watch?v=d9uRPjuoMZ4 - VIDEO_ID = "d9uRPjuoMZ4"
# https://www.youtube.com/watch?v=SgrLOZ4VLI8 - VIDEO_ID = "SgrLOZ4VLI8"
# https://www.youtube.com/watch?v=ITczp7xVUNs - VIDEO_ID = "ITczp7xVUNs"
# https://www.youtube.com/watch?v=1_h3SPRvBIw - VIDEO_ID = "1_h3SPRvBIw"
# https://www.youtube.com/watch?v=WYhOT9QreGk - VIDEO_ID = "WYhOT9QreGk"
# https://www.youtube.com/watch?v=F36X70kDTFE - VIDEO_ID = "F36X70kDTFE"
# https://www.youtube.com/watch?v=V95QMDOET90 - VIDEO_ID = "V95QMDOET90"
# https://www.youtube.com/watch?v=mfnRMrPcwNU - VIDEO_ID = "mfnRMrPcwNU"
# 

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd

# Replace with your YouTube API Key
DEVELOPER_KEY = "AIzaSyBWz3lTHE0wsL2ce_CU6ap5iUoDhTXstlc"

# List of video IDs
VIDEO_IDS = [
    "d9uRPjuoMZ4",
    "SgrLOZ4VLI8",
    "ITczp7xVUNs",
    "1_h3SPRvBIw",
    "WYhOT9QreGk",
    "F36X70kDTFE",
    "V95QMDOET90",
    "mfnRMrPcwNU"
]

def get_comments(video_id, part="snippet", max_results=100):
    """
    Function to get comments from a YouTube video

    Args:
        video_id: The ID of the YouTube video
        part: The part of the comment snippet to retrieve. Defaults to "snippet".
        max_results: The maximum number of comments to retrieve. Defaults to 100.

    Returns:
        A list of dictionaries containing comment text and number of likes.
    """
    youtube = build("youtube", "v3", developerKey=DEVELOPER_KEY)

    try:
        # Retrieve comment thread using the youtube.commentThreads().list() method
        response = youtube.commentThreads().list(
            part=part,
            videoId=video_id,
            textFormat="plainText",
            maxResults=max_results
        ).execute()

        comments = []
        for item in response["items"]:
            comment_text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            likes = item["snippet"]["topLevelComment"]["snippet"]["likeCount"]
            comments.append({"comment": comment_text, "num_of_likes": likes})

        return comments
    except HttpError as error:
        print(f"An HTTP error {error.http_status} occurred:\n {error.content}")
        return None

def main():
    for video_id in VIDEO_IDS:
        # Get comments from the video
        comments = get_comments(video_id)

        if comments:
            # Create a pandas dataframe from the comments list
            df = pd.DataFrame(comments)

            # Sort dataframe by number of likes in descending order
            df = df.sort_values(by=['num_of_likes'], ascending=False)

            # Print a preview of the first 10 rows
            print(f"Comments for video ID {video_id}:")
            print(df.head(10))

            # Export dataframe to a CSV file named "<video_id>_comments.csv"
            csv_filename = f"{video_id}_comments.csv"
            df.to_csv(csv_filename, index=False)
            print(f"Comments for video ID {video_id} saved to {csv_filename}")
        else:
            print(f"Error: Could not retrieve comments from video ID {video_id}.")

if __name__ == "__main__":
    main()