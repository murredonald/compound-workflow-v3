# Security — Common Mistakes & Anti-Patterns

Common mistakes when running the security specialist. Each pattern
describes a failure mode that leads to poor security decisions.

**Referenced by:** `specialist_security.md`
> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. Threat Modeling

### SEC-AP-01: Checklist security
**Mistake:** Runs through OWASP Top 10 as a rote checklist (injection, broken auth, XSS...) without building a threat model specific to the project. A static blog and a fintech app do not share the same threat surface.
**Why:** LLM training data is saturated with OWASP-style checklists. The model defaults to the most common security framework rather than reasoning about the specific system's architecture, data flows, and trust boundaries.
**Example:**
```
SEC-04: Prevent SQL Injection
All database queries must use parameterized statements...

SEC-05: Prevent XSS
All user input must be sanitized before rendering...
```
(Identical output whether the project is a CLI tool with no web interface or a SaaS platform with user-generated content.)
**Instead:** Start by identifying assets (what data matters), entry points (where external input arrives), and trust boundaries (where privilege changes). Then assess which OWASP categories actually apply. A project with no database has no SQL injection risk. A project with no user-rendered content has no stored XSS risk.

### SEC-AP-02: Everything is critical
**Mistake:** Marks every finding as CRITICAL or HIGH severity. When every finding screams urgency, the team cannot prioritize and real critical issues get buried.
**Why:** LLMs lack calibration for real-world exploitability. The model knows that "XSS is dangerous" but cannot assess whether a specific XSS vector is exploitable given the application's CSP headers, cookie flags, and deployment context.
**Example:**
```
SEC-07: Missing CSRF Protection — Severity: CRITICAL
SEC-08: No Content-Security-Policy Header — Severity: CRITICAL
SEC-09: Session Cookie Missing SameSite Attribute — Severity: CRITICAL
SEC-10: Server Version Disclosed in Headers — Severity: CRITICAL
```
(Server version disclosure is informational at best, not critical.)
**Instead:** Use a consistent severity model: CRITICAL = actively exploitable with severe impact (data breach, account takeover). HIGH = exploitable but requires specific conditions. MEDIUM = defense-in-depth gap. LOW/INFO = best practice, no direct exploit path. Rate each finding against the project's actual exposure.

### SEC-AP-03: Generic threat model
**Mistake:** Produces a threat model that could apply to any web application. Assets listed as "user data" and "system availability." Threats listed as "unauthorized access" and "data breach." No specifics about THIS project's data, users, or architecture.
**Why:** LLMs generalize from patterns in training data. Without strong project-specific grounding, the model defaults to the most common threat model template it has seen.
**Example:**
```
## Threat Model
**Assets:** User accounts, personal data, system availability
**Threats:** Unauthorized access, data exfiltration, denial of service
**Mitigations:** Authentication, encryption, rate limiting
```
(This threat model applies to literally every web application ever built.)
**Instead:** Name specific assets ("tax return PDFs containing SSNs, W-2 data, bank routing numbers"), specific threats ("malicious document upload containing embedded scripts," "horizontal privilege escalation between taxpayer accounts"), and specific mitigations tied to the architecture ("S3 bucket policy restricting access to the processing Lambda's IAM role").

