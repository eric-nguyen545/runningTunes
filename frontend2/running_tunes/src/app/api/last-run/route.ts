// src/app/api/last-run/route.ts
import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    distance: 5000, // meters
    elapsed_time: 1500, // seconds (25 min)
    start_date: new Date().toISOString(),
    songs: [
      {
        name: "Song One",
        artist: "Artist A",
        played_at: new Date().toISOString(),
        cover_art: "https://via.placeholder.com/150",
      },
      {
        name: "Song Two",
        artist: "Artist B",
        played_at: new Date().toISOString(),
        cover_art: "https://via.placeholder.com/150",
      }
    ]
  });
}
