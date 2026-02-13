export const prerender = false;

import type { APIRoute } from "astro";

// --- Rate limiting (BACK-03) ---
// In-memory IP-based throttle. Resets on cold start (acceptable for edge function).
const rateMap = new Map<string, { count: number; resetAt: number }>();
const RATE_LIMIT = 5;
const RATE_WINDOW_MS = 15 * 60 * 1000; // 15 minutes per BACK-03

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

// --- Email validation ---
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function isValidEmail(email: string): boolean {
  return EMAIL_RE.test(email);
}

// --- JSON response helpers (BACK-01 envelope) ---
function json(body: Record<string, unknown>, status: number) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

// --- POST handler ---
export const POST: APIRoute = async ({ request }) => {
  // Parse body
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return json({ success: false, error: "Invalid request body" }, 400);
  }

  // Honeypot check (BACK-04): hidden field "website".
  // If filled → bot. Return 200 silently to avoid bot adaptation.
  if (body.website) {
    return json({ success: true }, 200);
  }

  // Email validation
  const email =
    typeof body.email === "string" ? body.email.trim() : "";
  if (!email || !isValidEmail(email)) {
    return json({ success: false, error: "Invalid email address" }, 400);
  }

  // Rate limiting (BACK-03): 5 per 15 min per IP
  const ip = getClientIP(request);
  if (isRateLimited(ip)) {
    return json({ success: false, error: "Too many requests" }, 429);
  }

  // --- Brevo contact creation (BACK-06: direct fetch, no SDK) ---
  const BREVO_API_KEY = import.meta.env.BREVO_API_KEY;
  const BREVO_LIST_ID = Number(import.meta.env.BREVO_LIST_ID) || 2;

  // UTM parameter forwarding (BACK-05)
  const utm_source = typeof body.utm_source === "string" ? body.utm_source : "";
  const utm_medium = typeof body.utm_medium === "string" ? body.utm_medium : "";
  const utm_campaign =
    typeof body.utm_campaign === "string" ? body.utm_campaign : "";

  try {
    const res = await fetch("https://api.brevo.com/v3/contacts", {
      method: "POST",
      headers: {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({
        email,
        listIds: [BREVO_LIST_ID],
        attributes: {
          ...(utm_source && { UTM_SOURCE: utm_source }),
          ...(utm_medium && { UTM_MEDIUM: utm_medium }),
          ...(utm_campaign && { UTM_CAMPAIGN: utm_campaign }),
        },
        updateEnabled: true,
      }),
    });

    if (!res.ok) {
      const brevoErr = await res.json().catch(() => null);
      // Duplicate contact is acceptable — treat as success
      if (brevoErr?.code === "duplicate_parameter") {
        return json({ success: true }, 200);
      }
      // Log server-side only, never expose to client (BACK-07)
      console.error("Brevo API error:", res.status, brevoErr);
      return json({ success: false, error: "Service temporarily unavailable" }, 502);
    }

    return json({ success: true }, 200);
  } catch (err) {
    // Network/timeout — log server-side, generic client error (BACK-07)
    console.error("Brevo fetch failed:", err);
    return json({ success: false, error: "Service temporarily unavailable" }, 502);
  }
};
