// src/app/api/runs/route.ts (new file for all runs)
import { NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:5000';

export async function GET() {
  try {
    const response = await fetch(`${BACKEND_URL}/api/runs`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch runs data' }, 
        { status: response.status }
      );
    }

    const runsData = await response.json();
    return NextResponse.json(runsData);
  } catch (error) {
    console.error('Error fetching runs data:', error);
    return NextResponse.json(
      { error: 'Internal server error' }, 
      { status: 500 }
    );
  }
}