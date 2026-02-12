# Branding — Common Mistakes & Anti-Patterns

Common mistakes when running the branding specialist. Each pattern
describes a failure mode that leads to poor brand identity decisions.

**Referenced by:** `specialist_branding.md`
> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. Naming & Identity

### BRAND-AP-01: Name Without Availability Check
**Mistake:** Proposes a brilliant product name without checking domain availability, trademark conflicts, or social handle availability. A name that can't be secured online is unusable regardless of how good it sounds.
**Why:** The model generates names based on linguistic qualities (memorable, pronounceable, evocative) without access to real-time availability databases. It optimizes for the name itself rather than the full acquisition cost. In training data, name brainstorming articles focus on creativity, not on the practical reality that 90% of good .com domains are taken.
**Example:**
```
BRAND-01: Product Name
Recommended name: "Lumina"
- Evokes light, clarity, and insight
- Short, memorable, easy to spell
- Works across languages
- Strong brand potential
```
**Instead:** Propose names in batches with availability pre-filtering: "Name candidates (domain + social checked via research-scout): (1) 'CalSync' — calsync.com available ($12), @calsync available on X/GitHub. (2) 'Slotwise' — slotwise.com available ($15), @slotwise taken on X (inactive since 2019, recoverable). (3) 'Lumina' — lumina.com taken ($45,000 aftermarket), luminaapp.com available ($12), @lumina taken on all platforms. Recommendation: CalSync or Slotwise for acquisition simplicity. Lumina only if budget allows domain purchase and you're willing to use luminaapp.com during negotiation."

### BRAND-AP-02: Clever Over Clear
**Mistake:** Picks a witty, abstract, or invented name that requires explanation. Users can't spell it, can't search for it, and can't tell their colleagues about it without a follow-up explanation.
**Why:** LLMs are biased toward creative, distinctive outputs because creative naming gets more attention in training data (blog posts about clever startup names, brand identity case studies). Straightforward descriptive names are underrepresented because nobody writes articles about how "Booking.com" is a great name — but its directness is precisely why it works.
**Example:**
```
BRAND-02: Product Name
Recommended name: "Kronexia"
- Derived from Greek "kronos" (time) + Latin "nexus" (connection)
- Unique, no existing trademarks
- Sounds sophisticated and technical
```
**Instead:** Evaluate names on the "phone test": can someone hear the name once, spell it correctly, and find it on Google? "Kronexia" fails all three — users will search "cronexia," "kronexia," "chronexia." Compare with: "TimeBook" (clear what it does), "Bookly" (friendly, spellable), or "SlotPick" (descriptive, memorable). For B2B products especially, clarity beats cleverness. Save the creative naming for consumer brands with massive marketing budgets to build name recognition.

### BRAND-AP-03: Too Many Brand Values
**Mistake:** Defines 8+ brand values that collectively describe every positive attribute. When everything is a value, nothing is. Brand values must create real constraints on behavior — if the opposite is unthinkable, it's not a differentiating value.
**Why:** The model generates comprehensive lists because exclusion feels like a loss. Every positive attribute (innovative, trustworthy, playful, professional, bold, approachable, modern, reliable) seems worth including. But brand values work through constraint — choosing "playful" means NOT choosing "formal," and that choice should visibly affect copy, design, and product decisions.
**Example:**
```
BRAND-03: Brand Values
1. Innovative — we push boundaries
2. Trustworthy — users can rely on us
3. Approachable — friendly and welcoming
4. Professional — serious about quality
5. Bold — we take risks
6. Empathetic — we understand users
7. Transparent — honest communication
8. Modern — cutting-edge technology
```
**Instead:** Pick 3-4 values where the OPPOSITE is a valid choice another brand might make. Test: "Playful vs. Serious" — both are valid positions, so "playful" is a real brand choice. "Trustworthy vs. Untrustworthy" — no brand chooses untrustworthy, so this isn't differentiating. Better: "(1) Playful — we use humor and lightness even in business tools (opposite: serious/formal — Salesforce's approach). (2) Opinionated — we make decisions for you rather than offering 50 settings (opposite: flexible/customizable — Notion's approach). (3) Transparent — we show our pricing, roadmap, and mistakes publicly (opposite: controlled messaging — Apple's approach)."

### BRAND-AP-04: Generic Positioning
**Mistake:** Positions the product as "simple, modern, and intuitive" — which describes every SaaS product launched since 2015. Positioning must name WHAT is specifically different and FOR WHOM, creating a real reason to choose this product over alternatives.
**Why:** Generic positive adjectives are the safest output for the model. "Simple and intuitive" is never wrong, never controversial, and appears in thousands of SaaS landing pages in training data. Specific positioning requires understanding the competitive landscape, user segments, and making exclusionary choices (targeting X means NOT targeting Y), which the model avoids.
**Example:**
```
BRAND-04: Brand Positioning
[Product] is the simple, modern, and intuitive scheduling solution
for businesses of all sizes. We make scheduling easy so you can
focus on what matters.
```
**Instead:** Use a positioning formula that forces specificity: "For [specific audience] who [specific problem], [product] is the [category] that [specific differentiator] unlike [named alternative] which [specific limitation]." Example: "For solo therapists who lose 3+ hours/week managing their calendar across multiple tools, SlotPick is the scheduling tool that auto-syncs with insurance verification systems, unlike Calendly which treats all appointments as equal and doesn't understand session types, insurance codes, or no-show policies." This positioning excludes large clinics, non-healthcare users, and generic scheduling — and that exclusion is the point.

