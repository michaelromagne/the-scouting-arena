import { NextRequest, NextResponse } from 'next/server';

const API_BASE_URL = process.env.API_BASE_URL || 'http://127.0.0.1:8000';

// Ensure HTTPS for production Railway URLs
function ensureHttps(url: string): string {
  if (url.includes('railway.app') && url.startsWith('http://')) {
    return url.replace('http://', 'https://');
  }
  return url;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path, 'GET');
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path, 'POST');
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path, 'PUT');
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  return proxyRequest(request, path, 'DELETE');
}

async function proxyRequest(
  request: NextRequest,
  pathSegments: string[],
  method: string
) {
  try {
    const path = pathSegments.join('/');
    const searchParams = request.nextUrl.searchParams.toString();
    const baseUrl = ensureHttps(API_BASE_URL);
    const url = `${baseUrl}/${path}${searchParams ? `?${searchParams}` : ''}`;

    console.log(`🔄 Proxying ${method} ${url}`);

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Forward relevant headers
    const forwardHeaders = ['authorization', 'content-type', 'accept'];
    forwardHeaders.forEach(header => {
      const value = request.headers.get(header);
      if (value) {
        headers[header] = value;
      }
    });

    const options: RequestInit = {
      method,
      headers,
    };

    // Add body for POST/PUT requests
    if (method === 'POST' || method === 'PUT') {
      try {
        const body = await request.text();
        if (body) {
          console.log(`📦 Request body: ${body}`);
          options.body = body;
        }
      } catch (e) {
        console.error('❌ Failed to read request body:', e);
        // No body or invalid body, continue without it
      }
    }

    console.log(`🚀 Sending ${method} request to: ${url}`);
    console.log(`📋 Request options:`, JSON.stringify({ method: options.method, hasBody: !!options.body, headers: options.headers }));

    const response = await fetch(url, options);

    console.log(`📨 Response status: ${response.status} ${response.statusText}`);

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`❌ API Error: ${response.status} ${response.statusText}`, errorText);
      return NextResponse.json(
        { error: `API Error: ${response.statusText}`, details: errorText },
        { status: response.status }
      );
    }

    const data = await response.json();
    console.log(`✅ API Success: ${method} ${url}`, data);

    return NextResponse.json(data);
  } catch (error) {
    console.error('❌ Proxy error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
