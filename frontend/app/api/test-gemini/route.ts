import { NextResponse } from 'next/server';

const GEMINI_API_URL = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent';

export async function GET() {
  try {
    console.log('Testing Gemini API...');
    console.log('API Key exists:', !!process.env.GEMINI_API_KEY);
    console.log('API Key length:', process.env.GEMINI_API_KEY?.length);
    console.log('API Key starts with:', process.env.GEMINI_API_KEY?.substring(0, 10));

    // Simple test request
    const requestBody = {
      contents: [{
        parts: [{
          text: "Say 'Hello from Gemini API' in response"
        }]
      }]
    };

    const response = await fetch(`${GEMINI_API_URL}?key=${process.env.GEMINI_API_KEY}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody)
    });

    const data = await response.json();
    
    console.log('Gemini API response status:', response.status);
    console.log('Gemini API response:', JSON.stringify(data, null, 2));

    return NextResponse.json({
      status: response.status,
      statusText: response.statusText,
      apiKeyExists: !!process.env.GEMINI_API_KEY,
      apiKeyLength: process.env.GEMINI_API_KEY?.length,
      response: data
    });

  } catch (error) {
    console.error('Error testing Gemini API:', error);
    return NextResponse.json(
      { 
        error: 'Test failed', 
        details: error instanceof Error ? error.message : 'Unknown error',
        apiKeyExists: !!process.env.GEMINI_API_KEY,
        apiKeyLength: process.env.GEMINI_API_KEY?.length
      },
      { status: 500 }
    );
  }
}
