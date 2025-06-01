import os
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, redirect, session, send_from_directory
import requests

app = Flask(__name__, static_folder='build/static', static_url_path='/static')

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

DB_PATH = 'spotify_strava.db'
YOUR_DOMAIN = os.getenv('YOUR_DOMAIN', 'https://runningtunes.onrender.com')  # Replace with your Render domain or use env

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

    return f"✅ Successfully connected Strava for athlete ID {data['athlete']['id']}."

@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    print("Query parameters:", request.args)
    if request.method == 'GET':
        print('Query parameters:', request.args)
        mode = request.args.get('hub.mode')
        verify_token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        print(f"Verification request - mode: {mode}, token: {verify_token}, challenge: {challenge}")
        if mode == 'subscribe' and verify_token == STRAVA_VERIFY_TOKEN:
            return jsonify({'hub.challenge': challenge})
        return 'Verification failed', 403

    if request.method == 'POST':
        event = request.json
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
    # You should identify user by session/cookies or tokens
    # For demo, pick first user from DB:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT athlete_id FROM users LIMIT 1')
    row = c.fetchone()
    if not row:
        return jsonify({'error': 'No user connected'}), 403

    athlete_id = row[0]
    # You can add more user info here
    return jsonify({'athlete_id': athlete_id, 'athlete_name': 'Runner', 'last_sync': '2025-06-01 10:00:00'})

@app.route('/api/runs')
def api_runs():
    # Fetch recent runs for user from your DB or Strava API
    # This example returns dummy data - replace with your actual logic
    example_runs = [
        {
            'id': 1,
            'start_date': '2025-06-01T09:00:00Z',
            'distance': 5000,
            'elapsed_time': 1500,
            'songs': [
                {'name': 'Song A', 'artist': 'Artist A', 'played_at': '2025-06-01T09:05:00Z'},
                {'name': 'Song B', 'artist': 'Artist B', 'played_at': '2025-06-01T09:10:00Z'},
            ],
        },
        # Add more runs here
    ]
    return jsonify({'runs': example_runs})

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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
