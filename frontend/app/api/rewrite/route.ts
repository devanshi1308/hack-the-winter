import { NextRequest, NextResponse } from 'next/server';

// Run in Node runtime and proxy to the FastAPI backend so keys live server-side.
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
  try {
    const { text, style, intent } = await request.json();

    if (!text || typeof text !== 'string') {
      return NextResponse.json(
        { error: 'Text is required and must be a string' },
        { status: 400 }
      );
    }

    const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const resp = await fetch(`${baseUrl}/api/collab/rewrite`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, style, intent })
    });

    const data = await resp.json().catch(() => ({}));

    if (!resp.ok) {
      const msg = data?.detail || data?.error || `${resp.status} ${resp.statusText}`;
      if (resp.status === 503 || /rate limit|busy|overloaded/i.test(String(msg))) {
        return NextResponse.json(
          { error: 'The AI service is currently busy. Please try again shortly.' },
          { status: 503 }
        );
      }
      return NextResponse.json(
        { error: msg || 'Failed to rewrite text' },
        { status: 500 }
      );
    }

    // Backend returns { rewrittenText }
    return NextResponse.json({ rewrittenText: data?.rewrittenText || '' });
  } catch (error) {
    console.error('Error proxying rewrite request:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
