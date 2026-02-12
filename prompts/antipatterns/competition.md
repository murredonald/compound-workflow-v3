# Competition — Common Mistakes & Anti-Patterns

Common mistakes when running the competition specialist. Each pattern
describes a failure mode that leads to poor competitive analysis.

**Referenced by:** `specialist_competition.md`
> These patterns are **illustrative, not exhaustive**. They are a starting
> point — identify additional project-specific anti-patterns as you work.
> When a listed pattern doesn't apply to the current project, skip it.

---

## A. Research

### COMP-AP-01: Marketing Page Analysis
**Mistake:** Reads competitor feature pages and takes marketing claims at face value. Reports "AI-powered analytics" as a confirmed capability when the reality may be a basic chart with a filter dropdown.
**Why:** LLMs are trained on web content that is disproportionately marketing material. The model lacks the ability to verify product claims against actual user experience. It reads "enterprise-grade security" and records it as a feature rather than recognizing it as a marketing phrase that could mean anything from SOC 2 compliance to a login page.
**Example:**
```
COMP-03: Competitor Feature — Acme Analytics
- AI-powered insights (automatically surfaces trends)
- Enterprise-grade security (bank-level encryption)
- Seamless integrations (connects with 500+ tools)
- Real-time collaboration (work together instantly)
```
**Instead:** Verify claims against evidence. Check user reviews on G2/Capterra for actual feature descriptions. Look at the competitor's API docs and changelog — if "AI-powered insights" shipped 2 years ago and hasn't been updated, it's likely a basic feature with an AI label. Check their pricing page — if "500+ integrations" requires the enterprise tier, that's a gated feature, not a baseline capability. Record: "Claims AI insights; G2 reviews describe it as 'automated chart suggestions based on column types' — essentially pre-built chart templates, not ML-driven analysis."

### COMP-AP-02: Ignoring Indirect Competitors
**Mistake:** Only analyzes direct software competitors — other SaaS products in the same category. Misses that the real competition is often Excel spreadsheets, manual processes, email chains, or hiring a person to do the job.
**Why:** The model interprets "competitive analysis" as "compare similar software products." Training data about competition focuses on product-vs-product comparisons. Non-software alternatives are rarely discussed in competitor analysis frameworks, so the model doesn't consider them. Yet for most B2B SaaS products, the biggest competitor is "do nothing" or "use a spreadsheet."
**Example:**
```
## Competitive Landscape
1. Acme Scheduling — web-based, $49/mo
2. BookEasy — web-based, $39/mo
3. CalendarPro — web-based, $29/mo
4. ScheduleIt — web-based, $59/mo
```
**Instead:** Include the full competitive landscape: (1) Direct software competitors (Acme, BookEasy). (2) Adjacent tools being misused for this job (Google Calendar shared among staff, a shared Excel workbook on Dropbox). (3) Manual processes (phone-based booking with a paper appointment book — still common in small medical practices, salons, and trades). (4) Outsourced solutions (hiring a part-time receptionist at $18/hr). Each alternative has switching costs and the user must see MORE value than their current solution to switch.

### COMP-AP-03: Stale Competitive Data
**Mistake:** Uses information from training data that may be 1-2 years old. Competitor landscapes change rapidly — features ship, products pivot, companies shut down, pricing changes.
**Why:** The model's knowledge has a training data cutoff. It can describe competitors as they existed at training time but cannot verify current state. It presents this stale data with the same confidence as fresh information, creating a false sense of accuracy.
**Example:**
```
COMP-02: Competitor Pricing Analysis
Acme Pro: $49/month (starter), $99/month (business), $249/month (enterprise)
Based on this, we should price our starter tier at $39/month to undercut.
```
**Instead:** Flag all competitive data with a freshness caveat. Use the research-scout agent or web search to verify current pricing, feature sets, and company status. Note: "Pricing as of [date]. Acme raised prices by 30% in Q3 2025 per their blog announcement — previous $49 starter is now $65. They also removed the free tier that existed until 2024." Stale data leads to mispricing and strategic errors.

