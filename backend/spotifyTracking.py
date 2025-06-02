import time
import json
import requests
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Load environment variables
load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
BACKEND_URL = os.getenv("BACKEND_URL")  # e.g. https://runningtunes.onrender.com

# Set up Spotify auth
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope="user-read-currently-playing user-read-playback-state"
))

logged_songs = []

def log_current_track():
    current = sp.current_playback()
    if current and current['is_playing'] and current['item']:
        song = {
            'name': current['item']['name'],
            'artist': current['item']['artists'][0]['name'],
            'played_at': datetime.now(timezone.utc).isoformat() + 'Z'
        }

        if not logged_songs or song != logged_songs[-1]:
            logged_songs.append(song)
            print(f"🎵 Logged: {song['name']} by {song['artist']} at {song['played_at']}")

            try:
                # Send to Flask backend
                response = requests.post(f"{BACKEND_URL}/log-spotify", json=song)
                if response.ok:
                    print("✅ Sent to backend.")
                else:
                    print("⚠️ Failed to send to backend:", response.text)
            except Exception as e:
                print("❌ Error sending to backend:", e)
    else:
        print("No music playing.")

try:
    print("🎧 Starting Spotify track logger...")
    while True:
        log_current_track()
        time.sleep(45)  # every 45 secs
except KeyboardInterrupt:
    print("\n🛑 Logging stopped.")
    with open("spotify_log.json", "w") as f:
        json.dump(logged_songs, f, indent=2)
    print("💾 Songs saved to spotify_log.json")
