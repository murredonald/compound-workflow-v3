export const prerender = false;

import type { APIRoute } from "astro";

const VALID_USER = "schwyz";
const VALID_PASS = "money";

export const POST: APIRoute = async ({ request, cookies, redirect }) => {
  let body: Record<string, unknown>;
  try {
    body = await request.json();
  } catch {
    return new Response(JSON.stringify({ error: "Invalid request" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  const username = typeof body.username === "string" ? body.username.trim() : "";
  const password = typeof body.password === "string" ? body.password : "";

  if (username === VALID_USER && password === VALID_PASS) {
    cookies.set("auryth_auth", "authenticated", {
      path: "/",
      httpOnly: true,
      secure: true,
      sameSite: "lax",
      maxAge: 60 * 60 * 24 * 30, // 30 days
    });
    return new Response(JSON.stringify({ success: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  }

  return new Response(JSON.stringify({ error: "Invalid credentials" }), {
    status: 401,
    headers: { "Content-Type": "application/json" },
  });
};
