import { NextResponse } from 'next/server';

const PYTHON_SERVICE_URL = 'http://localhost:8000';

export async function POST(request: Request) {
  try {
    const { message } = await request.json();
    console.log('API Route: Received message:', message);

    const response = await fetch(`${PYTHON_SERVICE_URL}/query`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ question: message }),
    });

    if (!response.ok) {
      const error = await response.json();
      console.error('API Route: Service error:', error);
      return NextResponse.json({ error: error.message }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json({ content: data.response });
  } catch (error) {
    console.error('API Route: Error:', error);
    return NextResponse.json(
      { error: 'Failed to process request', details: error.message },
      { status: 500 }
    );
  }
}