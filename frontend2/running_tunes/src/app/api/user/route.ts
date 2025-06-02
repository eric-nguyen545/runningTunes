// src/app/api/user/route.ts
import { NextResponse } from 'next/server';

export async function GET() {
  // Simulate a logged-in user (replace with real logic later)
  return NextResponse.json({
    athlete_id: 137454021,
    name: "Test User",
  });
}
