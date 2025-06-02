import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, redirect, session, send_from_directory
from flask_cors import CORS
import requests
import base64
from urllib.parse import urlencode

app = Flask(__name__)
CORS(app, origins=["https://runningtunes-frontend.onrender.com"])

# Serve React App
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react(path):
    if path != "" and os.path.exists(f"build/{path}"):
        return send_from_directory('build', path)
    else:
        return send_from_directory('build', 'index.html')

# ============ CONFIGURATION ============
CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
STRAVA_VERIFY_TOKEN = "gopherrunclub"
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

DB_PATH = 'spotify_strava.db'
YOUR_DOMAIN = os.getenv('YOUR_DOMAIN', 'https://runningtunes.onrender.com')

# ============ DB SETUP ============
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            athlete_id INTEGER UNIQUE,
            access_token TEXT,
            refresh_token TEXT,
            expires_at INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS spotify_songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            artist TEXT NOT NULL,
            played_at TEXT NOT NULL UNIQUE
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS processed_activities (
            id INTEGER PRIMARY KEY,
            updated_at TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ============ Helper Functions ============

def save_song(name, artist, played_at):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('INSERT INTO spotify_songs (name, artist, played_at) VALUES (?, ?, ?)',
                  (name, artist, played_at))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()

def get_songs_in_range(start_time, end_time):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT name, artist, played_at FROM spotify_songs
        WHERE played_at BETWEEN ? AND ?
        ORDER BY played_at ASC
    ''', (start_time, end_time))
    rows = c.fetchall()
    conn.close()
    return [{'name': r[0], 'artist': r[1], 'played_at': r[2]} for r in rows]

def get_user_access_token(athlete_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT access_token, refresh_token, expires_at FROM users WHERE athlete_id=?', (athlete_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return None

    access_token, refresh_token, expires_at = row

    if datetime.utcnow().timestamp() > expires_at:
        resp = requests.post('https://www.strava.com/oauth/token', data={
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        })
        new_data = resp.json()
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''
            UPDATE users SET access_token=?, refresh_token=?, expires_at=? WHERE athlete_id=?
        ''', (
            new_data['access_token'],
            new_data['refresh_token'],
            new_data['expires_at'],
            athlete_id
        ))
        conn.commit()
        conn.close()
        return new_data['access_token']

    return access_token

