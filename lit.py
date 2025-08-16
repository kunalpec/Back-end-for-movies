from googleapiclient.discovery import build

API_KEY = "AIzaSyDRXI7MnhdbKoqQqnAi3rCr-P3XiTOUn44"
youtube = build('youtube', 'v3', developerKey=API_KEY)

def get_full_movie_url(movie_name):
    # Add "full movie" to the search for better results
    query = f"{movie_name} full movie"
    
    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=5,       # get multiple results to check duration
        videoDuration="long" # only long videos (over 20 minutes)
    )
    
    response = request.execute()
    
    # Return the first likely full movie
    for item in response['items']:
        video_id = item['id']['videoId']
        title = item['snippet']['title'].lower()
        if "full movie" in title:  # simple check in the title
            return f"https://www.youtube.com/watch?v={video_id}"
    
    # fallback: return the first result anyway
    first_video_id = response['items'][0]['id']['videoId']
    return f"https://www.youtube.com/watch?v={first_video_id}"

# Example usage
movie_name = "Iron Man"
url = get_full_movie_url(movie_name)
print("Likely movie URL:", url)
