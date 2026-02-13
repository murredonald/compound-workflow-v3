import { useState, type FormEvent } from "react";

type FormState = "idle" | "loading" | "success" | "error";

interface WaitlistFormProps {
  labels?: {
    emailLabel?: string;
    emailPlaceholder?: string;
    submit?: string;
    success?: string;
    consent?: string;
    privacyLinkText?: string;
    privacyHref?: string;
    errorInvalidEmail?: string;
    errorRateLimit?: string;
    errorGeneric?: string;
  };
  onSuccess?: () => void;
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function getUtmParams(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const params = new URLSearchParams(window.location.search);
  const utm: Record<string, string> = {};
  for (const key of ["utm_source", "utm_medium", "utm_campaign"]) {
    const val = params.get(key);
    if (val) utm[key] = val;
  }
  return utm;
}

export default function WaitlistForm({
  labels = {},
  onSuccess,
}: WaitlistFormProps) {
  const {
    emailLabel = "Email address",
    emailPlaceholder = "you@example.com",
    submit = "Join the waitlist",
    success = "You're on the list! We'll email you when a spot opens.",
    consent = "By joining you agree to receive updates about Auryth TX AI. Unsubscribe anytime.",
    privacyLinkText = "Privacy Policy",
    privacyHref = "/en/privacy/",
    errorInvalidEmail = "Please enter a valid email address.",
    errorRateLimit = "Too many attempts. Please try again in a few minutes.",
    errorGeneric = "Something went wrong. Please try again later.",
  } = labels;

  const [email, setEmail] = useState("");
  const [state, setState] = useState<FormState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();

    // Client-side validation
    const trimmed = email.trim();
    if (!trimmed || !EMAIL_RE.test(trimmed)) {
      setErrorMsg(errorInvalidEmail);
      setState("error");
      return;
    }

    setState("loading");
    setErrorMsg("");

    try {
      const res = await fetch("/api/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: trimmed,
          ...getUtmParams(),
        }),
      });

      const data = await res.json().catch(() => null);

      if (res.ok && data?.success) {
        setState("success");
        onSuccess?.();
        return;
      }

      // User-friendly error mapping
      if (res.status === 429) {
        setErrorMsg(errorRateLimit);
      } else if (res.status === 400) {
        setErrorMsg(errorInvalidEmail);
      } else {
        setErrorMsg(errorGeneric);
      }
      setState("error");
    } catch {
      setErrorMsg(errorGeneric);
      setState("error");
    }
  }

  // Success state replaces the form (UIX-04)
  if (state === "success") {
    return (
      <div role="status" className="rounded-lg border border-primary/30 bg-primary/5 p-6 text-center">
        <p className="text-body font-medium text-foreground">{success}</p>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} noValidate className="w-full max-w-md space-y-4">
      <div>
        <label htmlFor="waitlist-email" className="mb-1.5 block text-body-sm font-medium text-foreground">
          {emailLabel}
        </label>
        <input
          id="waitlist-email"
          type="email"
          name="email"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (state === "error") {
              setState("idle");
              setErrorMsg("");
            }
          }}
          placeholder={emailPlaceholder}
          required
          autoComplete="email"
          aria-describedby={errorMsg ? "waitlist-error" : undefined}
          aria-invalid={state === "error" ? "true" : undefined}
          className={`flex h-11 min-h-[44px] w-full rounded-lg border bg-background px-3 py-2 text-body text-foreground placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 ${
            state === "error" ? "border-destructive" : "border-input"
          }`}
          disabled={state === "loading"}
        />
        {state === "error" && errorMsg && (
          <p id="waitlist-error" role="alert" className="mt-1 text-body-sm text-destructive">
            {errorMsg}
          </p>
        )}
      </div>

      {/* Honeypot — BACK-04: hidden from users, catches bots */}
      <div aria-hidden="true" style={{ position: "absolute", left: "-9999px" }}>
        <label htmlFor="waitlist-website">Website</label>
        <input
          id="waitlist-website"
          type="text"
          name="website"
          tabIndex={-1}
          autoComplete="off"
        />
      </div>

      <button
        type="submit"
        disabled={state === "loading"}
        className="inline-flex h-11 min-h-[44px] w-full items-center justify-center gap-2 rounded-lg bg-primary px-5 py-2 text-body-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50"
      >
        {state === "loading" ? (
          <span className="inline-flex items-center gap-2">
            <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            {submit}
          </span>
        ) : (
          submit
        )}
      </button>

      {/* Consent text — LEGAL-07 */}
      <p className="text-center text-body-xs text-muted-foreground">
        {consent}{" "}
        <a href={privacyHref} className="underline decoration-dotted underline-offset-2 hover:decoration-solid">
          {privacyLinkText}
        </a>
      </p>
    </form>
  );
}
