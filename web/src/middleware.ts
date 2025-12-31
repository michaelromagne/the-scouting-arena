import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

/**
 * Simple in-memory rate limiter for demo site protection.
 *
 * For production, consider using Redis or a dedicated rate limiting service.
 * This implementation is sufficient for demo/small-scale deployments.
 */

interface RateLimitRecord {
  count: number;
  resetTime: number;
}

// In-memory storage for rate limiting
const rateLimitMap = new Map<string, RateLimitRecord>();

// Clean up old entries every 5 minutes to prevent memory leaks
setInterval(() => {
  const now = Date.now();
  for (const [key, record] of rateLimitMap.entries()) {
    if (now > record.resetTime) {
      rateLimitMap.delete(key);
    }
  }
}, 5 * 60 * 1000);

/**
 * Check if a request should be rate limited.
 *
 * @param identifier - Unique identifier (IP + endpoint)
 * @param limit - Maximum number of requests allowed
 * @param windowMs - Time window in milliseconds
 * @returns true if request is allowed, false if rate limited
 */
function checkRateLimit(
  identifier: string,
  limit: number,
  windowMs: number
): { allowed: boolean; remaining: number; resetTime: number } {
  const now = Date.now();
  const record = rateLimitMap.get(identifier);

  // No record or expired - allow and create new record
  if (!record || now > record.resetTime) {
    const resetTime = now + windowMs;
    rateLimitMap.set(identifier, { count: 1, resetTime });
    return { allowed: true, remaining: limit - 1, resetTime };
  }

  // Check if limit exceeded
  if (record.count >= limit) {
    return { allowed: false, remaining: 0, resetTime: record.resetTime };
  }

  // Increment count and allow
  record.count++;
  return { allowed: true, remaining: limit - record.count, resetTime: record.resetTime };
}

/**
 * Get client IP address from request.
 */
function getClientIp(request: NextRequest): string {
  // Try various headers in order of preference
  const forwarded = request.headers.get('x-forwarded-for');
  if (forwarded) {
    return forwarded.split(',')[0].trim();
  }

  const realIp = request.headers.get('x-real-ip');
  if (realIp) {
    return realIp;
  }

  // Fallback to 'unknown' if no IP found
  return 'unknown';
}

export function middleware(request: NextRequest) {
  const ip = getClientIp(request);
  const pathname = request.nextUrl.pathname;
  const method = request.method;

  // Rate limiting rules
  const rules: Array<{
    pattern: RegExp;
    method?: string;
    limit: number;
    windowMs: number;
    name: string;
  }> = [
    // Feedback endpoint - strictest limit (prevent spam)
    {
      pattern: /^\/api\/feedback$/,
      method: 'POST',
      limit: 5,
      windowMs: 60 * 1000, // 5 requests per minute
      name: 'feedback',
    },
    // Player search - prevent scraping
    {
      pattern: /^\/api\/players$/,
      limit: 30,
      windowMs: 60 * 1000, // 30 requests per minute
      name: 'search',
    },
    // Expensive scatter plot queries
    {
      pattern: /^\/api\/scatter$/,
      limit: 20,
      windowMs: 60 * 1000, // 20 requests per minute
      name: 'scatter',
    },
    // Rankings endpoint
    {
      pattern: /^\/api\/rankings$/,
      limit: 30,
      windowMs: 60 * 1000, // 30 requests per minute
      name: 'rankings',
    },
    // Similar players endpoint
    {
      pattern: /^\/api\/players\/.*\/similar$/,
      limit: 20,
      windowMs: 60 * 1000, // 20 requests per minute
      name: 'similar',
    },
    // General API rate limit (catch-all)
    {
      pattern: /^\/api\//,
      limit: 100,
      windowMs: 60 * 1000, // 100 requests per minute
      name: 'api',
    },
  ];

  // Check each rule
  for (const rule of rules) {
    if (rule.pattern.test(pathname)) {
      // Check method if specified
      if (rule.method && method !== rule.method) {
        continue;
      }

      // Create unique identifier for this IP + endpoint
      const identifier = `${ip}:${rule.name}`;
      const result = checkRateLimit(identifier, rule.limit, rule.windowMs);

      if (!result.allowed) {
        const retryAfter = Math.ceil((result.resetTime - Date.now()) / 1000);

        console.warn(
          `⚠️ Rate limit exceeded: ${ip} on ${pathname} (${rule.name})`
        );

        return NextResponse.json(
          {
            error: 'Too many requests',
            message: 'You have exceeded the rate limit. Please try again later.',
            retryAfter: retryAfter,
          },
          {
            status: 429,
            headers: {
              'Retry-After': retryAfter.toString(),
              'X-RateLimit-Limit': rule.limit.toString(),
              'X-RateLimit-Remaining': '0',
              'X-RateLimit-Reset': result.resetTime.toString(),
            },
          }
        );
      }

      // Add rate limit headers to successful responses
      const response = NextResponse.next();
      response.headers.set('X-RateLimit-Limit', rule.limit.toString());
      response.headers.set('X-RateLimit-Remaining', result.remaining.toString());
      response.headers.set('X-RateLimit-Reset', result.resetTime.toString());

      return response;
    }
  }

  // No rate limit rule matched - allow request
  return NextResponse.next();
}

// Configure which routes the middleware runs on
export const config = {
  matcher: [
    // Match all API routes
    '/api/:path*',
  ],
};
