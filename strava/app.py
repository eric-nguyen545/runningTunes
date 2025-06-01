import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, abort
import requests

app = Flask(__name__)

# ============ CONFIGURATION ============
CLIENT_ID = os.getenv('STRAVA_CLIENT_ID')
CLIENT_SECRET = os.getenv('STRAVA_CLIENT_SECRET')
STRAVA_VERIFY_TOKEN = os.getenv('STRAVA_VERIFY_TOKEN')  # any random string you choose
STRAVA_REFRESH_TOKEN = os.getenv('STRAVA_REFRESH_TOKEN')

DB_PATH = 'spotify_strava.db'

# ============ DB SETUP ============
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
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
        # Song with this played_at timestamp already exists; ignore duplicate
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

def get_strava_access_token():
    global STRAVA_REFRESH_TOKEN
    response = requests.post('https://www.strava.com/oauth/token', data={
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': STRAVA_REFRESH_TOKEN
    })
    data = response.json()
    if 'refresh_token' in data:
        STRAVA_REFRESH_TOKEN = data['refresh_token']  # update global refresh token if changed
    return data.get('access_token')

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
    if not songs:
        return "🏃 Great run! No Spotify songs logged."
    desc = "🏃 Great run!\n🎶 Songs listened to:\n"
    for s in songs:
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

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        # Strava webhook verification challenge
        mode = request.args.get('hub.mode')
        challenge = request.args.get('hub.challenge')
        verify_token = request.args.get('hub.verify_token')

        if mode == 'subscribe' and verify_token == STRAVA_VERIFY_TOKEN:
            return challenge, 200
        else:
            return 'Verification failed', 403

    if request.method == 'POST':
        event = request.json
        if not event:
            return 'No data', 400

        # Only handle activity creation/update events
        if event.get('object_type') == 'activity':
            activity_id = event.get('object_id')
            aspect_type = event.get('aspect_type')

            if is_activity_processed(activity_id):
                return 'Already processed', 200

            access_token = get_strava_access_token()
            activity = get_strava_activity(activity_id, access_token)

            if 'start_date' not in activity or 'elapsed_time' not in activity:
                return 'Invalid activity data', 400

            start_time = activity['start_date']  # ISO 8601 string
            elapsed = activity['elapsed_time']  # seconds
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