### COMP-AP-04: Top-3 Only Analysis
**Mistake:** Analyzes only the 3 most obvious, largest competitors. Misses the emerging #5 competitor or the startup launched 6 months ago that is growing 20% month-over-month and will be the real threat by launch time.
**Why:** The model has the most training data about market leaders. Smaller competitors have less web presence, fewer blog posts, and fewer reviews — so the model either doesn't know about them or treats them as insignificant. But market leaders are often the LEAST relevant competitors for a new entrant; the startup in the same weight class is the real threat.
**Example:**
```
## Competitors Analyzed
1. Salesforce (market leader, $200B company)
2. HubSpot (major player, $30B company)
3. Pipedrive (established challenger, $1.5B valuation)

Conclusion: The CRM market is dominated by large players with massive feature sets.
Our differentiation must be...
```
**Instead:** Segment competitors by relevance to YOUR product: (1) Direct competitors at similar stage/scale (other startups targeting the same niche — these are the real threat). (2) Established players whose specific feature overlaps with your product (not their entire platform). (3) Emerging alternatives (new tools, open-source projects, AI-native approaches that didn't exist 2 years ago). Analyzing Salesforce when you're building a niche CRM for real estate agents is a waste — analyze the 3 tools real estate agents actually use today.

---

## B. Analysis

### COMP-AP-05: Feature Parity as Strategy
**Mistake:** Recommends matching every competitor feature as the path to competitiveness. This creates a race to the bottom where you are always one release behind and never differentiated.
**Why:** Feature matrices are easy to construct and provide a false sense of rigor. The model sees gaps in the matrix and flags them as deficiencies to fix, without considering whether filling every gap is strategically sound. Training data is full of "gap analysis" frameworks that treat missing features as problems to solve.
**Example:**
```
## Feature Gap Analysis
| Feature | Us | Acme | BookEasy |
|---------|-----|------|----------|
| Calendar sync | Yes | Yes | Yes |
| SMS reminders | No | Yes | Yes |
| Group booking | No | Yes | No |
| Waitlist | No | No | Yes |
| AI scheduling | No | No | No |

Recommendation: Implement SMS reminders and group booking to reach
feature parity with Acme. Add waitlist to match BookEasy.
```
**Instead:** Distinguish between table-stakes features (user EXPECTS them — will churn without them) and differentiators (user CHOOSES you because of them). SMS reminders may be table-stakes; group booking may matter only for specific use cases. Recommend: "Match table-stakes only. Differentiate on [specific capability] that no competitor does well. Deprioritize group booking — only 12% of competitor reviews mention it, and it adds significant scheduling complexity."

### COMP-AP-06: Classification Without Evidence
**Mistake:** Marks features as "table-stakes," "differentiator," or "nice-to-have" based on intuition rather than evidence. Table-stakes means EVERY competitor has it AND users expect it — both conditions must be verified.
**Why:** The model applies labels based on how the feature sounds. "Search" sounds table-stakes. "AI-powered recommendations" sounds like a differentiator. But in some markets, AI features ARE table-stakes (e.g., email clients), and in others, basic features are missing across all competitors (nobody has good reporting in that niche). Labels need evidence, not vibes.
**Example:**
```
COMP-05: Feature Classification
Table-stakes: user auth, dashboard, reports, search, notifications
Differentiator: AI features, integrations, mobile app
Nice-to-have: dark mode, custom branding, API access
```
**Instead:** Back each classification with data: "Reports — classified as table-stakes. Evidence: 4/5 competitors offer reporting. 73% of G2 reviews for category mention reporting as expected. 3 of top 5 negative reviews for reportless competitor cite missing reports as reason for churning." And: "API access — classified as differentiator, not nice-to-have. Evidence: only 2/5 competitors offer API. But 8/10 enterprise prospects in our interview pipeline asked about API access. This is table-stakes for our target segment even though most competitors lack it."

### COMP-AP-07: Missing Usage Data
**Mistake:** Lists competitor features without considering which features users actually use. Feature lists are marketing artifacts — usage data tells the truth about what matters.
**Why:** Feature lists are publicly visible on competitor websites. Usage data is private and requires indirect inference from reviews, support forums, and user interviews. The model defaults to what's easy to find (feature pages) rather than what's informative (usage patterns). A competitor may list 200 features, but users may care about 15 of them.
**Example:**
```
COMP-06: Acme Feature Count
Acme offers 47 features across 8 categories. Our v1 should target
at least 25 features to be competitive.
```
**Instead:** Analyze which features users actually discuss. Mine review sites: "Of Acme's 47 listed features, G2 reviews mention only 12 by name. The top 5 by mention frequency: calendar sync (89%), email reminders (76%), client self-booking (71%), payment collection (54%), reporting (41%). 35 features are never mentioned in any review — these are either unused or undifferentiated. Target the top 5 user-valued features, not a feature count."

### COMP-AP-08: No Positioning Analysis
**Mistake:** Enumerates features without analyzing WHY competitors made those choices. Feature decisions reflect strategic positioning, target audience, and business model — understanding the reasoning matters more than the list.
**Why:** The model treats features as independent facts rather than expressions of a coherent strategy. It lists what competitors have without explaining the strategic logic. But knowing that Competitor A targets enterprise (hence SOC 2, SSO, audit logs) while Competitor B targets freelancers (hence simplicity, fast onboarding, low price) changes everything about which features to compare.
**Example:**
```
COMP-07: Competitor Features Comparison
Both Acme and BookEasy offer SSO, audit logs, and role-based access.
We should include these features in v1.
```
**Instead:** Analyze the positioning behind the features: "Acme targets mid-market teams (50-200 employees) — their SSO, audit logs, and role-based access serve enterprise procurement requirements, not end-user needs. BookEasy targets solo practitioners — they added SSO only after losing enterprise deals, and their implementation is basic (Google SSO only). Our target is small teams (5-20 people). SSO is not table-stakes for this segment — Google/email login is sufficient for v1. Invest in features that matter to small teams: simple onboarding, shared calendars, and team scheduling."

### COMP-AP-09: Moat Confusion
**Mistake:** Lists features as competitive moats. Real moats are structural advantages that are hard to replicate — network effects, switching costs, proprietary data, regulatory barriers, brand recognition, and economies of scale. Features are copied in weeks.
**Why:** The model conflates "competitive advantage" with "moat" because business articles use these terms loosely. A feature advantage is temporary — any competitor can copy a feature in their next release. A moat is durable. The model doesn't distinguish between "we have a better search" (feature, copyable) and "we have 5 years of user behavior data that makes our search better" (data moat, durable).
**Example:**
```
COMP-08: Our Competitive Moat
Our moat will be built on:
- Superior UI/UX design
- AI-powered scheduling optimization
- Comprehensive API
```
**Instead:** Separate moats from advantages: "Advantages (defensible for 6-12 months): better UX, AI scheduling, comprehensive API. These can and will be copied. Potential moats (defensible for 3-5 years): (1) Network effects — if we build a marketplace where providers and clients find each other, each new user makes the platform more valuable. (2) Data moat — after 12 months of scheduling data, our AI predictions become more accurate than any new entrant can match. (3) Integration switching costs — once 50 tools integrate with our API, users can't easily leave." Plan which moats to BUILD, not which features to ship.

---

## C. Recommendations

### COMP-AP-10: Everything Is v1
**Mistake:** Recommends including 15 "must-have" features in v1 when constraints say 4-week timeline and 1-2 developers. Fails to make the hard cuts that define an MVP.
**Why:** The model is trained on comprehensive feature analyses and has difficulty marking anything as "not yet." Every feature seems important when analyzed in isolation. The competitive pressure framing ("competitors have this, we need it too") creates urgency for every feature. The model doesn't internalize timeline and resource constraints as hard limits.
**Example:**
```
COMP-09: v1 Feature Recommendations
Must-have for v1:
1. Calendar sync (Google, Outlook, Apple)
2. Email + SMS reminders
3. Online booking page
4. Payment collection (Stripe)
5. Client management (CRM-lite)
6. Reporting dashboard
7. Team scheduling
8. Waitlist management
9. Custom branding
10. Mobile app
11. Multi-language support
12. API for integrations
```
**Instead:** Given the 4-week constraint: "v1 core (week 1-3): online booking page, calendar sync (Google only), email reminders. v1 polish (week 4): client list, basic settings. v1.1 (post-launch, based on user feedback): SMS reminders, payment collection, reporting. Deferred: team scheduling, waitlist, mobile app, API. Rationale: a single booking flow that works flawlessly beats 12 half-built features. Calendar sync with Google covers 65% of the target market. SMS and payment add cost/complexity but aren't required for initial validation."

### COMP-AP-11: Adding Without Cutting
**Mistake:** Recommends adding features from the competitive analysis but never recommends removing or deprioritizing existing planned features. Feature additions must be balanced by scope cuts.
**Why:** The model treats the existing plan and the competitive recommendations as independent streams. It doesn't have a sense of "budget" for scope — adding a feature doesn't trigger awareness that something else must be cut. Each recommendation is generated in isolation without referencing the cumulative scope impact.
**Example:**
```
COMP-10: Competitive Additions
Based on competitive analysis, add the following to the plan:
- Waitlist management (BookEasy has this)
- Group booking (Acme has this)
- Recurring appointments (both have this)

These additions will strengthen our competitive position.
```
**Instead:** Every addition must name what it displaces: "Add recurring appointments (estimated 3 days). This requires cutting custom branding from v1 (estimated 2 days) and simplifying the reporting dashboard to summary-only (saves 1 day). Justification: 62% of competitor reviews mention recurring appointments as a key workflow. Custom branding is mentioned in 4% of reviews — it's a nice-to-have, not a driver." Force a zero-sum conversation: scope in = scope out.

### COMP-AP-12: Differentiator Without Validation
**Mistake:** Proposes "unique" features that no competitor offers without evidence that users actually want them. A feature no competitor has might mean the market doesn't need it.
**Why:** The model is trained on startup advice that emphasizes differentiation ("find your unique value proposition"). This creates a bias toward novelty — if no competitor has it, it must be a blue ocean opportunity. But the absence of a feature across all competitors can equally mean that customers don't value it, the economics don't work, or previous attempts failed and were removed.
**Example:**
```
COMP-11: Unique Differentiator
No competitor offers AI-powered "mood-based scheduling" that adjusts
appointment types based on client sentiment analysis. This could be
our breakthrough feature.
```
**Instead:** Validate the differentiator against user demand: "Proposed differentiator: automated schedule optimization (suggests optimal time slots based on provider productivity patterns). Validation: (1) 23% of negative reviews for Acme mention 'wasted gaps between appointments' — there's a real pain point. (2) CalendarPro attempted this in 2023 and removed it after 6 months — research why (too complex? poor accuracy? users didn't trust it?). (3) Requires 3+ months of historical data to be useful — how do new users get value? Recommendation: validate with 5 user interviews before committing to this as a v1 differentiator."

### COMP-AP-13: Free Tier Pressure
**Mistake:** Sees a competitor's free tier and immediately recommends matching it without modeling the economics. Free tiers need 95%+ non-paying users subsidized by 2-5% conversion to paid. Not every business model supports this.
**Why:** Free tiers are highly visible in competitor analysis because they're featured prominently on pricing pages. The model treats "competitor has a free tier" as a competitive threat requiring a response. It doesn't model the unit economics: if serving each free user costs $2/month and only 3% convert to a $30/month plan, you need the average free user to stay for 22 months before converting — most don't.
**Example:**
```
COMP-12: Pricing Response
Acme and BookEasy both offer free tiers (up to 5 appointments/month).
We must offer a comparable free tier to remain competitive. Otherwise,
users will try competitors first and never evaluate our product.
```
**Instead:** Model the economics before matching: "Acme's free tier: up to 5 appointments/month. Estimated cost per free user: $0.50/month (email sends, storage, compute). Acme's reported conversion rate (from their investor deck): 4.2%. At $49/month paid tier, LTV of converted user: $588 (12-month avg retention). CAC via free tier: $0.50 x 24 months / 4.2% = $285. This works for Acme at scale. For us at launch: we can't afford 1000 free users ($500/month) waiting for 42 conversions. Alternative: 14-day free trial (no permanent free tier) — gets users to evaluate without ongoing cost. Revisit free tier at 500+ paying customers when unit economics support it."
