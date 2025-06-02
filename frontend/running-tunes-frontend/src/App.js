import React, { useEffect, useState } from 'react';
import { Clock, MapPin, Zap, Music, Play, User } from 'lucide-react';

export default function App() {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState('Loading...');
  const [lastRun, setLastRun] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load current user status
  useEffect(() => {
    Promise.all([
      fetch('/api/user').then(res => res.ok ? res.json() : null),
      fetch('/api/last-run').then(res => res.ok ? res.json() : null)
    ])
    .then(([userData, runData]) => {
      if (userData && userData.athlete_id) {
        setUser(userData);
        setStatus('Connected');
        setLastRun(runData);
      } else {
        setStatus('Not connected');
      }
    })
    .catch(err => {
      console.error('Error loading data:', err);
      setError('Failed to load data');
      setStatus('Error');
    })
    .finally(() => {
      setLoading(false);
    });
  }, []);

  const handleStravaConnect = () => {
    window.location.href = '/strava/auth';
  };

  const formatTime = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDistance = (meters) => {
    const km = (meters / 1000).toFixed(2);
    const miles = (meters / 1609.34).toFixed(2);
    return `${km} km (${miles} mi)`;
  };

  const formatPace = (timeInSeconds, distanceInMeters) => {
    const paceSecondsPerKm = (timeInSeconds / (distanceInMeters / 1000));
    const minutes = Math.floor(paceSecondsPerKm / 60);
    const seconds = Math.floor(paceSecondsPerKm % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}/km`;
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-400 via-red-500 to-pink-500 flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-400 via-red-500 to-pink-500">
      <div className="container mx-auto px-6 py-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-5xl font-bold text-white mb-4 flex items-center justify-center gap-3">
            🏃‍♂️ RunningTunes
          </h1>
          <p className="text-white/90 text-lg">Your running soundtrack, perfectly synced</p>
        </div>

        {/* Status Card */}
        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 mb-8 border border-white/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <User className="w-6 h-6 text-white" />
              <div>
                <p className="text-white font-medium">
                  Status: <span className="font-bold">{status}</span>
                </p>
                {user && (
                  <p className="text-white/80 text-sm">
                    Athlete ID: {user.athlete_id}
                  </p>
                )}
              </div>
            </div>
            
            {!user && (
              <button
                onClick={handleStravaConnect}
                className="px-6 py-3 bg-orange-500 hover:bg-orange-600 text-white rounded-xl font-medium transition-colors duration-200 shadow-lg"
              >
                Connect Strava
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="bg-red-500/20 backdrop-blur-md rounded-2xl p-6 mb-8 border border-red-400/30">
            <p className="text-white">{error}</p>
          </div>
        )}

        {user && lastRun && (
          <div className="space-y-8">
            {/* Run Details Card */}
            <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20">
              <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                <Zap className="w-7 h-7" />
                Latest Run
              </h2>
              
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
                <div className="bg-white/10 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <MapPin className="w-5 h-5 text-white/70" />
                    <span className="text-white/70 text-sm font-medium">Distance</span>
                  </div>
                  <p className="text-white text-xl font-bold">
                    {formatDistance(lastRun.distance)}
                  </p>
                </div>
                
                <div className="bg-white/10 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Clock className="w-5 h-5 text-white/70" />
                    <span className="text-white/70 text-sm font-medium">Duration</span>
                  </div>
                  <p className="text-white text-xl font-bold">
                    {formatTime(lastRun.elapsed_time)}
                  </p>
                </div>
                
                <div className="bg-white/10 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Zap className="w-5 h-5 text-white/70" />
                    <span className="text-white/70 text-sm font-medium">Pace</span>
                  </div>
                  <p className="text-white text-xl font-bold">
                    {formatPace(lastRun.elapsed_time, lastRun.distance)}
                  </p>
                </div>
                
                <div className="bg-white/10 rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-2">
                    <Music className="w-5 h-5 text-white/70" />
                    <span className="text-white/70 text-sm font-medium">Songs</span>
                  </div>
                  <p className="text-white text-xl font-bold">
                    {lastRun.songs ? lastRun.songs.length : 0}
                  </p>
                </div>
              </div>

              <div className="bg-white/10 rounded-xl p-4">
                <p className="text-white/70 text-sm mb-1">Started on</p>
                <p className="text-white font-medium">
                  {formatDate(lastRun.start_date)}
                </p>
              </div>
            </div>

            {/* Songs Playlist Card */}
            <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20">
              <h3 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                <Music className="w-7 h-7" />
                Your Running Playlist
              </h3>
              
              {lastRun.songs && lastRun.songs.length > 0 ? (
                <div className="space-y-4">
                  {lastRun.songs.map((song, index) => (
                    <div key={index} className="bg-white/10 rounded-xl p-4 flex items-center gap-4 hover:bg-white/20 transition-colors duration-200">
                      <div className="flex-shrink-0">
                        {song.cover_art ? (
                          <img 
                            src={song.cover_art} 
                            alt={`${song.name} cover`}
                            className="w-16 h-16 rounded-lg shadow-lg"
                          />
                        ) : (
                          <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
                            <Music className="w-8 h-8 text-white" />
                          </div>
                        )}
                      </div>
                      
                      <div className="flex-grow">
                        <h4 className="text-white font-semibold text-lg mb-1">
                          {song.name}
                        </h4>
                        <p className="text-white/70 text-sm mb-2">
                          by {song.artist}
                        </p>
                        <p className="text-white/50 text-xs">
                          Played at {new Date(song.played_at).toLocaleTimeString()}
                        </p>
                      </div>
                      
                      <div className="flex-shrink-0">
                        <button className="w-12 h-12 bg-green-500 hover:bg-green-600 rounded-full flex items-center justify-center transition-colors duration-200 shadow-lg">
                          <Play className="w-6 h-6 text-white ml-1" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Music className="w-16 h-16 text-white/30 mx-auto mb-4" />
                  <p className="text-white/70 text-lg">No songs found for this run</p>
                  <p className="text-white/50 text-sm mt-2">
                    Make sure your Spotify is playing during your runs!
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {user && !lastRun && (
          <div className="bg-white/10 backdrop-blur-md rounded-2xl p-12 border border-white/20 text-center">
            <Zap className="w-16 h-16 text-white/30 mx-auto mb-4" />
            <h3 className="text-white text-xl font-semibold mb-2">No runs found</h3>
            <p className="text-white/70">
              Go for a run with Spotify playing to see your running soundtrack!
            </p>
          </div>
        )}

        {!user && (
          <div className="bg-white/10 backdrop-blur-md rounded-2xl p-12 border border-white/20 text-center">
            <User className="w-16 h-16 text-white/30 mx-auto mb-4" />
            <h3 className="text-white text-xl font-semibold mb-2">Get Started</h3>
            <p className="text-white/70 mb-6">
              Connect your Strava account to start tracking your running soundtracks
            </p>
            <button
              onClick={handleStravaConnect}
              className="px-8 py-4 bg-orange-500 hover:bg-orange-600 text-white rounded-xl font-medium transition-colors duration-200 shadow-lg"
            >
              Connect Strava
            </button>
          </div>
        )}

        {/* Footer */}
        <footer className="mt-12 text-center">
          <p className="text-white/60 text-sm">
            Built with ❤️ by RunningTunes
          </p>
        </footer>
      </div>
    </div>
  );
}