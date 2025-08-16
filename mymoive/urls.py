"""
URL configuration for mymovie project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from myapp.views import movie_detail, genre_detail,more_detail,youtube_url  # keep same as view names

urlpatterns = [
    path('admin/', admin.site.urls),
    path('movies/', movie_detail, name='movie_detail'),   # POST endpoint for movie
    path('genres/', genre_detail, name='genre_detail'),   # POST endpoint for genre
    path('more_movies/', more_detail, name='more_movie'),
    path('youtube_url/', youtube_url, name='youtube_url'),
    path('', include('myapp.urls')),                     # include app-specific URLs
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
