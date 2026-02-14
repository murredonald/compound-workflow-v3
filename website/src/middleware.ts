import { defineMiddleware } from "astro:middleware";

const PUBLIC_PATHS = ["/login", "/api/login"];

export const onRequest = defineMiddleware(async (context, next) => {
  const { pathname } = context.url;

  // Allow public paths
  if (PUBLIC_PATHS.some((p) => pathname === p || pathname === p + "/")) {
    return next();
  }

  // Allow static assets
  if (pathname.startsWith("/_astro/") || pathname.match(/\.(css|js|ico|png|jpg|jpeg|svg|webp|woff2?|ttf)$/)) {
    return next();
  }

  // Check auth cookie
  const authCookie = context.cookies.get("auryth_auth");
  if (authCookie?.value === "authenticated") {
    return next();
  }

  // Redirect to login
  return context.redirect("/login");
});
