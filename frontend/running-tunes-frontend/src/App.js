import React, { useEffect, useState } from 'react';

export default function App() {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState('Not connected');
  const [songs, setSongs] = useState([]);

  // Load current user status
  useEffect(() => {
    fetch('/api/me')
      .then(res => res.json())
      .then(data => {
        if (data && data.user) {
          setUser(data.user);
          setStatus('Connected');
        }
      });
  }, []);

  const handleStravaConnect = () => {
    window.location.href = '/strava/auth';
  };

  const fetchSongs = () => {
    fetch('/api/my-songs')
      .then(res => res.json())
      .then(data => setSongs(data.songs || []));
  };

  return (
    <div className="min-h-screen bg-white text-black p-6">
      <h1 className="text-3xl font-bold mb-4">🏃‍♂️ RunningTunes</h1>

      <div className="mb-6">
        <p>Status: <strong>{status}</strong></p>
        {!user && (
          <button
            onClick={handleStravaConnect}
            className="mt-4 px-4 py-2 bg-blue-500 text-white rounded"
          >
            Connect Strava
          </button>
        )}
        {user && (
          <p>Welcome, {user.username || user.id}</p>
        )}
      </div>

      {user && (
        <div className="mb-6">
          <button
            onClick={fetchSongs}
            className="px-4 py-2 bg-green-600 text-white rounded"
          >
            View My Songs
          </button>

          <ul className="mt-4 list-disc list-inside">
            {songs.length === 0 && <li>No songs found</li>}
            {songs.map((s, idx) => (
              <li key={idx}>
                {s.name} – {s.artist} <span className="text-gray-500 text-sm">({s.played_at})</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <footer className="mt-12 text-sm text-gray-600">
        Built with ❤️ by RunningTunes
      </footer>
    </div>
  );
}
