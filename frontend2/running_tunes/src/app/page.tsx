"use client";

import { useEffect, useState } from 'react';
import { Clock, MapPin, Zap, Music, Play, User, Home as HomeIcon, Activity, Settings, List } from 'lucide-react';
import Image from 'next/image';

// API Configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'https://runningtunes-backend.onrender.com';

// Define proper interfaces
interface Song {
  name: string;
  artist: string;
  played_at: string;
  cover_art?: string;
  spotify_url?: string;
  preview_url?: string;
}

interface Run {
  id?: number;
  name?: string;
  distance: number;
  elapsed_time: number;
  moving_time?: number;
  start_date: string;
  total_elevation_gain?: number;
  type?: string;
  average_speed?: number;
  max_speed?: number;
  average_heartrate?: number;
  max_heartrate?: number;
  songs?: Song[];
}

interface UserData {
  athlete_id: number;
  athlete_name?: string;
  profile_pic?: string;
  city?: string;
  state?: string;
  country?: string;
}

type PageType = 'home' | 'last-run' | 'all-runs' | 'settings';

// API Helper Functions
const apiCall = async (endpoint: string, options: RequestInit = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const defaultOptions: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
    },
    ...options,
  };

  try {
    const response = await fetch(url, defaultOptions);
    
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
  } catch (error) {
    console.error(`API call failed for ${endpoint}:`, error);
    throw error;
  }
};