---

## B. Voice & Messaging

### BRAND-AP-05: Brand Voice Without Examples
**Mistake:** Defines voice as "friendly but professional" without concrete writing examples showing what that sounds like in actual product contexts — error messages, empty states, onboarding steps, CTAs, and email subject lines.
**Why:** Voice descriptions are abstract by nature, and the model produces them at the abstract level found in brand guideline templates. "Friendly but professional" is a spectrum, not a point — it could mean anything from Slack's casual tone to a bank's polite formality. Without examples, every developer interprets it differently.
**Example:**
```
BRAND-05: Brand Voice
Tone: Friendly but professional
We communicate with warmth while maintaining credibility.
Our voice is approachable yet authoritative.
```
**Instead:** Define voice through paired DO/DON'T examples across 5+ product contexts:
```
Error message:
  DO: "That time slot was just booked. Here are 3 similar openings."
  DON'T: "Error: Slot unavailable. Please select another time."
  DON'T: "Oopsie! Someone snagged that slot! Try another? :)"

Empty state:
  DO: "No appointments this week. Your clients can book at [link]."
  DON'T: "No data found."
  DON'T: "Looks like you've got a free week! Time to hit the beach! 🏖️"

Payment failure:
  DO: "Your payment didn't go through. Update your card to keep your account active."
  DON'T: "PAYMENT FAILED. Account will be suspended."
  DON'T: "Uh oh, your card got declined! No worries though!"
```

### BRAND-AP-06: Inconsistent Voice Guidance
**Mistake:** Voice guide says "casual and fun" but the provided example copy reads like a legal document. Or the guide says "professional" but examples use slang and emoji. The description and examples must match.
**Why:** The model generates the voice description and examples in separate steps without cross-checking consistency. The description is written first from brand positioning, then examples are generated from the model's default patterns (which tend toward formal, complete sentences). The model doesn't re-read its own description before generating examples.
**Example:**
```
BRAND-06: Voice Guidelines
Our voice is casual, fun, and energetic! We talk to users like friends.

Example onboarding message:
"Welcome to the platform. To begin, please complete your profile
information by navigating to Settings > Profile. Required fields
include your full name, email address, and professional credentials."
```
**Instead:** Write the description AFTER writing the examples. Start with 10 example messages across different contexts (success, error, onboarding, upgrade prompt, cancellation). Then derive the voice description from the patterns you see: "Voice: direct, warm, action-oriented. We use short sentences (under 15 words). We use 'you/your' not 'the user.' We name the next action, not the problem. Contractions always. Emoji never. Exclamation marks: max 1 per screen." The description becomes a testable checklist, not a mood board.

### BRAND-AP-07: Ignoring Stressful Moments
**Mistake:** Brand voice defined for happy paths (welcome screens, success messages, marketing copy) but not for stressful moments — payment failures, account suspensions, data loss warnings, security alerts. Voice matters MOST when users are anxious or frustrated.
**Why:** Brand voice guides in training data focus on marketing and onboarding contexts because those are what brand agencies typically produce. Product-specific stress moments (your card was declined, your account will be deleted in 7 days, we detected a login from a new device) are rarely covered in brand guidelines. The model follows this pattern.
**Example:**
```
BRAND-07: Voice Examples
Welcome: "Hey there! Ready to get started? Let's set up your first booking!"
Success: "Awesome! Your appointment is confirmed. See you Tuesday!"
Feature tip: "Pro tip: Turn on reminders so clients never forget."
```
**Instead:** Cover the full emotional spectrum with explicit guidance for negative states:
```
Payment failed: "Your payment didn't go through. Update your card by [date]
  to avoid any interruption." (calm, specific deadline, no blame)
Account deletion: "This will permanently delete your account and all
  appointment history. This cannot be undone." (direct, no softening,
  gravity must match consequence)
Security alert: "Someone logged into your account from [location]. If this
  wasn't you, change your password now." (urgent, factual, clear action)
Data export: "We're preparing your data export. This usually takes 5-10
  minutes. We'll email you when it's ready." (reassuring, specific timeline)
```

---

## C. Visual Identity

