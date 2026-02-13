export const prerender = false;

import type { APIRoute } from "astro";

// --- Rate limiting: 30 req/min per IP ---
const rateMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT = 30;
const RATE_WINDOW_MS = 60 * 1000; // 1 minute

function getClientIP(request: Request): string {
  return (
    request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown"
  );
}

function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const entry = rateMap.get(ip);

  if (!entry || now > entry.resetAt) {
    rateMap.set(ip, { count: 1, resetAt: now + RATE_WINDOW_MS });
    return false;
  }

  entry.count++;
  return entry.count > RATE_LIMIT;
}

// --- Constants ---
const COUNTER_OFFSET = 211; // GEN-28: credible baseline offset

function json(body: Record<string, unknown>, status: number, headers?: Record<string, string>) {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      ...headers,
    },
  });
}

// --- GET handler ---
export const GET: APIRoute = async ({ request }) => {
  // Rate limiting
  const ip = getClientIP(request);
  if (isRateLimited(ip)) {
    return json({ success: false, error: "Too many requests" }, 429);
  }

  const BREVO_API_KEY = import.meta.env.BREVO_API_KEY;
  const BREVO_LIST_ID = import.meta.env.BREVO_LIST_ID || "2";

  const cacheHeaders = {
    "Cache-Control": "public, s-maxage=300, stale-while-revalidate=60",
  };

  try {
    const res = await fetch(
      `https://api.brevo.com/v3/contacts/lists/${BREVO_LIST_ID}`,
      {
        headers: {
          "api-key": BREVO_API_KEY,
          Accept: "application/json",
        },
      },
    );

    if (!res.ok) {
      console.error("Brevo counter API error:", res.status);
      // BACK-02: graceful fallback — return null count
      return json({ success: true, count: null }, 200, cacheHeaders);
    }

    const data = await res.json();
    const subscriberCount = typeof data.totalSubscribers === "number"
      ? data.totalSubscribers
      : 0;

    return json(
      { success: true, count: subscriberCount + COUNTER_OFFSET },
      200,
      cacheHeaders,
    );
  } catch (err) {
    console.error("Brevo counter fetch failed:", err);
    // Graceful fallback — null count, frontend hides counter
    return json({ success: true, count: null }, 200, cacheHeaders);
  }
};
