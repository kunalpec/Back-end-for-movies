from googleapiclient.discovery import build
from django.http import HttpResponse
from sklearn.metrics.pairwise import cosine_similarity
from rest_framework.decorators import api_view
from rest_framework.response import Response
import pandas as pd
import pickle
import joblib
import numpy as np
import os
import json

# ----------------------------
# Load data
# ----------------------------
genre_data = pickle.load(open('static/genre_data.pkl', 'rb'))
movie_data = pickle.load(open('static/movies_data_new.pkl', 'rb'))

# ----------------------------
# Load compressed vectors
# ----------------------------
# For genre vectors
genre_vector = joblib.load('static/vectors_genre_file.pkl').astype(np.float32)

# For movie vectors
movie_vector = joblib.load('static/vectors_movie_file_new.pkl').astype(np.float32)

# ----------------------------
# Load TF-IDF matrices
# ----------------------------
genre_tfidf = pickle.load(open('static/genre_tfidf.pkl', 'rb'))
movie_tfidf = pickle.load(open('static/movie_tfidf.pkl', 'rb'))

# List of supported genres
sending_genre_list = [
    "action", "comedy", "drama", "horror", "romance",
    "thriller", "science", "fantasy", "animation", "adventure", "crime"
]

sending_genre = {
    "Action": "action",
    "Comedy": "comedy",
    "Drama": "drama",
    "Horror": "horror",
    "Romance": "romance",
    "Thriller": "thriller",
    "Science": "science",
    "Fantasy": "fantasy",
    "Animation": "animation",
    "Adventure": "adventure",
    "Crime": "crime",
}

# YouTube API setup
API_KEY = "AIzaSyDRXI7MnhdbKoqQqnAi3rCr-P3XiTOUn44"
youtube = build('youtube', 'v3', developerKey=API_KEY)

# ----------------------------
# Django views
# ----------------------------
def index(request):
    return HttpResponse("hello")


@api_view(['GET'])
def movie_detail(request):
    name = request.GET.get('name', '')
    if name == '':
        return Response({"error": "Movie name is required."}, status=400)

    data = recommend_movie(name, top_n=20)
    results = [{"title": title, "poster": poster} for title, poster in data[:20]]
    print("kunal")
    return Response(results)


@api_view(['GET'])
def genre_detail(request):
    name = request.GET.get('name', '')
    print(name)
    
    if name not in sending_genre:
        return Response({"error": "Invalid genre name."}, status=400)
    
    name = sending_genre[name]
    print(name)
    
    if name == '':
        return Response({"error": "Genre name is required."}, status=400)
    
    data = recommend_movie_genre(name, top_n=20)
    print(data)
    results = [{"title": title, "poster": poster} for title, poster in data[:20]]
    print("kunal")
    return Response(results)


@api_view(['GET'])
def more_detail(request):
    name = request.GET.get('name', '')
    page = int(request.GET.get('page', 1))  # Get page number from frontend

    if name == '':
        return Response({"error": "Name is required."}, status=400)

    top_n = page * 10  # Calculate top_n for this page
    name_simple = sending_genre.get(name, '')
    
    if name_simple in sending_genre_list:
        data = recommend_movie_genre(name_simple, top_n=top_n)
    else:
        data = recommend_movie(name, top_n=top_n)

    if not data:
        return Response([])  # No similar movies found

    # Get last 10 movies (or fewer if less than 10)
    results_slice = data[-10:] if len(data) >= 10 else data

    results = [{"title": title, "poster": poster} for title, poster in results_slice]
    return Response(results)