### BRAND-AP-08: Color Psychology as Universal
**Mistake:** Recommends brand colors based on Western color psychology generalizations ("blue means trust," "green means growth") as if these associations are universal truths. Color meanings are culturally dependent and category-specific.
**Why:** Color psychology articles are abundant in training data and present cultural associations as scientific facts. "Blue conveys trust — that's why banks use it" is repeated so often that the model treats it as a design principle. In reality, banks use blue because other banks use blue (category convention), and color associations vary significantly across cultures, age groups, and contexts.
**Example:**
```
BRAND-08: Brand Colors
Primary: Blue (#2563EB) — conveys trust, reliability, and professionalism
Secondary: Green (#16A34A) — represents growth, success, and harmony
Accent: Orange (#EA580C) — communicates energy, enthusiasm, and warmth
```
**Instead:** Choose colors based on: (1) Category differentiation — if every competitor uses blue, use something else to stand out on comparison pages and app store listings. (2) Functional needs — does the product need strong semantic colors for status indicators (success/error/warning)? If so, avoid using green/red/yellow as brand colors since they'll conflict. (3) Accessibility — ensure the primary color meets contrast requirements on both white and dark backgrounds. (4) Practical testing — "How does this look as a favicon? As a mobile app icon next to Instagram and Slack? On a Google search result?" Present 2-3 palette options with mockups, not psychology justifications.

### BRAND-AP-09: Logo Requirements Too Early
**Mistake:** Spends significant time on logo design details (symbol style, icon complexity, wordmark vs. lettermark) during the planning phase when no product exists yet. Logo refinement should happen AFTER brand positioning and voice are validated with real users.
**Why:** Logos are the most visible and tangible output of branding, so the model (and users) gravitate toward them. Training data about branding disproportionately covers logo design because it's visual and shareable. But a logo doesn't help you build a product — positioning, voice, and naming directly affect product decisions, while the logo can be a simple wordmark until post-launch.
**Example:**
```
BRAND-09: Logo Design
The logo should feature an abstract mark representing connected time blocks,
rendered in the primary blue with a gradient effect. The wordmark uses a
custom-modified geometric sans-serif font with rounded terminals. The icon
should work at 16x16px for favicons while maintaining recognizable detail
at billboard scale.
```
**Instead:** For the planning phase, define only what's needed for development: (1) A wordmark in the brand font (sufficient for header, favicon as first letter, email signatures). (2) A simple geometric icon for app icon / favicon (circle, square, or simple shape in brand color). (3) Placeholder specifications: "Logo area in header is 140x40px. Favicon is first letter of name in brand color on white. Full logo design deferred to post-MVP brand sprint." This unblocks development without burning planning time on details that will change after user feedback.

### BRAND-AP-10: Design System Conflation
**Mistake:** Mixes brand identity decisions (positioning, voice, values, personality) with design system decisions (component library, design tokens, interaction patterns). These are related but serve different purposes and are consumed by different people.
**Why:** "Branding" in training data spans everything from strategic positioning to button border radius. The model doesn't maintain a clear boundary between "brand guidelines" (a marketing/strategy document) and "design system" (a development reference). This leads to a brand guide that includes CSS variables, or a design system that includes mission statements.
**Example:**
```
BRAND-10: Brand Guidelines
Mission: Simplify scheduling for small businesses.
Values: Clarity, Speed, Warmth.
Primary color: #2563EB (--color-primary in CSS).
Button border-radius: 8px (--radius-md).
Font: Inter, loaded via Google Fonts CDN.
Card shadow: 0 1px 3px rgba(0,0,0,0.1).
Voice: Friendly but professional.
Tagline: "Scheduling, simplified."
```
**Instead:** Separate the outputs: Brand guide (consumed by marketing, content writers, product managers) contains: positioning statement, brand values, voice guidelines with examples, name and tagline, color palette (as human-readable swatches), typography direction (serif vs. sans-serif, formal vs. friendly). Design system / style guide (consumed by developers, created by the design specialist) contains: design tokens (CSS variables), component specifications, spacing scale, responsive breakpoints, interaction states. The branding specialist produces the first; the design specialist translates it into the second.

### BRAND-AP-11: No Brand Application Examples
**Mistake:** Defines brand guidelines in abstract (colors, fonts, voice adjectives) but doesn't show how they apply to actual product surfaces — login screen, onboarding flow, error page, marketing email, app store listing.
**Why:** Brand guideline templates in training data focus on the "identity system" level — logos, colors, typography, and voice. They rarely include product-specific application because traditional brand agencies produce guidelines for print and marketing, not for SaaS product UI. The model follows the template format rather than adapting to product-brand needs.
**Example:**
```
BRAND-11: Brand Application
The brand should be consistently applied across all touchpoints.
Use the primary color for key actions. Maintain the brand voice
in all communications. Ensure the logo is displayed per the
spacing guidelines.
```
**Instead:** Show the brand applied to 5 key product surfaces with specific guidance:
```
Login screen: White background, centered card, logo wordmark at top
  (32px height), primary color on "Sign in" button, voice example:
  "Welcome back" (not "Please authenticate").

Onboarding: Step indicator in primary color, one question per screen,
  voice: direct questions ("What's your business name?"), not
  instructions ("Please enter your business name in the field below").

Error page (404): Illustration in brand secondary color, headline
  in voice ("This page doesn't exist" not "404 Not Found"), primary
  CTA: "Go to dashboard."

Transactional email: Plain text preferred (higher deliverability),
  from name is product name (not "noreply"), subject line in voice
  ("Your Tuesday appointments" not "Appointment Notification Alert").
```