export default function Home() {
  const [user, setUser] = useState<UserData | null>(null);
  const [status, setStatus] = useState('Loading...');
  const [lastRun, setLastRun] = useState<Run | null>(null);
  const [allRuns, setAllRuns] = useState<Run[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState<PageType>('home');

  // Load current user status
  useEffect(() => {
    loadUserData();
  }, []);

  const loadUserData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Make parallel API calls to your backend
      const [userResponse, runResponse] = await Promise.allSettled([
        apiCall('/api/user'),
        apiCall('/api/last-run')
      ]);

      // Handle user data
      if (userResponse.status === 'fulfilled' && userResponse.value.athlete_id) {
        setUser(userResponse.value);
        setStatus('Connected');
      } else {
        setUser(null);
        setStatus('Not connected');
      }

      // Handle run data
      if (runResponse.status === 'fulfilled') {
        setLastRun(runResponse.value);
      } else {
        setLastRun(null);
      }

    } catch (err) {
      console.error('Error loading data:', err);
      setError('Failed to load data. Please check your connection.');
      setStatus('Error');
    } finally {
      setLoading(false);
    }
  };

  const loadAllRuns = async () => {
    try {
      const data = await apiCall('/api/runs');
      setAllRuns(data.runs || []);
    } catch (err) {
      console.error('Error loading all runs:', err);
      setError('Failed to load runs data');
    }
  };

  useEffect(() => {
    if (currentPage === 'all-runs' && user) {
      loadAllRuns();
    }
  }, [currentPage, user]);

  const handleStravaConnect = () => {
    window.location.href = `${API_BASE_URL}/strava/auth`;
  };

  const formatTime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDistance = (meters: number): string => {
    const km = (meters / 1000).toFixed(2);
    const miles = (meters / 1609.34).toFixed(2);
    return `${km} km (${miles} mi)`;
  };

  const formatPace = (timeInSeconds: number, distanceInMeters: number): string => {
    const paceSecondsPerKm = timeInSeconds / (distanceInMeters / 1000);
    const minutes = Math.floor(paceSecondsPerKm / 60);
    const seconds = Math.floor(paceSecondsPerKm % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}/km`;
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleDateString('en-US', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const NavigationBar = () => (
    <div className="bg-white/10 backdrop-blur-md rounded-2xl p-4 mb-8 border border-white/20">
      <div className="flex flex-wrap gap-2 justify-center">
        <button
          onClick={() => setCurrentPage('home')}
          className={`px-4 py-2 rounded-xl font-medium transition-colors duration-200 flex items-center gap-2 ${
            currentPage === 'home' 
              ? 'bg-orange-500 text-white' 
              : 'bg-white/10 text-white hover:bg-white/20'
          }`}
        >
          <HomeIcon className="w-4 h-4" />
          Home
        </button>
        
        {user && (
          <>
            <button
              onClick={() => setCurrentPage('last-run')}
              className={`px-4 py-2 rounded-xl font-medium transition-colors duration-200 flex items-center gap-2 ${
                currentPage === 'last-run' 
                  ? 'bg-orange-500 text-white' 
                  : 'bg-white/10 text-white hover:bg-white/20'
              }`}
            >
              <Activity className="w-4 h-4" />
              Latest Run
            </button>
            
            <button
              onClick={() => setCurrentPage('all-runs')}
              className={`px-4 py-2 rounded-xl font-medium transition-colors duration-200 flex items-center gap-2 ${
                currentPage === 'all-runs' 
                  ? 'bg-orange-500 text-white' 
                  : 'bg-white/10 text-white hover:bg-white/20'
              }`}
            >
              <List className="w-4 h-4" />
              All Runs
            </button>
            
            <button
              onClick={() => setCurrentPage('settings')}
              className={`px-4 py-2 rounded-xl font-medium transition-colors duration-200 flex items-center gap-2 ${
                currentPage === 'settings' 
                  ? 'bg-orange-500 text-white' 
                  : 'bg-white/10 text-white hover:bg-white/20'
              }`}
            >
              <Settings className="w-4 h-4" />
              Settings
            </button>
          </>
        )}
      </div>
    </div>
  );

  const SongsList = ({ songs }: { songs: Song[] }) => (
    <div className="space-y-4">
      {songs.map((song: Song, index: number) => (
        <div key={index} className="bg-white/10 rounded-xl p-4 flex items-center gap-4 hover:bg-white/20 transition-colors duration-200">
          <div className="flex-shrink-0">
            {song.cover_art ? (
              <Image 
                src={song.cover_art}
                alt={`${song.name} cover`}
                width={64}
                height={64}
                className="rounded-lg shadow-lg object-cover"
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

          <div className="flex-shrink-0 flex gap-2">
            {song.spotify_url && (
              <a
                href={song.spotify_url}
                target="_blank"
                rel="noopener noreferrer"
                className="w-12 h-12 bg-green-500 hover:bg-green-600 rounded-full flex items-center justify-center transition-colors duration-200 shadow-lg"
              >
                <Play className="w-6 h-6 text-white ml-1" />
              </a>
            )}
          </div>
        </div>
      ))}
    </div>
  );

  const RunCard = ({ run }: { run: Run }) => (
    <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 border border-white/20">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-xl font-bold text-white mb-1">
            {run.name || 'Morning Run'}
          </h3>
          <p className="text-white/70 text-sm">
            {formatDate(run.start_date)}
          </p>
        </div>
        <div className="text-right">
          <p className="text-white/70 text-sm">Songs</p>
          <p className="text-white text-xl font-bold">
            {run.songs ? run.songs.length : 0}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div className="text-center">
          <p className="text-white/70 text-xs mb-1">Distance</p>
          <p className="text-white font-semibold">
            {formatDistance(run.distance)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-white/70 text-xs mb-1">Duration</p>
          <p className="text-white font-semibold">
            {formatTime(run.elapsed_time)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-white/70 text-xs mb-1">Pace</p>
          <p className="text-white font-semibold">
            {formatPace(run.elapsed_time, run.distance)}
          </p>
        </div>
        <div className="text-center">
          <p className="text-white/70 text-xs mb-1">Type</p>
          <p className="text-white font-semibold">
            {run.type || 'Run'}
          </p>
        </div>
      </div>

      {run.songs && run.songs.length > 0 && (
        <div className="mt-4">
          <p className="text-white/70 text-sm mb-2">Top Songs:</p>
          <div className="flex gap-2 flex-wrap">
            {run.songs.slice(0, 3).map((song, index) => (
              <span key={index} className="bg-white/10 px-3 py-1 rounded-full text-white/90 text-xs">
                {song.name}
              </span>
            ))}
            {run.songs.length > 3 && (
              <span className="bg-white/10 px-3 py-1 rounded-full text-white/70 text-xs">
                +{run.songs.length - 3} more
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-400 via-red-500 to-pink-500 flex items-center justify-center p-8">
        <div className="text-white text-xl">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-400 via-red-500 to-pink-500 p-8 font-[family-name:var(--font-geist-sans)]">
      <div className="container mx-auto px-6 py-8">

        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-5xl font-bold text-white mb-4 flex items-center justify-center gap-3">
            🏃‍♂️ RunningTunes
          </h1>
          <p className="text-white/90 text-lg">Your running soundtrack, perfectly synced</p>
        </div>

        {/* Navigation */}
        <NavigationBar />

        {/* Status Card */}
        <div className="bg-white/10 backdrop-blur-md rounded-2xl p-6 mb-8 border border-white/20">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              {user?.profile_pic ? (
                <Image
                  src={user.profile_pic}
                  alt="Profile"
                  width={48}
                  height={48}
                  className="w-12 h-12 rounded-full"
                />
              ) : (
                <User className="w-6 h-6 text-white" />
              )}
              <div>
                <p className="text-white font-medium">
                  Status: <span className="font-bold">{status}</span>
                </p>
                {user && (
                  <div className="text-white/80 text-sm">
                    {user.athlete_name && (
                      <p>{user.athlete_name}</p>
                    )}
                    {user.city && user.state && (
                      <p>{user.city}, {user.state}</p>
                    )}
                    <p>Athlete ID: {user.athlete_id}</p>
                  </div>
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

            {user && (
              <button
                onClick={loadUserData}
                className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium transition-colors duration-200 text-sm"
              >
                Refresh
              </button>
            )}
          </div>
        </div>

        {error && (
          <div className="bg-red-500/20 backdrop-blur-md rounded-2xl p-6 mb-8 border border-red-400/30">
            <p className="text-white">{error}</p>
            <p className="text-white/70 text-sm mt-2">
              Backend URL: {API_BASE_URL}
            </p>
          </div>
        )}

        {/* Page Content */}
        {currentPage === 'home' && (
          <div className="space-y-8">
            {user && lastRun ? (
              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20">
                <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                  <Zap className="w-7 h-7" />
                  Quick Overview
                </h2>
                <RunCard run={lastRun} />
              </div>
            ) : user ? (
              <div className="bg-white/10 backdrop-blur-md rounded-2xl p-12 border border-white/20 text-center">
                <Zap className="w-16 h-16 text-white/30 mx-auto mb-4" />
                <h3 className="text-white text-xl font-semibold mb-2">No runs found</h3>
                <p className="text-white/70">
                  Go for a run with Spotify playing to see your running soundtrack!
                </p>
              </div>
            ) : (
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
          </div>
        )}

        {currentPage === 'last-run' && user && lastRun && (
          <div className="space-y-8">
            {/* Detailed Run Stats */}
            <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20">
              <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                <Zap className="w-7 h-7" />
                Latest Run Details
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

            {/* Songs Playlist */}
            <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20">
              <h3 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                <Music className="w-7 h-7" />
                Your Running Playlist
              </h3>

              {lastRun.songs && lastRun.songs.length > 0 ? (
                <SongsList songs={lastRun.songs} />
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

        {currentPage === 'all-runs' && user && (
          <div className="space-y-6">
            <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20">
              <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                <List className="w-7 h-7" />
                All Runs
              </h2>

              {allRuns.length > 0 ? (
                <div className="grid gap-6">
                  {allRuns.map((run, index) => (
                    <RunCard key={run.id || index} run={run} />
                  ))}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Activity className="w-16 h-16 text-white/30 mx-auto mb-4" />
                  <p className="text-white/70 text-lg">No runs found</p>
                  <p className="text-white/50 text-sm mt-2">
                    Your recent runs will appear here
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {currentPage === 'settings' && user && (
          <div className="space-y-6">
            <div className="bg-white/10 backdrop-blur-md rounded-2xl p-8 border border-white/20">
              <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-3">
                <Settings className="w-7 h-7" />
                Settings
              </h2>

              <div className="space-y-6">
                <div className="bg-white/10 rounded-xl p-4">
                  <h3 className="text-white font-semibold mb-2">Account Information</h3>
                  <div className="text-white/70 text-sm space-y-1">
                    <p>Athlete ID: {user.athlete_id}</p>
                    {user.athlete_name && <p>Name: {user.athlete_name}</p>}
                    {user.city && user.state && <p>Location: {user.city}, {user.state}</p>}
                  </div>
                </div>

                <div className="bg-white/10 rounded-xl p-4">
                  <h3 className="text-white font-semibold mb-2">Backend Connection</h3>
                  <div className="text-white/70 text-sm space-y-1">
                    <p>API URL: {API_BASE_URL}</p>
                    <p>Status: {status}</p>
                  </div>
                </div>

                <div className="bg-white/10 rounded-xl p-4">
                  <h3 className="text-white font-semibold mb-2">Actions</h3>
                  <div className="space-y-2">
                    <button
                      onClick={loadUserData}
                      className="w-full px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium transition-colors duration-200"
                    >
                      Refresh Data
                    </button>
                    <button
                      onClick={() => window.location.href = `${API_BASE_URL}/strava/auth`}
                      className="w-full px-4 py-2 bg-orange-500 hover:bg-orange-600 text-white rounded-lg font-medium transition-colors duration-200"
                    >
                      Reconnect Strava
                    </button>
                  </div>
                </div>
              </div>
            </div>
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