def get_strava_activity(activity_id, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(f'https://www.strava.com/api/v3/activities/{activity_id}', headers=headers)
    return response.json()

def update_strava_description(activity_id, access_token, description):
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.put(f'https://www.strava.com/api/v3/activities/{activity_id}',
                            headers=headers, data={'description': description})
    return response.status_code == 200

def mark_activity_processed(activity_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT OR REPLACE INTO processed_activities (id, updated_at) VALUES (?, ?)',
              (activity_id, datetime.utcnow().isoformat() + 'Z'))
    conn.commit()
    conn.close()

def is_activity_processed(activity_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id FROM processed_activities WHERE id=?', (activity_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def format_description(songs):
    """Format description with unique songs only"""
    if not songs:
        return "🏃 Great run! No Spotify songs logged."
    
    # Additional deduplication in case database query didn't catch everything
    unique_songs = {}
    for song in songs:
        key = f"{song['name']}|{song['artist']}"  # Use name+artist as unique key
        if key not in unique_songs:
            unique_songs[key] = song
    
    unique_song_list = list(unique_songs.values())
    
    desc = "🏃 Great run!\n🎶 Songs listened to:\n"
    for s in unique_song_list:
        desc += f"- {s['name']} – {s['artist']}\n"
    
    return desc.strip()

# ============ Routes ============

@app.route('/log-spotify', methods=['POST'])
def log_spotify():
    data = request.json
    if not data or 'name' not in data or 'artist' not in data or 'played_at' not in data:
        return jsonify({'error': 'Invalid data'}), 400
    save_song(data['name'], data['artist'], data['played_at'])
    return jsonify({'status': 'logged'})

@app.route('/strava/auth')
def strava_auth():
    redirect_uri = f'{YOUR_DOMAIN}/strava/callback'
    return redirect(f'https://www.strava.com/oauth/authorize?client_id={CLIENT_ID}'
                    f'&redirect_uri={redirect_uri}&response_type=code'
                    f'&scope=activity:read_all,activity:write')

@app.route('/strava/callback')
def strava_callback():
    code = request.args.get('code')
    if not code:
        return 'Missing code', 400

    response = requests.post('https://www.strava.com/oauth/token', data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code'
    })
    data = response.json()
    if 'access_token' not in data:
        return 'Failed to authenticate', 400

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO users (athlete_id, access_token, refresh_token, expires_at)
        VALUES (?, ?, ?, ?)
    ''', (
        data['athlete']['id'],
        data['access_token'],
        data['refresh_token'],
        data['expires_at']
    ))
    conn.commit()
    conn.close()

    return redirect("https://runningtunes-frontend.onrender.com/api/runs")

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Strava webhook verification
        mode = request.args.get('hub.mode')
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        print(f"Verification request - mode: {mode}, token: {verify_token}, challenge: {challenge}")
        
        if mode == 'subscribe' and verify_token == STRAVA_VERIFY_TOKEN:
            return jsonify({'hub.challenge': challenge})
        return 'Verification failed', 403

    if request.method == 'POST':
        # Only try to get JSON for POST requests
        try:
            event = request.get_json()
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            return 'Invalid JSON', 400
            
        if not event:
            return 'No data', 400

        if event.get('object_type') == 'activity':
            activity_id = event.get('object_id')
            athlete_id = event.get('owner_id')
            aspect_type = event.get('aspect_type')

            if is_activity_processed(activity_id):
                return 'Already processed', 200

            access_token = get_user_access_token(athlete_id)
            if not access_token:
                return 'User not authorized', 403

            activity = get_strava_activity(activity_id, access_token)
            if 'start_date' not in activity or 'elapsed_time' not in activity:
                return 'Invalid activity data', 400

            start_time = activity['start_date']
            elapsed = activity['elapsed_time']
            start_dt = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%SZ')
            end_dt = start_dt + timedelta(seconds=elapsed)

            songs = get_songs_in_range(start_time, end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'))
            description = format_description(songs)

            if update_strava_description(activity_id, access_token, description):
                mark_activity_processed(activity_id)
                return 'Updated', 200
            else:
                return 'Failed to update Strava', 500

        return 'Ignored event', 200
    
# Mock user session example (implement your own login/session)
@app.route('/api/user')
def api_user():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT athlete_id FROM users LIMIT 1')
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': 'No user connected'}), 404

    athlete_id = row[0]
    
    # Get additional user info from Strava
    access_token = get_user_access_token(athlete_id)
    user_info = {'athlete_id': athlete_id}
    
    if access_token:
        headers = {'Authorization': f'Bearer {access_token}'}
        try:
            response = requests.get('https://www.strava.com/api/v3/athlete', headers=headers)
            if response.status_code == 200:
                athlete_data = response.json()
                user_info.update({
                    'athlete_name': f"{athlete_data.get('firstname', '')} {athlete_data.get('lastname', '')}".strip(),
                    'profile_pic': athlete_data.get('profile'),
                    'city': athlete_data.get('city'),
                    'state': athlete_data.get('state'),
                    'country': athlete_data.get('country')
                })
        except:
            pass
    
    return jsonify(user_info)

# Add this new route for getting the last run with songs
@app.route('/api/last-run')
def api_last_run():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT athlete_id FROM users LIMIT 1')
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': 'No user connected'}), 404

    athlete_id = row[0]
    last_run = get_user_last_run(athlete_id)
    
    if not last_run:
        return jsonify({'error': 'No runs found'}), 404
    
    # Get songs for this run
    start_time = last_run['start_date']
    elapsed = last_run['elapsed_time']
    start_dt = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%SZ')
    end_dt = start_dt + timedelta(seconds=elapsed)
    
    songs = get_songs_in_range(start_time, end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'))
    
    # Enrich songs with Spotify metadata
    enriched_songs = enrich_songs_with_spotify_data(songs)
    
    # Add songs to the run data
    run_data = {
        'id': last_run['id'],
        'name': last_run.get('name', 'Morning Run'),
        'start_date': last_run['start_date'],
        'distance': last_run['distance'],
        'elapsed_time': last_run['elapsed_time'],
        'moving_time': last_run.get('moving_time'),
        'total_elevation_gain': last_run.get('total_elevation_gain'),
        'type': last_run.get('type'),
        'average_speed': last_run.get('average_speed'),
        'max_speed': last_run.get('max_speed'),
        'average_heartrate': last_run.get('average_heartrate'),
        'max_heartrate': last_run.get('max_heartrate'),
        'songs': enriched_songs
    }
    
    return jsonify(run_data)

# Add this route for getting all runs (optional, for future expansion)
@app.route('/api/runs')
def api_runs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT athlete_id FROM users LIMIT 1')
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': 'No user connected'}), 404

    athlete_id = row[0]
    access_token = get_user_access_token(athlete_id)
    
    if not access_token:
        return jsonify({'error': 'No access token'}), 401
    
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'per_page': 10, 'page': 1}
    
    try:
        response = requests.get('https://www.strava.com/api/v3/athlete/activities', 
                              headers=headers, params=params)
        if response.status_code == 200:
            activities = response.json()
            # Filter for running activities only
            runs = [activity for activity in activities 
                   if activity.get('type') in ['Run', 'TrailRun', 'VirtualRun']]
            
            # Add songs to each run (this might be expensive for many runs)
            for run in runs[:3]:  # Limit to first 3 runs to avoid too many API calls
                start_time = run['start_date']
                elapsed = run['elapsed_time']
                start_dt = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%SZ')
                end_dt = start_dt + timedelta(seconds=elapsed)
                
                songs = get_songs_in_range(start_time, end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'))
                run['songs'] = enrich_songs_with_spotify_data(songs)
            
            return jsonify({'runs': runs})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'runs': []})

@app.route('/spotify/callback')
def spotify_callback():
    return "✅ Spotify OAuth successful!"

@app.route('/debug/songs')
def debug_songs():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM spotify_songs ORDER BY played_at DESC')
    rows = c.fetchall()
    conn.close()
    return jsonify(rows)

def get_spotify_access_token():
    """Get Spotify app-only access token for track metadata"""
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        return None
    
    auth_string = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    auth_base64 = base64.b64encode(auth_string.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {auth_base64}',
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    data = {'grant_type': 'client_credentials'}
    
    try:
        response = requests.post('https://accounts.spotify.com/api/token', headers=headers, data=data)
        if response.status_code == 200:
            return response.json().get('access_token')
    except:
        pass
    return None

def search_spotify_track(track_name, artist_name, spotify_token):
    """Search for track on Spotify to get metadata"""
    if not spotify_token:
        return None
    
    query = f"track:{track_name} artist:{artist_name}"
    params = {
        'q': query,
        'type': 'track',
        'limit': 1
    }
    
    headers = {'Authorization': f'Bearer {spotify_token}'}
    
    try:
        response = requests.get('https://api.spotify.com/v1/search', headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            tracks = data.get('tracks', {}).get('items', [])
            if tracks:
                track = tracks[0]
                return {
                    'name': track['name'],
                    'artist': ', '.join([artist['name'] for artist in track['artists']]),
                    'cover_art': track['album']['images'][0]['url'] if track['album']['images'] else None,
                    'spotify_url': track['external_urls']['spotify'],
                    'preview_url': track.get('preview_url')
                }
    except:
        pass
    return None

def get_user_last_run(athlete_id):
    """Get the user's most recent run from Strava"""
    access_token = get_user_access_token(athlete_id)
    if not access_token:
        return None
    
    headers = {'Authorization': f'Bearer {access_token}'}
    params = {'per_page': 1, 'page': 1}
    
    try:
        response = requests.get('https://www.strava.com/api/v3/athlete/activities', 
                              headers=headers, params=params)
        if response.status_code == 200:
            activities = response.json()
            if activities:
                activity = activities[0]
                # Only return running activities
                if activity.get('type') in ['Run', 'TrailRun', 'VirtualRun']:
                    return activity
    except:
        pass
    return None

def enrich_songs_with_spotify_data(songs):
    """Add Spotify metadata to songs"""
    spotify_token = get_spotify_access_token()
    if not spotify_token:
        return songs
    
    enriched_songs = []
    for song in songs:
        spotify_data = search_spotify_track(song['name'], song['artist'], spotify_token)
        if spotify_data:
            enriched_song = {
                **song,
                'cover_art': spotify_data['cover_art'],
                'spotify_url': spotify_data['spotify_url'],
                'preview_url': spotify_data['preview_url']
            }
        else:
            enriched_song = song
        enriched_songs.append(enriched_song)
    
    return enriched_songs

if __name__ == '__main__':
    app.run(debug=True, port=5000)
