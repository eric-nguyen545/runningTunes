import time
import json
from datetime import datetime
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Set up Spotify auth from env variables
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=os.getenv("SPOTIPY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIPY_CLIENT_SECRET"),
    redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI", "https://runningtunes.onrender.com"),
    scope="user-read-currently-playing user-read-playback-state"
))

# Store songs in memory
logged_songs = []

def log_current_track():
    current = sp.current_playback()
    if current and current['is_playing'] and current['item']:
        song = {
            'name': current['item']['name'],
            'artist': current['item']['artists'][0]['name'],
            'played_at': datetime.utcnow().isoformat() + 'Z'
        }

        if not logged_songs or song != logged_songs[-1]:
            logged_songs.append(song)
            print(f"🎵 Logged: {song['name']} by {song['artist']} at {song['played_at']}")
    else:
        print("⏸️ No music playing.")

try:
    print("🎧 Starting Spotify track logger (every 2 min)...")
    while True:
        log_current_track()
        time.sleep(120)  # Check every 2 minutes
except KeyboardInterrupt:
    print("\n🛑 Logging stopped.")
    with open("spotify_log.json", "w") as f:
        json.dump(logged_songs, f, indent=2)
    print("💾 Songs saved to spotify_log.json")