### SEC-AP-04: Ignoring the human element
**Mistake:** Focuses entirely on technical controls (encryption algorithms, auth protocols, input validation) while ignoring social engineering, credential reuse, insider threat, and operational security gaps.
**Why:** LLM training data overwhelmingly covers technical security controls. Social engineering and operational security are discussed in prose articles, not in code-adjacent documentation, so the model under-weights them.
**Example:**
```
## Security Decisions
SEC-01: Use bcrypt for password hashing
SEC-02: Implement OAuth 2.0 with PKCE
SEC-03: Enable TLS 1.3 for all connections
SEC-04: Use AES-256-GCM for encryption at rest
```
(No mention of: what happens when an admin's laptop is stolen, how support staff verify caller identity, or what the password reset flow looks like to a social engineer.)
**Instead:** Include operational security in the threat model: admin account recovery procedures, support staff verification protocols, what happens when credentials leak (rotation plan), monitoring for credential stuffing from breached databases, and security awareness for team members with production access.

---

## B. Scope & Proportionality

### SEC-AP-05: Enterprise security for MVP
**Mistake:** Recommends a full enterprise security stack — WAF, SIEM, IDS/IPS, HSM, dedicated security team, SOC 2 Type II audit — for a solo developer building an MVP with 50 beta users.
**Why:** LLMs cannot assess organizational capacity or budget. The model optimizes for "most secure" rather than "appropriately secure given constraints." Enterprise security content dominates training data because enterprises produce more documentation.
**Example:**
```
SEC-12: Deploy AWS WAF with managed rule groups
SEC-13: Implement centralized SIEM (Splunk/Elastic)
SEC-14: HSM-backed key management via AWS CloudHSM ($1.60/hr)
SEC-15: Schedule quarterly penetration testing
SEC-16: Achieve SOC 2 Type II certification before launch
```
(Total cost: ~$5,000/month before the app has revenue.)
**Instead:** Scale security to the project's phase. MVP: strong auth (managed provider like Auth0/Clerk), HTTPS everywhere, secrets in environment variables, basic logging, automated dependency scanning. Growth: add rate limiting, monitoring, incident response plan. Scale: WAF, SIEM, penetration testing, compliance audits.

### SEC-AP-06: Security theater
**Mistake:** Proposes controls that look impressive on paper but do not meaningfully reduce risk. The controls create a false sense of security while leaving actual attack vectors unaddressed.
**Why:** LLMs optimize for appearing thorough. Recommending more controls always "sounds more secure" even when those controls are ineffective or counterproductive in context.
**Example:**
```
SEC-18: Implement IP whitelisting for API access
```
(The API is a public REST API meant to be called from any user's browser. IP whitelisting would break the product.)
```
SEC-19: Enforce 16-character minimum passwords with uppercase,
        lowercase, number, special character, no dictionary words
```
(Users write these passwords on sticky notes. NIST 800-63B recommends length over complexity.)
**Instead:** Evaluate each proposed control against the actual threat it mitigates. Ask: "If we implement this, what specific attack does it prevent? Does preventing that attack matter for THIS project? Will users circumvent this control?" Prefer controls users naturally comply with.

### SEC-AP-07: "Never" when the answer is "depends"
**Mistake:** Issues absolute prohibitions — "never store PII locally," "always encrypt all data at rest," "never use symmetric encryption for user data" — without considering the threat model or use case.
**Why:** Absolute rules are easier to generate than nuanced guidance. LLMs produce confident, unconditional statements because hedged advice appears in training data less often than prescriptive advice.
**Example:**
```
SEC-21: NEVER store any user data in local storage.
         All data must be stored server-side with encryption at rest.
```
(The app is an offline-first note-taking tool. Local storage IS the feature. The threat model should address local storage security, not prohibit it.)
**Instead:** Frame security guidance as conditional: "If the data includes authentication tokens, do not use localStorage (use httpOnly cookies). If the data is user-generated content with no secrets, localStorage is acceptable with XSS prevention as the primary control."

### SEC-AP-08: Ignoring usability impact
**Mistake:** Requires MFA on every login, aggressive CAPTCHA on every form, 15-minute session timeouts, and re-authentication for every sensitive action — for a low-risk application where the consequence of unauthorized access is minimal.
**Why:** LLMs do not model user frustration. More security always scores higher in the model's training signal. The tradeoff between security and usability requires empathy that the model lacks.
**Example:**
```
SEC-23: Require MFA for all user accounts
SEC-24: Add CAPTCHA to login, registration, and password reset
SEC-25: Session timeout of 15 minutes with mandatory re-login
SEC-26: Re-authenticate before viewing any account settings
```
(The app is a recipe-sharing site. The most sensitive data is a user's email address.)
**Instead:** Match authentication friction to data sensitivity. Low-risk apps: optional MFA, long sessions, CAPTCHA only on registration. Medium-risk: MFA encouraged, moderate session length, step-up auth for sensitive actions. High-risk (financial, medical): mandatory MFA, shorter sessions, re-auth for sensitive operations.

---

## C. Implementation Guidance

### SEC-AP-09: JWT as session replacement
**Mistake:** Recommends JWT for session management as a drop-in replacement for server-side sessions, without addressing the fundamental problem: JWTs cannot be revoked without maintaining server-side state (a blacklist), which defeats the "stateless" benefit.
**Why:** JWT is heavily marketed in tutorials and blog posts as "the modern way to do auth." LLMs absorb this marketing language and reproduce it uncritically. The nuances of JWT revocation, token size, and algorithm confusion attacks appear in fewer training examples.
**Example:**
```
SEC-28: Use JWT for stateless session management
  - Store user ID and roles in JWT payload
  - Set 24-hour expiration
  - Sign with HS256

Benefits: No session store needed, horizontally scalable
```
(No mention of: what happens when a user changes their password, how to force-logout a compromised account, or that a 24-hour window means stolen tokens are valid for 24 hours.)
**Instead:** If you need revocation (password change, account compromise, admin logout), use server-side sessions or short-lived JWTs (5-15 min) with a refresh token stored in httpOnly cookies. Document the revocation strategy explicitly. If you genuinely need stateless auth (microservices, API gateway), document that revocation is not instant and define the acceptable window.

### SEC-AP-10: Secrets management without specifics
**Mistake:** Says "use a secrets manager" or "never hardcode secrets" without specifying which tool, how secrets are injected at runtime, how rotation works, or the incident response procedure when a secret leaks.
**Why:** "Use a secrets manager" is a common refrain in security documentation. The model reproduces the recommendation without the operational details because those details are project-specific and less common in training data.
**Example:**
```
SEC-30: Use a secrets manager for all sensitive configuration.
         Never commit secrets to version control.
```
(Which secrets manager? How do developers access secrets locally? How does CI/CD get secrets? What is the rotation schedule? What happens when a key leaks?)
**Instead:** Specify the tool (e.g., "AWS Secrets Manager" or "1Password CLI + `op run`" or "Doppler"). Define the access pattern: local dev uses `.env` (gitignored), CI/CD uses platform secrets (GitHub Actions secrets), production uses the secrets manager with IAM-based access. Define rotation: "API keys rotated every 90 days. Database credentials rotated via automated Lambda on a 30-day schedule. Leaked secrets: immediately rotate, audit access logs for the exposure window, notify affected users if their data was at risk."

### SEC-AP-11: Encryption buzzword soup
**Mistake:** Mentions "AES-256," "RSA-2048," "TLS 1.3," and "bcrypt" in the same paragraph without specifying what each protects, where each applies, and what threat each addresses. Treats encryption as a single monolithic concept.
**Why:** LLMs see these terms co-occur frequently in security documentation. The model learns that mentioning more encryption terms sounds more authoritative, but it does not distinguish between encryption at rest, in transit, at the application layer, and for password hashing.
**Example:**
```
SEC-32: Encrypt all data using AES-256 and RSA-2048.
         Use TLS for all connections. Hash passwords with bcrypt.
```
(AES-256 for what? Disk encryption? Database column encryption? File encryption? RSA-2048 for what? Key exchange? Digital signatures? These serve completely different purposes.)
**Instead:** Map each cryptographic control to a specific data flow: "Passwords: bcrypt with cost factor 12 (hashing, not encryption). Data in transit: TLS 1.3 enforced via HSTS (protects against network sniffing). Data at rest: AES-256 via cloud provider's managed encryption (protects against physical disk theft). Application-layer encryption: AES-256-GCM for tax documents stored in S3, with per-user KEKs derived from KMS (protects against unauthorized S3 access)."

### SEC-AP-12: Missing rate limiting specifics
**Mistake:** Says "add rate limiting" without defining per-endpoint limits, the response when limits are hit, how authenticated and anonymous users differ, or how the limits were determined.
**Why:** "Add rate limiting" is a universal recommendation that appears in nearly every security review. The model reproduces the recommendation without the implementation specifics because those vary per application.
**Example:**
```
SEC-34: Implement rate limiting on all API endpoints.
```
(What rate? Per user? Per IP? Per endpoint? What happens when the limit is hit — 429 with Retry-After? Silent drop? Temporary ban? How does the limit differ for login attempts vs data reads vs writes?)
**Instead:** Define rates per endpoint category: "Login/auth: 5 attempts per IP per 15 minutes, then 429 with 15-minute lockout. API reads (authenticated): 100 req/min per user. API writes: 20 req/min per user. Registration: 3 accounts per IP per hour. Password reset: 3 requests per email per hour. Response: HTTP 429 with `Retry-After` header. Implementation: Redis sliding window via `express-rate-limit` or equivalent."

### SEC-AP-13: CORS misconfiguration
**Mistake:** Either recommends `Access-Control-Allow-Origin: *` (too permissive, allows any site to make credentialed requests) or locks CORS to a single origin that breaks legitimate cross-origin needs (mobile app, staging environment, partner integrations).
**Why:** CORS configuration is counterintuitive. LLMs either reproduce the permissive wildcard from tutorials or the overly strict single-origin from security guides. The nuanced middle ground (dynamic origin validation against an allowlist) appears less frequently in training data.
**Example:**
```
# Too permissive
SEC-36: Set Access-Control-Allow-Origin: *

# Too strict
SEC-36: Set Access-Control-Allow-Origin: https://app.example.com
```
(The wildcard lets any website make requests. The single origin breaks the mobile app at `capacitor://localhost`, the staging site at `https://staging.example.com`, and the partner dashboard at `https://partner.example.com`.)
**Instead:** Define an allowlist of legitimate origins and validate dynamically: "CORS allowed origins: `https://app.example.com`, `https://staging.example.com`, `capacitor://localhost` (mobile). Origin validated on each request against the allowlist. `Access-Control-Allow-Credentials: true` only for allowlisted origins. Non-matching origins receive no CORS headers (browser blocks the request). Allowlist stored in environment config, not hardcoded."