@api_view(['GET'])
def youtube_url(request):
    # Get movie name from GET parameter
    name = request.GET.get('name', '').strip()
    if not name:
        return Response({"error": "Movie name is required."}, status=400)

    # Load cache
    cache_file_path = 'static/movie_cache.json'

    # Check if file exists and has content
    if os.path.exists(cache_file_path) and os.path.getsize(cache_file_path) > 0:
        with open(cache_file_path, 'r', encoding='utf-8') as f:
            try:
                movie_cache = json.load(f)
            except json.JSONDecodeError:
                movie_cache = {}  # fallback if file is corrupt
    else:
        movie_cache = {}  # fallback if file doesn't exist or is empty

    movie_key = name.lower()  # normalize for cache

    # Check cache
    if movie_key in movie_cache:
        url = movie_cache[movie_key]
        return Response({"url": url})
    else:
        # Call your function to get YouTube full movie URL
        url = get_full_movie_url(name)
        if not url:
            return Response({"error": "No YouTube video found."}, status=404)

        # Store in cache
        movie_cache[movie_key] = url
        with open(cache_file_path, "w", encoding='utf-8') as f:
            json.dump(movie_cache, f, indent=4)

        return Response({"url": url})


# ----------------------------
# Helper functions
# ----------------------------

def get_full_movie_url(movie_name):
    """
    Search YouTube for a movie and return the likely full movie embed URL.
    """
    query = f"{movie_name} full movie"
    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=5,
        videoDuration="long"
    )
    
    response = request.execute()
    items = response.get('items', [])

    if not items:
        return None  # No videos found

    # Return the first likely full movie
    for item in items:
        video_id = item['id']['videoId']
        title = item['snippet']['title'].lower()
        if "full movie" in title:
            return f"https://www.youtube.com/embed/{video_id}"

    # fallback: first result
    first_video_id = items[0]['id']['videoId']
    return f"https://www.youtube.com/embed/{first_video_id}"


def get_top_similar(query_vector, vectors, top_n=10, batch_size=5000):
    """
    Get top N similar items based on cosine similarity.
    """
    scores = []
    
    # Process in batches to avoid memory issues
    for start in range(0, vectors.shape[0], batch_size):
        end = min(start + batch_size, vectors.shape[0])
        batch = vectors[start:end]
        
        # Calculate cosine similarity
        sim = cosine_similarity(query_vector, batch)[0]
        
        # Store index and score
        for i, s in enumerate(sim, start=start):
            scores.append((i, s))
    
    # Sort by similarity score (descending)
    scores.sort(key=lambda x: x[1], reverse=True)
    # Return top N results
    return scores[0:top_n]


def recommend_movie(title, top_n=10):
    """
    Recommend movies similar to the given title.
    Handles case-insensitive and partial matches.
    """
    # Try to match title (case-insensitive, exact or partial match)
    filtered = movie_data[movie_data["title"].str.lower() == title.lower()]
    if filtered.empty:
        filtered = movie_data[movie_data["title"].str.lower().str.contains(title.lower(), na=False)]
    if filtered.empty:
        return []

    # Take the first matched movie
    index = int(filtered.iloc[0]["index"])

    # Query vector
    query_vector = movie_vector[index].reshape(1, -1)

    # Get similar movies
    similar_scores = get_top_similar(query_vector, movie_vector, top_n+1, batch_size=5000)

    # Build recommendation list (skip the same movie itself)
    recommendations = []
    for i, score in similar_scores:
        if i != index:  # avoid returning the same movie
            movie = movie_data.iloc[i]
            recommendations.append((movie["title"], movie["poster_path"]))
        if len(recommendations) >= top_n:
            break

    return recommendations



def recommend_movie_genre(genre, top_n=10):
    """
    Recommend movies based on genre.
    """
    # Transform genre to TF-IDF vector
    query_vector = genre_tfidf.transform([genre.lower()])

    # Get similar movies based on genre
    similar_scores = get_top_similar(query_vector, genre_vector, top_n, batch_size=5000)

    # Prepare recommendations
    recommendations = []
    for i, score in similar_scores:
        movie = genre_data.iloc[i]
        recommendations.append((movie["title"], movie["poster_path"]))

    return recommendations
